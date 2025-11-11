"""
ConfigDict 실제 사용 예제

이 파일은 Pydantic v2의 ConfigDict 설정을 실제로 사용하는 예제를 제공합니다.
각 예제는 독립적으로 실행 가능합니다.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# 1. from_attributes 예제: ORM 모델 변환
# ============================================================================

class DjangoLikeModel:
    """Django ORM 모델을 시뮬레이션하는 클래스"""
    def __init__(self):
        self.id = 1
        self.username = "john_doe"
        self.email = "john@example.com"
        self.is_active = True
        self.created_at = datetime(2024, 1, 1, 12, 0)


class UserSchema(BaseModel):
    """from_attributes=True로 ORM 객체를 변환하는 스키마"""
    model_config = ConfigDict(
        from_attributes=True,  # 객체 속성으로부터 생성 가능
        use_enum_values=True
    )

    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime


def example_from_attributes():
    """from_attributes 사용 예제"""
    print("\n=== from_attributes 예제 ===")

    # Django 스타일 모델 인스턴스 생성
    django_user = DjangoLikeModel()

    # from_attributes=True 덕분에 객체에서 직접 변환
    user_schema = UserSchema.model_validate(django_user)
    print(f"변환된 스키마: {user_schema}")
    print(f"JSON 출력: {user_schema.model_dump_json()}")


# ============================================================================
# 2. validate_assignment 예제: 런타임 검증
# ============================================================================

class Product(BaseModel):
    """속성 할당 시 검증하는 모델"""
    model_config = ConfigDict(
        validate_assignment=True,  # 속성 변경 시 검증
        str_strip_whitespace=True   # 문자열 공백 자동 제거
    )

    name: str
    price: float
    quantity: int = Field(gt=0, description="수량은 0보다 커야 함")

    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('가격은 0 이상이어야 합니다')
        return round(v, 2)  # 소수점 2자리까지


def example_validate_assignment():
    """validate_assignment 사용 예제"""
    print("\n=== validate_assignment 예제 ===")

    # 제품 생성
    product = Product(name="  노트북  ", price=1500000.999, quantity=5)
    print(f"생성된 제품: {product}")
    print(f"제품명 (공백 제거됨): '{product.name}'")
    print(f"가격 (반올림됨): {product.price}")

    # 속성 변경 시 검증
    try:
        product.quantity = -1  # 에러 발생!
    except Exception as e:
        print(f"검증 에러: {e}")

    product.quantity = 10  # 정상
    print(f"수량 업데이트: {product.quantity}")


# ============================================================================
# 3. extra 설정 예제: 추가 필드 처리
# ============================================================================

class StrictAPIRequest(BaseModel):
    """엄격한 API 요청 모델 (추가 필드 거부)"""
    model_config = ConfigDict(
        extra='forbid',             # 정의되지 않은 필드 거부
        str_strip_whitespace=True
    )

    username: str
    password: str


class FlexibleAPIRequest(BaseModel):
    """유연한 API 요청 모델 (추가 필드 허용)"""
    model_config = ConfigDict(
        extra='allow',              # 추가 필드 허용
        str_strip_whitespace=True
    )

    username: str
    password: str


def example_extra_fields():
    """extra 설정 사용 예제"""
    print("\n=== extra 필드 처리 예제 ===")

    # 유연한 모델 - 추가 필드 허용
    flexible = FlexibleAPIRequest(
        username="john",
        password="secret",
        remember_me=True,  # 추가 필드
        session_id="abc123"  # 추가 필드
    )
    print(f"유연한 모델: {flexible.model_dump()}")

    # 엄격한 모델 - 추가 필드 거부
    try:
        strict = StrictAPIRequest(
            username="john",
            password="secret",
            remember_me=True  # 에러 발생!
        )
    except Exception as e:
        print(f"엄격한 모델 에러: {e}")


# ============================================================================
# 4. populate_by_name 예제: 별칭 사용
# ============================================================================

class APIResponse(BaseModel):
    """API 응답 모델 (별칭 지원)"""
    model_config = ConfigDict(
        populate_by_name=True  # 별칭과 실제 필드명 모두 허용
    )

    user_id: int = Field(alias='userId')
    user_name: str = Field(alias='userName')
    created_date: datetime = Field(alias='createdAt')


def example_populate_by_name():
    """populate_by_name 사용 예제"""
    print("\n=== populate_by_name 예제 ===")

    # camelCase 별칭 사용
    response1 = APIResponse(
        userId=1,
        userName="김철수",
        createdAt=datetime.now()
    )
    print(f"별칭으로 생성: {response1}")

    # snake_case 실제 필드명 사용
    response2 = APIResponse(
        user_id=2,
        user_name="이영희",
        created_date=datetime.now()
    )
    print(f"실제 필드명으로 생성: {response2}")

    # JSON 출력 시 별칭 사용
    print(f"JSON (별칭 사용): {response1.model_dump(by_alias=True)}")


# ============================================================================
# 5. 복합 예제: 실제 사용 시나리오
# ============================================================================

class UserStatus(str, Enum):
    """사용자 상태 Enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class CompleteUserModel(BaseModel):
    """실제 프로덕션에서 사용할 만한 완전한 사용자 모델"""
    model_config = ConfigDict(
        from_attributes=True,        # ORM 변환 지원
        validate_assignment=True,    # 런타임 검증
        use_enum_values=True,        # Enum을 값으로 직렬화
        str_strip_whitespace=True,   # 문자열 공백 제거
        populate_by_name=True,       # 별칭 지원
        extra='forbid'               # 엄격한 필드 검증
    )

    id: int = Field(gt=0, description="사용자 ID")
    username: str = Field(min_length=3, max_length=20, alias='userName')
    email: str = Field(regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    status: UserStatus = UserStatus.ACTIVE
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = []
    metadata: Optional[dict] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v:
            raise ValueError('사용자명은 알파벳, 숫자, 언더스코어만 가능')
        return v.lower()  # 소문자로 변환


class SQLAlchemyLikeModel:
    """SQLAlchemy ORM 모델 시뮬레이션"""
    def __init__(self):
        self.id = 100
        self.username = "  JOHN_DOE  "
        self.email = "john@example.com"
        self.status = UserStatus.ACTIVE
        self.is_verified = True
        self.created_at = datetime(2024, 1, 1)
        self.tags = ["developer", "python"]
        self.metadata = {"location": "Seoul"}


def example_complete_model():
    """복합 모델 사용 예제"""
    print("\n=== 복합 모델 예제 ===")

    # 1. ORM 객체에서 변환
    orm_user = SQLAlchemyLikeModel()
    user = CompleteUserModel.model_validate(orm_user)
    print(f"ORM에서 변환: {user}")
    print(f"사용자명 (소문자/공백제거): '{user.username}'")

    # 2. 딕셔너리로 생성 (별칭 사용)
    user2 = CompleteUserModel(
        id=200,
        userName="  Alice_Smith  ",  # 별칭 사용, 공백 제거, 소문자 변환
        email="alice@example.com",
        status="inactive",  # 문자열로도 가능
        tags=["designer", "ui/ux"]
    )
    print(f"\n별칭으로 생성: {user2}")

    # 3. 런타임 속성 변경 및 검증
    user2.email = "newalice@example.com"  # 검증됨
    print(f"이메일 변경: {user2.email}")

    try:
        user2.email = "invalid-email"  # 검증 실패
    except Exception as e:
        print(f"이메일 검증 에러: {e}")

    # 4. JSON 직렬화
    json_data = user2.model_dump_json(by_alias=True, indent=2)
    print(f"\nJSON 출력:\n{json_data}")


# ============================================================================
# 6. from_attributes 유무 비교 예제
# ============================================================================

class WithoutFromAttributes(BaseModel):
    """from_attributes가 없는 모델 (기본)"""
    # model_config 없음 (기본값: from_attributes=False)

    name: str
    age: int


class WithFromAttributes(BaseModel):
    """from_attributes가 있는 모델"""
    model_config = ConfigDict(from_attributes=True)

    name: str
    age: int


class PersonObject:
    """일반 Python 객체"""
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age


def example_from_attributes_comparison():
    """from_attributes 유무 비교"""
    print("\n=== from_attributes 유무 비교 ===")

    # 일반 객체 생성
    person = PersonObject("박민수", 25)

    # from_attributes=False (기본값)
    print("1. from_attributes=False (기본값):")
    try:
        without = WithoutFromAttributes.model_validate(person)
    except Exception as e:
        print(f"  - 객체 변환 실패: {type(e).__name__}")

    # 딕셔너리 변환 필요
    without = WithoutFromAttributes(**person.__dict__)
    print(f"  - 딕셔너리 변환 성공: {without}")

    # from_attributes=True
    print("\n2. from_attributes=True:")
    with_attr = WithFromAttributes.model_validate(person)
    print(f"  - 객체 직접 변환 성공: {with_attr}")

    # 딕셔너리도 여전히 작동
    with_attr2 = WithFromAttributes(name="김영희", age=30)
    print(f"  - 딕셔너리도 작동: {with_attr2}")


# ============================================================================
# 메인 실행
# ============================================================================

def main():
    """모든 예제 실행"""
    print("=" * 60)
    print("Pydantic ConfigDict 예제 모음")
    print("=" * 60)

    example_from_attributes()
    example_validate_assignment()
    example_extra_fields()
    example_populate_by_name()
    example_complete_model()
    example_from_attributes_comparison()

    print("\n" + "=" * 60)
    print("모든 예제 실행 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()