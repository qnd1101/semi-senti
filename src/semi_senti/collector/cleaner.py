"""뉴스 본문 정제 (T-012, F-1.2.2).

> "BeautifulSoup4를 활용하여 HTML 태그·특수문자를 제거하고 순수 텍스트를
>  추출한다." — PRD F-1.2.2

설계
----
- BeautifulSoup 가 설치되지 않은 환경(예: 단위 테스트 격리)에서도 본 모듈은
  import 가능해야 하므로 **lazy import** 처리한다.
- BS4 가 부재할 때는 정규식 기반 폴백 클리너로 동작하여 최소한의 태그를
  제거한다 (정밀도는 떨어지지만 파이프라인 정지를 막는 것이 목표).
- 모든 클래스/함수는 stateless 하게 동작한다(스레드 안전).
"""

from __future__ import annotations

import html
import logging
import re
from typing import Optional

_LOGGER = logging.getLogger(__name__)

# 정규식 폴백용 패턴 (BS4 가 없을 때만 사용).
_RE_HTML_TAG = re.compile(r"<[^>]+>")
# 제어 문자(0x00-0x1F, 0x7F) 제거. 단, 탭/줄바꿈은 공백으로 치환할 수 있도록 별도 처리.
_RE_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_RE_MULTI_WS = re.compile(r"\s+")
_RE_NAVER_HIGHLIGHT = re.compile(r"</?b>", re.IGNORECASE)


class TextCleaner:
    """HTML/특수문자 제거 + 공백 정규화 유틸리티.

    사용 예::

        cleaner = TextCleaner()
        clean = cleaner.clean("<b>HBM</b> 수요 &quot;역대급&quot;... \\n공급 부족")
        # -> 'HBM 수요 "역대급"... 공급 부족'
    """

    def __init__(self, parser: str = "html.parser") -> None:
        self._parser = parser

    # ------------------------------------------------------------------ public
    def clean(self, raw: Optional[str]) -> str:
        """주어진 문자열에서 HTML 과 잡음 문자를 제거하고 공백을 정규화한다.

        ``None`` 또는 빈 문자열 입력 시 빈 문자열을 반환한다 (호출자가 별도
        분기 없이 안전하게 사용할 수 있도록).
        """
        if raw is None:
            return ""
        if not isinstance(raw, str):
            raw = str(raw)
        if not raw.strip():
            return ""

        # 1) 네이버 뉴스 API 응답에는 <b>...</b> 강조 태그가 자주 들어옴 → 우선 제거.
        text = _RE_NAVER_HIGHLIGHT.sub("", raw)

        # 2) BS4 우선, 실패 시 정규식 폴백.
        try:
            text = self._strip_with_bs4(text)
        except Exception as exc:  # pragma: no cover
            _LOGGER.debug("BS4 정제 실패, 정규식 폴백으로 전환: %s", exc)
            text = _RE_HTML_TAG.sub(" ", text)

        # 3) HTML entity 디코드(예: &quot; &amp; &#39;).
        text = html.unescape(text)

        # 4) 제어 문자 제거.
        text = _RE_CTRL.sub("", text)

        # 5) 줄바꿈/탭 → 공백, 연속 공백 → 1칸.
        text = text.replace("\n", " ").replace("\t", " ")
        text = _RE_MULTI_WS.sub(" ", text).strip()

        return text

    def clean_many(self, items):
        """여러 문자열을 일괄 정제. 입력은 임의의 iterable."""
        return [self.clean(x) for x in items]

    # ------------------------------------------------------------------ internal
    def _strip_with_bs4(self, text: str) -> str:
        # BS4 가 설치되지 않은 환경에서도 동작하도록 동적 import.
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except ImportError:
            # BS4 미설치 시 정규식 폴백을 사용한다.
            return _RE_HTML_TAG.sub(" ", text)

        soup = BeautifulSoup(text, self._parser)
        # script/style 등 본문 가치 없는 태그는 통째로 제거.
        for noise in soup(["script", "style", "noscript", "iframe"]):
            noise.decompose()
        return soup.get_text(separator=" ")
