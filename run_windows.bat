@echo off
REM =============================================================================
REM Semi Senti — Windows 1-Click Launcher
REM =============================================================================
REM 이 스크립트는 다음 작업을 자동으로 수행합니다:
REM   1. Python/Node.js/JDK 환경 확인
REM   2. Python 가상환경 생성 및 활성화 (없으면 자동 생성)
REM   3. Python 의존성 설치 (requirements.txt)
REM   4. .env 파일 존재 확인 및 샘플 복사
REM   5. Next.js 의존성 설치 (web/node_modules)
REM   6. Next.js 개발 서버 시작 (http://localhost:3000)
REM   7. 브라우저 자동 오픈
REM
REM 요구사항:
REM   - Python 3.8+
REM   - JDK 1.8+
REM   - Node.js 20 LTS
REM   - npm 9+
REM =============================================================================

setlocal enabledelayedexpansion

echo.
echo ====================================================================
echo   Semi Senti — Windows 1-Click Launcher
echo ====================================================================
echo.

REM -----------------------------------------------------------------------------
REM 1. 환경 확인 (Python / Node.js / JDK)
REM -----------------------------------------------------------------------------

echo [1/7] Checking environment...

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please download Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo [OK] Python %PYTHON_VERSION% found.

REM Node.js 확인
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please download Node.js 20 LTS from https://nodejs.org/
    pause
    exit /b 1
)
for /f %%v in ('node --version') do set NODE_VERSION=%%v
echo [OK] Node.js %NODE_VERSION% found.

REM npm 확인
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed or not in PATH.
    pause
    exit /b 1
)
for /f %%v in ('npm --version') do set NPM_VERSION=%%v
echo [OK] npm %NPM_VERSION% found.

REM JDK 확인 (KoNLPy 필수)
java -version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Java (JDK) is not installed or not in PATH.
    echo JDK 1.8+ is required for KoNLPy (NLP engine).
    echo Download from: https://adoptium.net/
    echo.
    echo You can continue without JDK, but NLP features will not work.
    choice /C YN /M "Continue anyway?"
    if errorlevel 2 (
        pause
        exit /b 1
    )
) else (
    for /f "tokens=3" %%v in ('java -version 2^>^&1 ^| findstr /I "version"') do set JAVA_VERSION=%%v
    echo [OK] Java %JAVA_VERSION% found.
)

echo.

REM -----------------------------------------------------------------------------
REM 2. Python 가상환경 생성 및 활성화
REM -----------------------------------------------------------------------------

echo [2/7] Setting up Python virtual environment...

if not exist ".venv\" (
    echo Creating new virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

REM 가상환경 활성화
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    echo If you see "Execution Policy" error, run PowerShell as Administrator and execute:
    echo    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
    pause
    exit /b 1
)
echo [OK] Virtual environment activated.

echo.

REM -----------------------------------------------------------------------------
REM 3. Python 의존성 설치
REM -----------------------------------------------------------------------------

echo [3/7] Installing Python dependencies...

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found in project root.
    pause
    exit /b 1
)

REM pip 업그레이드
python -m pip install --upgrade pip --quiet

REM 의존성 설치
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed.

echo.

REM -----------------------------------------------------------------------------
REM 4. .env 파일 확인 및 샘플 복사
REM -----------------------------------------------------------------------------

echo [4/7] Checking environment configuration...

if not exist ".env" (
    if exist ".env.example" (
        echo .env file not found. Copying from .env.example...
        copy .env.example .env >nul
        echo [WARNING] Please edit .env file and add your API keys:
        echo    - OPEN_DART_API_KEY
        echo    - NAVER_CLIENT_ID
        echo    - NAVER_CLIENT_SECRET
        echo.
        echo Opening .env file in notepad...
        start notepad .env
        echo.
        choice /C YN /M "Continue after editing .env?"
        if errorlevel 2 (
            pause
            exit /b 1
        )
    ) else (
        echo [ERROR] .env.example not found. Cannot create .env file.
        pause
        exit /b 1
    )
) else (
    echo [OK] .env file exists.
)

echo.

REM -----------------------------------------------------------------------------
REM 5. Next.js 프론트엔드 의존성 설치
REM -----------------------------------------------------------------------------

echo [5/7] Installing Next.js dependencies...

if not exist "web\" (
    echo [ERROR] web/ directory not found.
    pause
    exit /b 1
)

cd web

REM web/.env.local 확인 및 샘플 복사
if not exist ".env.local" (
    if exist ".env.local.example" (
        echo .env.local not found. Copying from .env.local.example...
        copy .env.local.example .env.local >nul
        echo [OK] web/.env.local created.
    ) else (
        echo [WARNING] web/.env.local.example not found.
    )
) else (
    echo [OK] web/.env.local exists.
)

REM node_modules 확인 및 설치
if not exist "node_modules\" (
    echo Installing Next.js dependencies (this may take a few minutes)...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install Next.js dependencies.
        cd ..
        pause
        exit /b 1
    )
    echo [OK] Next.js dependencies installed.
) else (
    echo [OK] node_modules already exists. Skipping npm install.
    echo (Run 'npm install' manually in web/ to update dependencies)
)

cd ..

echo.

REM -----------------------------------------------------------------------------
REM 6. 포트 충돌 확인
REM -----------------------------------------------------------------------------

echo [6/7] Checking port availability...

REM 포트 3000 사용 중인지 확인
netstat -ano | findstr :3000 >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 3000 is already in use.
    echo Please close the application using port 3000 or choose a different port.
    echo.
    choice /C YN /M "Continue anyway? (May fail to start)"
    if errorlevel 2 (
        pause
        exit /b 1
    )
) else (
    echo [OK] Port 3000 is available.
)

echo.

REM -----------------------------------------------------------------------------
REM 7. Next.js 개발 서버 시작
REM -----------------------------------------------------------------------------

echo [7/7] Starting Next.js development server...
echo.
echo ====================================================================
echo   Server starting at http://localhost:3000
echo   Press Ctrl+C to stop the server.
echo ====================================================================
echo.

REM 브라우저 자동 오픈 (5초 후)
start "" cmd /c "timeout /t 5 /nobreak >nul && start http://localhost:3000"

REM Next.js 개발 서버 시작
cd web
call npm run dev

REM 서버 종료 시
cd ..
echo.
echo Server stopped.
pause
