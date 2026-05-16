"""SQLite DB 초기화 스크립트.

CLI 진입점::

    python -m semi_senti init-db
    python -m semi_senti init-db --db ./custom.db --force

라이브러리 호출::

    from semi_senti.db import init_database
    init_database()
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from ..config import get_settings
from .schema import ALL_TABLES, SCHEMA_STATEMENTS

_LOGGER = logging.getLogger(__name__)


class DatabaseInitError(RuntimeError):
    """DB 초기화 실패."""


def _ensure_parent_dir(db_path: Path) -> None:
    """DB 파일 상위 디렉터리를 보장한다 (없으면 생성)."""
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DatabaseInitError(f"DB 상위 디렉터리 생성 실패: {db_path.parent} ({exc})") from exc


def init_database(
    db_path: Optional[Path] = None,
    *,
    force: bool = False,
) -> Path:
    """SQLite 파일 및 모든 테이블을 생성한다.

    Parameters
    ----------
    db_path:
        명시되지 않으면 ``Settings.sqlite_path`` 값을 사용한다.
    force:
        True 면 기존 DB 파일을 삭제 후 재생성한다 (개발 편의용).
        프로덕션에서는 절대 ``True`` 로 호출하지 말 것.

    Returns
    -------
    Path
        실제로 생성된 DB 파일의 절대 경로.

    Raises
    ------
    DatabaseInitError
        파일 시스템·SQL 실행 단계 중 어느 하나라도 실패한 경우.
    """
    settings = get_settings()
    target = Path(db_path) if db_path is not None else Path(settings.sqlite_path)
    target = target.expanduser().resolve()

    _ensure_parent_dir(target)

    if force and target.exists():
        try:
            target.unlink()
            _LOGGER.warning("기존 DB 파일을 삭제했습니다(force=True): %s", target)
        except OSError as exc:
            raise DatabaseInitError(f"기존 DB 삭제 실패: {target} ({exc})") from exc

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(str(target), timeout=settings.sqlite_timeout)
        for ddl in SCHEMA_STATEMENTS:
            conn.executescript(ddl)
        conn.commit()
        _LOGGER.info(
            "DB 초기화 완료: path=%s, tables=%s",
            target,
            ", ".join(ALL_TABLES),
        )
    except sqlite3.Error as exc:
        if conn is not None:
            try:
                conn.rollback()
            except sqlite3.Error:  # pragma: no cover - rollback 실패는 무시
                pass
        raise DatabaseInitError(f"SQLite 초기화 실패: {exc}") from exc
    finally:
        if conn is not None:
            conn.close()

    return target
