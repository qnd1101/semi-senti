@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"

echo ============================================================
echo   Semi Senti - 반도체 15종목 전체 데이터 수집
echo   주가(전체이력) + 재무(DART) + 뉴스(2년치) + 감성분석
echo ============================================================
echo.

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] .venv 가 없습니다. 먼저 README 의 백엔드 설치를 진행하세요.
  echo   py -3.12 -m venv .venv  ^&^&  .venv\Scripts\activate  ^&^&  pip install -r requirements.txt  ^&^&  pip install -e .
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
pip install -e . -q

python scripts\seed_all_data.py

echo.
echo 완료. 아무 키나 누르면 종료합니다.
pause >nul
