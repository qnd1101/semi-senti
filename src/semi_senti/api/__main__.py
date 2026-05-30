"""python -m semi_senti.api 로 FastAPI 서버 실행."""

import uvicorn

from ..config import get_settings
from .main import app  # noqa: F401

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "semi_senti.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
