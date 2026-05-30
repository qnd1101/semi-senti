"""분석 엔진 계층 (sentiment, signal, divergence, fundamental band, cycle).

Phase 2 ~ Phase 4-2 산출물 (T-014 ~ T-027, T-044 ~ T-045)::

    from semi_senti.engine import (
        SentimentEngine,
        SemiconductorLexicon,
        KoreanTokenizer,
        FundamentalBand,
        SignalLogic,
        DivergenceDetector,
        CycleAnalyzer,
    )
"""

from .band import Band, FundamentalBand
from .cycle import CycleAnalyzer, CycleResult, classify_phase, compute_cycle_score
from .divergence import DivergenceDetector, DivergenceResult
from .lexicon import KeywordHit, SemiconductorLexicon, build_default_lexicon
from .sentiment import SentimentEngine, SentimentResult
from .reasoning import ReasoningEngine, ReasoningResult
from .signal import MultiPerspectiveResult, SignalDecision, SignalLogic
from .tokenizer import KoreanTokenizer

__all__ = [
    # sentiment
    "SentimentEngine",
    "SentimentResult",
    "SemiconductorLexicon",
    "KeywordHit",
    "build_default_lexicon",
    "KoreanTokenizer",
    # band / signal
    "FundamentalBand",
    "Band",
    "SignalLogic",
    "SignalDecision",
    "MultiPerspectiveResult",
    # reasoning (Phase 3)
    "ReasoningEngine",
    "ReasoningResult",
    # divergence
    "DivergenceDetector",
    "DivergenceResult",
    # cycle (Phase 4-2)
    "CycleAnalyzer",
    "CycleResult",
    "classify_phase",
    "compute_cycle_score",
]
