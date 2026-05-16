@echo off
REM ============================================================================
REM Semi Senti - One-Shot Bootstrap Script (Windows)
REM ----------------------------------------------------------------------------
REM 사용법 (CMD 또는 PowerShell 모두 가능):
REM    setup.bat
REM
REM 수행 단계:
REM    1) Python 3.8+ 인터프리터 탐색 (py launcher 우선, 없으면 python)
REM    2) .\.venv 가상환경 생성 (이미 있으면 재사용)
REM    3) pip 업그레이드 + requirements.txt 설치 + 로컬 패키지 editable 설치
REM    4) .env 파일 부재 시 .env.example -> .env 복사
REM    5) db_seed.py 자동 실행 (DB 초기화 + 기본 종목/재무 시딩)
REM
REM 종료 코드:
REM    10  Python 미설치 / 버전 부적합
REM    20  가상환경 생성 실패
REM    30  pip 패키지 설치 실패
REM    40  db_seed.py 실행 실패
REM ============================================================================

setlocal EnableExtensions EnableDelayedExpansion

REM 콘솔 코드페이지를 UTF-8 로 (한글 종목명/로그 깨짐 방지).
chcp 65001 >nul 2>&1

REM 스크립트 위치 = 프로젝트 루트.
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
pushd "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] 프로젝트 루트로 이동 실패: %SCRIPT_DIR%
    exit /b 1
)

echo =====================================================================
echo   Semi Senti - Bootstrap (Windows)
echo =====================================================================
echo   project root : %SCRIPT_DIR%
echo   shell        : %COMSPEC%
echo   os           : %OS% %PROCESSOR_ARCHITECTURE%
echo =====================================================================
echo.

REM ---------------------------------------------------------------------------
REM 1) Python 인터프리터 탐색 (3.8+)
REM    - Windows 는 `py -3.X` launcher 가 가장 안정적.
REM    - launcher 가 없으면 PATH 의 python 으로 폴백.
REM ---------------------------------------------------------------------------
echo [STEP] 1/5 Python 3.8+ 인터프리터 탐색
set "PYTHON_BIN="

where py >nul 2>&1
if not errorlevel 1 (
    for %%V in (3.12 3.11 3.10 3.9 3.8) do (
        if not defined PYTHON_BIN (
            py -%%V -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
            if not errorlevel 1 (
                set "PYTHON_BIN=py -%%V"
            )
        )
    )
)

if not defined PYTHON_BIN (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_BIN=python"
        )
    )
)

if not defined PYTHON_BIN (
    echo [FAIL] Python 3.8 이상을 찾지 못했습니다.
    echo        - https://www.python.org/downloads/windows/ 에서 3.12 설치 권장
    echo        - 설치 시 "Add python.exe to PATH" 체크
    popd >nul
    exit /b 10
)

for /f "delims=" %%V in ('%PYTHON_BIN% -c "import platform;print(platform.python_version())"') do set "PY_VERSION=%%V"
echo [ OK ] Python 발견: %PYTHON_BIN%  (v%PY_VERSION%)
echo.

REM ---------------------------------------------------------------------------
REM 2) 가상환경 생성
REM ---------------------------------------------------------------------------
echo [STEP] 2/5 가상환경(.venv) 생성
set "VENV_DIR=%SCRIPT_DIR%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if exist "%VENV_PY%" (
    echo [ OK ] .venv 이미 존재 -^> 재사용 ^(%VENV_DIR%^)
) else (
    echo        venv 생성 중: %VENV_DIR%
    %PYTHON_BIN% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [FAIL] 가상환경 생성 실패
        echo        - Microsoft Store 버전 Python 은 venv 가 제한될 수 있음 -^> python.org 설치본 사용
        echo        - C 드라이브 외 경로에서 권한 부족 가능: 관리자 권한 또는 다른 위치에서 시도
        popd >nul
        exit /b 20
    )
    echo [ OK ] .venv 생성 완료
)

if not exist "%VENV_PY%" (
    echo [FAIL] .venv\Scripts\python.exe 가 존재하지 않습니다.
    popd >nul
    exit /b 20
)
echo        활성화된 python: %VENV_PY%
echo.

REM ---------------------------------------------------------------------------
REM 3) pip 업그레이드 + 의존성 설치
REM    NOTE: .venv\Scripts\python.exe 를 직접 호출하여 활성화 정책(PSSecurityException)
REM          이슈를 우회한다.
REM ---------------------------------------------------------------------------
echo [STEP] 3/5 pip 업그레이드 및 requirements.txt 설치

"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [FAIL] pip 업그레이드 실패 ^(네트워크/프록시 확인^)
    popd >nul
    exit /b 30
)

set "REQ_FILE=%SCRIPT_DIR%\requirements.txt"
if not exist "%REQ_FILE%" (
    echo [FAIL] requirements.txt 가 없습니다: %REQ_FILE%
    popd >nul
    exit /b 30
)

echo        pip install -r requirements.txt ...
"%VENV_PY%" -m pip install -r "%REQ_FILE%"
if errorlevel 1 (
    echo [FAIL] requirements.txt 설치 실패
    echo        원인 후보:
    echo          - Python 3.14 사용 중이면 일부 wheel 부재 -^> py -3.12 -m venv 로 재생성
    echo          - C++ Build Tools 부재 ^(JPype1, lxml^) -^> Visual Studio Build Tools 설치
    echo          - 사내 프록시: pip --proxy 또는 HTTPS_PROXY 환경 변수 설정
    popd >nul
    exit /b 30
)
echo [ OK ] requirements.txt 의존성 설치 완료

REM 로컬 패키지(editable) 설치 -> from semi_senti.db import ... 가능.
echo        로컬 패키지 editable 설치 ^(pip install -e . --no-deps^) ...
"%VENV_PY%" -m pip install -e "%SCRIPT_DIR%" --no-deps
if errorlevel 1 (
    echo [WARN] editable 설치 실패 -^> db_seed.py 는 sys.path 폴백으로 동작합니다.
)
echo.

REM ---------------------------------------------------------------------------
REM 4) .env 파일 보강
REM ---------------------------------------------------------------------------
echo [STEP] 4/5 .env 파일 점검
if exist "%SCRIPT_DIR%\.env" (
    echo [ OK ] .env 이미 존재 -^> 그대로 사용
) else if exist "%SCRIPT_DIR%\.env.example" (
    copy /Y "%SCRIPT_DIR%\.env.example" "%SCRIPT_DIR%\.env" >nul
    echo [ OK ] .env.example -^> .env 복사 ^(API 키 등은 직접 채워주세요^)
) else (
    echo [WARN] .env / .env.example 둘 다 없음 -^> 기본값으로 동작
)
echo.

REM ---------------------------------------------------------------------------
REM 5) DB 초기화 + 시딩
REM ---------------------------------------------------------------------------
echo [STEP] 5/5 DB 초기화 및 시딩 ^(db_seed.py 실행^)
set "SEED_SCRIPT=%SCRIPT_DIR%\db_seed.py"
if not exist "%SEED_SCRIPT%" (
    echo [FAIL] db_seed.py 가 없습니다: %SEED_SCRIPT%
    popd >nul
    exit /b 40
)

"%VENV_PY%" "%SEED_SCRIPT%"
if errorlevel 1 (
    echo [FAIL] db_seed.py 실행 실패
    echo        원인 후보:
    echo          - db\ 디렉터리 쓰기 권한 부족 ^(읽기전용 폴더 여부 확인^)
    echo          - .env 의 SEMI_SENTI_SQLITE_PATH 가 잘못 지정됨
    echo          - semi_senti import 실패 -^> "%VENV_PY%" -m pip install -e . --no-deps 수동 실행
    popd >nul
    exit /b 40
)
echo.

echo =====================================================================
echo [ OK ] Semi Senti 환경 구축이 모두 끝났습니다.
echo   활성화: .\.venv\Scripts\activate.bat    ^(PowerShell: .\.venv\Scripts\Activate.ps1^)
echo   대시보드: python -m semi_senti dashboard
echo =====================================================================

popd >nul
endlocal
exit /b 0
