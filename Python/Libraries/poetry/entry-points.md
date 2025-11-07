# Python 패키지 엔트리 포인트 (Entry Points)

## 개요

`[project.scripts]`는 Python 패키지를 설치할 때 CLI 명령어를 시스템에 자동으로 등록하는 메커니즘입니다.

## 기본 문법

```toml
[project.scripts]
명령어이름 = "패키지명:함수명"
```

## 실제 예제: httpx

### pyproject.toml 설정

```toml
[project.scripts]
httpx = "httpx:main"
```

### 동작 방식

1. **패키지 설치 시**
   ```bash
   pip install httpx
   # 또는
   poetry add httpx
   ```

2. **명령어 등록**
   - `httpx`라는 실행 가능한 명령어가 시스템 PATH에 자동 등록됩니다
   - Linux/macOS: `/usr/local/bin/httpx` 또는 가상환경의 `bin/httpx`
   - Windows: `Scripts/httpx.exe`

3. **함수 연결**
   ```
   httpx:main
   ├── httpx → 패키지명
   └── main → 함수명
   ```

### 코드 구조

```
httpx/
├── __init__.py
│   └── from ._main import main  # main 함수를 패키지 레벨에서 노출
└── _main.py
    └── def main():              # 실제 진입점 함수
            print("Hello from httpx CLI!")
```

### httpx/__init__.py

```python
from ._main import main

__all__ = ["main"]
```

### httpx/_main.py

```python
def main():
    """httpx CLI의 실제 진입점"""
    import sys
    print(f"httpx CLI started with args: {sys.argv}")
    # CLI 로직 구현
```

### 실행 흐름

```
$ httpx --help
      ↓
시스템이 httpx 명령어 찾기
      ↓
httpx 패키지의 main 함수 호출
      ↓
httpx/__init__.py의 main → httpx._main.main 실행
```

## Poetry에서 사용하기

### pyproject.toml

```toml
[tool.poetry]
name = "myapp"
version = "0.1.0"

[tool.poetry.scripts]
myapp = "myapp.cli:main"
mycli = "myapp.commands:run"
```

### 프로젝트 구조

```
myapp/
├── pyproject.toml
├── myapp/
│   ├── __init__.py
│   ├── cli.py
│   │   └── def main():
│   │           print("Main CLI")
│   └── commands.py
│       └── def run():
│               print("Running command")
```

### 설치 후 사용

```bash
poetry install

# 명령어 사용
myapp       # myapp.cli:main 실행
mycli       # myapp.commands:run 실행
```

## 다양한 패턴

### 1. 단순 함수 연결

```toml
[project.scripts]
hello = "mypackage:say_hello"
```

```python
# mypackage/__init__.py
def say_hello():
    print("Hello, World!")
```

### 2. 모듈 내 함수 연결

```toml
[project.scripts]
deploy = "mypackage.deployment:deploy_app"
```

```python
# mypackage/deployment.py
def deploy_app():
    print("Deploying application...")
```

### 3. 클래스 메서드 연결

```toml
[project.scripts]
server = "mypackage.server:Server.run"
```

```python
# mypackage/server.py
class Server:
    @staticmethod
    def run():
        print("Starting server...")
```

### 4. Click/Typer와 함께 사용

```toml
[project.scripts]
mycli = "mypackage.cli:app"
```

```python
# mypackage/cli.py
import typer

app = typer.Typer()

@app.command()
def hello(name: str):
    print(f"Hello {name}!")

@app.command()
def goodbye(name: str):
    print(f"Goodbye {name}!")
```

```bash
mycli hello World     # Hello World!
mycli goodbye World   # Goodbye World!
```

## 실전 예제: 간단한 CLI 도구 만들기

### 1. 프로젝트 초기화

```bash
mkdir mytool
cd mytool
poetry init -n
```

### 2. pyproject.toml 수정

```toml
[tool.poetry]
name = "mytool"
version = "0.1.0"
description = "My CLI Tool"

[tool.poetry.dependencies]
python = "^3.8"
typer = "^0.9.0"

[tool.poetry.scripts]
mytool = "mytool.main:app"
```

### 3. 코드 작성

```python
# mytool/__init__.py
# (비어있어도 됨)

# mytool/main.py
import typer

app = typer.Typer()

@app.command()
def hello(name: str = "World"):
    """Say hello to someone"""
    typer.echo(f"Hello {name}!")

@app.command()
def version():
    """Show version"""
    typer.echo("mytool version 0.1.0")

if __name__ == "__main__":
    app()
```

### 4. 설치 및 사용

```bash
poetry install

# CLI 사용
mytool hello
mytool hello Alice
mytool version
```

## 디버깅 팁

### 등록된 명령어 확인

```bash
# 가상환경 활성화 후
which httpx
# 또는
type httpx
```

### 진입점 스크립트 내용 확인

```bash
cat $(which httpx)
```

출력 예시:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import sys
from httpx import main

if __name__ == '__main__':
    sys.exit(main())
```

## 주의사항

1. **함수는 반드시 호출 가능해야 함**
   ```python
   # OK
   def main():
       pass

   # NG
   main = "string"  # 함수가 아님
   ```

2. **패키지 레벨에서 import 가능해야 함**
   ```python
   # __init__.py에서 노출 필요
   from ._main import main
   ```

3. **명령어 이름 충돌 주의**
   - 시스템 명령어와 겹치지 않도록 확인
   - 예: `ls`, `cd`, `python` 등은 피하기

## pyproject.toml vs setup.py 비교

### 구식 (setup.py)

```python
from setuptools import setup

setup(
    name="myapp",
    entry_points={
        "console_scripts": [
            "myapp=myapp.cli:main",
        ],
    },
)
```

### 현대식 (pyproject.toml)

```toml
[project.scripts]
myapp = "myapp.cli:main"
```

## 참고 자료

- [PEP 621 - Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [Poetry Documentation - Scripts](https://python-poetry.org/docs/pyproject/#scripts)
- [Setuptools - Entry Points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html)
