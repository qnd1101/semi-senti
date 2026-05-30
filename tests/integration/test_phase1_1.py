"""Phase 1-1 (T-001~T-004) 통합 검증 스크립트.

검증 범위
---------
1. 필수 디렉터리 존재 여부 (`/collector`, `/engine`, `/admin`, `/db`)
2. ``db/semisenti.db`` 파일 생성 및 4개 핵심 테이블(Stocks, Financials, News, Signals)
   스키마 정상 빌드
3. ``DBControl`` 의 INSERT / SELECT / UPDATE / UPSERT / DELETE / TRANSACTION 동작

실행 방법
---------
(가상환경 활성화 후)

    # 1) 스크립트로 직접 실행 (권장)
    python tests/integration/test_phase1_1.py

    # 2) 옵션 사용
    python tests/integration/test_phase1_1.py --keep-db     # DB 파일 보존(기본)
    python tests/integration/test_phase1_1.py --purge-db    # DB 파일까지 삭제

    # 3) unittest 디스커버리도 호환
    python -m unittest tests.integration.test_phase1_1 -v

설계 원칙
---------
- 모든 단계는 ``TestReporter`` 에 누적 기록되며, 한 단계가 실패해도 가능한
  다음 단계까지 수행하여 풀 리포트를 출력한다.
- 더미 데이터는 ``stock_code`` 의 ``TST_`` prefix 로만 사용하여, 정리 시
  ``WHERE stock_code LIKE 'TST_%'`` 일괄 삭제로 안전 정리한다.
- 에러는 ``DBControlError`` / ``OSError`` / ``sqlite3.Error`` 등 가능한 모든
  예외를 try/except 로 포착하여 ``[FAIL]`` 로 보고한다.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import traceback
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# 0. 경로 부트스트랩
#    `pip install -e .` 이전에도 스크립트가 단독 실행될 수 있도록 src 를
#    sys.path 에 보정한다.
# ---------------------------------------------------------------------------
# 본 파일 위치: <root>/tests/integration/test_phase1_1.py
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
SRC_PATH: Path = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# 통합 테스트가 실행되는 동안 항상 동일한 DB 경로를 보장하기 위해
# (Settings 가 환경변수 기반이므로) 환경변수를 미리 강제 설정한다.
_DEFAULT_DB_PATH = PROJECT_ROOT / "db" / "semisenti.db"
os.environ.setdefault("SEMI_SENTI_SQLITE_PATH", str(_DEFAULT_DB_PATH))

from semi_senti.db import DBControl, init_database  # noqa: E402 (sys.path 보정 후)
from semi_senti.db.control import DBControlError  # noqa: E402
from semi_senti.db.init_db import DatabaseInitError  # noqa: E402


# ---------------------------------------------------------------------------
# 1. 상수
# ---------------------------------------------------------------------------
REQUIRED_MODULE_DIRS: Tuple[str, ...] = (
    "collector",
    "engine",
    "admin",
    "db",
)

REQUIRED_TABLES: Tuple[str, ...] = ("stocks", "financials", "news", "signals")

# 더미 데이터 식별 prefix (cleanup 안전성을 위해)
TEST_PREFIX: str = "TST_"


# ---------------------------------------------------------------------------
# 2. 컬러 출력 유틸 (Windows PowerShell 안전 폴백 포함)
# ---------------------------------------------------------------------------
class _Color:
    GREEN = ""
    RED = ""
    YELLOW = ""
    CYAN = ""
    BOLD = ""
    RESET = ""


def _try_enable_color() -> None:
    """colorama 가 있으면 ANSI 색상 활성화. 없으면 무색으로 동작."""
    try:
        import colorama  # type: ignore

        colorama.just_fix_windows_console()
        _Color.GREEN = "\033[32m"
        _Color.RED = "\033[31m"
        _Color.YELLOW = "\033[33m"
        _Color.CYAN = "\033[36m"
        _Color.BOLD = "\033[1m"
        _Color.RESET = "\033[0m"
    except Exception:  # pragma: no cover
        # 색상은 비필수 - 미설치 시 무색으로 처리.
        pass


# ---------------------------------------------------------------------------
# 3. 결과 리포터
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str = ""


@dataclass
class TestReporter:
    results: List[CheckResult] = field(default_factory=list)

    def record(self, name: str, ok: bool, message: str = "") -> bool:
        self.results.append(CheckResult(name=name, ok=ok, message=message))
        tag = (
            f"{_Color.GREEN}[SUCCESS]{_Color.RESET}"
            if ok
            else f"{_Color.RED}[FAIL]{_Color.RESET}"
        )
        line = f"  {tag} {name}"
        if message:
            line += f" - {message}"
        print(line)
        return ok

    def fail(self, name: str, exc: BaseException) -> None:
        msg = f"{type(exc).__name__}: {exc}"
        self.record(name, ok=False, message=msg)
        # 디버깅 편의 - traceback 은 들여쓰기해서 출력
        for line in traceback.format_exc().splitlines():
            print(f"      | {line}")

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.ok)

    @property
    def total(self) -> int:
        return len(self.results)

    def print_summary(self) -> None:
        bar = "=" * 60
        color = _Color.GREEN if self.failed_count == 0 else _Color.RED
        status = "PASSED" if self.failed_count == 0 else "FAILED"
        print()
        print(bar)
        print(
            f" {_Color.BOLD}RESULT:{_Color.RESET} "
            f"{color}{self.passed_count} / {self.total} {status}{_Color.RESET}"
        )
        print(bar)
        if self.failed_count:
            print()
            print(f"{_Color.RED}실패 항목:{_Color.RESET}")
            for r in self.results:
                if not r.ok:
                    print(f"  - {r.name}: {r.message}")


# ---------------------------------------------------------------------------
# 4. 검증 단계
# ---------------------------------------------------------------------------
def _print_header(step_no: int, step_total: int, title: str) -> None:
    print()
    print(f"{_Color.CYAN}[STEP {step_no}/{step_total}] {title}{_Color.RESET}")
    print("-" * 60)


def step_check_directories(reporter: TestReporter) -> None:
    """STEP 1: 필수 디렉터리 5종 + DB 저장 디렉터리 보장."""
    _print_header(1, 5, "필수 디렉터리 존재 여부 확인 (os.path.isdir)")

    # 사용자가 명시한 `/collector` 등 모듈 폴더는 src layout 의
    # `src/semi_senti/<name>/` 위치에 있다. 양쪽 후보를 모두 탐색하여
    # 둘 중 하나라도 존재하면 통과로 인정한다.
    for sub in REQUIRED_MODULE_DIRS:
        candidates = [
            PROJECT_ROOT / "src" / "semi_senti" / sub,
            PROJECT_ROOT / sub,  # 루트 직속 폴더가 별도 운용될 가능성
        ]
        found = next((p for p in candidates if os.path.isdir(str(p))), None)
        if found is not None:
            reporter.record(
                f"디렉터리 존재: /{sub}",
                ok=True,
                message=str(found.relative_to(PROJECT_ROOT)),
            )
        else:
            reporter.record(
                f"디렉터리 존재: /{sub}",
                ok=False,
                message=f"후보 경로 모두 부재 → {[str(c) for c in candidates]}",
            )

    # DB 파일 저장용 디렉터리 (없으면 생성)
    db_dir = PROJECT_ROOT / "db"
    try:
        db_dir.mkdir(parents=True, exist_ok=True)
        reporter.record(
            "DB 저장 디렉터리 보장: /db",
            ok=os.path.isdir(str(db_dir)),
            message=str(db_dir.relative_to(PROJECT_ROOT)),
        )
    except OSError as exc:
        reporter.fail("DB 저장 디렉터리 보장: /db", exc)


def step_init_db(reporter: TestReporter, db_path: Path) -> bool:
    """STEP 2: DB 파일 생성. 실패하면 이후 단계 의미 없으므로 False 반환."""
    _print_header(2, 5, "SQLite DB 파일 생성 (init_database)")

    try:
        created = init_database(db_path=db_path, force=True)
    except DatabaseInitError as exc:
        reporter.fail("init_database() 호출", exc)
        return False
    except Exception as exc:  # pragma: no cover - 예기치 못한 예외
        reporter.fail("init_database() 호출", exc)
        return False

    reporter.record(
        "init_database() 호출",
        ok=True,
        message=f"force=True 로 재생성 → {created}",
    )

    exists = os.path.isfile(str(created))
    size = os.path.getsize(str(created)) if exists else 0
    reporter.record(
        "DB 파일 생성 확인",
        ok=exists and size > 0,
        message=f"{created} ({size:,} bytes)",
    )
    return exists and size > 0


def step_verify_tables(reporter: TestReporter, db_path: Path) -> None:
    """STEP 3: sqlite_master 와 PRAGMA table_info 로 스키마 검증."""
    _print_header(3, 5, "4개 핵심 테이블 스키마 검증")

    try:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
            # SQLite 는 테이블명 비교 시 기본 case-insensitive 이지만,
            # 우리 schema 의 물리명은 모두 소문자로 통일되어 있다.
            existing = {row[0].lower() for row in cur.fetchall()}
    except sqlite3.Error as exc:
        reporter.fail("sqlite_master 조회", exc)
        return

    for table in REQUIRED_TABLES:
        if table not in existing:
            reporter.record(f"테이블 존재: {table}", ok=False, message="not found")
            continue

        try:
            with sqlite3.connect(str(db_path)) as conn:
                cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
            col_names = [c[1] for c in cols]
        except sqlite3.Error as exc:
            reporter.fail(f"테이블 컬럼 조회: {table}", exc)
            continue

        reporter.record(
            f"테이블 존재: {table}",
            ok=len(col_names) > 0,
            message=f"{len(col_names)} columns: {', '.join(col_names[:4])}...",
        )

    # 추가: signals 의 CHECK 제약(BUY/SELL/HOLD) 동작 확인
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                "INSERT INTO stocks (stock_code, name) VALUES (?, ?)",
                (TEST_PREFIX + "CHK", "SCHEMA_CHECK_DUMMY"),
            )
            try:
                conn.execute(
                    "INSERT INTO signals "
                    "(stock_code, signal_type, price, signaled_at) "
                    "VALUES (?, ?, ?, ?)",
                    (TEST_PREFIX + "CHK", "INVALID_TYPE", 1000, "2026-05-16T00:00:00"),
                )
                # 여기 도달하면 CHECK 제약이 동작하지 않은 것.
                reporter.record(
                    "CHECK 제약: signals.signal_type",
                    ok=False,
                    message="INVALID_TYPE 이 거부되지 않음",
                )
            except sqlite3.IntegrityError:
                reporter.record(
                    "CHECK 제약: signals.signal_type",
                    ok=True,
                    message="BUY/SELL/HOLD 외 값 거부 OK",
                )
            finally:
                conn.execute(
                    "DELETE FROM stocks WHERE stock_code = ?",
                    (TEST_PREFIX + "CHK",),
                )
                conn.commit()
    except sqlite3.Error as exc:
        reporter.fail("CHECK 제약: signals.signal_type", exc)


def step_crud(reporter: TestReporter, db_path: Path) -> None:
    """STEP 4: DBControl CRUD 일관성 검증."""
    _print_header(4, 5, "DBControl CRUD 동작 검증")

    try:
        db = DBControl(db_path=db_path)
    except Exception as exc:  # pragma: no cover
        reporter.fail("DBControl 인스턴스 생성", exc)
        return

    try:
        with db:
            # ---------- INSERT (stocks) ----------
            try:
                rowid = db.insert(
                    "stocks",
                    {
                        "stock_code": TEST_PREFIX + "001",
                        "name": "테스트반도체",
                        "market": "KOSPI",
                    },
                )
                reporter.record(
                    "INSERT: stocks",
                    ok=isinstance(rowid, int),
                    message=f"row inserted (stock_code={TEST_PREFIX + '001'})",
                )
            except DBControlError as exc:
                reporter.fail("INSERT: stocks", exc)

            # ---------- INSERT MANY (stocks) ----------
            try:
                affected = db.insert_many(
                    "stocks",
                    [
                        {"stock_code": TEST_PREFIX + "002", "name": "테스트메모리"},
                        {"stock_code": TEST_PREFIX + "003", "name": "테스트파운드리"},
                    ],
                )
                reporter.record(
                    "INSERT MANY: stocks",
                    ok=affected == 2,
                    message=f"affected={affected}",
                )
            except DBControlError as exc:
                reporter.fail("INSERT MANY: stocks", exc)

            # ---------- SELECT (fetch_one) ----------
            try:
                row = db.fetch_one(
                    "SELECT stock_code, name, market, is_active "
                    "FROM stocks WHERE stock_code = ?",
                    (TEST_PREFIX + "001",),
                )
                ok = row is not None and row["name"] == "테스트반도체"
                reporter.record(
                    "SELECT: fetch_one",
                    ok=ok,
                    message=str(row),
                )
            except DBControlError as exc:
                reporter.fail("SELECT: fetch_one", exc)

            # ---------- SELECT (fetch_all) ----------
            try:
                rows = db.fetch_all(
                    "SELECT stock_code FROM stocks WHERE stock_code LIKE ? "
                    "ORDER BY stock_code",
                    (TEST_PREFIX + "%",),
                )
                reporter.record(
                    "SELECT: fetch_all",
                    ok=len(rows) >= 3,
                    message=f"count={len(rows)}",
                )
            except DBControlError as exc:
                reporter.fail("SELECT: fetch_all", exc)

            # ---------- UPDATE ----------
            try:
                changed = db.update(
                    "stocks",
                    {"name": "테스트반도체(수정)"},
                    where="stock_code = ?",
                    where_params=(TEST_PREFIX + "001",),
                )
                row = db.fetch_one(
                    "SELECT name FROM stocks WHERE stock_code = ?",
                    (TEST_PREFIX + "001",),
                )
                ok = (
                    changed == 1
                    and row is not None
                    and row["name"] == "테스트반도체(수정)"
                )
                reporter.record(
                    "UPDATE: stocks",
                    ok=ok,
                    message=f"changed={changed}, name={row and row['name']}",
                )
            except DBControlError as exc:
                reporter.fail("UPDATE: stocks", exc)

            # ---------- UPSERT ----------
            try:
                db.upsert(
                    "stocks",
                    {
                        "stock_code": TEST_PREFIX + "001",
                        "name": "테스트반도체(업서트)",
                        "market": "KOSDAQ",
                    },
                    conflict_columns=["stock_code"],
                )
                row = db.fetch_one(
                    "SELECT market FROM stocks WHERE stock_code = ?",
                    (TEST_PREFIX + "001",),
                )
                reporter.record(
                    "UPSERT: stocks (PK 충돌 시 UPDATE)",
                    ok=row is not None and row["market"] == "KOSDAQ",
                    message=f"market={row and row['market']}",
                )
            except DBControlError as exc:
                reporter.fail("UPSERT: stocks", exc)

            # ---------- 자식 테이블 INSERT (FK 확인) ----------
            try:
                db.insert(
                    "financials",
                    {
                        "stock_code": TEST_PREFIX + "001",
                        "record_date": "2026-05-16",
                        "open_price": 100.0,
                        "high_price": 110.0,
                        "low_price": 95.0,
                        "close_price": 105.0,
                        "volume": 1234567,
                        "per": 12.3,
                        "pbr": 1.4,
                        "eps": 8500.0,
                    },
                )
                db.insert(
                    "news",
                    {
                        "stock_code": TEST_PREFIX + "001",
                        "title": "테스트용 뉴스 헤드라인",
                        "summary": "통합 테스트용 더미 기사",
                        "cleaned_text": "본문 정제 후 결과",
                        "source": "integration_test",
                        "url": "https://example.test/news/1",
                        "published_at": "2026-05-16T09:00:00",
                    },
                )
                db.insert(
                    "signals",
                    {
                        "stock_code": TEST_PREFIX + "001",
                        "signal_type": "BUY",
                        "price": 105.0,
                        "band_low": 110.0,
                        "band_high": 130.0,
                        "sentiment_score": -75.0,
                        "rationale": "현재가<밴드하단 & 감성=-75",
                        "signaled_at": "2026-05-16T10:00:00",
                    },
                )
                reporter.record(
                    "INSERT: financials/news/signals (FK 정상)",
                    ok=True,
                    message="외래키 정상 적재",
                )
            except DBControlError as exc:
                reporter.fail("INSERT: financials/news/signals", exc)

            # ---------- TRANSACTION rollback ----------
            try:
                pre = db.fetch_one(
                    "SELECT name FROM stocks WHERE stock_code = ?",
                    (TEST_PREFIX + "001",),
                )
                try:
                    with db.transaction() as conn:
                        conn.execute(
                            "UPDATE stocks SET name = ? WHERE stock_code = ?",
                            ("롤백되어야_할_이름", TEST_PREFIX + "001"),
                        )
                        raise RuntimeError("의도된 예외 (rollback 검증)")
                except RuntimeError:
                    pass
                post = db.fetch_one(
                    "SELECT name FROM stocks WHERE stock_code = ?",
                    (TEST_PREFIX + "001",),
                )
                ok = (
                    pre is not None
                    and post is not None
                    and pre["name"] == post["name"]
                )
                reporter.record(
                    "TRANSACTION rollback",
                    ok=ok,
                    message=f"pre={pre and pre['name']} / post={post and post['name']}",
                )
            except DBControlError as exc:
                reporter.fail("TRANSACTION rollback", exc)
    except Exception as exc:  # pragma: no cover
        reporter.fail("DBControl 컨텍스트 블록", exc)


def step_cleanup(
    reporter: TestReporter,
    db_path: Path,
    *,
    purge_db: bool,
) -> None:
    """STEP 5: 더미 데이터 정리 + (옵션) DB 파일 삭제."""
    _print_header(5, 5, "더미 데이터 정리 (cleanup)")

    # 1) 자식 테이블 row 개수 사전 확인 (CASCADE 검증용)
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            child_counts_before = {}
            for tbl in ("financials", "news", "signals"):
                cur = conn.execute(
                    f"SELECT COUNT(*) FROM {tbl} WHERE stock_code LIKE ?",
                    (TEST_PREFIX + "%",),
                )
                child_counts_before[tbl] = cur.fetchone()[0]
    except sqlite3.Error as exc:
        reporter.fail("cleanup 사전 카운트", exc)
        child_counts_before = {}

    # 2) DBControl 을 통한 일괄 삭제 (stocks 만 지워도 FK CASCADE 로 자식도 정리)
    try:
        with DBControl(db_path=db_path) as db:
            deleted = db.delete(
                "stocks",
                where="stock_code LIKE ?",
                where_params=(TEST_PREFIX + "%",),
            )
        reporter.record(
            "DELETE: stocks WHERE stock_code LIKE 'TST_%'",
            ok=deleted >= 0,
            message=f"deleted={deleted}",
        )
    except DBControlError as exc:
        reporter.fail("DELETE: stocks (cleanup)", exc)

    # 3) CASCADE 동작 확인 - 자식 테이블에 더미가 남았는지
    try:
        with sqlite3.connect(str(db_path)) as conn:
            remaining = {}
            for tbl in ("financials", "news", "signals"):
                cur = conn.execute(
                    f"SELECT COUNT(*) FROM {tbl} WHERE stock_code LIKE ?",
                    (TEST_PREFIX + "%",),
                )
                remaining[tbl] = cur.fetchone()[0]
        all_clean = all(v == 0 for v in remaining.values())
        reporter.record(
            "CASCADE 정리 (자식 테이블 잔존 0)",
            ok=all_clean,
            message=(
                f"before={child_counts_before}, after={remaining}"
                if child_counts_before
                else f"after={remaining}"
            ),
        )
    except sqlite3.Error as exc:
        reporter.fail("CASCADE 정리 확인", exc)

    # 4) DB 무결성 검사
    try:
        with sqlite3.connect(str(db_path)) as conn:
            integrity = conn.execute("PRAGMA integrity_check;").fetchone()
        ok = integrity is not None and str(integrity[0]).lower() == "ok"
        reporter.record(
            "PRAGMA integrity_check",
            ok=ok,
            message=str(integrity[0]) if integrity else "no result",
        )
    except sqlite3.Error as exc:
        reporter.fail("PRAGMA integrity_check", exc)

    # 5) (옵션) DB 파일 자체 삭제
    if purge_db:
        try:
            if os.path.isfile(str(db_path)):
                os.remove(str(db_path))
            reporter.record(
                "DB 파일 삭제(--purge-db)",
                ok=not os.path.isfile(str(db_path)),
                message=str(db_path),
            )
        except OSError as exc:
            reporter.fail("DB 파일 삭제(--purge-db)", exc)


# ---------------------------------------------------------------------------
# 5. 메인 진입점 (스크립트 모드)
# ---------------------------------------------------------------------------
def _print_banner(db_path: Path) -> None:
    bar = "=" * 60
    print(bar)
    print(f"{_Color.BOLD} Semi Senti - Phase 1-1 Integration Verification{_Color.RESET}")
    print(bar)
    print(f" Project Root : {PROJECT_ROOT}")
    print(f" Target DB    : {db_path}")
    print(f" Python       : {sys.version.split()[0]}")
    print(bar)


def run_verification(*, purge_db: bool = False) -> int:
    """전체 검증 실행. 종료 코드(0=성공, 1=실패)를 반환한다."""
    _try_enable_color()

    db_path = (PROJECT_ROOT / "db" / "semisenti.db").resolve()
    _print_banner(db_path)

    reporter = TestReporter()
    try:
        step_check_directories(reporter)

        db_ready = step_init_db(reporter, db_path)
        if db_ready:
            step_verify_tables(reporter, db_path)
            step_crud(reporter, db_path)
        else:
            print(
                f"  {_Color.YELLOW}[WARN]{_Color.RESET} "
                "DB 초기화 실패로 STEP 3·4 를 건너뜁니다."
            )

        # cleanup 은 DB 파일이 어떻게든 생성되어 있다면 시도한다.
        if os.path.isfile(str(db_path)):
            step_cleanup(reporter, db_path, purge_db=purge_db)
        else:
            reporter.record(
                "cleanup 스킵",
                ok=False,
                message="DB 파일이 존재하지 않아 정리를 건너뜀",
            )
    except KeyboardInterrupt:
        print("\n[중단] 사용자에 의해 중단되었습니다.")
        reporter.print_summary()
        return 130

    reporter.print_summary()
    return 0 if reporter.failed_count == 0 else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test_phase1_1",
        description="Phase 1-1 (T-001~T-004) 통합 검증 스크립트",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--keep-db",
        dest="purge_db",
        action="store_false",
        help="검증 종료 후 DB 파일을 보존한다 (기본값)",
    )
    group.add_argument(
        "--purge-db",
        dest="purge_db",
        action="store_true",
        help="검증 종료 후 DB 파일도 삭제한다",
    )
    parser.set_defaults(purge_db=False)
    return parser


# ---------------------------------------------------------------------------
# 6. unittest 호환 래퍼
#    `python -m unittest tests.integration.test_phase1_1` 형태로도 실행되도록
#    얇은 TestCase 한 개를 노출한다.
# ---------------------------------------------------------------------------
class Phase11IntegrationTest(unittest.TestCase):
    """unittest 디스커버리 호환용 래퍼."""

    def test_full_phase_1_1(self) -> None:
        exit_code = run_verification(purge_db=False)
        self.assertEqual(exit_code, 0, "Phase 1-1 통합 검증에서 실패한 항목이 있습니다.")


if __name__ == "__main__":
    args = _build_parser().parse_args()
    sys.exit(run_verification(purge_db=args.purge_db))
