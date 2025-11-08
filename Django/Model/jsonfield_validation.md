# Django JSONField 안전하게 사용하기

## 목차
1. [기본 개념](#기본-개념)
2. [왜 검증이 필요한가](#왜-검증이-필요한가)
3. [방법 1: Pydantic Schema를 사용한 검증](#방법-1-pydantic-schema를-사용한-검증)
4. [방법 2: clean() 메서드를 사용한 검증](#방법-2-clean-메서드를-사용한-검증)
5. [두 방법 비교](#두-방법-비교)
6. [실전 예제](#실전-예제)
7. [베스트 프랙티스](#베스트-프랙티스)

---

## 기본 개념

### JSONField란?

Django의 `JSONField`는 Python dict/list를 JSON 형식으로 데이터베이스에 저장할 수 있는 필드입니다.

```python
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    # JSON 형태로 다양한 속성을 저장
    attributes = models.JSONField(default=dict)
```

### 특징
- PostgreSQL, MySQL 8.0+, SQLite 3.9+, Oracle에서 사용 가능
- Python의 dict, list를 자동으로 JSON으로 변환
- 유연한 데이터 구조 저장 가능
- 데이터베이스 레벨에서 JSON 쿼리 지원

---

## 왜 검증이 필요한가

### ❌ 문제 상황

JSONField는 자유로운 구조를 허용하기 때문에 검증 없이 사용하면 문제가 발생할 수 있습니다.

```python
# 문제 1: 불일치한 데이터 구조
product1 = Product.objects.create(
    name="노트북",
    attributes={"color": "silver", "weight": 1.5}
)

product2 = Product.objects.create(
    name="마우스",
    attributes={"colour": "black", "size": "medium"}  # typo: colour
)

# 문제 2: 타입 불일치
product3 = Product.objects.create(
    name="키보드",
    attributes={"color": "white", "weight": "500g"}  # weight가 문자열
)

# 코드에서 사용 시 예기치 않은 오류 발생
for product in Product.objects.all():
    total_weight = product.attributes.get("weight", 0) * 2  # TypeError 발생 가능
```

### 발생할 수 있는 문제
1. **타입 불일치**: 숫자여야 할 값이 문자열로 저장됨
2. **키 이름 오타**: `color` vs `colour`
3. **필수 필드 누락**: 필요한 키가 없음
4. **구조 불일치**: 같은 모델인데 서로 다른 JSON 구조
5. **디버깅 어려움**: 런타임에만 오류 발견

---

## 방법 1: Pydantic Schema를 사용한 검증

### Pydantic이란?

Pydantic은 Python의 타입 힌트를 사용하여 데이터 검증을 수행하는 라이브러리입니다.

### 설치

```bash
pip install pydantic
```

### 기본 사용법

```python
from django.db import models
from pydantic import BaseModel, Field, ValidationError
from typing import Optional

# 1. Pydantic Schema 정의
class ProductAttributesSchema(BaseModel):
    color: str = Field(..., min_length=1, max_length=50)
    weight: float = Field(..., gt=0)  # 0보다 커야 함
    dimensions: Optional[dict] = None

    class Config:
        # 추가 필드 허용 여부
        extra = "forbid"  # 정의되지 않은 필드는 거부

# 2. Django Model에서 사용
class Product(models.Model):
    name = models.CharField(max_length=100)
    attributes = models.JSONField(default=dict)

    def clean(self):
        """모델 레벨 검증"""
        super().clean()
        try:
            # Pydantic으로 검증
            ProductAttributesSchema(**self.attributes)
        except ValidationError as e:
            from django.core.exceptions import ValidationError as DjangoValidationError
            raise DjangoValidationError(f"Invalid attributes: {e}")

    def save(self, *args, **kwargs):
        # clean() 메서드 호출
        self.full_clean()
        super().save(*args, **kwargs)
```

### 고급 사용 예제

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class UserSettingsSchema(BaseModel):
    """사용자 설정 스키마"""
    theme: str = Field(..., pattern="^(light|dark|auto)$")
    language: str = Field(..., min_length=2, max_length=5)
    notifications: dict = Field(default_factory=dict)
    font_size: int = Field(default=14, ge=10, le=24)

    @validator('notifications')
    def validate_notifications(cls, v):
        """알림 설정 검증"""
        allowed_keys = {'email', 'push', 'sms'}
        if not set(v.keys()).issubset(allowed_keys):
            raise ValueError(f"Only {allowed_keys} are allowed")

        for key, value in v.items():
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be boolean")
        return v

    class Config:
        extra = "forbid"

class UserProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    settings = models.JSONField(default=dict)

    def clean(self):
        super().clean()
        try:
            UserSettingsSchema(**self.settings)
        except ValidationError as e:
            from django.core.exceptions import ValidationError as DjangoValidationError
            raise DjangoValidationError(f"Invalid settings: {e}")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### 사용 예시

```python
# ✅ 올바른 사용
profile = UserProfile.objects.create(
    user=user,
    settings={
        "theme": "dark",
        "language": "ko",
        "notifications": {
            "email": True,
            "push": False
        },
        "font_size": 16
    }
)

# ❌ 잘못된 테마 값
try:
    profile = UserProfile(
        user=user,
        settings={
            "theme": "blue",  # light, dark, auto만 허용
            "language": "ko"
        }
    )
    profile.save()  # ValidationError 발생
except ValidationError as e:
    print(e)

# ❌ 잘못된 알림 설정
try:
    profile = UserProfile(
        user=user,
        settings={
            "theme": "dark",
            "language": "ko",
            "notifications": {
                "email": "yes"  # boolean이어야 함
            }
        }
    )
    profile.save()  # ValidationError 발생
except ValidationError as e:
    print(e)
```

---

## 방법 2: clean() 메서드를 사용한 검증

### 기본 개념

Django Model의 `clean()` 메서드는 모델 레벨에서 검증을 수행하는 표준 방법입니다.

### 기본 사용법

```python
from django.db import models
from django.core.exceptions import ValidationError

class Product(models.Model):
    name = models.CharField(max_length=100)
    attributes = models.JSONField(default=dict)

    def clean(self):
        """JSONField 데이터 검증"""
        super().clean()

        # 1. 필수 키 확인
        required_keys = {'color', 'weight'}
        missing_keys = required_keys - set(self.attributes.keys())
        if missing_keys:
            raise ValidationError(
                f"Missing required attributes: {', '.join(missing_keys)}"
            )

        # 2. 타입 검증
        if not isinstance(self.attributes.get('color'), str):
            raise ValidationError("'color' must be a string")

        if not isinstance(self.attributes.get('weight'), (int, float)):
            raise ValidationError("'weight' must be a number")

        # 3. 값 범위 검증
        if self.attributes.get('weight', 0) <= 0:
            raise ValidationError("'weight' must be greater than 0")

        # 4. 선택적 필드 검증
        if 'dimensions' in self.attributes:
            dimensions = self.attributes['dimensions']
            if not isinstance(dimensions, dict):
                raise ValidationError("'dimensions' must be a dictionary")

            required_dim_keys = {'width', 'height', 'depth'}
            if not required_dim_keys.issubset(set(dimensions.keys())):
                raise ValidationError(
                    f"'dimensions' must contain {required_dim_keys}"
                )

    def save(self, *args, **kwargs):
        # clean() 메서드 호출
        self.full_clean()
        super().save(*args, **kwargs)
```

### 재사용 가능한 검증 헬퍼 함수

```python
class JSONFieldValidationMixin:
    """JSONField 검증을 위한 믹스인"""

    def validate_json_structure(self, data, schema):
        """
        JSON 데이터가 스키마를 만족하는지 검증

        schema 예시:
        {
            'color': {'type': str, 'required': True},
            'weight': {'type': (int, float), 'required': True, 'min': 0},
            'tags': {'type': list, 'required': False}
        }
        """
        for key, rules in schema.items():
            # 필수 필드 확인
            if rules.get('required', False) and key not in data:
                raise ValidationError(f"'{key}' is required")

            # 값이 있을 때만 검증
            if key in data:
                value = data[key]

                # 타입 검증
                expected_type = rules.get('type')
                if expected_type and not isinstance(value, expected_type):
                    raise ValidationError(
                        f"'{key}' must be {expected_type.__name__}"
                    )

                # 최소값 검증
                if 'min' in rules and value < rules['min']:
                    raise ValidationError(
                        f"'{key}' must be at least {rules['min']}"
                    )

                # 최대값 검증
                if 'max' in rules and value > rules['max']:
                    raise ValidationError(
                        f"'{key}' must be at most {rules['max']}"
                    )

                # 선택지 검증
                if 'choices' in rules and value not in rules['choices']:
                    raise ValidationError(
                        f"'{key}' must be one of {rules['choices']}"
                    )

                # 커스텀 검증 함수
                if 'validator' in rules:
                    validator = rules['validator']
                    validator(value)

class Product(JSONFieldValidationMixin, models.Model):
    name = models.CharField(max_length=100)
    attributes = models.JSONField(default=dict)

    def clean(self):
        super().clean()

        schema = {
            'color': {
                'type': str,
                'required': True,
                'choices': ['red', 'blue', 'green', 'silver', 'black', 'white']
            },
            'weight': {
                'type': (int, float),
                'required': True,
                'min': 0,
                'max': 1000
            },
            'dimensions': {
                'type': dict,
                'required': False,
                'validator': self._validate_dimensions
            }
        }

        self.validate_json_structure(self.attributes, schema)

    def _validate_dimensions(self, dimensions):
        """dimensions 필드 검증"""
        required_keys = {'width', 'height', 'depth'}
        if not required_keys.issubset(set(dimensions.keys())):
            raise ValidationError(
                f"dimensions must contain {required_keys}"
            )

        for key in required_keys:
            if not isinstance(dimensions[key], (int, float)) or dimensions[key] <= 0:
                raise ValidationError(
                    f"dimensions.{key} must be a positive number"
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### 사용 예시

```python
# ✅ 올바른 사용
product = Product.objects.create(
    name="노트북",
    attributes={
        "color": "silver",
        "weight": 1.5,
        "dimensions": {
            "width": 30,
            "height": 20,
            "depth": 2
        }
    }
)

# ❌ 필수 필드 누락
try:
    product = Product(
        name="마우스",
        attributes={"color": "black"}  # weight 누락
    )
    product.save()  # ValidationError 발생
except ValidationError as e:
    print(e)

# ❌ 잘못된 타입
try:
    product = Product(
        name="키보드",
        attributes={
            "color": "white",
            "weight": "500g"  # 문자열이 아닌 숫자여야 함
        }
    )
    product.save()  # ValidationError 발생
except ValidationError as e:
    print(e)

# ❌ 범위 초과
try:
    product = Product(
        name="무거운 물건",
        attributes={
            "color": "black",
            "weight": 1500  # max=1000 초과
        }
    )
    product.save()  # ValidationError 발생
except ValidationError as e:
    print(e)
```

---

## 두 방법 비교

### Pydantic Schema 방식

#### 장점
✅ 타입 힌트 기반으로 코드 가독성이 높음
✅ IDE 자동완성 지원
✅ 복잡한 검증 로직을 선언적으로 표현 가능
✅ 중첩된 구조 검증이 쉬움
✅ 재사용 가능한 스키마 정의
✅ 자동 타입 변환 (coercion) 지원
✅ JSON Schema 생성 가능

#### 단점
❌ 외부 라이브러리 의존성
❌ Pydantic 학습 필요
❌ 약간의 성능 오버헤드

#### 적합한 경우
- 복잡한 JSON 구조를 다룰 때
- 타입 안정성이 중요할 때
- 여러 곳에서 같은 스키마를 재사용할 때
- API와 데이터 구조를 공유할 때

### clean() 메서드 방식

#### 장점
✅ Django 표준 방식
✅ 외부 의존성 없음
✅ Django의 다른 검증과 일관성 유지
✅ 세밀한 제어 가능
✅ Django 에러 메시지와 통합

#### 단점
❌ 검증 로직이 길어질 수 있음
❌ 반복적인 코드 작성
❌ 타입 힌트 지원 부족
❌ 중첩된 구조 검증이 복잡해질 수 있음

#### 적합한 경우
- 간단한 JSON 구조를 다룰 때
- 외부 의존성을 최소화하고 싶을 때
- Django의 다른 검증과 통합이 필요할 때
- 프로젝트 규모가 작을 때

### 비교표

| 특성 | Pydantic | clean() 메서드 |
|------|----------|----------------|
| 학습 곡선 | 중간 | 낮음 |
| 코드 가독성 | 높음 | 중간 |
| 외부 의존성 | 있음 | 없음 |
| 타입 안정성 | 높음 | 낮음 |
| 재사용성 | 높음 | 중간 |
| Django 통합 | 중간 | 높음 |
| 복잡한 검증 | 쉬움 | 복잡함 |
| 성능 | 약간 느림 | 빠름 |

---

## 실전 예제

### 예제 1: 전자상거래 상품 메타데이터

#### Pydantic 방식

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from decimal import Decimal

class PriceSchema(BaseModel):
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(..., pattern="^[A-Z]{3}$")

class SpecificationSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)

class ProductMetadataSchema(BaseModel):
    sku: str = Field(..., min_length=1, max_length=50)
    price: PriceSchema
    specifications: List[SpecificationSchema]
    warranty_months: Optional[int] = Field(None, ge=0, le=120)
    in_stock: bool = True

    @validator('specifications')
    def validate_specifications(cls, v):
        if len(v) == 0:
            raise ValueError("At least one specification required")

        # 중복 이름 검사
        names = [spec.name for spec in v]
        if len(names) != len(set(names)):
            raise ValueError("Specification names must be unique")

        return v

    class Config:
        extra = "forbid"

class Product(models.Model):
    name = models.CharField(max_length=200)
    metadata = models.JSONField(default=dict)

    def clean(self):
        super().clean()
        try:
            ProductMetadataSchema(**self.metadata)
        except ValidationError as e:
            from django.core.exceptions import ValidationError as DjangoValidationError
            raise DjangoValidationError(f"Invalid metadata: {e}")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# 사용
product = Product.objects.create(
    name="맥북 프로",
    metadata={
        "sku": "MBP-M2-16-512",
        "price": {
            "amount": "2499.99",  # Pydantic이 자동으로 Decimal로 변환
            "currency": "USD"
        },
        "specifications": [
            {"name": "CPU", "value": "Apple M2"},
            {"name": "RAM", "value": "16GB"},
            {"name": "Storage", "value": "512GB SSD"}
        ],
        "warranty_months": 12,
        "in_stock": True
    }
)
```

#### clean() 메서드 방식

```python
from decimal import Decimal, InvalidOperation
import re

class Product(JSONFieldValidationMixin, models.Model):
    name = models.CharField(max_length=200)
    metadata = models.JSONField(default=dict)

    def clean(self):
        super().clean()

        # 1. 필수 필드 확인
        required_keys = {'sku', 'price', 'specifications', 'in_stock'}
        missing_keys = required_keys - set(self.metadata.keys())
        if missing_keys:
            raise ValidationError(f"Missing: {', '.join(missing_keys)}")

        # 2. SKU 검증
        sku = self.metadata.get('sku', '')
        if not sku or len(sku) > 50:
            raise ValidationError("Invalid SKU")

        # 3. Price 검증
        price = self.metadata.get('price', {})
        if not isinstance(price, dict):
            raise ValidationError("price must be a dictionary")

        if 'amount' not in price or 'currency' not in price:
            raise ValidationError("price must have amount and currency")

        try:
            amount = Decimal(str(price['amount']))
            if amount < 0:
                raise ValidationError("price amount must be non-negative")
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid price amount")

        currency = price.get('currency', '')
        if not re.match(r'^[A-Z]{3}$', currency):
            raise ValidationError("currency must be 3-letter code")

        # 4. Specifications 검증
        specs = self.metadata.get('specifications', [])
        if not isinstance(specs, list) or len(specs) == 0:
            raise ValidationError("At least one specification required")

        spec_names = []
        for spec in specs:
            if not isinstance(spec, dict):
                raise ValidationError("Each specification must be a dictionary")

            if 'name' not in spec or 'value' not in spec:
                raise ValidationError("Each specification needs name and value")

            spec_names.append(spec['name'])

        # 중복 이름 검사
        if len(spec_names) != len(set(spec_names)):
            raise ValidationError("Specification names must be unique")

        # 5. Warranty 검증 (선택적)
        if 'warranty_months' in self.metadata:
            warranty = self.metadata['warranty_months']
            if not isinstance(warranty, int) or warranty < 0 or warranty > 120:
                raise ValidationError("warranty_months must be 0-120")

        # 6. in_stock 검증
        if not isinstance(self.metadata.get('in_stock'), bool):
            raise ValidationError("in_stock must be boolean")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### 예제 2: 사용자 알림 설정

```python
# Pydantic 방식
from pydantic import BaseModel, Field
from typing import Dict

class NotificationChannelSchema(BaseModel):
    enabled: bool
    frequency: str = Field(..., pattern="^(instant|daily|weekly)$")

class NotificationSettingsSchema(BaseModel):
    email: NotificationChannelSchema
    push: NotificationChannelSchema
    sms: NotificationChannelSchema
    quiet_hours: Dict[str, str] = Field(default_factory=dict)

    @validator('quiet_hours')
    def validate_quiet_hours(cls, v):
        if v:
            required = {'start', 'end'}
            if not required.issubset(set(v.keys())):
                raise ValueError("quiet_hours needs start and end")

            # 시간 형식 검증 (HH:MM)
            import re
            time_pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'
            for key in required:
                if not re.match(time_pattern, v[key]):
                    raise ValueError(f"{key} must be in HH:MM format")

        return v

    class Config:
        extra = "forbid"

class UserNotificationSettings(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    settings = models.JSONField(default=dict)

    def clean(self):
        super().clean()
        try:
            NotificationSettingsSchema(**self.settings)
        except ValidationError as e:
            from django.core.exceptions import ValidationError as DjangoValidationError
            raise DjangoValidationError(f"Invalid settings: {e}")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# 사용
settings = UserNotificationSettings.objects.create(
    user=user,
    settings={
        "email": {
            "enabled": True,
            "frequency": "daily"
        },
        "push": {
            "enabled": True,
            "frequency": "instant"
        },
        "sms": {
            "enabled": False,
            "frequency": "weekly"
        },
        "quiet_hours": {
            "start": "22:00",
            "end": "08:00"
        }
    }
)
```

---

## 베스트 프랙티스

### 1. 항상 검증하라

#### ❌ 나쁜 예
```python
class Product(models.Model):
    attributes = models.JSONField(default=dict)

    # 검증 없음 - 런타임 에러 발생 가능
```

#### ✅ 좋은 예
```python
class Product(models.Model):
    attributes = models.JSONField(default=dict)

    def clean(self):
        super().clean()
        # 검증 로직 구현
        self.validate_attributes()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### 2. 명확한 에러 메시지

#### ❌ 나쁜 예
```python
if 'color' not in self.attributes:
    raise ValidationError("Invalid data")
```

#### ✅ 좋은 예
```python
if 'color' not in self.attributes:
    raise ValidationError(
        "Missing required field 'color' in attributes"
    )
```

### 3. 기본값 제공

#### ❌ 나쁜 예
```python
class Product(models.Model):
    attributes = models.JSONField()  # NULL이 될 수 있음
```

#### ✅ 좋은 예
```python
class Product(models.Model):
    attributes = models.JSONField(default=dict)  # 빈 dict 기본값
```

### 4. 스키마 문서화

#### ✅ 좋은 예
```python
class Product(models.Model):
    """
    상품 모델

    attributes 스키마:
    {
        "color": str,  # 필수, 색상 이름
        "weight": float,  # 필수, kg 단위
        "dimensions": {  # 선택, cm 단위
            "width": float,
            "height": float,
            "depth": float
        },
        "tags": List[str]  # 선택, 검색 태그
    }
    """
    attributes = models.JSONField(default=dict)
```

### 5. 마이그레이션 시 주의

```python
# 기존 데이터가 있을 때 검증 추가하기
class Product(models.Model):
    attributes = models.JSONField(default=dict)

    def clean(self):
        super().clean()

        # 기존 데이터는 검증 스킵 (pk가 있으면 기존 데이터)
        if self.pk:
            try:
                self.validate_attributes()
            except ValidationError:
                # 로깅하고 넘어가기
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Product {self.pk} has invalid attributes"
                )
                return
        else:
            # 새 데이터는 엄격하게 검증
            self.validate_attributes()
```

### 6. 버전 관리

```python
class ProductMetadataSchema(BaseModel):
    """메타데이터 스키마 v2"""
    version: int = Field(default=2, const=2)
    # ... 다른 필드들

    class Config:
        extra = "forbid"

class Product(models.Model):
    metadata = models.JSONField(default=lambda: {"version": 2})

    def clean(self):
        super().clean()

        version = self.metadata.get('version', 1)

        if version == 1:
            # 이전 버전 스키마로 검증
            self.validate_v1_metadata()
        elif version == 2:
            # 최신 버전 스키마로 검증
            ProductMetadataSchema(**self.metadata)
        else:
            raise ValidationError(f"Unknown metadata version: {version}")
```

### 7. Form에서도 검증하기

```python
from django import forms

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'attributes']

    def clean_attributes(self):
        """Form 레벨 검증"""
        attributes = self.cleaned_data['attributes']

        try:
            # Pydantic으로 검증
            ProductAttributesSchema(**attributes)
        except ValidationError as e:
            raise forms.ValidationError(f"Invalid attributes: {e}")

        return attributes
```

### 8. Admin에서 보기 좋게 표시

```python
from django.contrib import admin
import json

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'formatted_attributes']

    def formatted_attributes(self, obj):
        """JSON을 보기 좋게 표시"""
        return json.dumps(obj.attributes, indent=2, ensure_ascii=False)

    formatted_attributes.short_description = 'Attributes'
```

---

## 주의사항

### 1. 성능 고려

JSONField 쿼리는 일반 필드보다 느릴 수 있습니다.

```python
# ❌ 비효율적
products = Product.objects.filter(
    attributes__color='red'
)  # JSON 필드 쿼리는 인덱스를 사용하기 어려움

# ✅ 더 나은 방법: 자주 쿼리하는 필드는 별도 컬럼으로
class Product(models.Model):
    color = models.CharField(max_length=50, db_index=True)  # 인덱스
    attributes = models.JSONField(default=dict)  # 나머지 속성
```

### 2. 데이터베이스 호환성

모든 데이터베이스가 JSON 쿼리를 지원하는 것은 아닙니다.

```python
# PostgreSQL - 강력한 JSON 지원
Product.objects.filter(attributes__dimensions__width__gt=50)

# SQLite - 제한적 지원
# 복잡한 JSON 쿼리는 Python에서 처리
products = [
    p for p in Product.objects.all()
    if p.attributes.get('dimensions', {}).get('width', 0) > 50
]
```

### 3. 마이그레이션 전략

```python
# 1단계: 검증 추가하되 경고만 출력
# 2단계: 기존 데이터 정리
# 3단계: 엄격한 검증 적용

def migrate_existing_data():
    """기존 데이터를 새 스키마에 맞게 변환"""
    for product in Product.objects.all():
        try:
            # 새 스키마로 검증
            ProductAttributesSchema(**product.attributes)
        except ValidationError:
            # 기본값으로 수정
            product.attributes = {
                "color": product.attributes.get("color", "unknown"),
                "weight": float(product.attributes.get("weight", 0)),
            }
            product.save(update_fields=['attributes'])
```

---

## 참고 자료

- [Django JSONField 공식 문서](https://docs.djangoproject.com/en/stable/ref/models/fields/#jsonfield)
- [Pydantic 공식 문서](https://docs.pydantic.dev/)
- [Django Model Validation](https://docs.djangoproject.com/en/stable/ref/models/instances/#validating-objects)
- [PostgreSQL JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)
