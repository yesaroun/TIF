# FastAPI 테스트 프로젝트

FastAPI를 학습하고 테스트하기 위한 기본 프로젝트입니다. Python 3.11과 uv 패키지 매니저를 사용합니다.

## 🚀 프로젝트 구조

```
FastAPITestCodes/
├── main.py              # FastAPI 애플리케이션
├── pyproject.toml       # 프로젝트 설정 및 의존성
├── README.md           # 프로젝트 문서
└── scripts/            # 커스텀 스크립트들
    ├── serve.py        # 개발 서버 (hot reload)
    ├── start.py        # 프로덕션 서버
    └── test_api.py     # API 테스트
```

## 📦 uv 패키지 매니저 사용법

### 기본 명령어

#### 프로젝트 초기화
```bash
# Python 3.11로 새 프로젝트 생성
uv init --python 3.11

# 기존 프로젝트에서 의존성 설치
uv sync
```

#### 의존성 관리
```bash
# 의존성 추가
uv add fastapi uvicorn requests

# 개발 의존성 추가
uv add --dev pytest black isort

# 의존성 제거
uv remove requests

# 의존성 업데이트
uv sync --upgrade
```

#### 파이썬 실행
```bash
# 가상환경에서 Python 실행
uv run python main.py

# 가상환경에서 특정 명령어 실행
uv run uvicorn main:app --reload

# 가상환경 활성화 (선택사항)
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

#### 기타 유용한 명령어
```bash
# Python 버전 확인
uv run python --version

# 설치된 패키지 목록
uv pip list

# 프로젝트 정보 확인
uv tree
```

## 🛠️ 프로젝트 스크립트 사용법

### 1. 개발 서버 실행 (추천)
```bash
uv run python scripts/serve.py
```
- **기능**: Hot reload 기능이 포함된 개발 서버
- **사용 시기**: 개발 중 코드 변경사항을 실시간으로 확인할 때
- **특징**: 파일 저장 시 자동으로 서버 재시작

### 2. 프로덕션 서버 실행
```bash
uv run python scripts/start.py
```
- **기능**: Reload 기능이 없는 프로덕션 서버
- **사용 시기**: 배포 환경이나 성능 테스트 시
- **특징**: 더 빠른 성능, 안정적인 운영

### 3. API 테스트 실행
```bash
uv run python scripts/test_api.py
```
- **기능**: 모든 API 엔드포인트 자동 테스트
- **테스트 항목**:
  - 루트 엔드포인트 (`/`)
  - 헬스체크 엔드포인트 (`/health`)
  - 아이템 조회 엔드포인트 (`/items/{item_id}`)

### 4. 직접 uvicorn 명령어 사용
```bash
# 개발용 (hot reload)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션용
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# 다른 포트로 실행
uv run uvicorn main:app --reload --port 3000
```

## 🌐 API 엔드포인트

서버 실행 후 다음 URL들에 접근할 수 있습니다:

| 엔드포인트 | 설명 | 예시 |
|-----------|------|------|
| `GET /` | 환영 메시지 | http://localhost:8000/ |
| `GET /health` | 서버 상태 확인 | http://localhost:8000/health |
| `GET /items/{item_id}` | 아이템 조회 | http://localhost:8000/items/42?q=test |
| `GET /docs` | 자동 생성 API 문서 (Swagger UI) | http://localhost:8000/docs |
| `GET /redoc` | 대안 API 문서 (ReDoc) | http://localhost:8000/redoc |

## 🔧 개발 환경 설정

### 요구사항
- Python 3.11 이상
- uv 패키지 매니저

### 프로젝트 설정
1. **저장소 클론 및 이동**
   ```bash
   cd FastAPITestCodes
   ```

2. **의존성 설치**
   ```bash
   uv sync
   ```

3. **개발 서버 실행**
   ```bash
   uv run python scripts/serve.py
   ```

4. **브라우저에서 확인**
   - API: http://localhost:8000/
   - 문서: http://localhost:8000/docs

## 📝 주요 의존성

- **FastAPI**: 현대적이고 빠른 웹 API 프레임워크
- **Uvicorn**: ASGI 서버 (FastAPI 실행용)
- **Requests**: HTTP 클라이언트 라이브러리 (테스트용)

## 🚨 문제 해결

### 서버가 시작되지 않는 경우
```bash
# Python 버전 확인
uv run python --version

# 의존성 재설치
uv sync

# 포트 사용 확인
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows
```

### API 테스트가 실패하는 경우
1. 서버가 실행 중인지 확인
2. 방화벽 설정 확인
3. 포트 8000이 사용 가능한지 확인

## 💡 팁과 트릭

### 다른 포트로 실행
```bash
# 포트 3000으로 실행
uv run uvicorn main:app --reload --port 3000
```

### 로그 레벨 설정
```bash
# 디버그 모드로 실행
uv run uvicorn main:app --reload --log-level debug
```

### 특정 호스트에서만 접근 허용
```bash
# localhost에서만 접근 가능
uv run uvicorn main:app --reload --host 127.0.0.1
```

## 📚 추가 학습 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [uv 공식 문서](https://docs.astral.sh/uv/)
- [Uvicorn 문서](https://www.uvicorn.org/)

---

**즐거운 FastAPI 개발하세요! 🎉**
