"""모든 모듈이 공유하는 SQLite 접근 창구 (``DBControl``).

설계 원칙
---------
- **단일 책임**: 본 클래스는 SQL 실행/트랜잭션/연결 관리만 담당한다.
  비즈니스 로직(NLP, 시그널 산출 등) 은 호출자가 책임진다.
- **컨텍스트 매니저**: ``with DBControl() as db:`` 패턴으로 connection
  누수를 원천 차단한다.
- **트랜잭션**: ``transaction()`` 컨텍스트로 명시적으로 묶을 수 있으며,
  단순 CRUD 헬퍼는 호출 시점 자동 커밋한다.
- **Row 반환 형태**: ``sqlite3.Row`` (dict-like) 로 통일하여 호출자 편의성↑.
- **하드코딩 금지**: 기본 DB 경로/타임아웃은 ``Settings`` 에서 주입받는다.
- **예외 일원화**: 모든 SQLite 예외는 ``DBControlError`` 로 래핑하여
  상위 계층이 동일한 except 절로 처리할 수 있게 한다.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

from ..config import get_settings

_LOGGER = logging.getLogger(__name__)

# 바인딩 파라미터 허용 타입 (sqlite3 표준).
ParamsType = Union[Sequence[Any], Mapping[str, Any], None]


class DBControlError(RuntimeError):
    """``DBControl`` 내부 SQL 오류를 일원화한 도메인 예외."""


class DBControl:
    """SQLite CRUD 공통 인터페이스.

    Parameters
    ----------
    db_path:
        명시되지 않으면 ``Settings.sqlite_path`` 를 사용한다.
    timeout:
        ``sqlite3.connect`` 의 timeout(초). 미지정 시 ``Settings.sqlite_timeout``.
    enable_foreign_keys:
        외래 키 제약 활성화 여부. 기본 True.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        *,
        timeout: Optional[int] = None,
        enable_foreign_keys: bool = True,
    ) -> None:
        settings = get_settings()
        self._db_path: Path = (
            Path(db_path).expanduser().resolve()
            if db_path is not None
            else Path(settings.sqlite_path).expanduser().resolve()
        )
        self._timeout: int = timeout if timeout is not None else settings.sqlite_timeout
        self._enable_fk: bool = enable_foreign_keys
        self._conn: Optional[sqlite3.Connection] = None

    # ---------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------
    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def connection(self) -> sqlite3.Connection:
        """현재 열린 연결을 반환한다. 없으면 ``DBControlError``."""
        if self._conn is None:
            raise DBControlError(
                "DB 연결이 열려 있지 않습니다. 'with DBControl() as db:' 형태로 사용하거나 connect() 를 호출하세요."
            )
        return self._conn

    def connect(self) -> sqlite3.Connection:
        """수동 연결. 컨텍스트 매니저 사용을 권장한다."""
        if self._conn is not None:
            return self._conn
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self._db_path),
                timeout=self._timeout,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            conn.row_factory = sqlite3.Row
            if self._enable_fk:
                conn.execute("PRAGMA foreign_keys = ON;")
            self._conn = conn
            _LOGGER.debug("SQLite 연결 생성: %s", self._db_path)
            return conn
        except (sqlite3.Error, OSError) as exc:
            raise DBControlError(f"SQLite 연결 실패: {self._db_path} ({exc})") from exc

    def close(self) -> None:
        """연결을 안전하게 종료한다. 이미 닫혀 있으면 무시한다."""
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error as exc:  # pragma: no cover
                _LOGGER.warning("SQLite 연결 종료 중 경고: %s", exc)
            finally:
                self._conn = None

    def __enter__(self) -> "DBControl":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---------------------------------------------------------------------
    # Transaction
    # ---------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """명시적 트랜잭션 컨텍스트.

        예외 발생 시 자동 rollback, 정상 종료 시 commit.
        """
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except sqlite3.Error as rollback_exc:  # pragma: no cover
                _LOGGER.error("rollback 실패: %s", rollback_exc)
            raise

    # ---------------------------------------------------------------------
    # Low-level execute
    # ---------------------------------------------------------------------
    def execute(self, sql: str, params: ParamsType = None) -> sqlite3.Cursor:
        """단일 SQL 실행 (자동 커밋). 결과 커서를 반환한다."""
        conn = self.connect()
        try:
            cur = conn.execute(sql, params or ())
            conn.commit()
            return cur
        except sqlite3.Error as exc:
            try:
                conn.rollback()
            except sqlite3.Error:  # pragma: no cover
                pass
            raise DBControlError(f"SQL 실행 실패: {sql.strip().splitlines()[0]} ({exc})") from exc

    def executemany(self, sql: str, seq_of_params: Iterable[ParamsType]) -> sqlite3.Cursor:
        """다건 배치 실행 (자동 커밋)."""
        conn = self.connect()
        try:
            cur = conn.executemany(sql, list(seq_of_params))
            conn.commit()
            return cur
        except sqlite3.Error as exc:
            try:
                conn.rollback()
            except sqlite3.Error:  # pragma: no cover
                pass
            raise DBControlError(f"executemany 실패: {sql.strip().splitlines()[0]} ({exc})") from exc

    # ---------------------------------------------------------------------
    # Read helpers
    # ---------------------------------------------------------------------
    def fetch_one(self, sql: str, params: ParamsType = None) -> Optional[Dict[str, Any]]:
        """단일 행을 dict 로 반환. 결과가 없으면 ``None``."""
        conn = self.connect()
        try:
            cur = conn.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row is not None else None
        except sqlite3.Error as exc:
            raise DBControlError(f"fetch_one 실패: {exc}") from exc

    def fetch_all(self, sql: str, params: ParamsType = None) -> List[Dict[str, Any]]:
        """모든 행을 dict 리스트로 반환."""
        conn = self.connect()
        try:
            cur = conn.execute(sql, params or ())
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.Error as exc:
            raise DBControlError(f"fetch_all 실패: {exc}") from exc

    # ---------------------------------------------------------------------
    # CRUD helpers
    # ---------------------------------------------------------------------
    def insert(self, table: str, data: Mapping[str, Any]) -> int:
        """단일 row INSERT. 새로 생성된 ``rowid`` 를 반환한다."""
        if not data:
            raise DBControlError("insert 데이터가 비어 있습니다.")
        columns, placeholders, values = self._split_columns(data)
        sql = f"INSERT INTO {self._quote_ident(table)} ({columns}) VALUES ({placeholders})"
        cur = self.execute(sql, values)
        return int(cur.lastrowid or 0)

    def insert_many(self, table: str, rows: Sequence[Mapping[str, Any]]) -> int:
        """다건 INSERT. 반영된 row 개수를 반환한다."""
        if not rows:
            return 0
        first = rows[0]
        columns = ", ".join(self._quote_ident(c) for c in first.keys())
        placeholders = ", ".join(f":{c}" for c in first.keys())
        sql = f"INSERT INTO {self._quote_ident(table)} ({columns}) VALUES ({placeholders})"
        cur = self.executemany(sql, rows)
        return int(cur.rowcount or 0)

    def upsert(
        self,
        table: str,
        data: Mapping[str, Any],
        conflict_columns: Sequence[str],
        update_columns: Optional[Sequence[str]] = None,
    ) -> int:
        """SQLite ``INSERT ... ON CONFLICT ... DO UPDATE`` 헬퍼.

        Parameters
        ----------
        conflict_columns:
            충돌 판별 컬럼 (PK 또는 UNIQUE 인덱스).
        update_columns:
            충돌 시 갱신할 컬럼. 미지정 시 ``data`` 의 비-conflict 컬럼 전체.
        """
        if not data:
            raise DBControlError("upsert 데이터가 비어 있습니다.")
        if not conflict_columns:
            raise DBControlError("upsert 의 conflict_columns 가 비어 있습니다.")

        columns, placeholders, values = self._split_columns(data)
        upd_cols = list(update_columns) if update_columns else [
            c for c in data.keys() if c not in conflict_columns
        ]

        sql = f"INSERT INTO {self._quote_ident(table)} ({columns}) VALUES ({placeholders})"
        if upd_cols:
            conflict_part = ", ".join(self._quote_ident(c) for c in conflict_columns)
            update_part = ", ".join(
                f"{self._quote_ident(c)} = excluded.{self._quote_ident(c)}" for c in upd_cols
            )
            sql += f" ON CONFLICT({conflict_part}) DO UPDATE SET {update_part}"
        else:
            # 갱신할 컬럼이 없을 경우 충돌은 무시.
            conflict_part = ", ".join(self._quote_ident(c) for c in conflict_columns)
            sql += f" ON CONFLICT({conflict_part}) DO NOTHING"

        cur = self.execute(sql, values)
        return int(cur.rowcount or 0)

    def update(
        self,
        table: str,
        data: Mapping[str, Any],
        where: str,
        where_params: ParamsType = None,
    ) -> int:
        """UPDATE. 반영된 row 개수를 반환한다."""
        if not data:
            raise DBControlError("update 데이터가 비어 있습니다.")
        if not where.strip():
            # 안전장치: where 절 누락 시 전체 갱신을 방지.
            raise DBControlError("update 시 where 절은 필수입니다.")
        set_clause = ", ".join(f"{self._quote_ident(k)} = ?" for k in data.keys())
        values: Tuple[Any, ...] = tuple(data.values())
        if where_params is None:
            where_values: Tuple[Any, ...] = ()
        elif isinstance(where_params, Mapping):
            raise DBControlError("update 의 where_params 는 시퀀스여야 합니다.")
        else:
            where_values = tuple(where_params)
        sql = f"UPDATE {self._quote_ident(table)} SET {set_clause} WHERE {where}"
        cur = self.execute(sql, values + where_values)
        return int(cur.rowcount or 0)

    def delete(self, table: str, where: str, where_params: ParamsType = None) -> int:
        """DELETE. 반영된 row 개수를 반환한다."""
        if not where.strip():
            raise DBControlError("delete 시 where 절은 필수입니다.")
        sql = f"DELETE FROM {self._quote_ident(table)} WHERE {where}"
        cur = self.execute(sql, where_params)
        return int(cur.rowcount or 0)

    # ---------------------------------------------------------------------
    # Inspection helpers
    # ---------------------------------------------------------------------
    def table_exists(self, table: str) -> bool:
        """``sqlite_master`` 로 테이블 존재 여부 확인."""
        row = self.fetch_one(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?;",
            (table,),
        )
        return row is not None

    def list_tables(self) -> List[str]:
        rows = self.fetch_all(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [r["name"] for r in rows]

    # ---------------------------------------------------------------------
    # Internal utilities
    # ---------------------------------------------------------------------
    @staticmethod
    def _quote_ident(identifier: str) -> str:
        """식별자 따옴표 처리(예약어/대소문자 안전)."""
        if not identifier or not isinstance(identifier, str):
            raise DBControlError(f"유효하지 않은 식별자: {identifier!r}")
        # SQLite 권장 따옴표(이중 따옴표) 사용. 내부 이중 따옴표는 이스케이프.
        return '"' + identifier.replace('"', '""') + '"'

    @classmethod
    def _split_columns(
        cls, data: Mapping[str, Any]
    ) -> Tuple[str, str, Tuple[Any, ...]]:
        """data dict 를 (컬럼절, 플레이스홀더절, 값 튜플) 로 분해."""
        cols = list(data.keys())
        columns_sql = ", ".join(cls._quote_ident(c) for c in cols)
        placeholders_sql = ", ".join("?" for _ in cols)
        values = tuple(data[c] for c in cols)
        return columns_sql, placeholders_sql, values
