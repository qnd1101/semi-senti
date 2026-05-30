@echo off
REM =============================================================================
REM Semi Senti — Windows 1-Click Launcher (PRD v1.2)
REM =============================================================================
REM  1. Python/JDK/Node.js 환경 확인
REM  2. Python 가상환경 생성 및 의존성 설치
REM  3. .env 파일 확인 (PostgreSQL DATABASE_URL 등)
REM  4. DB 초기화 (db_seed.py)
REM  5. FastAPI 서버 시작 (http://localhost:8001)
REM  6. Next.js 대시보드 시작 (http://localhost:3000)
REM
REM 사전 요구사항: Python 3.12, JDK 1.8+, Node.js 20+, PostgreSQL 15+
REM =============================================================================

setlocal enabledelayedexpansion

echo.
echo ====================================================================
echo   Semi Senti — Windows Launcher (PRD v1.2)
echo ====================================================================
echo.

echo [1/6] Checking environment...

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12 is not installed or not in PATH.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('py -3.12 --version 2^>^&1') do set PYTHON_VERSION=%%v
echo [OK] Python %PYTHON_VERSION% found.

java -version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] JDK not found. KoNLPy NLP will not work.
) else (
    echo [OK] Java found.
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Node.js not found. Web dashboard will not start.
    set NO_NODE=1
) else (
    echo [OK] Node.js found.
    set NO_NODE=0
)

echo.

echo [2/6] Setting up Python virtual environment...

if not exist ".venv\" (
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment exists.
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed (psycopg2-binary, pykrx included).

echo.

echo [3/6] Checking .env file...

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] .env created from .env.example
        echo       *** Edit DATABASE_URL and API keys before use! ***
    ) else (
        echo [ERROR] .env.example not found.
        pause
        exit /b 1
    )
) else (
    echo [OK] .env file exists.
)

echo.

echo [4/6] Initializing database (PostgreSQL)...

python db_seed.py
if errorlevel 1 (
    echo [WARNING] db_seed.py failed. Check DATABASE_URL in .env.
)

echo.

echo [5/6] Starting Python FastAPI (http://localhost:8001)...

if not defined API_PORT set API_PORT=8001
start "Semi Senti API" cmd /k "call .venv\Scripts\activate.bat && python -m semi_senti.api"
echo [OK] FastAPI starting in new window.
timeout /t 3 >nul

echo.

if "%NO_NODE%"=="0" (
    echo [6/6] Starting Next.js dashboard (http://localhost:3000)...
    if exist "web\package.json" (
        cd web
        if not exist "node_modules\" (
            npm install -q
        )
        start "Semi Senti Web" cmd /k "npm run dev"
        cd ..
        echo [OK] Next.js starting in new window.
    ) else (
        echo [WARNING] web\package.json not found. Skipping web dashboard.
    )
) else (
    echo [6/6] Skipping Next.js (Node.js not found).
)

echo.
echo ====================================================================
echo   Services:
echo   - FastAPI:    http://localhost:8001
echo   - API Docs:   http://localhost:8001/docs
echo   - Dashboard:  http://localhost:3000
echo ====================================================================
echo.
pause
