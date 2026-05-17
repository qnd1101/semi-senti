# Semi Senti

<div align="center">

**반도체 특화 주가 감성 분석 서비스**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

반도체 도메인 특화 NLP 감성 분석과 재무 펀더멘털을 결합하여  
개인 투자자에게 객관적인 매매 타점을 제공하는 주가 분석 대시보드

</div>

---

## 🚀 Quick Start (사용자)

### Windows에서 실행

```powershell
# 1-click 실행 (자동 환경 설정 + 의존성 설치 + 서버 시작)
run_windows.bat
```

### Linux/macOS에서 실행

```bash
# 실행 권한 부여 (최초 1회)
chmod +x run_linux.sh

# 1-click 실행
./run_linux.sh
```

실행 후 브라우저에서 자동으로 열리며, 수동 접속 시 아래 주소를 사용하세요:

- **프론트엔드:** http://localhost:3000
- **백엔드 API (옵션):** http://localhost:8000

> **주의:** 최초 실행 시 `.env` 파일에 API 키 설정이 필요합니다. (아래 ⚙️ Configuration 참조)

---

## 🛠️ Development Setup (개발자)

### Prerequisites (사전 요구사항)

#### 필수 설치 항목

| 항목 | 버전 | 확인 명령 | 설치 링크 |
|------|------|-----------|----------|
| **Python** | 3.12 (필수) | `py -3.12 --version` | [python.org](https://www.python.org/) |
| **JDK** | 1.8 이상 | `java -version` | [OpenJDK](https://adoptium.net/) |
| **Node.js** | 20 LTS | `node --version` | [nodejs.org](https://nodejs.org/) |
| **npm** | 9 이상 | `npm --version` | Node.js 포함 |

#### 외부 API 키 발급

| 서비스 | 용도 | 발급 링크 |
|--------|------|----------|
| **Open DART API** | 재무제표 데이터 수집 | [opendart.fss.or.kr](https://opendart.fss.or.kr/) |
| **네이버 검색 API** | 뉴스 데이터 수집 | [developers.naver.com](https://developers.naver.com/) |
| **Telegram Bot** (선택) | 매매 시그널 알림 | [@BotFather](https://t.me/BotFather) |

---

### Manual Build Steps (수동 설치)

#### 1. 저장소 클론

```bash
git clone https://github.com/YOUR_USERNAME/semi-senti.git
cd semi-senti
```

#### 2. Python 백엔드 설정

```bash
# 가상환경 생성 (Python 3.12 필수)
# Windows:
py -3.12 -m venv .venv
# Linux/macOS:
python3.12 -m venv .venv

# 가상환경 활성화
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS

# .env 파일 편집하여 API 키 입력
notepad .env                    # Windows
# nano .env                     # Linux/macOS

# 데이터베이스 초기화 (선택)
python db_seed.py
```

#### 3. Next.js 프론트엔드 설정

```bash
cd web

# 의존성 설치
npm install

# 환경 변수 설정
copy .env.local.example .env.local    # Windows
# cp .env.local.example .env.local    # Linux/macOS

# 개발 서버 시작
npm run dev
```

#### 4. 접속

- 프론트엔드: http://localhost:3000
- 백엔드 API (FastAPI, 선택): `cd src/semi_senti/api && uvicorn main:app --reload`

---

### Directory Structure (디렉토리 구조)

```
semi-senti/
├─ src/
│  └─ semi_senti/               # Python 백엔드
│     ├─ collector/             # 데이터 수집 (DART, 네이버, yfinance)
│     ├─ engine/                # NLP 감성 분석 + 시그널 로직
│     ├─ notifier/              # 텔레그램 알림
│     ├─ api/                   # FastAPI 어댑터 (선택)
│     ├─ cli.py                 # CLI 진입점
│     └─ bootstrap.py           # 초기화 헬퍼
├─ web/                         # Next.js 14 프론트엔드
│  ├─ app/                      # App Router (pages + API routes)
│  ├─ components/               # UI 컴포넌트 (Shadcn UI)
│  ├─ hooks/                    # SWR 데이터 훅
│  ├─ lib/                      # db.ts, snapshot.ts, types.ts
│  └─ package.json
├─ db/                          # SQLite 데이터베이스
│  ├─ semisenti.db              # 메인 DB (gitignore)
│  └─ cache/                    # API 캐시
├─ docs/                        # 프로젝트 문서
│  ├─ PRD.md                    # 제품 요구사항 명세서
│  ├─ UseCases.md               # 유스케이스 시나리오
│  ├─ Tasks.md                  # Task 관리 (Phase 1-5 완료)
│  └─ RELEASE_NOTES.md          # 릴리즈 노트
├─ tests/                       # 단위 테스트
│  └─ unit/                     # Python 백엔드 테스트
├─ .env.example                 # 백엔드 환경 변수 템플릿
├─ pyproject.toml               # Python 프로젝트 설정
├─ requirements.txt             # Python 의존성
├─ run_windows.bat              # Windows 1-click 실행
├─ run_linux.sh                 # Linux/macOS 1-click 실행
└─ README.md                    # 본 문서
```

---

## ⚙️ Configuration (환경 변수 설정)

### 백엔드 설정 (`.env`)

루트 디렉토리의 `.env.example`을 복사하여 `.env` 파일을 생성하고 아래 필수 항목을 입력하세요.

| 환경 변수 | 설명 | 필수 여부 | 기본값 | 예시 |
|-----------|------|-----------|--------|------|
| `OPEN_DART_API_KEY` | Open DART API 키 | ✅ 필수 | - | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `NAVER_CLIENT_ID` | 네이버 검색 API Client ID | ✅ 필수 | - | `AbCdEfGhIjK` |
| `NAVER_CLIENT_SECRET` | 네이버 검색 API Secret | ✅ 필수 | - | `1234567890` |
| `SEMI_SENTI_SQLITE_PATH` | SQLite DB 경로 | 선택 | `./db/semisenti.db` | `./db/semisenti.db` |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 Bot Token (알림용) | 선택 | - | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_CHAT_ID` | 텔레그램 Chat ID | 선택 | - | `123456789` |
| `LOG_LEVEL` | 로그 레벨 | 선택 | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `SENTIMENT_NORMALIZATION_K` | 감성 스코어 정규화 계수 | 선택 | `10` | `10` |
| `SIGNAL_SENTIMENT_BUY_THRESHOLD` | 매수 시그널 임계값 | 선택 | `-70` | `-70` |
| `SIGNAL_SENTIMENT_SELL_THRESHOLD` | 매도 시그널 임계값 | 선택 | `70` | `70` |

#### 예시: `.env` 파일 내용

```env
# API 키 (필수)
OPEN_DART_API_KEY=your_dart_api_key_here
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret

# 선택 사항
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
LOG_LEVEL=INFO
```

### 프론트엔드 설정 (`web/.env.local`)

`web/.env.local.example`을 복사하여 `web/.env.local` 파일을 생성하세요.

| 환경 변수 | 설명 | 기본값 |
|-----------|------|--------|
| `SEMI_SENTI_DB_PATH` | 백엔드 SQLite 파일 경로 (상대경로) | `../db/semisenti.db` |
| `NEXT_PUBLIC_AUTO_REFRESH_SECONDS` | 대시보드 자동 갱신 주기 (초) | `300` (5분) |

---

## 🔍 Troubleshooting (문제 해결)

### Common Errors (자주 발생하는 오류)

#### 1. **Python 가상환경 활성화 실패 (Windows)**

**증상:**
```
.venv\Scripts\activate : 이 시스템에서 스크립트를 실행할 수 없으므로...
```

**해결:**
```powershell
# PowerShell 실행 정책 변경 (관리자 권한)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. **JDK 미설치로 KoNLPy 구동 실패**

**증상:**
```
RuntimeError: Java gateway process exited before sending its port number
```

**해결:**
- JDK 1.8 이상 설치: [OpenJDK 다운로드](https://adoptium.net/)
- 환경 변수 `JAVA_HOME` 설정 후 재부팅

#### 3. **포트 충돌 (Port 3000 already in use)**

**증상:**
```
Error: listen EADDRINUSE: address already in use :::3000
```

**해결 (포트 프로세스 종료):**

```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:3000 | xargs kill -9
```

**또는 다른 포트 사용:**
```bash
cd web
npm run dev -- -p 3001
```

#### 4. **SQLite 파일 권한 오류 (Linux/macOS)**

**증상:**
```
sqlite3.OperationalError: unable to open database file
```

**해결:**
```bash
# 디렉토리 권한 확인 및 수정
chmod 755 db/
touch db/semisenti.db
chmod 644 db/semisenti.db
```

#### 5. **API 키 누락 오류**

**증상:**
```
ValueError: OPEN_DART_API_KEY is not set in environment
```

**해결:**
- `.env` 파일이 루트 디렉토리에 있는지 확인
- `.env.example`을 복사하여 `.env` 생성
- 필수 API 키 입력 후 애플리케이션 재시작

#### 6. **Node.js 버전 불일치**

**증상:**
```
Error: The engine "node" is incompatible with this module
```

**해결:**
```bash
# Node.js 버전 확인
node --version

# nvm 사용 시 버전 전환
nvm install 20
nvm use 20
```

---

## 📚 기능 개요

### Core Features (핵심 기능)

| 기능 | 설명 | 상태 |
|------|------|------|
| **데이터 수집** | DART 재무제표 + yfinance 주가 + 네이버 뉴스 자동 수집 | ✅ 완료 |
| **NLP 감성 분석** | 반도체 특화 사전 기반 감성 스코어링 (-100 ~ +100) | ✅ 완료 |
| **펀더멘털 밴드** | PER/PBR/EPS 기반 적정 가치 범위 산출 | ✅ 완료 |
| **매매 시그널** | BUY/SELL/HOLD 자동 도출 (저평가+공포 vs 고평가+환희) | ✅ 완료 |
| **TradingView 차트** | 캔들 차트 + 시그널 마커 + 다이버전스 표시 | ✅ 완료 |
| **감성 게이지** | 공포/중립/탐욕 시각화 + 상위 키워드 트렌드 | ✅ 완료 |
| **다이버전스 탐지** | 주가 추세 vs 감성 추세 괴리 포착 | ✅ 완료 |
| **텔레그램 알림** | 매매 시그널 + 감성 급변 경고 실시간 발송 | ✅ 완료 |
| **관리자 시스템** | 종목 관리 + 시스템 모니터링 UI | ✅ 완료 |
| **Claude 스타일 UI** | Next.js 14 + Tailwind + Shadcn UI 다크 대시보드 | ✅ 완료 |

### 지원 종목 (기본 제공)

- 삼성전자 (005930.KS)
- SK하이닉스 (000660.KS)
- 삼성전자우 (005935.KS)
- SK스퀘어 (402340.KS)
- POSCO홀딩스 (005490.KS)

> 관리자 페이지(`/admin`)에서 종목 추가/삭제 가능

---

## 🎯 사용 시나리오

### 시나리오 1: 매매 타점 확인

1. 대시보드 접속 (http://localhost:3000)
2. 종목 선택 (예: SK하이닉스)
3. 차트에서 BUY(▲) / SELL(▼) 시그널 마커 확인
4. 감성 게이지로 현재 시장 심리 파악 (공포 구간 = 매수 기회)
5. 재무 요약 패널에서 펀더멘털 밴드 대비 현재가 위치 확인

### 시나리오 2: 다이버전스 포착

- 주가 하락 중 감성 지수는 상승 → 차트에 황색 ◆ 마커 표시
- 추세 반전 가능성 인지 → 포지션 재검토

### 시나리오 3: 알림 수신 (백그라운드)

- 시스템이 BUY 시그널 감지 (저평가 + 공포 심리)
- 텔레그램으로 즉시 알림 발송
- 앱 미실행 상태에서도 매수 타점 포착 가능

---

## 🧪 Testing (테스트)

```bash
# Python 백엔드 테스트
pytest tests/ -v --cov=src/semi_senti

# Next.js 타입체크
cd web
npm run typecheck

# Next.js 린트
npm run lint
```

---

## 📦 Scripts Reference (스크립트 참조)

### Python CLI

```bash
# CLI 진입점
semi-senti --help

# 데이터 수집 (DART + 네이버 + yfinance)
semi-senti collect --stock 005930.KS

# 감성 분석 실행
semi-senti analyze --stock 005930.KS

# 매매 시그널 생성
semi-senti signal --stock 005930.KS
```

### Next.js 프론트엔드

```bash
cd web

# 개발 서버 (HMR)
npm run dev

# 프로덕션 빌드
npm run build

# 프로덕션 서버 시작
npm start

# 타입체크
npm run typecheck

# 린트
npm run lint
```

---

## 🛡️ Security & Privacy (보안 및 개인정보)

- **자동 매매 미연동:** 증권사 계좌 연동 기능 없음 (법적 제약 준수)
- **로컬 실행:** 모든 데이터는 로컬 SQLite에 저장 (외부 전송 없음)
- **API 키 관리:** `.env` 파일은 `.gitignore`에 포함 (절대 커밋 금지)
- **읽기 전용 DB:** Next.js 프론트엔드는 SQLite를 read-only로만 접근

---

## 🤝 Contributing (기여)

이슈 제보 및 Pull Request는 언제나 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

이 프로젝트는 MIT 라이선스로 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 📞 Support (지원)

- **문서:** [docs/](docs/) 디렉토리 참조
  - [PRD.md](docs/PRD.md) — 제품 요구사항 명세서
  - [UseCases.md](docs/UseCases.md) — 유스케이스 시나리오
  - [Tasks.md](docs/Tasks.md) — 개발 Task 관리
  - [RELEASE_NOTES.md](docs/RELEASE_NOTES.md) — 릴리즈 노트
- **이슈 제보:** [GitHub Issues](https://github.com/YOUR_USERNAME/semi-senti/issues)
- **이메일:** your.email@example.com

---

<div align="center">

**Made with ❤️ for Semiconductor Investors**

</div>
