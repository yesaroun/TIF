# ConfigDict 완벽 가이드

## 개요

Pydantic v2에서는 모델 설정을 `ConfigDict`를 통해 정의합니다. 이전 버전의 `Config` 클래스를 대체하며, 더 명확하고 타입 안전한 방식을 제공합니다.

```python
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        # 여기에 설정 옵션들을 정의
    )
```

## 주요 ConfigDict 설정

### 1. `from_attributes` (구 orm_mode)

**용도:** 일반 Python 객체의 속성으로부터 모델을 생성할 수 있게 합니다.

**언제 사용하나?**
- Django/SQLAlchemy ORM 모델을 Pydantic 모델로 변환할 때
- 속성으로 데이터에 접근하는 객체를 다룰 때
- dataclass나 namedtuple을 변환할 때

```python
from pydantic import BaseModel, ConfigDict

class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str

# Django 모델 예시
class DjangoUser:
    def __init__(self):
        self.id = 1
        self.name = "홍길동"
        self.email = "hong@example.com"

# from_attributes=True로 인해 객체 속성에서 직접 생성 가능
django_user = DjangoUser()
user = UserSchema.model_validate(django_user)
print(user)  # id=1 name='홍길동' email='hong@example.com'

# from_attributes=False(기본값)라면 에러 발생
# 딕셔너리 형태로 변환 필요: UserSchema(**django_user.__dict__)
```

### 2. `validate_assignment`

**용도:** 모델 인스턴스 생성 후 속성 할당 시에도 검증을 수행합니다.

```python
class User(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    name: str
    age: int

user = User(name="김철수", age=30)
user.age = "스물"  # ValidationError 발생! (int가 아님)
user.age = 25      # 정상 작동
```

### 3. `str_strip_whitespace`

**용도:** 문자열 필드의 앞뒤 공백을 자동으로 제거합니다.

```python
class User(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str
    email: str

user = User(
    username="  john_doe  ",
    email="  john@example.com  "
)
print(user.username)  # "john_doe" (공백 제거됨)
print(user.email)     # "john@example.com"
```

### 4. `extra`

**용도:** 정의되지 않은 추가 필드를 어떻게 처리할지 결정합니다.

```python
# extra='forbid' - 추가 필드 거부
class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str

# 에러 발생: unexpected keyword argument 'age'
# strict = StrictModel(name="김철수", age=30)

# extra='ignore' - 추가 필드 무시 (기본값)
class IgnoreModel(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: str

ignore = IgnoreModel(name="김철수", age=30)
print(ignore.model_dump())  # {'name': '김철수'} (age 무시됨)

# extra='allow' - 추가 필드 허용
class AllowModel(BaseModel):
    model_config = ConfigDict(extra='allow')
    name: str

allow = AllowModel(name="김철수", age=30)
print(allow.model_dump())  # {'name': '김철수', 'age': 30}
```

### 5. `populate_by_name`

**용도:** 필드 별칭(alias)과 실제 필드명 모두를 사용할 수 있게 합니다.

```python
from pydantic import Field

class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(alias='user_name')
    email: str

# 별칭과 실제 필드명 모두 사용 가능
user1 = User(user_name="john", email="john@example.com")
user2 = User(username="jane", email="jane@example.com")
```

### 6. `use_enum_values`

**용도:** Enum 필드를 실제 값으로 직렬화합니다.

```python
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class User(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str
    status: Status

user = User(name="김철수", status=Status.ACTIVE)
print(user.model_dump())  # {'name': '김철수', 'status': 'active'}
# use_enum_values=False라면: {'name': '김철수', 'status': <Status.ACTIVE>}
```

### 7. `arbitrary_types_allowed`

**용도:** Pydantic이 검증할 수 없는 임의의 타입을 허용합니다.

```python
import numpy as np

class DataModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    data: np.ndarray  # NumPy 배열 같은 커스텀 타입

arr = np.array([1, 2, 3])
model = DataModel(name="dataset", data=arr)
```

### 8. `json_encoders` (v2에서는 `model_serializer` 사용 권장)

**용도:** 특정 타입의 JSON 직렬화 방식을 커스터마이징합니다.

```python
from datetime import datetime

class Event(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }
    )

    name: str
    created_at: datetime

event = Event(name="미팅", created_at=datetime.now())
print(event.model_dump_json())
```

## ConfigDict 설정 조합 예시

### API 요청 모델 (엄격한 검증)

```python
class APIRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,  # 문자열 공백 제거
        extra='forbid',              # 추가 필드 거부
        validate_assignment=True     # 할당 시 검증
    )

    username: str
    password: str
```

### ORM 연동 모델 (유연한 변환)

```python
class ORMSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,        # ORM 객체에서 변환
        populate_by_name=True,       # 별칭 허용
        use_enum_values=True         # Enum 값 직렬화
    )

    id: int
    name: str
    status: Status
```

### 설정 모델 (환경 변수)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,        # 대소문자 구분 없음
        extra='ignore'               # 추가 환경 변수 무시
    )

    database_url: str
    api_key: str
```

## from_attributes 사용/미사용 비교

### `from_attributes=False` (기본값)

```python
class UserSchema(BaseModel):
    # from_attributes 설정 없음 (기본값 False)
    name: str
    age: int

# 딕셔너리로만 생성 가능
user = UserSchema(name="김철수", age=30)  # OK
user = UserSchema(**{"name": "김철수", "age": 30})  # OK

# 객체 속성으로는 생성 불가
class Person:
    def __init__(self):
        self.name = "김철수"
        self.age = 30

person = Person()
# user = UserSchema.model_validate(person)  # 에러!
# 변환 필요:
user = UserSchema(**person.__dict__)  # OK
```

### `from_attributes=True`

```python
class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    age: int

# 모든 방식으로 생성 가능
user1 = UserSchema(name="김철수", age=30)  # 딕셔너리 방식
user2 = UserSchema.model_validate(person)   # 객체 속성 방식
user3 = UserSchema.model_validate({"name": "김철수", "age": 30})  # 딕셔너리도 OK
```

## 마이그레이션 가이드

### Pydantic v1 → v2 주요 변경사항

| v1 (Config 클래스) | v2 (ConfigDict) |
|-------------------|-----------------|
| `orm_mode = True` | `from_attributes=True` |
| `allow_population_by_field_name = True` | `populate_by_name=True` |
| `validate_all = True` | 기본 동작 |
| `allow_mutation = False` | `frozen=True` |
| `smart_union = True` | `smart_union=True` (deprecated) |
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `parse_obj()` | `model_validate()` |
| `schema()` | `model_json_schema()` |

## 자주 하는 실수와 해결법

### 1. from_attributes를 설정하지 않고 ORM 객체 변환

```python
# ❌ 잘못된 방법
class UserSchema(BaseModel):
    name: str

django_user = DjangoUser.objects.get(id=1)
user = UserSchema.model_validate(django_user)  # 에러!

# ✅ 올바른 방법
class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str

user = UserSchema.model_validate(django_user)  # 성공!
```

### 2. validate_assignment 없이 속성 수정

```python
# ❌ 검증 없이 잘못된 타입 할당
class User(BaseModel):
    age: int

user = User(age=30)
user.age = "thirty"  # 에러 없이 잘못된 값 할당됨

# ✅ 속성 할당 시 검증
class User(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    age: int

user = User(age=30)
user.age = "thirty"  # ValidationError 발생!
```

### 3. 불필요한 from_attributes 사용

```python
# ❌ 딕셔너리만 사용하는데 from_attributes 설정
class APIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # 불필요
    data: dict

# ✅ 필요한 경우에만 사용
class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM 변환 시 필요
    id: int
    name: str
```

## 성능 고려사항

1. **from_attributes**: 약간의 오버헤드 발생 (속성 접근 체크)
2. **validate_assignment**: 모든 속성 할당마다 검증으로 성능 영향
3. **str_strip_whitespace**: 모든 문자열 처리로 약간의 오버헤드
4. **extra='forbid'**: 추가 필드 체크로 약간의 오버헤드

일반적으로 성능 영향은 미미하지만, 대량 데이터 처리 시에는 필요한 설정만 사용하는 것이 좋습니다.