# Django Model Custom Validators

## 목차
1. [기본 개념](#기본-개념)
2. [Field-level Validators](#field-level-validators)
3. [Model-level Validators](#model-level-validators)
4. [재사용 가능한 Validator 함수](#재사용-가능한-validator-함수)
5. [내장 Validators 활용](#내장-validators-활용)
6. [실전 예제](#실전-예제)
7. [베스트 프랙티스](#베스트-프랙티스)

---

## 기본 개념

### Django Validation의 계층

Django는 여러 단계에서 데이터 검증을 수행합니다:

```
1. Field 타입 검증 (CharField, IntegerField 등)
     ↓
2. Field의 validators 실행
     ↓
3. Model의 clean_<fieldname>() 메서드 실행
     ↓
4. Model의 clean() 메서드 실행
     ↓
5. Model의 unique 제약조건 검증
     ↓
6. 저장
```

### Custom Validator란?

Custom validator는 Django의 기본 검증을 넘어서는 비즈니스 로직을 검증하는 함수입니다.

```python
from django.core.exceptions import ValidationError

def validate_even_number(value):
    """짝수만 허용하는 validator"""
    if value % 2 != 0:
        raise ValidationError(
            f'{value} is not an even number.',
            params={'value': value},
        )
```

---

## Field-level Validators

### 기본 사용법

Field-level validator는 특정 필드에만 적용되는 검증 함수입니다.

```python
from django.db import models
from django.core.exceptions import ValidationError

# 1. Validator 함수 정의
def validate_positive(value):
    """양수만 허용"""
    if value <= 0:
        raise ValidationError(
            '%(value)s must be positive',
            params={'value': value},
        )

def validate_phone_number(value):
    """한국 전화번호 형식 검증"""
    import re
    pattern = r'^01[0-9]-\d{3,4}-\d{4}$'
    if not re.match(pattern, value):
        raise ValidationError(
            '%(value)s is not a valid Korean phone number. '
            'Use format: 010-1234-5678',
            params={'value': value},
        )

# 2. Model에 적용
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[validate_positive]  # validator 추가
    )
    quantity = models.IntegerField(
        validators=[validate_positive]
    )

class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(
        max_length=13,
        validators=[validate_phone_number]
    )
```

### 파라미터가 있는 Validator

```python
from django.core.exceptions import ValidationError

def validate_min_length(min_length):
    """최소 길이를 검증하는 validator 생성기"""
    def validator(value):
        if len(value) < min_length:
            raise ValidationError(
                f'Must be at least {min_length} characters long. '
                f'Current length: {len(value)}'
            )
    return validator

def validate_file_size(max_size_mb):
    """파일 크기를 검증하는 validator 생성기"""
    def validator(file):
        if file.size > max_size_mb * 1024 * 1024:
            raise ValidationError(
                f'File size must not exceed {max_size_mb}MB. '
                f'Current size: {file.size / (1024*1024):.2f}MB'
            )
    return validator

class Document(models.Model):
    title = models.CharField(
        max_length=200,
        validators=[validate_min_length(5)]  # 최소 5자
    )
    file = models.FileField(
        upload_to='documents/',
        validators=[validate_file_size(10)]  # 최대 10MB
    )
```

### 클래스 기반 Validator

```python
from django.core.exceptions import ValidationError

class RangeValidator:
    """값의 범위를 검증하는 validator"""

    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, value):
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                f'Value must be at least {self.min_value}. '
                f'Got: {value}'
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                f'Value must be at most {self.max_value}. '
                f'Got: {value}'
            )

    def __eq__(self, other):
        """마이그레이션을 위해 필요"""
        return (
            isinstance(other, RangeValidator) and
            self.min_value == other.min_value and
            self.max_value == other.max_value
        )

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[RangeValidator(min_value=0, max_value=1000000)]
    )
    discount_rate = models.IntegerField(
        validators=[RangeValidator(min_value=0, max_value=100)]
    )
```

### 여러 Validators 조합

```python
from django.core.validators import MinLengthValidator, MaxLengthValidator
import re

def validate_alphanumeric(value):
    """영문자와 숫자만 허용"""
    if not re.match(r'^[a-zA-Z0-9]+$', value):
        raise ValidationError(
            'Only alphanumeric characters are allowed'
        )

def validate_no_spaces(value):
    """공백 불허"""
    if ' ' in value:
        raise ValidationError('Spaces are not allowed')

class User(models.Model):
    username = models.CharField(
        max_length=30,
        validators=[
            MinLengthValidator(3),  # 최소 3자
            MaxLengthValidator(30),  # 최대 30자
            validate_alphanumeric,  # 영문자+숫자만
            validate_no_spaces,  # 공백 불허
        ]
    )
```

---

## Model-level Validators

Model-level validator는 여러 필드를 함께 검증하거나 복잡한 비즈니스 로직을 검증할 때 사용합니다.

### clean() 메서드

```python
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class Event(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_participants = models.IntegerField()
    current_participants = models.IntegerField(default=0)

    def clean(self):
        """Model-level validation"""
        super().clean()

        # 1. 날짜 검증
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError({
                    'end_date': 'End date must be after start date'
                })

            # 과거 날짜 불허
            if self.start_date < timezone.now():
                raise ValidationError({
                    'start_date': 'Cannot create events in the past'
                })

        # 2. 참가자 수 검증
        if self.current_participants > self.max_participants:
            raise ValidationError(
                'Current participants cannot exceed maximum'
            )

        # 3. 비즈니스 로직 검증
        if self.max_participants > 1000:
            # 대규모 이벤트는 특별 승인 필요
            if not hasattr(self, 'is_approved') or not self.is_approved:
                raise ValidationError(
                    'Events with more than 1000 participants require approval'
                )

    def save(self, *args, **kwargs):
        # clean() 메서드 자동 실행
        self.full_clean()
        super().save(*args, **kwargs)
```

### clean_<fieldname>() 메서드

특정 필드에 대한 복잡한 검증 로직을 분리할 수 있습니다.

```python
class Order(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    def clean_quantity(self):
        """수량 검증"""
        quantity = self.quantity

        if quantity <= 0:
            raise ValidationError('Quantity must be positive')

        # 재고 확인
        if self.product_id:
            product = Product.objects.get(pk=self.product_id)
            if quantity > product.stock:
                raise ValidationError(
                    f'Only {product.stock} items available in stock'
                )

        return quantity

    def clean_discount(self):
        """할인 검증"""
        discount = self.discount

        if discount < 0:
            raise ValidationError('Discount cannot be negative')

        if discount > 100:
            raise ValidationError('Discount cannot exceed 100%')

        # 가격 대비 할인율 확인
        if self.price:
            max_discount_amount = self.price * self.quantity * 0.5
            discount_amount = self.price * self.quantity * (discount / 100)

            if discount_amount > max_discount_amount:
                raise ValidationError(
                    'Discount cannot exceed 50% of total price'
                )

        return discount

    def clean(self):
        """전체 검증"""
        super().clean()

        # clean_<fieldname>() 메서드들이 먼저 실행된 후
        # clean()이 실행됨

        # 최종 가격 검증
        if self.price and self.quantity:
            total = self.price * self.quantity
            discount_amount = total * (self.discount / 100)
            final_price = total - discount_amount

            if final_price < 0:
                raise ValidationError('Final price cannot be negative')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### 조건부 검증

```python
class Article(models.Model):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
        (ARCHIVED, 'Archived'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    def clean(self):
        super().clean()

        # 상태에 따른 조건부 검증
        if self.status == self.PUBLISHED:
            # 발행 상태일 때는 필수 검증
            if not self.title or len(self.title.strip()) == 0:
                raise ValidationError({
                    'title': 'Published articles must have a title'
                })

            if not self.content or len(self.content.strip()) < 100:
                raise ValidationError({
                    'content': 'Published articles must have at least 100 characters'
                })

            if not self.published_at:
                # 발행 시간 자동 설정
                self.published_at = timezone.now()

        elif self.status == self.ARCHIVED:
            # 아카이브는 발행된 글만 가능
            if not self.published_at:
                raise ValidationError(
                    'Only published articles can be archived'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

---

## 재사용 가능한 Validator 함수

### validators.py 모듈 만들기

```python
# myapp/validators.py

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re

def validate_korean_name(value):
    """한글 이름 검증"""
    if not re.match(r'^[가-힣]+$', value):
        raise ValidationError(
            _('%(value)s is not a valid Korean name'),
            params={'value': value},
        )

def validate_business_registration_number(value):
    """사업자등록번호 검증 (형식 + 체크섬)"""
    # 하이픈 제거
    number = value.replace('-', '')

    # 길이 확인
    if len(number) != 10:
        raise ValidationError(
            'Business registration number must be 10 digits'
        )

    # 숫자 확인
    if not number.isdigit():
        raise ValidationError(
            'Business registration number must contain only digits'
        )

    # 체크섬 검증
    check_sum = 0
    multipliers = [1, 3, 7, 1, 3, 7, 1, 3, 5]

    for i in range(9):
        check_sum += int(number[i]) * multipliers[i]

    check_sum += int(number[8]) * 5 // 10
    check_digit = (10 - (check_sum % 10)) % 10

    if int(number[9]) != check_digit:
        raise ValidationError(
            'Invalid business registration number checksum'
        )

def validate_future_date(value):
    """미래 날짜만 허용"""
    from django.utils import timezone

    if value <= timezone.now().date():
        raise ValidationError(
            'Date must be in the future'
        )

def validate_past_date(value):
    """과거 날짜만 허용"""
    from django.utils import timezone

    if value >= timezone.now().date():
        raise ValidationError(
            'Date must be in the past'
        )

def validate_image_dimensions(min_width=None, min_height=None, max_width=None, max_height=None):
    """이미지 크기 검증"""
    def validator(image):
        from PIL import Image

        img = Image.open(image)
        width, height = img.size

        if min_width and width < min_width:
            raise ValidationError(
                f'Image width must be at least {min_width}px. Current: {width}px'
            )

        if min_height and height < min_height:
            raise ValidationError(
                f'Image height must be at least {min_height}px. Current: {height}px'
            )

        if max_width and width > max_width:
            raise ValidationError(
                f'Image width must not exceed {max_width}px. Current: {width}px'
            )

        if max_height and height > max_height:
            raise ValidationError(
                f'Image height must not exceed {max_height}px. Current: {height}px'
            )

    return validator

def validate_file_extension(allowed_extensions):
    """파일 확장자 검증"""
    def validator(file):
        import os
        ext = os.path.splitext(file.name)[1].lower()

        if ext not in allowed_extensions:
            raise ValidationError(
                f'File extension "{ext}" is not allowed. '
                f'Allowed extensions: {", ".join(allowed_extensions)}'
            )

    return validator
```

### 사용 예제

```python
# myapp/models.py

from django.db import models
from .validators import (
    validate_korean_name,
    validate_business_registration_number,
    validate_future_date,
    validate_image_dimensions,
    validate_file_extension,
)

class Company(models.Model):
    name = models.CharField(max_length=100)
    business_number = models.CharField(
        max_length=12,
        validators=[validate_business_registration_number]
    )
    ceo_name = models.CharField(
        max_length=50,
        validators=[validate_korean_name]
    )
    logo = models.ImageField(
        upload_to='logos/',
        validators=[
            validate_image_dimensions(
                min_width=200,
                min_height=200,
                max_width=2000,
                max_height=2000
            )
        ]
    )

class Contract(models.Model):
    title = models.CharField(max_length=200)
    contract_date = models.DateField()
    expiry_date = models.DateField(
        validators=[validate_future_date]
    )
    document = models.FileField(
        upload_to='contracts/',
        validators=[
            validate_file_extension(['.pdf', '.docx', '.hwp'])
        ]
    )

    def clean(self):
        super().clean()

        if self.contract_date and self.expiry_date:
            if self.expiry_date <= self.contract_date:
                raise ValidationError({
                    'expiry_date': 'Expiry date must be after contract date'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

---

## 내장 Validators 활용

Django는 많은 유용한 내장 validators를 제공합니다.

### 자주 사용하는 내장 Validators

```python
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
    MaxLengthValidator,
    RegexValidator,
    EmailValidator,
    URLValidator,
    FileExtensionValidator,
    DecimalValidator,
    validate_email,
    validate_slug,
    validate_ipv4_address,
    validate_ipv6_address,
)

class Product(models.Model):
    # 숫자 범위 검증
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0.01),  # 최소값
            MaxValueValidator(999999.99),  # 최대값
        ]
    )

    # 문자열 길이 검증
    description = models.TextField(
        validators=[
            MinLengthValidator(10),
            MaxLengthValidator(1000),
        ]
    )

    # 정규식 검증
    sku = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{3}-\d{6}$',
                message='SKU must be in format: ABC-123456',
                code='invalid_sku'
            )
        ]
    )

    # 이메일 검증
    contact_email = models.CharField(
        max_length=254,
        validators=[EmailValidator(message='Invalid email address')]
    )

    # URL 검증
    website = models.CharField(
        max_length=200,
        validators=[URLValidator(schemes=['http', 'https'])]
    )

    # 파일 확장자 검증
    image = models.FileField(
        upload_to='products/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif']
            )
        ]
    )

    # Slug 검증
    slug = models.CharField(
        max_length=100,
        validators=[validate_slug]
    )
```

### RegexValidator 활용 예제

```python
from django.core.validators import RegexValidator

# 한국 우편번호 (5자리)
postal_code_validator = RegexValidator(
    regex=r'^\d{5}$',
    message='Enter a valid 5-digit postal code',
    code='invalid_postal_code'
)

# 한국 휴대폰 번호
phone_validator = RegexValidator(
    regex=r'^01[016789]-\d{3,4}-\d{4}$',
    message='Enter a valid Korean phone number (e.g., 010-1234-5678)',
    code='invalid_phone'
)

# 영문자와 숫자만 허용 (username)
username_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9_]+$',
    message='Username can only contain letters, numbers, and underscores',
    code='invalid_username'
)

# 신용카드 번호 (기본 형식)
credit_card_validator = RegexValidator(
    regex=r'^\d{4}-\d{4}-\d{4}-\d{4}$',
    message='Enter a valid credit card number (XXXX-XXXX-XXXX-XXXX)',
    code='invalid_credit_card'
)

class Customer(models.Model):
    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[username_validator]
    )
    phone = models.CharField(
        max_length=13,
        validators=[phone_validator]
    )
    postal_code = models.CharField(
        max_length=5,
        validators=[postal_code_validator]
    )
```

---

## 실전 예제

### 예제 1: 회원가입 폼 검증

```python
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
import re

class User(models.Model):
    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[
            MinLengthValidator(3),
            RegexValidator(
                regex=r'^[a-zA-Z0-9_]+$',
                message='Username can only contain letters, numbers, and underscores'
            )
        ]
    )
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    age = models.IntegerField()
    phone = models.CharField(max_length=13)

    def clean_password(self):
        """비밀번호 강도 검증"""
        password = self.password

        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long')

        # 대문자, 소문자, 숫자, 특수문자 각각 1개 이상
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')

        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')

        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one digit')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character')

        # 연속된 문자 금지
        for i in range(len(password) - 2):
            if ord(password[i]) + 1 == ord(password[i+1]) == ord(password[i+2]) - 1:
                raise ValidationError('Password cannot contain sequential characters')

        return password

    def clean_age(self):
        """나이 검증"""
        age = self.age

        if age < 14:
            raise ValidationError('Must be at least 14 years old to register')

        if age > 120:
            raise ValidationError('Invalid age')

        return age

    def clean(self):
        super().clean()

        # 이메일 도메인 화이트리스트
        allowed_domains = ['gmail.com', 'naver.com', 'kakao.com', 'company.com']
        email_domain = self.email.split('@')[-1]

        if email_domain not in allowed_domains:
            raise ValidationError({
                'email': f'Only emails from {", ".join(allowed_domains)} are allowed'
            })

    def save(self, *args, **kwargs):
        # 비밀번호 해싱
        if not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)

        self.full_clean()
        super().save(*args, **kwargs)
```

### 예제 2: 예약 시스템

```python
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

class Room(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    is_active = models.BooleanField(default=True)

class Reservation(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    participant_count = models.IntegerField()
    purpose = models.TextField()

    class Meta:
        ordering = ['start_time']

    def clean(self):
        super().clean()

        # 1. 시간 검증
        if self.start_time and self.end_time:
            # 종료 시간이 시작 시간보다 늦어야 함
            if self.end_time <= self.start_time:
                raise ValidationError({
                    'end_time': 'End time must be after start time'
                })

            # 최소 30분 이상 예약
            min_duration = timedelta(minutes=30)
            if self.end_time - self.start_time < min_duration:
                raise ValidationError(
                    'Reservation must be at least 30 minutes'
                )

            # 최대 4시간까지만 예약
            max_duration = timedelta(hours=4)
            if self.end_time - self.start_time > max_duration:
                raise ValidationError(
                    'Reservation cannot exceed 4 hours'
                )

            # 과거 시간 예약 불가
            if self.start_time < timezone.now():
                raise ValidationError({
                    'start_time': 'Cannot make reservation in the past'
                })

            # 영업 시간 확인 (9:00 - 22:00)
            if self.start_time.hour < 9 or self.end_time.hour > 22:
                raise ValidationError(
                    'Reservations are only available between 9:00 and 22:00'
                )

        # 2. 방 검증
        if self.room and not self.room.is_active:
            raise ValidationError({
                'room': 'This room is not available for reservation'
            })

        # 3. 인원 검증
        if self.room and self.participant_count:
            if self.participant_count > self.room.capacity:
                raise ValidationError({
                    'participant_count': f'Room capacity is {self.room.capacity} people'
                })

            if self.participant_count < 1:
                raise ValidationError({
                    'participant_count': 'Must have at least one participant'
                })

        # 4. 중복 예약 확인
        if self.room and self.start_time and self.end_time:
            overlapping = Reservation.objects.filter(
                room=self.room,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )

            # 수정 시 자기 자신은 제외
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)

            if overlapping.exists():
                raise ValidationError(
                    'This room is already reserved for the selected time period'
                )

        # 5. 사용자별 예약 제한 (하루 최대 2건)
        if self.user and self.start_time:
            user_reservations_today = Reservation.objects.filter(
                user=self.user,
                start_time__date=self.start_time.date()
            )

            if self.pk:
                user_reservations_today = user_reservations_today.exclude(pk=self.pk)

            if user_reservations_today.count() >= 2:
                raise ValidationError(
                    'Maximum 2 reservations per day allowed'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### 예제 3: 쇼핑몰 상품 및 주문

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    stock = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField(default=True)
    max_order_quantity = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)]
    )

class Order(models.Model):
    PENDING = 'pending'
    PAID = 'paid'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
        (SHIPPED, 'Shipped'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        super().clean()

        if not self.product:
            return

        # 1. 상품 활성화 상태 확인
        if not self.product.is_active:
            raise ValidationError({
                'product': 'This product is not available for purchase'
            })

        # 2. 재고 확인
        if self.quantity > self.product.stock:
            raise ValidationError({
                'quantity': f'Only {self.product.stock} items available in stock'
            })

        # 3. 최대 주문 수량 확인
        if self.quantity > self.product.max_order_quantity:
            raise ValidationError({
                'quantity': f'Maximum {self.product.max_order_quantity} items per order'
            })

        # 4. 주문 상태 확인
        if self.order and self.order.status != Order.PENDING:
            raise ValidationError(
                'Cannot modify items in a non-pending order'
            )

        # 5. 가격 확인 (가격 변조 방지)
        if self.price != self.product.price:
            raise ValidationError({
                'price': 'Price mismatch with product price'
            })

    def save(self, *args, **kwargs):
        # 가격 자동 설정
        if self.product and not self.price:
            self.price = self.product.price

        self.full_clean()
        super().save(*args, **kwargs)

        # 재고 감소
        if not kwargs.get('update_fields'):
            self.product.stock -= self.quantity
            self.product.save(update_fields=['stock'])
```

---

## 베스트 프랙티스

### 1. 명확하고 구체적인 에러 메시지

#### ❌ 나쁜 예
```python
def validate_price(value):
    if value <= 0:
        raise ValidationError('Invalid price')
```

#### ✅ 좋은 예
```python
def validate_price(value):
    if value <= 0:
        raise ValidationError(
            f'Price must be positive. Got: {value}'
        )
```

### 2. params 사용으로 국제화 지원

#### ❌ 나쁜 예
```python
def validate_min_age(value):
    if value < 18:
        raise ValidationError(f'Must be at least 18 years old')
```

#### ✅ 좋은 예
```python
from django.utils.translation import gettext_lazy as _

def validate_min_age(value):
    if value < 18:
        raise ValidationError(
            _('Must be at least %(min_age)s years old'),
            params={'min_age': 18},
            code='min_age'
        )
```

### 3. 필드별 에러 구분

#### ❌ 나쁜 예
```python
def clean(self):
    if self.start_date > self.end_date:
        raise ValidationError('Invalid dates')
```

#### ✅ 좋은 예
```python
def clean(self):
    if self.start_date > self.end_date:
        raise ValidationError({
            'end_date': 'End date must be after start date'
        })
```

### 4. 재사용 가능한 Validator 작성

#### ❌ 나쁜 예
```python
class Product(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        if self.price <= 0:
            raise ValidationError('Price must be positive')

class Service(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        if self.price <= 0:
            raise ValidationError('Price must be positive')
```

#### ✅ 좋은 예
```python
# validators.py
def validate_positive_price(value):
    if value <= 0:
        raise ValidationError('Price must be positive')

# models.py
class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[validate_positive_price]
    )

class Service(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[validate_positive_price]
    )
```

### 5. save() 메서드에서 full_clean() 호출

#### ❌ 나쁜 예
```python
class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[validate_positive_price]
    )

    def clean(self):
        # 검증 로직
        pass

    # full_clean()을 호출하지 않으면 검증이 실행되지 않음
```

#### ✅ 좋은 예
```python
class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[validate_positive_price]
    )

    def clean(self):
        super().clean()
        # 검증 로직

    def save(self, *args, **kwargs):
        # 검증 자동 실행
        self.full_clean()
        super().save(*args, **kwargs)
```

### 6. 클래스 기반 Validator에 __eq__ 구현

#### ❌ 나쁜 예
```python
class RangeValidator:
    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, value):
        # 검증 로직
        pass

    # __eq__가 없으면 마이그레이션 시 문제 발생
```

#### ✅ 좋은 예
```python
class RangeValidator:
    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, value):
        # 검증 로직
        pass

    def __eq__(self, other):
        """마이그레이션을 위해 필요"""
        return (
            isinstance(other, RangeValidator) and
            self.min_value == other.min_value and
            self.max_value == other.max_value
        )
```

### 7. Form과 Model 검증 분리

```python
# forms.py
from django import forms

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock']

    def clean_price(self):
        """Form에서만 필요한 검증"""
        price = self.cleaned_data['price']

        # 사용자 입력에 대한 추가 검증
        if price > 1000000:
            # 경고만 표시하고 통과
            self.add_warning('price', 'This is a very high price')

        return price

# models.py
class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    def clean(self):
        """Model의 핵심 비즈니스 로직 검증"""
        super().clean()

        if self.price <= 0:
            raise ValidationError('Price must be positive')
```

### 8. 성능 최적화

#### ❌ 나쁜 예
```python
def clean(self):
    # 매번 데이터베이스 쿼리
    for item in OrderItem.objects.filter(order=self.order):
        # 검증 로직
        pass
```

#### ✅ 좋은 예
```python
def clean(self):
    # select_related, prefetch_related 사용
    items = OrderItem.objects.filter(
        order=self.order
    ).select_related('product')

    # 한 번의 쿼리로 처리
    for item in items:
        # 검증 로직
        pass
```

### 9. 테스트 작성

```python
# tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Product

class ProductValidationTestCase(TestCase):
    def test_positive_price_validation(self):
        """가격은 양수여야 함"""
        product = Product(name='Test', price=-10, stock=10)

        with self.assertRaises(ValidationError) as cm:
            product.full_clean()

        self.assertIn('price', cm.exception.message_dict)

    def test_stock_validation(self):
        """재고는 0 이상이어야 함"""
        product = Product(name='Test', price=100, stock=-5)

        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_valid_product(self):
        """정상적인 상품 생성"""
        product = Product(name='Test', price=100, stock=10)

        try:
            product.full_clean()
            product.save()
        except ValidationError:
            self.fail('Valid product raised ValidationError')

        self.assertEqual(Product.objects.count(), 1)
```

---

## 주의사항

### 1. full_clean()은 자동으로 호출되지 않음

```python
# ❌ 검증이 실행되지 않음
product = Product(name='Test', price=-10)
product.save()  # 저장됨!

# ✅ 검증 실행
product = Product(name='Test', price=-10)
product.full_clean()  # ValidationError 발생
product.save()
```

**해결책: save() 메서드 오버라이드**

```python
def save(self, *args, **kwargs):
    self.full_clean()
    super().save(*args, **kwargs)
```

### 2. bulk_create, update 등은 검증을 건너뜀

```python
# ❌ 검증이 실행되지 않음
Product.objects.bulk_create([
    Product(name='A', price=-10),
    Product(name='B', price=-20),
])

# ✅ 수동 검증 필요
products = [
    Product(name='A', price=10),
    Product(name='B', price=20),
]

for product in products:
    product.full_clean()  # 검증

Product.objects.bulk_create(products)
```

### 3. QuerySet의 update()는 검증을 건너뜀

```python
# ❌ 검증이 실행되지 않음
Product.objects.filter(id=1).update(price=-10)

# ✅ 개별 객체로 업데이트
product = Product.objects.get(id=1)
product.price = 10
product.save()  # full_clean() 호출
```

### 4. Form 검증과 Model 검증은 다름

```python
# Form은 자동으로 full_clean() 호출
form = ProductForm(data={'name': 'Test', 'price': '-10'})
if form.is_valid():  # False - 검증 실행
    form.save()

# Model은 수동으로 호출해야 함
product = Product(name='Test', price=-10)
product.save()  # 검증 없이 저장됨!
```

---

## 참고 자료

- [Django Model Validation 공식 문서](https://docs.djangoproject.com/en/stable/ref/models/instances/#validating-objects)
- [Django Validators 공식 문서](https://docs.djangoproject.com/en/stable/ref/validators/)
- [Django Form Validation](https://docs.djangoproject.com/en/stable/ref/forms/validation/)
- [Writing Custom Validators](https://docs.djangoproject.com/en/stable/ref/validators/#writing-validators)
