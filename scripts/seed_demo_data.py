# -*- coding: utf-8 -*-
"""삼성전자·SK하이닉스 데모 데이터 일괄 수집·분석 (UTF-8).

권장: ``python -m semi_senti bootstrap`` 또는 루트 ``run.bat`` / ``run.sh``
"""
from __future__ import annotations

import sys

from semi_senti.bootstrap import print_bootstrap_report, run_bootstrap


def main() -> int:
    report = run_bootstrap(force=True)
    print_bootstrap_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
