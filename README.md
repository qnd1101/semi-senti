# Semi Senti

반도체 특화 NLP 감성 분석과 재무 펀더멘털을 결합한 주가 분석 서비스 프로젝트입니다.

## Quick Start (clone 직후 1줄 실행)

`git clone` 직후 아래 한 줄만 실행하면 **가상환경 생성 → 의존성 설치 → DB 초기화 → 기본 시드 데이터(삼성전자·SK하이닉스) 적재**까지 한 번에 끝납니다.

### Windows (CMD / PowerShell)

```bat
git clone <REPO_URL> semi-senti
cd semi-senti
setup.bat
```

> PowerShell 사용자도 동일하게 `.\setup.bat` 으로 실행하면 됩니다. (Activate.ps1 보안 정책 우회를 위해 내부적으로 `.\.venv\Scripts\python.exe` 를 직접 호출합니다.)

### macOS / Linux (bash / zsh)

```bash
git clone <REPO_URL> semi-senti
cd semi-senti
chmod +x setup.sh
./setup.sh
```

### 자동화 스크립트가 수행하는 단계

| # | 단계 | 설명 |
|---|------|------|
| 1 | Python 탐색 | 3.12 → 3.11 → 3.10 → 3.9 → 3.8 순으로 사용 가능한 인터프리터 자동 선택 |
| 2 | `.venv` 생성 | 프로젝트 루트에 가상환경 생성 (이미 있으면 재사용) |
| 3 | 패키지 설치 | `pip install -r requirements.txt` + `pip install -e . --no-deps` |
| 4 | `.env` 보강 | 없으면 `.env.example` → `.env` 자동 복사 |
| 5 | DB 시딩 | `db_seed.py` 실행 → SQLite + 7개 테이블 + 삼성전자/SK하이닉스 + 펀더멘털 더미 데이터 |

### 시딩만 다시 실행하고 싶을 때

```bash
# 활성화 후
python db_seed.py              # 기본: 이미 있으면 skip
python db_seed.py --force      # financials 더미 데이터를 강제로 덮어쓰기
python db_seed.py --reset-db   # DB 파일을 지우고 처음부터 다시 생성
```

### 종료 코드 (CI 연동용)

| 코드 | 의미 |
|------|------|
| 0  | 정상 완료 |
| 10 | Python 3.8+ 미감지 |
| 20 | 가상환경 생성 실패 |
| 30 | `pip install` 실패 |
| 40 | `db_seed.py` 실행 실패 |

> 실행 중 `[FAIL]` 로그 바로 다음 줄에 원인 후보(권한/네트워크/빌드 도구 등)가 함께 출력되므로, 그 메시지를 그대로 이슈로 옮겨주세요.

---

## Development Setup

Python **3.10 ~ 3.12** 권장 (`pandas 2.0.x` 호환). **3.14** 는 아직 의존성 wheel 이 없어 설치가 실패할 수 있습니다.

### 가상환경 (venv)

**Windows (PowerShell)** — Python 3.12 예시

```powershell
# 3.12 설치 후: py -3.12 -m venv .venv  (기본 python 이 3.14 인 경우)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

활성화 없이 설치·실행만 할 때 (실행 정책 오류 우회):

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m semi_senti init-db
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

### 문제 해결 (Windows)

| 증상 | 조치 |
|------|------|
| `Activate.ps1` 보안 오류 (`PSSecurityException`) | **A)** `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 후 다시 활성화<br>**B)** CMD에서 `\.venv\Scripts\activate.bat`<br>**C)** 활성화 생략 → `.\.venv\Scripts\python.exe -m pip ...` |
| `pip` 가 전역 Python(3.14)을 가리킴 | 프롬프트에 `(.venv)` 가 보이는지 확인. 없으면 위 **C)** 사용 |
| `pandas` 빌드 실패 | venv 를 **Python 3.12** 로 다시 생성 (`Remove-Item -Recurse .venv` 후 `py -3.12 -m venv .venv`) |
| `pip install` 이 `canceled` | 설치가 끝날 때까지 중단하지 않기 (build dependencies 단계에서 시간 소요) |

의존성만 일괄 설치: `pip install -r requirements.txt` (editable 설치 대신)

### 환경 변수

```bash
cp .env.example .env   # Windows: copy .env.example .env
# .env 에 API 키 등 값 입력
```

## Run

```bash
# 1) DB 초기화 (최초 1회)
python -m semi_senti init-db

# 2) 데이터 수집 (예시)
python -m semi_senti collect price --stock-code 005930 --stock-name 삼성전자 --market KOSPI
python -m semi_senti collect news  --stock-code 005930 --stock-name 삼성전자 --query "삼성전자 HBM"
python -m semi_senti collect dart  --stock-code 005930 --corp-code 00126380

# 3) 분석 엔진 실행
python -m semi_senti analyze sentiment  --stock-code 005930
python -m semi_senti analyze signal     --stock-code 005930
python -m semi_senti analyze divergence --stock-code 005930

# 4) 대시보드 실행 (Phase 3)
python -m semi_senti dashboard            # localhost:8501
# 또는
streamlit run src/semi_senti/dashboard/app.py

# 5) 알림 (Phase 4-1)
python -m semi_senti notify test --message "Semi Senti hello"
python -m semi_senti notify signal           --stock-code 005930
python -m semi_senti notify sentiment-shift  --stock-code 005930

# 6) 사이클 분석 (Phase 4-2)
python -m semi_senti analyze cycle --stock-code 005930

# 7) 관리자 (Phase 4-3)
python -m semi_senti admin add     --stock-code 000660 --stock-name SK하이닉스 --market KOSPI
python -m semi_senti admin list
python -m semi_senti admin status
python -m semi_senti admin refresh --stock-code 000660 --query "SK하이닉스 HBM"
python -m semi_senti admin delete  --stock-code 000660 --soft
```

## Test

```bash
python -m unittest -v
```
