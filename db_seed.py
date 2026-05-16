# -*- coding: utf-8 -*-
"""Semi Senti - 데이터베이스 초기화 및 시딩 부트스트랩 스크립트.

이 스크립트는 ``git clone`` 직후 setup.sh/setup.bat 의 마지막 단계에서
자동으로 실행되며, 다음 작업을 수행합니다.

    1) ``semi_senti.db.init_database()`` 호출
       → SQLite 파일(.env 의 ``SEMI_SENTI_SQLITE_PATH``)과
         핵심 7개 테이블(stocks/financials/news/signals/sentiment_scores/
         notifications/cycle_scores) 스키마 생성.
    2) ``stocks`` 테이블에 기본 분석 기업(삼성전자 005930, SK하이닉스 000660)
       Upsert (재실행 시 멱등).
    3) ``financials`` 테이블에 두 기업의 기초 펀더멘털 더미 데이터를
       (해당 종목 row 가 없을 때만) ``DBControl`` 기반으로 적재.

CLI 실행::

    python db_seed.py
    python db_seed.py --force         # 기존 financials 더미 데이터 무시하고 재적재
    python db_seed.py --reset-db      # DB 파일 삭제 후 처음부터 재생성 (개발 편의)

종료 코드:
    0 : 정상 완료
    1 : DB 초기화 실패
    2 : 시딩 단계 실패 (stocks/financials)
    3 : 예기치 못한 예외
"""
from __future__ import annotations

import argparse
import logging
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

# -----------------------------------------------------------------------------
# import 경로 폴백
# - setup.sh/setup.bat 는 `pip install -e . --no-deps` 를 함께 실행하므로
#   기본적으로 site-packages 경유로 import 가 성공합니다.
# - 그러나 사용자가 venv 활성화 없이 단독 실행할 가능성을 대비해
#   `<repo>/src` 를 sys.path 에 보강합니다.
# -----------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent
_SRC_DIR = _PROJECT_ROOT / "src"
if _SRC_DIR.is_dir() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

try:
    from semi_senti.db import DBControl, DBControlError, init_database  # noqa: E402
    from semi_senti.db.init_db import DatabaseInitError  # noqa: E402
except ImportError as exc:  # pragma: no cover - 의존성/경로 미설치 시 진단용
    sys.stderr.write(
        "[FAIL] semi_senti 패키지를 import 하지 못했습니다.\n"
        f"       원인: {exc}\n"
        "       해결: 1) `pip install -r requirements.txt` 가 정상 완료됐는지 확인\n"
        "              2) `pip install -e . --no-deps` 로 로컬 패키지를 설치했는지 확인\n"
        "              3) 가상환경(.venv)이 활성화돼 있는지 확인\n"
    )
    sys.exit(3)


_LOGGER = logging.getLogger("semi_senti.db_seed")


# =============================================================================
# 시딩 데이터 정의 (하드코딩이 아닌 "더미/샘플" 데이터)
# - 실제 시세/재무는 collector 모듈이 채워 넣지만,
#   클론 직후 테스트가 즉시 가능하도록 펀더멘털 컬럼 전부에 값을 부여합니다.
# - 단위: revenue/operating_profit 은 KRW(원), per/pbr/eps 는 배·원, volume 은 주.
# =============================================================================

# stocks 테이블 기본 적재 대상 (PRD §2: 삼성전자/SK하이닉스 2종).
_DEFAULT_STOCKS: Sequence[Mapping[str, object]] = (
    {
        "stock_code": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "is_active": 1,
    },
    {
        "stock_code": "000660",
        "name": "SK하이닉스",
        "market": "KOSPI",
        "is_active": 1,
    },
)


def _build_dummy_financial_rows(
    stock_code: str,
    *,
    base_close: float,
    base_volume: int,
    quarter_revenue: float,
    quarter_op_profit: float,
    per: float,
    pbr: float,
    eps: float,
    rows: int = 7,
) -> List[Dict[str, object]]:
    """단일 종목의 더미 일별 financials 레코드를 생성.

    - 최근 ``rows`` 일자에 대해 종가가 ±3% 범위로 살짝 변동하는 시계열을 만든다.
    - 분기 재무지표(revenue/operating_profit/per/pbr/eps)는 같은 분기 스냅샷
      이므로 모든 일자 row 에 동일하게 복제 적재한다(시장 통념).
    """
    today = date.today()
    series: List[Dict[str, object]] = []
    for i in range(rows):
        # 가장 최근 일자가 idx=0 → 과거로 갈수록 i 증가.
        record_dt = today - timedelta(days=i)
        # 종가에 ±3% 이내 노이즈 (i 가 클수록 더 낮게 - 단순 우상향 가정).
        drift_pct = 1.0 - (i * 0.005)
        close = round(base_close * drift_pct, 1)
        open_p = round(close * 0.998, 1)
        high_p = round(close * 1.012, 1)
        low_p = round(close * 0.988, 1)
        volume = int(base_volume * (1.0 + (i % 3) * 0.05))

        series.append(
            {
                "stock_code": stock_code,
                "record_date": record_dt.isoformat(),
                "open_price": open_p,
                "high_price": high_p,
                "low_price": low_p,
                "close_price": close,
                "volume": volume,
                "revenue": quarter_revenue,
                "operating_profit": quarter_op_profit,
                "per": per,
                "pbr": pbr,
                "eps": eps,
                "currency": "KRW",
            }
        )
    return series


# 종목별 펀더멘털 더미 데이터 (단위: KRW).
# - 실제 분기 보고서 수치와는 무관한 샘플 값이며, 대시보드/시그널 로직이
#   정상 동작함을 확인하기 위한 "비-NULL" 충족용입니다.
_SAMPLE_FINANCIAL_PROFILES: Dict[str, Dict[str, float]] = {
    "005930": {  # 삼성전자
        "base_close": 78500.0,
        "base_volume": 15_000_000,
        "quarter_revenue": 71_200_000_000_000.0,   # 약 71.2조
        "quarter_op_profit": 6_500_000_000_000.0,  # 약 6.5조
        "per": 14.5,
        "pbr": 1.35,
        "eps": 5400.0,
    },
    "000660": {  # SK하이닉스
        "base_close": 198_000.0,
        "base_volume": 4_500_000,
        "quarter_revenue": 17_300_000_000_000.0,   # 약 17.3조
        "quarter_op_profit": 5_100_000_000_000.0,  # 약 5.1조
        "per": 11.8,
        "pbr": 2.15,
        "eps": 16800.0,
    },
}


# =============================================================================
# 단계별 실행 함수
# =============================================================================

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
    )


def _step_init_db(force_reset: bool) -> Path:
    """1단계: DB 파일과 전체 스키마 생성."""
    print("[STEP 1/3] DB 초기화 (init_database) ...")
    try:
        db_path = init_database(force=force_reset)
    except DatabaseInitError as exc:
        print(f"[FAIL] DB 초기화 실패: {exc}")
        print("       - SQLite 파일 경로 권한(.env의 SEMI_SENTI_SQLITE_PATH) 확인")
        print("       - 디스크 용량 / 읽기전용 마운트 여부 확인")
        raise
    print(f"[ OK ] DB 스키마 준비 완료 → {db_path}")
    return db_path


def _step_seed_stocks(db: DBControl) -> int:
    """2단계: stocks 테이블에 기본 종목 upsert."""
    print("[STEP 2/3] stocks 테이블 시딩 (삼성전자/SK하이닉스) ...")
    affected = 0
    try:
        for row in _DEFAULT_STOCKS:
            n = db.upsert(
                "stocks",
                dict(row),
                conflict_columns=["stock_code"],
                update_columns=["name", "market", "is_active"],
            )
            print(f"        - upsert stocks[{row['stock_code']}] ({row['name']}): {n} row")
            affected += n
    except DBControlError as exc:
        print(f"[FAIL] stocks 시딩 실패: {exc}")
        print("       - DB 파일 권한 / 락(.db-journal) 여부 확인")
        raise
    print(f"[ OK ] stocks 시딩 완료 (총 {affected} row 반영)")
    return affected


def _financials_has_rows(db: DBControl, stock_code: str) -> bool:
    """해당 종목의 financials row 가 1건이라도 있는지."""
    row = db.fetch_one(
        "SELECT COUNT(*) AS cnt FROM financials WHERE stock_code = ?;",
        (stock_code,),
    )
    return bool(row and int(row["cnt"]) > 0)


def _step_seed_financials(db: DBControl, *, force: bool) -> int:
    """3단계: financials 더미 데이터 적재 (없을 때만)."""
    print("[STEP 3/3] financials 더미 데이터 시딩 ...")
    total_inserted = 0
    try:
        for code, profile in _SAMPLE_FINANCIAL_PROFILES.items():
            already = _financials_has_rows(db, code)
            if already and not force:
                print(f"        - skip financials[{code}]: 이미 데이터 존재 (force 사용 시 덮어쓰기)")
                continue

            rows = _build_dummy_financial_rows(
                code,
                base_close=profile["base_close"],
                base_volume=int(profile["base_volume"]),
                quarter_revenue=profile["quarter_revenue"],
                quarter_op_profit=profile["quarter_op_profit"],
                per=profile["per"],
                pbr=profile["pbr"],
                eps=profile["eps"],
            )

            inserted_for_code = 0
            # UNIQUE(stock_code, record_date) 충돌 시 갱신 (= 멱등 보장).
            for row in rows:
                n = db.upsert(
                    "financials",
                    row,
                    conflict_columns=["stock_code", "record_date"],
                    update_columns=[
                        "open_price", "high_price", "low_price", "close_price",
                        "volume", "revenue", "operating_profit",
                        "per", "pbr", "eps", "currency",
                    ],
                )
                inserted_for_code += n
            print(f"        - upsert financials[{code}]: {inserted_for_code} row")
            total_inserted += inserted_for_code

    except DBControlError as exc:
        print(f"[FAIL] financials 시딩 실패: {exc}")
        print("       - DB 파일 잠금 여부(.db-journal) 또는 디스크 권한 확인")
        raise
    print(f"[ OK ] financials 시딩 완료 (총 {total_inserted} row 반영)")
    return total_inserted


def _print_summary(db: DBControl) -> None:
    """완료 후 적재 결과 요약."""
    print("\n=========================  SEEDING SUMMARY  =========================")
    try:
        stocks = db.fetch_all(
            "SELECT stock_code, name, market, is_active "
            "FROM stocks ORDER BY stock_code;"
        )
        print(f"  stocks rows : {len(stocks)}")
        for s in stocks:
            print(
                f"    - {s['stock_code']} {s['name']:<10} "
                f"market={s['market']:<6} active={s['is_active']}"
            )

        fin_summary = db.fetch_all(
            "SELECT stock_code, COUNT(*) AS rows, "
            "       MIN(record_date) AS first_date, MAX(record_date) AS last_date "
            "FROM financials GROUP BY stock_code ORDER BY stock_code;"
        )
        print(f"  financials  : {sum(int(r['rows']) for r in fin_summary)} rows total")
        for r in fin_summary:
            print(
                f"    - {r['stock_code']}: {r['rows']} rows  "
                f"({r['first_date']} ~ {r['last_date']})"
            )
    except DBControlError as exc:  # pragma: no cover - summary 단계는 비-크리티컬
        print(f"  [warn] 요약 조회 실패: {exc}")
    print("=====================================================================\n")


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="db_seed.py",
        description="Semi Senti SQLite DB 초기화 + 기본 데이터 시딩",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="financials 에 데이터가 이미 있어도 더미 데이터를 덮어쓴다(upsert).",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="기존 DB 파일을 삭제하고 처음부터 다시 생성한다 (개발 편의).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="DEBUG 로그까지 출력한다.",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    _setup_logging(args.verbose)

    print("=====================================================================")
    print("  Semi Senti - Database Seeding (db_seed.py)")
    print("=====================================================================")
    print(f"  project root : {_PROJECT_ROOT}")
    print(f"  options      : force={args.force}, reset-db={args.reset_db}, verbose={args.verbose}")
    print()

    # 1) DB 초기화 -----------------------------------------------------------
    try:
        db_path = _step_init_db(force_reset=args.reset_db)
    except DatabaseInitError:
        return 1
    except Exception:  # noqa: BLE001
        print("[FAIL] DB 초기화 중 예기치 못한 오류:")
        traceback.print_exc()
        return 3

    # 2~3) DBControl 으로 시딩 -----------------------------------------------
    try:
        with DBControl(db_path=db_path) as db:
            _step_seed_stocks(db)
            _step_seed_financials(db, force=args.force)
            _print_summary(db)
    except DBControlError:
        return 2
    except Exception:  # noqa: BLE001
        print("[FAIL] 시딩 중 예기치 못한 오류:")
        traceback.print_exc()
        return 3

    print("[DONE] Semi Senti DB 시딩이 정상적으로 끝났습니다.")
    print("       이제 다음 명령으로 분석을 시작할 수 있습니다:")
    print("         python -m semi_senti admin list")
    print("         python -m semi_senti analyze signal --stock-code 005930")
    return 0


if __name__ == "__main__":
    sys.exit(main())
