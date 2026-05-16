"""FastAPI 어댑터 (T-058, Phase 5).

Next.js 프론트엔드에서 Python 분석 엔진 기능을 호출하기 위한 HTTP 인터페이스.

사용법::

    # 개발 서버 (uvicorn)
    uvicorn semi_senti.api:app --reload --port 8000

    # 또는 모듈 직접 실행
    python -m semi_senti.api
"""

from .main import app

__all__ = ["app"]
