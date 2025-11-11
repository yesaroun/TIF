# Pydantic 가이드

Pydantic은 Python의 타입 힌트를 사용하여 데이터 검증과 설정 관리를 제공하는 라이브러리입니다.

## Pydantic v2 주요 변경사항

Pydantic v2에서는 성능 개선과 함께 여러 API 변경이 있었습니다:
- `Config` 클래스 → `ConfigDict` 사용
- `model_config` 속성으로 설정 정의
- 더 빠른 검증 속도 (Rust 기반 핵심 검증 로직)

## 문서 목록

### 핵심 개념
- [ConfigDict 설정 가이드](./config-dict.md) - model_config와 ConfigDict의 모든 것

### 예제
- [ConfigDict 실제 사용 예제](./examples/model-config-examples.py)

## 빠른 시작

### 기본 사용법

```python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    # Pydantic v2 스타일
    model_config = ConfigDict(
        str_strip_whitespace=True,  # 문자열 공백 자동 제거
        validate_assignment=True     # 속성 할당 시 검증
    )

    name: str
    age: int
    email: str
```

### v1 → v2 마이그레이션

**Pydantic v1 (구버전):**
```python
class User(BaseModel):
    name: str

    class Config:
        orm_mode = True
        validate_assignment = True
```

**Pydantic v2 (현재):**
```python
from pydantic import ConfigDict

class User(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # orm_mode → from_attributes
        validate_assignment=True
    )

    name: str
```

## 주요 사용 사례

### 1. FastAPI 요청/응답 모델
```python
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

class RequestModel(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid'  # 정의되지 않은 필드 거부
    )

    username: str
    password: str
```

### 2. Django ORM 연동
```python
from pydantic import BaseModel, ConfigDict
from myapp.models import User as DjangoUser

class UserSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True  # Django 모델 객체로부터 생성 가능
    )

    id: int
    username: str
    email: str

# Django 모델에서 Pydantic 모델로 변환
django_user = DjangoUser.objects.get(id=1)
user_schema = UserSchema.model_validate(django_user)
```

### 3. 환경 설정 관리
```python
from pydantic import BaseSettings, ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file='.env',
        env_file_encoding='utf-8'
    )

    database_url: str
    secret_key: str
    debug: bool = False
```

## 참고 자료

- [공식 문서](https://docs.pydantic.dev/)
- [v1 → v2 마이그레이션 가이드](https://docs.pydantic.dev/latest/migration/)
- [FastAPI와 Pydantic](https://fastapi.tiangolo.com/tutorial/body/)