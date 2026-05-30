"""데이터베이스 접근 계층 및 스키마 유틸리티.

PRD v1.2: PostgreSQL 기반으로 전환 (F-1.3).
모든 상위 모듈(``collector``, ``engine``, ``admin``)은
직접 psycopg2 를 임포트하지 않고 본 패키지를 통해서만 DB 에 접근한다.

Quick start::

    from semi_senti.db import DBControl, init_database

    init_database()                # 최초 1회 - 테이블 생성
    with DBControl() as db:
        rows = db.fetch_all("SELECT * FROM stocks")
"""

from .control import DBControl, DBControlError
from .init_db import init_database
from .schema import ALL_TABLES, SCHEMA_STATEMENTS

__all__ = [
    "DBControl",
    "DBControlError",
    "init_database",
    "ALL_TABLES",
    "SCHEMA_STATEMENTS",
]
