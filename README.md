# Semi Senti

<div align="center">

**반도체 특화 주가 감성 분석 서비스 (PRD v1.2)**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

반도체 도메인 특화 NLP 감성 분석 · 다중 관점 매매 시그널 · Gemini AI 근거 생성  
**FastAPI 백엔드 + Next.js 14 대시보드**

</div>

---

## 🚀 Quick Start

### 사전 요구사항

| 항목 | 버전 | 필수 여부 |
|------|------|-----------|
| Python | 3.12 | ✅ 필수 |
| JDK | 1.8 이상 | ✅ 필수 (KoNLPy) |
| Node.js | 20 이상 | ✅ 필수 (대시보드) |
| PostgreSQL | 15 이상 | ✅ 필수 |

### Windows 1-Click 실행

```bat
run_windows.bat
```

- FastAPI: http://localhost:8001
- 대시보드: http://localhost:3000
- API 문서: http://localhost:8001/docs

### Linux/macOS 1-Click 실행

```bash
chmod +x run_linux.sh
./run_linux.sh
```

> **주의:** 최초 실행 전 `.env`에 필수 설정을 입력하세요. (아래 Configuration 참조)

---

## ⚙️ Configuration (환경 변수 설정)

`.env.example`을 복사하여 `.env` 파일을 생성하고 아래 항목을 입력하세요.

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

### 필수 설정

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | `postgresql://user:pass@localhost:5432/semisenti` |
| `OPEN_DART_API_KEY` | Open DART API 키 | [opendart.fss.or.kr](https://opendart.fss.or.kr/) |
| `NAVER_CLIENT_ID` | 네이버 검색 API Client ID | [developers.naver.com](https://developers.naver.com/) |
| `NAVER_CLIENT_SECRET` | 네이버 검색 API Secret | |

### 선택 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `GEMINI_API_KEY` | Gemini AI 근거 생성 API 키 | (미설정 시 폴백 규칙 사용) |
| `GEMINI_MODEL` | Gemini 모델명 | `gemini-1.5-flash` |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 알림 Bot Token | |
| `TELEGRAM_CHAT_ID` | 텔레그램 Chat ID | |
| `API_PORT` | FastAPI 포트 | `8001` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |

---

## 🛠️ Manual Setup (수동 설치)

### 1. PostgreSQL DB 생성

```sql
CREATE DATABASE semisenti;
CREATE USER semisenti_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE semisenti TO semisenti_user;
```

### 2. Python 백엔드

```bash
# Windows
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Linux/macOS
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. DB 초기화

```bash
python db_seed.py
```

### 4. FastAPI 서버 시작

```bash
python -m semi_senti.api
```

### 5. Next.js 대시보드

```bash
cd web
npm install
# .env.local 설정 (NEXT_PUBLIC_API_BASE_URL=http://localhost:8001)
npm run dev
```

---

## 📁 Directory Structure

```
semi-senti/
├─ src/
│  └─ semi_senti/
│     ├─ collector/         # 데이터 수집 (DART, 네이버, pykrx)
│     ├─ engine/            # NLP 감성 분석 + 다중 관점 시그널 + Reasoning
│     ├─ pipeline/          # LiveDataPipeline (실시간 수집)
│     ├─ notifier/          # 텔레그램 알림
│     ├─ admin/             # 관리자 기능
│     ├─ api/               # FastAPI HTTP API
│     ├─ db/                # PostgreSQL 스키마·컨트롤
│     ├─ config/            # 설정 (settings.py)
│     └─ cli.py             # CLI 진입점
├─ web/                     # Next.js 14 대시보드
│  ├─ src/
│  │  ├─ app/               # App Router (page.tsx, layout.tsx)
│  │  ├─ components/        # UI 컴포넌트 (SentimentGauge, SignalCard 등)
│  │  └─ lib/               # API 클라이언트, 타입, 유틸
│  └─ package.json
├─ docs/
│  ├─ PRD.md                # 제품 요구사항 명세서 (v1.2)
│  ├─ Tasks.md              # Task 진행 현황
│  └─ RELEASE_NOTES.md      # 릴리즈 노트
├─ tests/                   # 단위·통합 테스트
├─ .env.example             # 환경 변수 템플릿
├─ db_seed.py               # DB 초기화 스크립트
├─ requirements.txt         # Python 의존성
├─ run_windows.bat          # Windows 1-click 실행
└─ run_linux.sh             # Linux/macOS 1-click 실행
```

---

## 📚 기능 개요

### 핵심 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| **pykrx 주가 수집** | KRX·네이버 기반 일별 OHLCV (API 키 불필요) | ✅ |
| **DART 재무제표** | 매출·영업이익·PER·PBR·EPS 자동 수집 | ✅ |
| **네이버 뉴스 NLP** | KoNLPy + 반도체 특화 사전 감성 스코어 (-100~+100) | ✅ |
| **다중 관점 시그널** | SHORT / MID / LONG 관점별 BUY/SELL/HOLD 독립 산출 | ✅ |
| **Gemini AI 근거** | 시그널 + 뉴스 + 재무를 Gemini로 분석한 투자 판단 근거 | ✅ |
| **1화면 대시보드** | Next.js 14, Claude 스타일 다크, TradingView 차트 | ✅ |
| **REST API** | FastAPI `/api/snapshot/{code}` 등 | ✅ |
| **텔레그램 알림** | 매매 시그널 발생 시 즉시 발송 | ✅ |

### 다중 관점 시그널 로직 (PRD §F-3.2)

| 관점 | 가중치 구성 | 임계값 |
|------|------------|--------|
| SHORT (단기) | 뉴스 감성 40% + 일봉 모멘텀 35% + 밴드 위치 25% | ±25pt |
| MID (중기) | 주봉 추세 35% + 재무 밴드 40% + 뉴스 감성 25% | ±25pt |
| LONG (장기) | 재고 회전율 30% + 사이클 25% + 재무 30% + 감성 15% | ±25pt |

---

## 🔍 Troubleshooting

### PostgreSQL 연결 오류

```bash
psql: error: could not connect to server
```

`.env`의 `DATABASE_URL` 확인 후 PostgreSQL 서비스가 실행 중인지 확인:
```bash
# Windows
net start postgresql-x64-15

# Linux
sudo systemctl start postgresql
```

### JDK 미설치로 KoNLPy 실패

```
RuntimeError: Java gateway process exited before sending its port number
```

JDK 1.8 이상 설치: [OpenJDK](https://adoptium.net/)  
환경 변수 `JAVA_HOME` 설정 후 재시작.

### PowerShell 가상환경 활성화 실패

```powershell
# 한 번만 설정 (관리자 권한 불필요)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\activate

# 또는 cmd 사용
.venv\Scripts\activate.bat
```

### API 포트 충돌

```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

`.env`에서 `API_PORT=8002`로 변경 가능.

---

## 🧪 Testing

```bash
pytest tests/ -v --cov=src/semi_senti
```

---

## 🛡️ Security & Privacy

- **자동 매매 미연동:** 증권사 계좌 연동 없음
- **로컬 실행:** 모든 데이터는 로컬 PostgreSQL에 저장
- **API 키 관리:** `.env` 파일은 `.gitignore` 포함 (커밋 금지)

---

## 📄 License

MIT License — [LICENSE](LICENSE) 참조

---

<div align="center">

**Made with ❤️ for Semiconductor Investors**

</div>
