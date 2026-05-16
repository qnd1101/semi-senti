"""한국어 형태소 분석 wrapper (T-014, T-016).

> "KoNLPy 라이브러리로 뉴스 본문·헤드라인에서 명사·형용사 추출"
>  — PRD §F-2.1 / Tasks T-016

설계
----
- ``KoNLPy`` 가 설치되지 않거나 JVM 구동에 실패하면, **정규식 기반 폴백
  토크나이저** 로 우아하게 강등된다 (CI/단위 테스트 환경 대비).
- 기본 태거(`Okt`) 외 ``KONLPY_TAGGER`` 환경 변수로 ``Hannanum/Komoran/Kkma``
  선택 가능.
- JVM 메모리 제한은 ``KONLPY_JVM_MAX_HEAP_MB`` (기본 1024MB) 로 강제.
"""

from __future__ import annotations

import logging
import os
import re
from typing import List, Optional, Tuple

from ..config import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

# Okt 등 KoNLPy 태거가 반환하는 품사 코드 중 명사·형용사·동사(서술성).
_POS_TARGETS_KONLPY = {
    "Noun", "ProperNoun", "Adjective", "Verb",                # Okt 계열
    "N", "NC", "NQ", "PA", "PV",                              # Hannanum
    "NNG", "NNP", "VA", "VV",                                 # Komoran/Kkma
}

# 폴백용 한글 단어/영문 키워드 추출 정규식.
# - 2자 이상 한글 또는 영문 대문자 약어(예: HBM) 캡처.
_RE_HANGUL_TOKEN = re.compile(r"[가-힣A-Za-z]{2,}")


class KoreanTokenizer:
    """KoNLPy 우선, 실패 시 정규식 폴백을 제공하는 토크나이저."""

    def __init__(
        self,
        tagger_name: Optional[str] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._tagger_name = (tagger_name or self._settings.konlpy_tagger or "Okt").strip()
        self._tagger = None  # lazy
        self._tried_init = False
        self._using_fallback = False

    # ------------------------------------------------------------------ life
    def _ensure_tagger(self) -> None:
        """KoNLPy 태거를 lazy init. 실패 시 fallback 모드로 전환."""
        if self._tried_init:
            return
        self._tried_init = True
        try:
            self._configure_jvm_memory()
            from konlpy import tag  # type: ignore

            tagger_cls = getattr(tag, self._tagger_name, None)
            if tagger_cls is None:
                _LOGGER.warning(
                    "KoNLPy 태거 %s 미발견 → Okt 로 폴백",
                    self._tagger_name,
                )
                tagger_cls = getattr(tag, "Okt", None)
            if tagger_cls is None:
                raise RuntimeError("KoNLPy 에 사용 가능한 태거가 없습니다.")
            self._tagger = tagger_cls()
            _LOGGER.info("KoNLPy 태거 초기화 완료: %s", type(self._tagger).__name__)
        except Exception as exc:  # pylint: disable=broad-except
            # ImportError (KoNLPy 미설치), JVMNotFoundException, JavaException 등.
            _LOGGER.warning(
                "KoNLPy 초기화 실패 → 정규식 폴백 토크나이저 사용 (사유: %s)", exc
            )
            self._tagger = None
            self._using_fallback = True

    def _configure_jvm_memory(self) -> None:
        """JPype 시작 전 JVM 힙 메모리를 환경변수로 강제 설정.

        KoNLPy 내부에서 jpype.startJVM 호출 시 ``JAVA_OPTIONS`` 가 참조된다.
        """
        max_heap = int(self._settings.konlpy_jvm_max_heap_mb)
        if max_heap <= 0:
            return
        existing = os.environ.get("JAVA_OPTIONS", "")
        opt = f"-Xmx{max_heap}m"
        if opt not in existing:
            os.environ["JAVA_OPTIONS"] = f"{existing} {opt}".strip()

    # ------------------------------------------------------------------ props
    @property
    def is_fallback(self) -> bool:
        """현재 폴백 모드로 동작 중인지 여부."""
        self._ensure_tagger()
        return self._using_fallback

    @property
    def tagger_name(self) -> str:
        self._ensure_tagger()
        if self._using_fallback:
            return "regex-fallback"
        return type(self._tagger).__name__ if self._tagger else "unknown"

    # ------------------------------------------------------------------ public
    def extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 의미 있는 토큰(명사·형용사 등) 리스트를 반환.

        - 빈 입력은 빈 리스트 반환.
        - KoNLPy 모드: 품사 필터를 적용해 명사/형용사/(서술성)동사 만 남김.
        - 폴백 모드: 한글/영문 2자 이상 단어를 모두 후보로 반환.
        """
        if not text or not text.strip():
            return []
        self._ensure_tagger()

        if self._tagger is None:
            return self._fallback_tokens(text)

        try:
            pos_pairs: List[Tuple[str, str]] = self._tagger.pos(text)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("KoNLPy.pos 실패 → 폴백 사용: %s", exc)
            return self._fallback_tokens(text)

        out: List[str] = []
        for word, pos in pos_pairs:
            if not word:
                continue
            if pos in _POS_TARGETS_KONLPY and len(word.strip()) >= 1:
                out.append(word)
        return out

    def extract_keywords_many(self, texts) -> List[List[str]]:
        return [self.extract_keywords(t) for t in (texts or [])]

    # ------------------------------------------------------------------ internal
    @staticmethod
    def _fallback_tokens(text: str) -> List[str]:
        """KoNLPy 부재 시 사용하는 정규식 기반 토큰화."""
        return _RE_HANGUL_TOKEN.findall(text or "")
