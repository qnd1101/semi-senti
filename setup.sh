#!/usr/bin/env bash
# =============================================================================
# Semi Senti - One-Shot Bootstrap Script (Linux / macOS)
# -----------------------------------------------------------------------------
# 사용법:
#   chmod +x setup.sh
#   ./setup.sh
#
# 수행 단계:
#   1) Python 3.8+ 인터프리터 탐색
#   2) ./.venv 가상환경 생성 (이미 있으면 재사용)
#   3) pip 업그레이드 + requirements.txt 설치 + 로컬 패키지 editable 설치
#   4) .env 파일 부재 시 .env.example → .env 복사
#   5) db_seed.py 자동 실행 (DB 초기화 + 기본 종목·재무 시딩)
#
# 종료 코드(끝까지 도달하지 못했을 경우):
#   10  Python 미설치 / 버전 부적합
#   20  가상환경 생성 실패
#   30  pip 패키지 설치 실패
#   40  db_seed.py 실행 실패
# =============================================================================

set -u

# ----- 색상 (TTY 일 때만) ----------------------------------------------------
if [ -t 1 ]; then
    C_BOLD="$(printf '\033[1m')"
    C_DIM="$(printf '\033[2m')"
    C_RED="$(printf '\033[31m')"
    C_GRN="$(printf '\033[32m')"
    C_YLW="$(printf '\033[33m')"
    C_RST="$(printf '\033[0m')"
else
    C_BOLD=""; C_DIM=""; C_RED=""; C_GRN=""; C_YLW=""; C_RST=""
fi

log_step()  { echo "${C_BOLD}[STEP]${C_RST} $*"; }
log_ok()    { echo "${C_GRN}[ OK ]${C_RST} $*"; }
log_warn()  { echo "${C_YLW}[WARN]${C_RST} $*"; }
log_fail()  { echo "${C_RED}[FAIL]${C_RST} $*" >&2; }
log_info()  { echo "${C_DIM}       $*${C_RST}"; }

# 스크립트가 위치한 디렉터리 = 프로젝트 루트로 가정.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR" || { log_fail "프로젝트 루트로 이동 실패: $SCRIPT_DIR"; exit 1; }

echo "====================================================================="
echo "  Semi Senti - Bootstrap (Linux / macOS)"
echo "====================================================================="
echo "  project root : $SCRIPT_DIR"
echo "  shell        : ${SHELL:-unknown}"
echo "  uname        : $(uname -srm 2>/dev/null || echo 'n/a')"
echo "====================================================================="
echo

# -----------------------------------------------------------------------------
# 1) Python 인터프리터 탐색 (3.8+)
# -----------------------------------------------------------------------------
log_step "1/5 Python 3.8+ 인터프리터 탐색"

PYTHON_BIN=""
# pandas 2.1.x 호환을 고려해 3.12 → 3.11 → 3.10 → 3.9 → 3.8 → python3 → python 순으로 탐색.
for candidate in python3.12 python3.11 python3.10 python3.9 python3.8 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    log_fail "Python 3.8 이상이 감지되지 않았습니다."
    log_info "macOS:  brew install python@3.12"
    log_info "Ubuntu: sudo apt-get install -y python3 python3-venv python3-pip"
    exit 10
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import platform; print(platform.python_version())')"
log_ok "Python 발견: $PYTHON_BIN (v$PY_VERSION)"
echo

# -----------------------------------------------------------------------------
# 2) 가상환경 생성
# -----------------------------------------------------------------------------
log_step "2/5 가상환경(.venv) 생성"

VENV_DIR="$SCRIPT_DIR/.venv"
if [ -d "$VENV_DIR" ] && [ -x "$VENV_DIR/bin/python" ]; then
    log_ok ".venv 이미 존재 → 재사용 ($VENV_DIR)"
else
    log_info "venv 생성 중: $VENV_DIR"
    if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
        log_fail "가상환경 생성 실패"
        log_info "Ubuntu에서 'ensurepip is not available' 오류 시: sudo apt-get install -y python3-venv"
        exit 20
    fi
    log_ok ".venv 생성 완료"
fi

VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
if [ ! -x "$VENV_PY" ]; then
    log_fail ".venv/bin/python 이 실행 가능하지 않습니다: $VENV_PY"
    exit 20
fi

# 셸이 종료돼도 다음 명령이 venv 의 python 을 사용하도록 활성화.
# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate" || { log_fail ".venv 활성화 실패"; exit 20; }
log_info "활성화된 python: $(command -v python)"
echo

# -----------------------------------------------------------------------------
# 3) pip 업그레이드 + 의존성 설치
# -----------------------------------------------------------------------------
log_step "3/5 pip 업그레이드 및 requirements.txt 설치"

if ! "$VENV_PY" -m pip install --upgrade pip setuptools wheel; then
    log_fail "pip 업그레이드 실패 (네트워크/프록시 확인)"
    exit 30
fi

REQ_FILE="$SCRIPT_DIR/requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
    log_fail "requirements.txt 가 없습니다: $REQ_FILE"
    exit 30
fi

log_info "pip install -r requirements.txt ..."
if ! "$VENV_PY" -m pip install -r "$REQ_FILE"; then
    log_fail "requirements.txt 설치 실패"
    log_info "원인 후보:"
    log_info "  - macOS arm64 + 일부 wheel 부재: Python 3.12 권장"
    log_info "  - Ubuntu에서 빌드 도구 부재: sudo apt-get install -y build-essential python3-dev"
    log_info "  - 사내 프록시: pip 인증/방화벽 확인 (https_proxy 환경 변수)"
    exit 30
fi
log_ok "requirements.txt 의존성 설치 완료"

# 로컬 패키지(editable) 설치 → `from semi_senti.db import ...` 가능.
# 의존성은 위에서 이미 고정 버전으로 설치했으므로 --no-deps 로 충돌 회피.
log_info "로컬 패키지 editable 설치 (pip install -e . --no-deps) ..."
if ! "$VENV_PY" -m pip install -e "$SCRIPT_DIR" --no-deps; then
    log_warn "editable 설치 실패 → db_seed.py 는 sys.path 폴백으로 동작합니다."
fi
echo

# -----------------------------------------------------------------------------
# 4) .env 파일 보강
# -----------------------------------------------------------------------------
log_step "4/5 .env 파일 점검"
if [ -f "$SCRIPT_DIR/.env" ]; then
    log_ok ".env 이미 존재 → 그대로 사용"
elif [ -f "$SCRIPT_DIR/.env.example" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    log_ok ".env.example → .env 복사 (API 키 등은 직접 채워주세요)"
else
    log_warn ".env 와 .env.example 모두 없음 → 기본값으로 동작합니다"
fi
echo

# -----------------------------------------------------------------------------
# 5) DB 초기화 + 시딩
# -----------------------------------------------------------------------------
log_step "5/5 DB 초기화 및 시딩 (db_seed.py 실행)"

SEED_SCRIPT="$SCRIPT_DIR/db_seed.py"
if [ ! -f "$SEED_SCRIPT" ]; then
    log_fail "db_seed.py 가 없습니다: $SEED_SCRIPT"
    exit 40
fi

if ! "$VENV_PY" "$SEED_SCRIPT"; then
    log_fail "db_seed.py 실행 실패"
    log_info "원인 후보:"
    log_info "  - SQLite 파일 권한: ls -l ./db/ (없으면 자동 생성, 디렉터리 쓰기 권한 필요)"
    log_info "  - .env 의 SEMI_SENTI_SQLITE_PATH 가 잘못 지정된 경우"
    log_info "  - pip 설치는 됐지만 semi_senti import 실패: pip install -e . --no-deps 수동 실행"
    exit 40
fi
echo

echo "====================================================================="
log_ok "Semi Senti 환경 구축이 모두 끝났습니다."
echo "  활성화: source .venv/bin/activate"
echo "  대시보드: python -m semi_senti dashboard"
echo "====================================================================="
