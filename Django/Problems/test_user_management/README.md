# 프로덕션 환경 테스트 유저 관리 시스템

## 1. 문제 정의

### 1.1 배경
실제 사용자 데이터(홈택스, 금융 정보 등)를 연동하는 서비스에서는 테스트 시 다음과 같은 제약사항이 발생합니다:

- **단일 테스터의 한계**: 한 명의 테스터가 모든 비즈니스 시나리오를 테스트할 수 없음
  - 예: 환급액이 있는 경우 vs 없는 경우
  - 예: 홈택스 가입자 vs 미가입자

### 1.2 기존 접근 방식의 문제점

```python
# 문제가 있는 기존 코드
test_emails = ["test1@company.com", "test2@company.com"]

if user.email in test_emails:
    # 특정 플로우 강제 실행
    return mock_data
```

**한계점**:
- 코드 수정 없이 테스트 케이스 변경 불가
- 테스터와 시나리오 매핑 관리 어려움

## 2. 해결 방안: 데이터베이스 기반 동적 관리

### 2.1 아키텍처 설계

```
┌─────────────┐      M:N       ┌──────────────┐
│    User     │◄──────────────►│  TestCase    │
└─────────────┘                └──────────────┘
       ▲                              │
       │                              │
       └──────────────────────────────┘
              UserTestCaseAssignment
```

## 3. 핵심 구현 코드

### 3.1 모델 정의

```python
# models.py
from django.db import models

class TestCase(models.Model):
    """테스트 시나리오 정의"""
    # 핵심 테스트 케이스 2개만 정의
    NOT_HOMETAX_MEMBER = "NOT_HOMETAX_MEMBER"
    MONTHLY_RENT_REFUND = "MONTHLY_RENT_REFUND"

    CHOICES = [
        (NOT_HOMETAX_MEMBER, "홈택스 미가입자"),
        (MONTHLY_RENT_REFUND, "월세 환급 대상자"),
    ]

    name = models.CharField(max_length=100, unique=True, choices=CHOICES)
    test_data = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    # Many-to-Many with User
    users = models.ManyToManyField(
        'user.User',
        through='UserTestCaseAssignment',
        related_name='test_cases'
    )


class UserTestCaseAssignment(models.Model):
    """유저-테스트케이스 매핑"""
    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    test_case = models.ForeignKey('TestCase', on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'test_case']
```

### 3.2 핵심 유틸리티 함수

```python
# utils.py
from django.conf import settings

def is_test_user_for_scenario(user_id: int, scenario: str) -> bool:
    """
    특정 유저가 특정 테스트 시나리오에 할당되었는지 확인
    개발/스테이징 환경에서만 동작

    Args:
        user_id: 확인할 유저 ID
        scenario: 테스트 시나리오 이름 (예: "NOT_HOMETAX_MEMBER")

    Returns:
        bool: 테스트 유저 여부
    """
    # 프로덕션에서는 항상 False 반환
    if settings.IS_PRODUCTION:
        return False

    try:
        # DB 조회
        from .models import UserTestCaseAssignment
        return UserTestCaseAssignment.objects.filter(
            user_id=user_id,
            test_case__name=scenario,
            test_case__is_active=True
        ).exists()
    except Exception:
        # 테이블이 없거나 에러 발생 시 안전하게 False 반환
        return False
```

### 3.3 비즈니스 로직에서 활용

```python
# services/refund_service.py
from django.conf import settings
from apps.test_manager.utils import is_test_user_for_scenario

class RefundService:
    """환급 계산 서비스"""

    def calculate_monthly_rent_refund(self, user_id: int) -> dict:
        """월세 환급 계산"""

        # 테스트 시나리오 체크 (개발 환경에서만)
        if not settings.IS_PRODUCTION:
            if is_test_user_for_scenario(user_id, "MONTHLY_RENT_REFUND"):
                # 테스트 데이터 반환
                return {
                    'refund_amount': 1_500_000,
                    'status': 'approved',
                    'is_test': True
                }

        # 실제 계산 로직
        return self._calculate_actual_refund(user_id)

    def validate_hometax_member(self, user_id: int) -> dict:
        """홈택스 가입 확인"""
        # 프로덕션이 아닌 경우에만 테스트 유저 체크
        if not settings.IS_PRODUCTION:
            if is_test_user_for_scenario(user_id, "NOT_HOMETAX_MEMBER"):
                return {'error': 'NOT_REGISTERED'}

        # 실제 홈택스 API 호출
        return self._call_hometax_api(user_id)
```

## 4. 실제 사용 예시

### 4.1 외부 API 연동 시

```python
# services/external_api.py
from django.conf import settings
from apps.test_manager.utils import is_test_user_for_scenario

def check_hometax_registration(user_id: int):
    """홈택스 가입 여부 확인"""
    # 프로덕션이 아닌 경우에만 테스트 유저 체크
    if not settings.IS_PRODUCTION:
        if is_test_user_for_scenario(user_id, "NOT_HOMETAX_MEMBER"):
            return {"registered": False}

    # 실제 외부 API 호출
    response = external_api_call(user_id)
    return response


# 사용하는 곳
def process_tax_refund(user_id: int):
    # 테스트 유저는 자동으로 mock 데이터 받음
    result = check_hometax_registration(user_id)

    if not result['registered']:
        raise HomeTaxNotRegistered()

    # 이후 처리...
```

### 4.2 환급 계산 로직

```python
# services/calculation.py
from django.conf import settings
from apps.test_manager.utils import is_test_user_for_scenario

def calculate_refund(user_id: int):
    # 프로덕션이 아닌 경우에만 테스트 유저 체크
    if not settings.IS_PRODUCTION:
        # 테스트 유저용 특별 처리
        if is_test_user_for_scenario(user_id, "MONTHLY_RENT_REFUND"):
            # 항상 환급액이 있는 시나리오
            return {'amount': 1_500_000, 'is_test': True}

    # 실제 계산 로직
    income = get_user_income(user_id)
    if income > 70_000_000:
        return {'amount': 0, 'reason': '소득 초과'}

    return calculate_actual_refund(user_id)
```

## 5. 설정

```python
# settings.py
IS_PRODUCTION = env.bool('IS_PRODUCTION', default=False)

# 개발/스테이징: False
# 프로덕션: True
```

## 6. 장점

1. **유연성**: Admin에서 테스터 할당 변경 가능
2. **안전성**: 환경 변수로 프로덕션 보호
3. **확장성**: 새로운 테스트 케이스 쉽게 추가
4. **투명성**: 테스터-시나리오 매핑 명확

## 7. 단점

1. **초기 설정**: 모델 생성 필요
2. **관리 부담**: 지속적 관리 필요

## 8. 핵심 포인트

### 문제의 본질
- 실제 데이터를 사용하는 서비스에서 모든 시나리오를 테스트할 수 없는 한계

### 해결 방식
- 테스트 케이스를 코드가 아닌 데이터로 관리
- 데코레이터로 기존 코드 최소 수정
- 환경 변수로 프로덕션 안전성 확보

### 확장 가능성
- A/B 테스트로 확장 가능
- Feature Flag 시스템으로 발전 가능
