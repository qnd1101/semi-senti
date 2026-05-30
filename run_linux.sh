#!/usr/bin/env bash
# =============================================================================
# Semi Senti — Linux/macOS Launcher (PRD v1.2)
# =============================================================================
#   1. Python/JDK/Node.js 확인
#   2. 가상환경 + requirements.txt (psycopg2-binary, pykrx 포함)
#   3. .env 확인 (DATABASE_URL 필수)
#   4. DB 초기화 (db_seed.py)
#   5. FastAPI 시작 (http://localhost:8001)
#   6. Next.js 대시보드 (http://localhost:3000)
#
# 사용법:
#   chmod +x run_linux.sh
#   ./run_linux.sh
#   ./run_linux.sh --bg    # 백그라운드 (api.log)
#
# 사전 요구사항: Python 3.12, JDK 1.8+, Node.js 20+, PostgreSQL 15+
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "===================================================================="
echo "  Semi Senti — Linux/macOS Launcher (PRD v1.2)"
echo "===================================================================="
echo ""

log_info "[1/6] Checking environment..."

if ! command -v python3.12 &> /dev/null; then
    log_error "Python 3.12 is not installed or not in PATH."
    exit 1
fi
log_success "Python $(python3.12 --version | awk '{print $2}') found."

if ! command -v java &> /dev/null; then
    log_warning "JDK not found. KoNLPy NLP will not work."
else
    log_success "Java found."
fi

NO_NODE=false
if ! command -v node &> /dev/null; then
    log_warning "Node.js not found. Web dashboard will not start."
    NO_NODE=true
else
    log_success "Node.js $(node --version) found."
fi

echo ""

log_info "[2/6] Setting up Python virtual environment..."

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d ".venv" ]]; then
    python3.12 -m venv .venv
    log_success "Virtual environment created."
else
    log_success "Virtual environment exists."
fi

source .venv/bin/activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
log_success "Python dependencies installed (psycopg2-binary, pykrx included)."

echo ""

log_info "[3/6] Checking .env..."

if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        log_warning ".env created from .env.example — edit DATABASE_URL and API keys before use!"
    else
        log_error ".env.example not found."
        exit 1
    fi
else
    log_success ".env file exists."
fi

echo ""

log_info "[4/6] Initializing database (PostgreSQL)..."

python db_seed.py || log_warning "db_seed.py failed. Check DATABASE_URL in .env."

echo ""

API_PORT="${API_PORT:-8001}"
BACKGROUND=false
if [[ "$1" == "--bg" || "$1" == "-b" ]]; then
    BACKGROUND=true
fi

log_info "[5/6] Starting FastAPI (http://localhost:${API_PORT})..."

if lsof -Pi :"${API_PORT}" -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    log_warning "Port ${API_PORT} is already in use — skipping API start."
else
    if [[ "$BACKGROUND" == true ]]; then
        API_PORT="${API_PORT}" nohup python -m semi_senti.api > api.log 2>&1 &
        log_success "FastAPI started in background (log: api.log)"
        sleep 2
    else
        API_PORT="${API_PORT}" python -m semi_senti.api &
        API_PID=$!
        log_success "FastAPI starting (PID: $API_PID)"
        sleep 2
    fi
fi

echo ""

if [[ "$NO_NODE" == false ]]; then
    log_info "[6/6] Starting Next.js dashboard (http://localhost:3000)..."
    if [[ -f "web/package.json" ]]; then
        cd web
        if [[ ! -d "node_modules" ]]; then
            npm install --quiet
        fi
        if [[ "$BACKGROUND" == true ]]; then
            nohup npm run dev > ../web.log 2>&1 &
            log_success "Next.js started in background (log: web.log)"
        else
            npm run dev &
            WEB_PID=$!
            log_success "Next.js starting (PID: $WEB_PID)"
        fi
        cd "$ROOT"
    else
        log_warning "web/package.json not found. Skipping web dashboard."
    fi
else
    log_info "[6/6] Skipping Next.js (Node.js not found)."
fi

echo ""
echo "===================================================================="
echo "  Services:"
echo "  - FastAPI:    http://localhost:${API_PORT}"
echo "  - API Docs:   http://localhost:${API_PORT}/docs"
echo "  - Dashboard:  http://localhost:3000"
echo "===================================================================="
echo ""

if [[ "$BACKGROUND" == false ]]; then
    wait
fi
