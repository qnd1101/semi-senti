"""PostgreSQL DB 초기화 스크립트.

PRD v1.2: SQLite → PostgreSQL 전환

CLI 진입점::

    python -m semi_senti init-db
    python -m semi_senti init-db --force

라이브러리 호출::

    from semi_senti.db import init_database
    init_database()
"""

from __future__ import annotations

import logging
from typing import Any, Optional

try:
    import psycopg2
except ImportError as _e:  # pragma: no cover
    raise ImportError("psycopg2-binary 를 설치해주세요: pip install psycopg2-binary") from _e

from ..config import get_settings
from .schema import ALL_TABLES, SCHEMA_STATEMENTS

_LOGGER = logging.getLogger(__name__)


class DatabaseInitError(RuntimeError):
    """DB 초기화 실패."""


def init_database(
    db_url: Optional[str] = None,
    *,
    force: bool = False,
    db_path: Any = None,  # 하위 호환 — SQLite 시절 인자, PostgreSQL 전환 후 무시됨
) -> str:
    """PostgreSQL 스키마(테이블·인덱스)를 생성한다.

    Parameters
    ----------
    db_url:
        명시되지 않으면 ``Settings.database_url`` 값을 사용한다.
    force:
        True 면 public 스키마의 모든 대상 테이블을 DROP 후 재생성한다.
        프로덕션에서는 절대 ``True`` 로 호출하지 말 것.

    Returns
    -------
    str
        연결된 DATABASE_URL (마스킹 버전).
    """
    settings = get_settings()
    url = db_url or settings.database_url

    try:
        conn = psycopg2.connect(url, connect_timeout=settings.db_connect_timeout)
        conn.autocommit = True
    except psycopg2.Error as exc:
        raise DatabaseInitError(f"PostgreSQL 연결 실패: {exc}") from exc

    try:
        cur = conn.cursor()

        if force:
            for table in reversed(ALL_TABLES):
                cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                _LOGGER.warning("테이블 삭제(force=True): %s", table)

        for ddl in SCHEMA_STATEMENTS:
            try:
                cur.execute(ddl)
            except psycopg2.Error as exc:
                raise DatabaseInitError(f"DDL 실행 실패: {ddl[:80]}... ({exc})") from exc

        _LOGGER.info(
            "DB 초기화 완료: tables=%s",
            ", ".join(ALL_TABLES),
        )
    finally:
        conn.close()

    from .control import _mask_dsn
    return _mask_dsn(url)
