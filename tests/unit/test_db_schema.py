"""``semi_senti.db.schema`` / ``init_database`` 단위 테스트.

검증 항목 (T-003):
1. 4개의 핵심 테이블이 모두 생성된다 (Stocks, Financials, News, Signals).
2. ``init_database`` 는 멱등(idempotent) 하다 - 두 번 호출해도 에러 없음.
3. ``signals.signal_type`` 의 CHECK 제약이 동작한다.
4. 외래 키 제약이 활성화되어 동작한다.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from semi_senti.db import ALL_TABLES, init_database


class TestDatabaseSchema(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "schema_test.db"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def test_all_required_tables_created(self) -> None:
        init_database(db_path=self.db_path)
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            names = sorted(r[0] for r in cur.fetchall())
        for required in ALL_TABLES:
            self.assertIn(required, names, msg=f"필수 테이블 누락: {required}")

    def test_init_is_idempotent(self) -> None:
        init_database(db_path=self.db_path)
        try:
            init_database(db_path=self.db_path)
        except Exception as exc:  # pylint: disable=broad-except
            self.fail(f"init_database 2회 호출이 실패해서는 안 됩니다: {exc}")

    def test_signal_type_check_constraint(self) -> None:
        init_database(db_path=self.db_path)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO stocks (stock_code, name) VALUES (?, ?)",
                ("005930", "삼성전자"),
            )
            conn.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO signals "
                    "(stock_code, signal_type, price, signaled_at) "
                    "VALUES (?, ?, ?, ?)",
                    ("005930", "INVALID", 80000, "2026-05-16T10:00:00"),
                )

    def test_foreign_key_enforced(self) -> None:
        init_database(db_path=self.db_path)
        with self._connect() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO news (stock_code, title, published_at) "
                    "VALUES (?, ?, ?)",
                    ("NOT_EXIST", "타이틀", "2026-05-16T10:00:00"),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
