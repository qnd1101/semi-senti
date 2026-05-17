#!/usr/bin/env bash
# =============================================================================
# Semi Senti — Linux/macOS 1-Click Launcher
# =============================================================================
# 이 스크립트는 다음 작업을 자동으로 수행합니다:
#   1. OS 및 셸 환경 확인
#   2. Python/Node.js/JDK 환경 확인
#   3. Python 가상환경 생성 및 활성화 (없으면 자동 생성)
#   4. Python 의존성 설치 (requirements.txt)
#   5. .env 파일 존재 확인 및 샘플 복사
#   6. Next.js 의존성 설치 (web/node_modules)
#   7. Next.js 개발 서버 시작 (http://localhost:3000)
#   8. 브라우저 자동 오픈
#
# 요구사항:
#   - Python 3.8+
#   - JDK 1.8+
#   - Node.js 20 LTS
#   - npm 9+
#
# 사용법:
#   chmod +x run_linux.sh   # 실행 권한 부여 (최초 1회)
#   ./run_linux.sh          # 실행
#   ./run_linux.sh --bg     # 백그라운드 실행 (옵션)
# =============================================================================

set -e  # 오류 발생 시 즉시 종료

# 색상 정의 (터미널 출력용)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 배너 출력
echo ""
echo "===================================================================="
echo "  Semi Senti — Linux/macOS 1-Click Launcher"
echo "===================================================================="
echo ""

# -----------------------------------------------------------------------------
# 0. OS 및 권한 확인
# -----------------------------------------------------------------------------

log_info "[0/7] Checking OS and permissions..."

# OS 종류 확인
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    OPEN_CMD="xdg-open"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    OPEN_CMD="open"
else
    log_warning "Unknown OS: $OSTYPE"
    OS="Unknown"
    OPEN_CMD="echo"
fi
log_success "Detected OS: $OS"

# 실행 권한 확인
if [[ ! -x "$0" ]]; then
    log_warning "This script is not executable."
    log_info "Run: chmod +x $0"
    exit 1
fi

echo ""

# -----------------------------------------------------------------------------
# 1. 환경 확인 (Python / Node.js / JDK)
# -----------------------------------------------------------------------------

log_info "[1/7] Checking environment..."

# Python 확인
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed or not in PATH."
    log_info "Install Python 3.8+ from: https://www.python.org/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log_success "Python $PYTHON_VERSION found."

# Node.js 확인
if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed or not in PATH."
    log_info "Install Node.js 20 LTS from: https://nodejs.org/"
    exit 1
fi
NODE_VERSION=$(node --version)
log_success "Node.js $NODE_VERSION found."

# npm 확인
if ! command -v npm &> /dev/null; then
    log_error "npm is not installed or not in PATH."
    exit 1
fi
NPM_VERSION=$(npm --version)
log_success "npm $NPM_VERSION found."

# JDK 확인 (KoNLPy 필수)
if ! command -v java &> /dev/null; then
    log_warning "Java (JDK) is not installed or not in PATH."
    log_warning "JDK 1.8+ is required for KoNLPy (NLP engine)."
    log_info "Download from: https://adoptium.net/"
    echo ""
    read -p "Continue anyway? (NLP features will not work) [y/N]: " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    JAVA_VERSION=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}')
    log_success "Java $JAVA_VERSION found."
fi

echo ""

# -----------------------------------------------------------------------------
# 2. Python 가상환경 생성 및 활성화
# -----------------------------------------------------------------------------

log_info "[2/7] Setting up Python virtual environment..."

if [[ ! -d ".venv" ]]; then
    log_info "Creating new virtual environment..."
    python3 -m venv .venv
    log_success "Virtual environment created."
else
    log_success "Virtual environment already exists."
fi

# 가상환경 활성화
source .venv/bin/activate
if [[ $? -ne 0 ]]; then
    log_error "Failed to activate virtual environment."
    exit 1
fi
log_success "Virtual environment activated."

echo ""

# -----------------------------------------------------------------------------
# 3. Python 의존성 설치
# -----------------------------------------------------------------------------

log_info "[3/7] Installing Python dependencies..."

if [[ ! -f "requirements.txt" ]]; then
    log_error "requirements.txt not found in project root."
    exit 1
fi

# pip 업그레이드
python3 -m pip install --upgrade pip --quiet

# 의존성 설치
pip install -r requirements.txt --quiet
if [[ $? -ne 0 ]]; then
    log_error "Failed to install Python dependencies."
    exit 1
fi
log_success "Python dependencies installed."

echo ""

# -----------------------------------------------------------------------------
# 4. .env 파일 확인 및 샘플 복사
# -----------------------------------------------------------------------------

log_info "[4/7] Checking environment configuration..."

if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        log_info ".env file not found. Copying from .env.example..."
        cp .env.example .env
        log_warning "Please edit .env file and add your API keys:"
        log_warning "  - OPEN_DART_API_KEY"
        log_warning "  - NAVER_CLIENT_ID"
        log_warning "  - NAVER_CLIENT_SECRET"
        echo ""
        log_info "Opening .env file in default editor..."
        ${EDITOR:-nano} .env
        echo ""
        read -p "Continue after editing .env? [Y/n]: " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            exit 1
        fi
    else
        log_error ".env.example not found. Cannot create .env file."
        exit 1
    fi
else
    log_success ".env file exists."
fi

echo ""

# -----------------------------------------------------------------------------
# 5. Next.js 프론트엔드 의존성 설치
# -----------------------------------------------------------------------------

log_info "[5/7] Installing Next.js dependencies..."

if [[ ! -d "web" ]]; then
    log_error "web/ directory not found."
    exit 1
fi

cd web

# web/.env.local 확인 및 샘플 복사
if [[ ! -f ".env.local" ]]; then
    if [[ -f ".env.local.example" ]]; then
        log_info ".env.local not found. Copying from .env.local.example..."
        cp .env.local.example .env.local
        log_success "web/.env.local created."
    else
        log_warning "web/.env.local.example not found."
    fi
else
    log_success "web/.env.local exists."
fi

# node_modules 확인 및 설치
if [[ ! -d "node_modules" ]]; then
    log_info "Installing Next.js dependencies (this may take a few minutes)..."
    npm install
    if [[ $? -ne 0 ]]; then
        log_error "Failed to install Next.js dependencies."
        cd ..
        exit 1
    fi
    log_success "Next.js dependencies installed."
else
    log_success "node_modules already exists. Skipping npm install."
    log_info "(Run 'npm install' manually in web/ to update dependencies)"
fi

cd ..

echo ""

# -----------------------------------------------------------------------------
# 6. 포트 충돌 확인
# -----------------------------------------------------------------------------

log_info "[6/7] Checking port availability..."

# 포트 3000 사용 중인지 확인
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    log_warning "Port 3000 is already in use."
    log_info "Kill process: lsof -ti:3000 | xargs kill -9"
    echo ""
    read -p "Continue anyway? (May fail to start) [y/N]: " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    log_success "Port 3000 is available."
fi

echo ""

# -----------------------------------------------------------------------------
# 7. Next.js 개발 서버 시작
# -----------------------------------------------------------------------------

log_info "[7/7] Starting Next.js development server..."
echo ""
echo "===================================================================="
echo "  Server starting at http://localhost:3000"
echo "  Press Ctrl+C to stop the server."
echo "===================================================================="
echo ""

# 백그라운드 실행 옵션
BACKGROUND=false
if [[ "$1" == "--bg" || "$1" == "-b" ]]; then
    BACKGROUND=true
    log_info "Running in background mode..."
fi

# 브라우저 자동 오픈 (5초 후)
(sleep 5 && $OPEN_CMD http://localhost:3000) &

# Next.js 개발 서버 시작
cd web
if [[ "$BACKGROUND" == true ]]; then
    # 백그라운드 실행
    nohup npm run dev > ../server.log 2>&1 &
    PID=$!
    log_success "Server started in background (PID: $PID)"
    log_info "Logs: tail -f server.log"
    log_info "Stop: kill $PID"
else
    # 포그라운드 실행
    npm run dev
fi

# 서버 종료 시
cd ..
echo ""
log_info "Server stopped."
