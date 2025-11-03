# uv 학습 노트

이 프로젝트는 `uv init uv`로 생성한 스터디용 공간입니다. `uv`의 핵심 명령과 사용 패턴을 정리해 두었으며, 필요 시 이 프로젝트 내부에서 직접 명령을 실습할 수 있습니다.

## 설치

- macOS/Linux: `curl -LsSf https://astral.sh/install.sh | sh`
- Windows(PowerShell): `irm https://astral.sh/install.ps1 | iex`
- Homebrew: `brew install uv`

설치 후 `uv --version`으로 설치 상태를 확인하세요.

## 기본 구조

`uv`는 패키지 작업과 런타임 관리를 모두 수행하며, 핵심 명령은 `uv <subcommand>` 형식입니다.

| 범주 | 명령 예시 | 설명 |
| --- | --- | --- |
| 프로젝트 초기화 | `uv init`, `uv init --package` | pyproject 기반 프로젝트 생성 |
| 의존성 관리 | `uv add requests`, `uv remove pytest` | 의존성 추가/삭제 |
| 설치 | `uv sync`, `uv pip install -r requirements.txt` | `pyproject.toml` 또는 requirements 파일 동기화 |
| 실행 | `uv run python app.py`, `uv run pytest` | 가상환경 자동 선택 후 명령 실행 |
| 환경 | `uv python install 3.11`, `uv venv --python 3.12` | 파이썬 런타임 설치/가상환경 생성 |
| 캐시 | `uv cache prune`, `uv cache stats` | 다운로드 캐시 관리 |

## 빠른 시작

```bash
# 새 프로젝트 생성
uv init myapp
cd myapp

# 의존성 추가
uv add fastapi uvicorn
uv add --dev pytest

# 애플리케이션 실행
uv run uvicorn myapp.main:app --reload

# 테스트 실행
uv run pytest
```

`uv run`은 항상 프로젝트 전용 가상환경을 활성화한 뒤 명령을 실행하므로, 별도로 `source .venv/bin/activate`를 수행할 필요가 없습니다.

## 주요 기능 정리

- **초고속 패키지 설치**: Rust 기반 병렬 다운로드/빌드로 pip 대비 큰 속도 향상을 제공합니다.
- **단일 잠금 파일**: `uv lock` 혹은 `uv add`가 `uv.lock`을 관리해 재현 가능한 환경 구성이 가능합니다.
- **여러 런타임 관리**: `uv python install`, `uv python list` 등으로 pyenv 없이도 버전 관리가 가능합니다.
- **Node.js 지원**: `uv add --tool nodejs`와 같이 도구 의존성도 설치할 수 있습니다.
- **서브 명령 호환**: 기존 pip 명령에 익숙하다면 `uv pip <명령>` 형식으로 대부분 동일하게 사용할 수 있습니다.

## 팁과 베스트 프랙티스

- `uv sync`는 `pyproject.toml`과 `uv.lock`을 기준으로 가상환경을 재구성합니다. CI에서도 동일한 명령을 사용하세요.
- 프로젝트 루트에 `.python-version`이 있다면 `uv`가 버전을 읽어 자동으로 해당 런타임을 준비합니다.
- `uv run --with coverage pytest`처럼 필요 시 일회성 도구를 `--with` 옵션으로 가져올 수 있습니다.
- 기존 requirements 프로젝트를 이전할 때는 `uv pip compile requirements.in`으로 변환하거나, `uv init --package` 후 `uv add -r requirements.txt`를 수행하면 됩니다.

## 추가 자료

- 공식 사이트: <https://docs.astral.sh/uv/>
- 프로젝트 템플릿 예시: `uv init --template astral-sh/uv-template`
- GitHub: <https://github.com/astral-sh/uv>
