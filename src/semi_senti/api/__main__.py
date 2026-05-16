"""python -m semi_senti.api 로 FastAPI 서버 실행."""

import uvicorn

from .main import app  # noqa: F401

if __name__ == "__main__":
    uvicorn.run(
        "semi_senti.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
