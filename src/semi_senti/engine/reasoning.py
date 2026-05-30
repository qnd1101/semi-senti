"""Gemini API 기반 투자 판단 근거 생성 (F-3.3, PRD v1.2).

PRD §F-3.3 Gemini Reasoning 파이프라인:
1. Prompt Builder: 구조화 프롬프트 생성 (JSON + 한국어 설명 지시문)
2. Gemini API 호출 (GEMINI_API_KEY)
3. 응답 검증 후 reasonings 테이블 저장
4. API 실패 시 규칙 기반 템플릿 문장으로 폴백 (F-3.3.2)
5. 생성 근거는 prompt_hash 와 함께 저장해 회귀 검증 가능 (F-3.3.3)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Settings, get_settings
from ..db import DBControl

_LOGGER = logging.getLogger(__name__)

# API 키 없을 때 경고 (1회만)
_WARNED_NO_KEY: bool = False


@dataclass
class ReasoningResult:
    """Gemini 또는 폴백 근거 생성 결과."""

    stock_code: str
    perspective: str      # 'SHORT' | 'MID' | 'LONG'
    signal_type: str      # 'BUY' | 'SELL' | 'HOLD'
    reasoning: str
    is_fallback: bool
    prompt_hash: Optional[str] = None
    model_version: Optional[str] = None

    def to_db_row(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "perspective": self.perspective,
            "signal_type": self.signal_type,
            "reasoning": self.reasoning,
            "prompt_hash": self.prompt_hash,
            "model_version": self.model_version,
            "is_fallback": self.is_fallback,
        }


# ---------------------------------------------------------------------------
# 폴백 템플릿 (F-3.3.2)
# ---------------------------------------------------------------------------

_FALLBACK_TEMPLATES: Dict[str, Dict[str, str]] = {
    "SHORT": {
        "BUY": (
            "단기 관점에서 매수 신호가 감지되었습니다. "
            "현재 뉴스 감성이 긍정적으로 전환 중이며, 최근 가격 추세가 상향을 나타냅니다. "
            "현재가는 펀더멘털 밴드 하단 부근에 위치해 단기 반등 가능성이 있습니다."
        ),
        "SELL": (
            "단기 관점에서 매도 신호가 감지되었습니다. "
            "뉴스 감성이 부정적이고 단기 가격 추세가 하락 중입니다. "
            "현재가가 펀더멘털 밴드 상단을 초과한 과열 구간입니다."
        ),
        "HOLD": (
            "단기 관점에서 현재 명확한 방향성을 확인하기 어렵습니다. "
            "감성 점수와 가격 추세가 중립 범위에 있으며, "
            "추가 신호 확인 후 진입 여부를 결정하는 것이 적절합니다."
        ),
    },
    "MID": {
        "BUY": (
            "중기 관점에서 매수 신호가 발생했습니다. "
            "주봉 추세가 상향 전환 초기 국면으로 판단되며, "
            "현재 밸류에이션이 적정 밴드 하단 부근으로 저평가 구간입니다. "
            "반도체 키워드 모멘텀도 긍정적으로 전환 중입니다."
        ),
        "SELL": (
            "중기 관점에서 매도 신호가 발생했습니다. "
            "주봉 기준 가격 추세가 꺾이는 신호가 감지되었으며, "
            "현재가가 펀더멘털 밴드 상단 이상의 고평가 구간에 위치합니다."
        ),
        "HOLD": (
            "중기 관점에서 보유 또는 관망이 권고됩니다. "
            "밸류에이션과 주봉 추세가 중립 범위에 있으며, "
            "업황 사이클 전환 신호를 추가 확인할 필요가 있습니다."
        ),
    },
    "LONG": {
        "BUY": (
            "장기 관점에서 매수 신호가 포착되었습니다. "
            "펀더멘털 저평가 + 업황 사이클 저점 근접으로 중장기 매력이 높습니다. "
            "재고자산 회전율 개선 추세는 사이클 저점 통과 가능성을 시사합니다."
        ),
        "SELL": (
            "장기 관점에서 매도 신호가 포착되었습니다. "
            "업황 사이클 고점 부근이 감지되며, 밸류에이션이 상단 초과 구간입니다. "
            "재고 부담이 증가하는 추세로 장기 수익성 악화 우려가 있습니다."
        ),
        "HOLD": (
            "장기 관점에서 현 시점은 관망이 적절합니다. "
            "업황 사이클 위치가 명확하지 않으며, 재무·감성·가격 추세가 "
            "중립 범위에 있어 추세 확인 후 포지션 조정을 권고합니다."
        ),
    },
}


def _fallback_reasoning(perspective: str, signal_type: str) -> str:
    p = (perspective or "SHORT").upper()
    s = (signal_type or "HOLD").upper()
    return _FALLBACK_TEMPLATES.get(p, {}).get(s, "현재 데이터를 기반으로 한 투자 판단 근거입니다.")


# ---------------------------------------------------------------------------
# Prompt 생성
# ---------------------------------------------------------------------------

def _build_prompt(
    stock_code: str,
    perspective: str,
    signal_type: str,
    score: float,
    price: Optional[float],
    band_low: Optional[float],
    band_high: Optional[float],
    sentiment_score: Optional[float],
    top_keywords: Optional[List[Dict[str, Any]]],
    price_trend_d: Optional[float],
    price_trend_w: Optional[float],
    price_trend_m: Optional[float],
    cycle_score: Optional[float],
) -> str:
    """구조화 프롬프트 생성 (JSON 데이터 + 한국어 설명 지시문)."""
    perspective_label = {"SHORT": "단기(1일~2주)", "MID": "중기(2주~3개월)", "LONG": "장기(3개월~12개월+)"}.get(
        perspective, perspective
    )
    signal_label = {"BUY": "매수", "SELL": "매도", "HOLD": "보유"}.get(signal_type, signal_type)

    band_pos_pct: Optional[float] = None
    if price and band_low and band_high and (band_high - band_low) > 0:
        band_pos_pct = round((price - band_low) / (band_high - band_low) * 100, 1)

    data = {
        "stock_code": stock_code,
        "perspective": perspective_label,
        "signal": signal_label,
        "perspective_score": round(score, 2),
        "current_price": price,
        "fundamental_band": {"low": band_low, "high": band_high, "position_pct": band_pos_pct},
        "sentiment_score": sentiment_score,
        "top_keywords": top_keywords or [],
        "price_trend": {"daily_5d": price_trend_d, "weekly_15d": price_trend_w, "monthly_30d": price_trend_m},
        "cycle_score": cycle_score,
    }

    return (
        f"당신은 반도체 주식 전문 투자 분석가입니다.\n"
        f"아래 JSON 데이터는 종목 {stock_code}의 {perspective_label} 관점 분석 결과입니다.\n"
        f"현재 시그널: {signal_label}\n\n"
        f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```\n\n"
        f"위 데이터를 바탕으로 '{signal_label}' 시그널이 발생한 이유를 투자자가 이해하기 쉽게 "
        f"3~5문장으로 설명해 주세요. "
        f"반도체 업황, 감성 지표, 밸류에이션, 가격 추세를 종합해서 설명하되, "
        f"투자 조언이 아닌 분석 근거 설명으로 작성해 주세요. "
        f"응답은 한국어로만 작성하고, JSON이나 마크다운 없이 순수 텍스트로 반환하세요."
    )


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Gemini API 호출
# ---------------------------------------------------------------------------

def _call_gemini(prompt: str, *, api_key: str, model: str, timeout: int) -> str:
    """Gemini API 호출. 실패 시 예외 전파."""
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError("google-generativeai 패키지가 필요합니다: pip install google-generativeai") from exc

    genai.configure(api_key=api_key)
    model_obj = genai.GenerativeModel(model)
    try:
        response = model_obj.generate_content(
            prompt,
            generation_config={"max_output_tokens": 512, "temperature": 0.3},
            request_options={"timeout": timeout},
        )
        text = response.text.strip()
        if not text or len(text) < 20:
            raise ValueError(f"Gemini 응답이 너무 짧습니다: {text!r}")
        return text
    except Exception as exc:
        raise RuntimeError(f"Gemini 호출 실패: {exc}") from exc


# ---------------------------------------------------------------------------
# ReasoningEngine
# ---------------------------------------------------------------------------

class ReasoningEngine:
    """Gemini API 기반 투자 판단 근거 생성 엔진 (F-3.3)."""

    def __init__(
        self,
        db: Optional[DBControl] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._db: Optional[DBControl] = db
        self._owns_db: bool = db is None

    def db(self) -> DBControl:
        if self._db is None:
            self._db = DBControl()
            self._db.connect()
        else:
            self._db.connect()
        return self._db

    def close(self) -> None:
        if self._owns_db and self._db is not None:
            self._db.close()
            self._db = None

    def __enter__(self) -> "ReasoningEngine":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def generate(
        self,
        stock_code: str,
        perspective: str,
        signal_type: str,
        score: float = 0.0,
        price: Optional[float] = None,
        band_low: Optional[float] = None,
        band_high: Optional[float] = None,
        sentiment_score: Optional[float] = None,
        top_keywords: Optional[List[Dict[str, Any]]] = None,
        price_trend_d: Optional[float] = None,
        price_trend_w: Optional[float] = None,
        price_trend_m: Optional[float] = None,
        cycle_score: Optional[float] = None,
    ) -> ReasoningResult:
        """Gemini API로 근거 생성. 실패 시 폴백 텍스트 사용."""
        global _WARNED_NO_KEY  # noqa: PLW0603

        api_key = self._settings.gemini_api_key
        if not api_key:
            if not _WARNED_NO_KEY:
                _LOGGER.warning(
                    "GEMINI_API_KEY 미설정 — 규칙 기반 폴백 근거를 사용합니다. "
                    ".env 에 GEMINI_API_KEY 를 추가하면 AI 근거가 활성화됩니다."
                )
                _WARNED_NO_KEY = True
            return self._fallback(stock_code, perspective, signal_type)

        prompt = _build_prompt(
            stock_code=stock_code,
            perspective=perspective,
            signal_type=signal_type,
            score=score,
            price=price,
            band_low=band_low,
            band_high=band_high,
            sentiment_score=sentiment_score,
            top_keywords=top_keywords,
            price_trend_d=price_trend_d,
            price_trend_w=price_trend_w,
            price_trend_m=price_trend_m,
            cycle_score=cycle_score,
        )
        ph = _hash_prompt(prompt)

        try:
            text = _call_gemini(
                prompt,
                api_key=api_key,
                model=self._settings.gemini_model,
                timeout=self._settings.gemini_timeout_seconds,
            )
            result = ReasoningResult(
                stock_code=stock_code,
                perspective=perspective,
                signal_type=signal_type,
                reasoning=text,
                is_fallback=False,
                prompt_hash=ph,
                model_version=self._settings.gemini_model,
            )
        except Exception as exc:
            _LOGGER.warning("Gemini 생성 실패 → 폴백 사용 (%s/%s): %s", stock_code, perspective, exc)
            result = self._fallback(stock_code, perspective, signal_type, prompt_hash=ph)

        self._store(result)
        return result

    def generate_for_signal_result(self, signal_result: Any) -> Dict[str, ReasoningResult]:
        """MultiPerspectiveResult 를 입력받아 3관점 근거를 일괄 생성."""
        from .signal import MultiPerspectiveResult  # local import 순환 방지
        if not isinstance(signal_result, MultiPerspectiveResult):
            raise TypeError("signal_result 는 MultiPerspectiveResult 여야 합니다.")

        out: Dict[str, ReasoningResult] = {}
        for decision in signal_result.decisions:
            r = self.generate(
                stock_code=decision.stock_code,
                perspective=decision.perspective,
                signal_type=decision.signal_type,
                score=decision.score,
                price=decision.price,
                band_low=decision.band_low,
                band_high=decision.band_high,
                sentiment_score=decision.sentiment_score,
            )
            out[decision.perspective.lower()] = r
        return out

    def _fallback(
        self,
        stock_code: str,
        perspective: str,
        signal_type: str,
        prompt_hash: Optional[str] = None,
    ) -> ReasoningResult:
        return ReasoningResult(
            stock_code=stock_code,
            perspective=perspective,
            signal_type=signal_type,
            reasoning=_fallback_reasoning(perspective, signal_type),
            is_fallback=True,
            prompt_hash=prompt_hash,
            model_version=None,
        )

    def _store(self, result: ReasoningResult) -> None:
        try:
            self.db().insert("reasonings", result.to_db_row())
        except Exception as exc:  # pragma: no cover
            _LOGGER.error("reasonings 저장 실패: %s", exc)

    def latest(self, stock_code: str, perspective: str) -> Optional[dict]:
        return self.db().fetch_one(
            "SELECT reasoning, is_fallback, model_version, generated_at "
            "FROM reasonings WHERE stock_code = %s AND perspective = %s "
            "ORDER BY generated_at DESC LIMIT 1",
            (stock_code, perspective.upper()),
        )
