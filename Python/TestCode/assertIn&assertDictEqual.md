# Python Testing 완벽 가이드: assertIn & assertDictEqual

Django/DRF 프로젝트에서 테스트 코드 작성 시 자주 사용하는 `assertIn`과 `assertDictEqual` 메서드의 사용법을 상세히 설명합니다.

## 목차
- [assertIn 메서드](#1-assertin-메서드)
- [assertDictEqual 메서드](#2-assertdictequal-메서드)
- [두 메서드 함께 사용하기](#3-두-메서드-함께-사용하기)
- [비교표](#4-비교표-언제-무엇을-사용할까)
- [주요 차이점](#5-주요-차이점)
- [베스트 프랙티스](#6-베스트-프랙티스)

---

## 1. assertIn 메서드

### 기본 사용법

```python
self.assertIn(member, container, msg=None)
```

**매개변수:**
- `member`: 찾으려는 항목
- `container`: 검색할 컨테이너 (리스트, 세트, 딕셔너리, 문자열 등)
- `msg` (선택): 실패 시 표시할 커스텀 메시지

### 일반적인 사용 예시

```python
from django.test import TestCase

class BasicAssertInTests(TestCase):
    def test_string_in_list(self):
        """리스트에 문자열이 있는지 확인"""
        self.assertIn('apple', ['apple', 'banana', 'orange'])

    def test_key_in_dictionary(self):
        """딕셔너리에 키가 있는지 확인"""
        data = {'name': 'John', 'age': 30}
        self.assertIn('name', data)

    def test_substring_in_string(self):
        """문자열에 부분 문자열이 있는지 확인"""
        self.assertIn('world', 'hello world')

    def test_value_in_set(self):
        """세트에 값이 있는지 확인"""
        self.assertIn(1, {1, 2, 3, 4, 5})
```

### Django API 테스트 패턴

```python
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

class UserAPITestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            phone_number="01012345678"
        )

    def test_response_contains_required_fields(self):
        """API 응답에 필수 필드가 포함되어 있는지 확인"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/users/me/')
        data = response.json()

        # 각 필드가 응답에 포함되어 있는지 확인
        self.assertIn('id', data)
        self.assertIn('username', data)
        self.assertIn('email', data)

    def test_multiple_fields_with_loop(self):
        """여러 필드를 반복문으로 확인"""
        response = self.client.get('/api/v1/profile/')
        data = response.json()

        required_fields = ['username', 'email', 'phone_number', 'created_at']
        for field in required_fields:
            self.assertIn(
                field,
                data,
                msg=f"응답에 '{field}' 필드가 없습니다"
            )

    def test_user_in_queryset(self):
        """특정 객체가 QuerySet에 포함되어 있는지 확인"""
        User = get_user_model()
        all_users = User.objects.all()
        self.assertIn(self.user, all_users)
```

### 고급 사용 예시

```python
class AdvancedAssertInTests(TestCase):
    def test_with_custom_error_message(self):
        """커스텀 에러 메시지 사용"""
        allowed_statuses = ['pending', 'approved', 'rejected']
        current_status = 'completed'

        self.assertIn(
            current_status,
            allowed_statuses,
            msg=f"상태 '{current_status}'는 허용되지 않습니다. "
                f"허용된 상태: {allowed_statuses}"
        )

    def test_nested_data_structure(self):
        """중첩된 데이터 구조에서 값 확인"""
        response_data = {
            'data': {
                'users': [
                    {'id': 1, 'name': 'John'},
                    {'id': 2, 'name': 'Jane'}
                ]
            }
        }

        # 중첩된 리스트에서 특정 ID가 있는지 확인
        user_ids = [user['id'] for user in response_data['data']['users']]
        self.assertIn(1, user_ids)

    def test_performance_with_large_collection(self):
        """큰 컬렉션에서 성능을 고려한 테스트"""
        large_list = list(range(10000))
        # set으로 변환하여 검색 성능 향상
        self.assertIn(5000, set(large_list))
```

---

## 2. assertDictEqual 메서드

### 기본 사용법

```python
self.assertDictEqual(first, second, msg=None)
```

**매개변수:**
- `first`: 비교할 첫 번째 딕셔너리
- `second`: 비교할 두 번째 딕셔너리
- `msg` (선택): 실패 시 표시할 커스텀 메시지

### 일반적인 사용 예시

```python
from django.test import TestCase

class BasicAssertDictEqualTests(TestCase):
    def test_identical_dictionaries(self):
        """동일한 두 딕셔너리 비교"""
        dict1 = {'name': 'John', 'age': 30}
        dict2 = {'name': 'John', 'age': 30}
        self.assertDictEqual(dict1, dict2)

    def test_order_doesnt_matter(self):
        """키 순서가 달라도 내용이 같으면 같다고 판단"""
        dict1 = {'a': 1, 'b': 2, 'c': 3}
        dict2 = {'c': 3, 'a': 1, 'b': 2}
        self.assertDictEqual(dict1, dict2)

    def test_nested_dictionaries(self):
        """중첩된 딕셔너리 구조 비교"""
        dict1 = {
            'user': {'name': 'John', 'age': 30},
            'address': {'city': 'Seoul', 'zip': '12345'}
        }
        dict2 = {
            'user': {'name': 'John', 'age': 30},
            'address': {'city': 'Seoul', 'zip': '12345'}
        }
        self.assertDictEqual(dict1, dict2)
```

### Django Serializer 테스트 패턴

```python
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

class SerializerTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            phone_number="01012345678"
        )

    def test_user_serialization_format(self):
        """Serializer가 올바른 형식으로 데이터를 반환하는지 확인"""
        from apps.user.serializers import UserSerializer

        serializer = UserSerializer(self.user)

        expected_data = {
            'id': self.user.id,
            'username': 'testuser',
            'email': 'test@example.com',
            'phone_number': '01012345678',
            'is_active': True,
        }

        self.assertDictEqual(serializer.data, expected_data)

    def test_api_response_structure(self):
        """API 응답 구조가 예상과 일치하는지 확인"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/users/me/')

        expected_response = {
            'success': True,
            'message': '',
            'data': {
                'id': self.user.id,
                'username': 'testuser',
                'email': 'test@example.com'
            }
        }

        self.assertDictEqual(response.json(), expected_response)
```

### 고급 사용 예시

```python
class AdvancedAssertDictEqualTests(TestCase):
    def test_partial_dict_comparison(self):
        """큰 딕셔너리에서 일부분만 비교"""
        full_response = {
            'id': 1,
            'name': 'John',
            'email': 'john@example.com',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-02T00:00:00Z',
            'extra_field': 'extra_value'
        }

        # 관심 있는 필드만 추출
        relevant_fields = ['id', 'name', 'email']
        actual_data = {k: full_response[k] for k in relevant_fields}

        expected_data = {
            'id': 1,
            'name': 'John',
            'email': 'john@example.com'
        }

        self.assertDictEqual(actual_data, expected_data)

    def test_complex_nested_structure(self):
        """복잡한 중첩 구조 비교"""
        actual_response = {
            'success': True,
            'data': {
                'refunds': [
                    {
                        'year': 2024,
                        'amount': 1000000,
                        'status': 'approved',
                        'details': {
                            'tax_type': '종합소득세',
                            'deductions': [100000, 200000]
                        }
                    }
                ],
                'total_count': 1
            }
        }

        expected_response = {
            'success': True,
            'data': {
                'refunds': [
                    {
                        'year': 2024,
                        'amount': 1000000,
                        'status': 'approved',
                        'details': {
                            'tax_type': '종합소득세',
                            'deductions': [100000, 200000]
                        }
                    }
                ],
                'total_count': 1
            }
        }

        self.assertDictEqual(actual_response, expected_response)
```

### Manager 테스트 패턴

```python
from apps.refund.models import WorkerRefundGroup

class ManagerTestCase(TestCase):
    def test_manager_returns_correct_structure(self):
        """Manager 메서드가 올바른 딕셔너리 구조를 반환하는지 확인"""
        # 테스트 데이터 생성
        User = get_user_model()
        user = User.objects.create_user(username='testuser')
        WorkerRefundGroup.objects.create(
            user=user,
            year=2024,
            total_amount=1000000,
            status='approved'
        )

        # Manager 메서드 호출
        summary = WorkerRefundGroup.objects.get_user_summary(user=user)

        expected_summary = {
            'user_id': user.id,
            'year': 2024,
            'total_refunds': 1,
            'total_amount': 1000000,
            'status': 'approved'
        }

        self.assertDictEqual(summary, expected_summary)
```

---

## 3. 두 메서드 함께 사용하기

```python
class CombinedUsageTests(APITestCase):
    def test_api_response_comprehensive_check(self):
        """assertIn과 assertDictEqual을 함께 사용"""
        response = self.client.get('/api/v1/dashboard/')
        data = response.json()

        # 1단계: 최상위 키 존재 확인 (assertIn)
        self.assertIn('success', data)
        self.assertIn('data', data)
        self.assertIn('message', data)

        # 2단계: data 안의 중첩 키 확인 (assertIn)
        self.assertIn('user', data['data'])
        self.assertIn('stats', data['data'])

        # 3단계: 특정 객체의 정확한 구조 확인 (assertDictEqual)
        expected_user = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com'
        }
        self.assertDictEqual(data['data']['user'], expected_user)

        # 4단계: 통계 객체의 구조 확인 (assertDictEqual)
        expected_stats = {
            'total_refunds': 5,
            'approved_count': 3,
            'pending_count': 2
        }
        self.assertDictEqual(data['data']['stats'], expected_stats)

    def test_refund_list_response(self):
        """환급 목록 API 응답 종합 검증"""
        response = self.client.get('/api/v1/refunds/')
        data = response.json()

        # 기본 응답 구조 확인
        required_keys = ['success', 'message', 'data']
        for key in required_keys:
            self.assertIn(key, data)

        # 성공 응답인지 확인
        self.assertTrue(data['success'])

        # data 내부에 results가 있는지 확인
        self.assertIn('results', data['data'])

        # 첫 번째 환급 항목의 구조 확인
        if len(data['data']['results']) > 0:
            first_refund = data['data']['results'][0]
            expected_keys = {'id', 'year', 'amount', 'status', 'created_at'}

            # 모든 필수 키가 있는지 확인
            for key in expected_keys:
                self.assertIn(key, first_refund)
```

---

## 4. 비교표: 언제 무엇을 사용할까?

| 상황 | 사용할 메서드 | 예시 |
|------|--------------|------|
| 리스트/세트에 값이 있는지 확인 | `assertIn` | `self.assertIn('admin', user_roles)` |
| 딕셔너리에 키가 있는지 확인 | `assertIn` | `self.assertIn('token', response.json())` |
| 두 딕셔너리가 완전히 같은지 확인 | `assertDictEqual` | `self.assertDictEqual(serializer.data, expected)` |
| 여러 필드가 존재하는지 확인 | `assertIn` + 반복문 | `for f in fields: self.assertIn(f, data)` |
| 중첩된 딕셔너리 구조 검증 | `assertDictEqual` | `self.assertDictEqual(response.json(), expected_structure)` |
| API 응답 형식 비교 | `assertDictEqual` | `self.assertDictEqual(data, expected_format)` |
| 문자열에 부분 문자열 포함 여부 | `assertIn` | `self.assertIn('error', error_message)` |
| QuerySet에 객체 포함 여부 | `assertIn` | `self.assertIn(user, User.objects.all())` |

---

## 5. 주요 차이점

### assertIn vs assertEqual

```python
# assertIn - 멤버십 테스트 (키 존재 확인)
self.assertIn('name', {'name': 'John', 'age': 30})

# assertEqual - 동등성 테스트 (값 비교)
self.assertEqual(data['name'], 'John')
```

**사용 시나리오:**
- `assertIn`: "이 키/값이 컨테이너에 존재하는가?"
- `assertEqual`: "이 두 값이 같은가?"

### assertDictEqual vs assertEqual

```python
dict1 = {'a': 1, 'b': 2}
dict2 = {'a': 1, 'b': 99}

# assertEqual - 일반적인 에러 메시지
self.assertEqual(dict1, dict2)
# AssertionError: {'a': 1, 'b': 2} != {'a': 1, 'b': 99}

# assertDictEqual - 상세한 차이점 표시
self.assertDictEqual(dict1, dict2)
# AssertionError: {'a': 1, 'b': 2} != {'a': 1, 'b': 99}
# Differing items:
# {'b': 2} != {'b': 99}
```

**장점:**
- `assertDictEqual`은 어떤 키의 값이 다른지 명확하게 보여줌
- 디버깅 시간 단축
- 테스트 실패 원인 파악 용이

### assertIn vs assertContains (Django 전용)

```python
# assertIn - 일반적인 멤버십 테스트 (unittest)
self.assertIn('success', ['success', 'failure', 'pending'])

# assertContains - Django HTTP 응답 전용
response = self.client.get('/api/endpoint/')
self.assertContains(response, 'success')  # HTML/JSON 응답 본문 검사
self.assertContains(response, 'success', status_code=200)  # 상태 코드도 확인
```

**차이점:**
- `assertContains`는 응답 상태 코드도 함께 확인 (기본 200)
- `assertContains`는 Django TestCase에서만 사용 가능
- `assertIn`은 범용적으로 사용 가능

---

## 6. 베스트 프랙티스

### 1. 명확한 에러 메시지 제공

```python
# 나쁜 예 - 에러 메시지 없음
self.assertIn('user_id', response_data)

# 좋은 예 - 간단한 메시지
self.assertIn(
    'user_id',
    response_data,
    msg="API 응답에 'user_id' 필드가 반드시 포함되어야 합니다"
)

# 더 좋은 예 - 현재 상태 포함
self.assertDictEqual(
    actual,
    expected,
    msg=f"환급 요약 형식이 일치하지 않습니다.\n"
        f"실제: {actual}\n"
        f"예상: {expected}"
)
```

### 2. 부분 비교 패턴

```python
def test_partial_response_structure(self):
    """전체가 아닌 필요한 부분만 검증"""
    response = self.client.get('/api/v1/complex-data/')
    data = response.json()

    # 방법 1: 관심 있는 필드만 추출하여 비교
    relevant_keys = ['id', 'status', 'amount']
    actual_subset = {k: data[k] for k in relevant_keys if k in data}

    expected = {
        'id': 1,
        'status': 'approved',
        'amount': 1000000
    }

    self.assertDictEqual(actual_subset, expected)

    # 방법 2: 각 필드를 개별적으로 확인
    self.assertEqual(data['id'], 1)
    self.assertEqual(data['status'], 'approved')
    self.assertEqual(data['amount'], 1000000)
```

### 3. 성능 고려사항

```python
# 나쁜 예 - 큰 리스트에서 직접 검색
large_list = list(range(10000))
self.assertIn(5000, large_list)  # O(n) 시간 복잡도

# 좋은 예 - set으로 변환하여 검색
large_list = list(range(10000))
self.assertIn(5000, set(large_list))  # O(1) 평균 시간 복잡도

# 더 좋은 예 - 처음부터 set 사용
large_set = set(range(10000))
self.assertIn(5000, large_set)
```

### 4. 테스트 계층화 전략

```python
class RefundAPITestCase(APITestCase):
    def test_response_structure_layered(self):
        """계층적으로 응답 구조 검증"""
        response = self.client.get('/api/v1/refunds/summary/')
        data = response.json()

        # Level 1: 최상위 구조 확인
        self.assertIn('success', data)
        self.assertIn('data', data)
        self.assertTrue(data['success'])

        # Level 2: data 내부 키 확인
        required_data_keys = ['total', 'by_year', 'by_status']
        for key in required_data_keys:
            self.assertIn(key, data['data'])

        # Level 3: 특정 객체의 정확한 구조 확인
        if len(data['data']['by_year']) > 0:
            first_year_data = data['data']['by_year'][0]
            expected_structure = {
                'year': 2024,
                'amount': 1000000,
                'count': 5
            }
            self.assertDictEqual(first_year_data, expected_structure)
```

### 5. 동적 값 처리

```python
class DynamicValueTestCase(TestCase):
    def test_response_with_dynamic_values(self):
        """동적 값(timestamp 등)이 포함된 응답 테스트"""
        from datetime import datetime

        response = self.client.post('/api/v1/refunds/')
        data = response.json()

        # 정적 필드는 assertDictEqual로 검증
        static_fields = ['id', 'status', 'amount']
        expected_static = {
            'id': 1,
            'status': 'pending',
            'amount': 1000000
        }
        actual_static = {k: data[k] for k in static_fields}
        self.assertDictEqual(actual_static, expected_static)

        # 동적 필드는 존재 여부와 타입만 확인
        self.assertIn('created_at', data)
        self.assertIsInstance(data['created_at'], str)

        # 날짜 형식 검증
        try:
            datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        except ValueError:
            self.fail("created_at 필드가 올바른 ISO 형식이 아닙니다")
```

### 6. 재사용 가능한 헬퍼 메서드

```python
class BaseAPITestCase(APITestCase):
    """재사용 가능한 assertion 헬퍼 메서드"""

    def assertResponseSuccess(self, response, expected_data=None):
        """성공 응답 구조 검증"""
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn('success', data)
        self.assertTrue(data['success'])

        if expected_data:
            self.assertDictEqual(data.get('data'), expected_data)

    def assertResponseError(self, response, expected_code=None):
        """에러 응답 구조 검증"""
        data = response.json()

        self.assertIn('success', data)
        self.assertFalse(data['success'])
        self.assertIn('code', data)
        self.assertIn('message', data)

        if expected_code:
            self.assertEqual(data['code'], expected_code)

    def assertHasFields(self, data, fields):
        """여러 필드 존재 여부 확인"""
        for field in fields:
            self.assertIn(
                field,
                data,
                msg=f"'{field}' 필드가 응답에 없습니다"
            )

# 사용 예시
class RefundAPITestCase(BaseAPITestCase):
    def test_refund_detail(self):
        """환급 상세 조회 테스트"""
        response = self.client.get('/api/v1/refunds/1/')

        # 헬퍼 메서드 사용
        self.assertResponseSuccess(response)

        data = response.json()['data']
        self.assertHasFields(data, ['id', 'year', 'amount', 'status'])
```

---

## 7. 실전 예시: 프로젝트별 패턴

### 환급(Refund) API 테스트

```python
from apps.refund.models import WorkerRefundGroup
from django.contrib.auth import get_user_model

class WorkerRefundGroupAPITestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)

    def test_refund_group_list_response(self):
        """환급 그룹 목록 응답 구조 검증"""
        # 테스트 데이터 생성
        WorkerRefundGroup.objects.create(
            user=self.user,
            year=2024,
            total_amount=1000000,
            status='approved'
        )

        response = self.client.get('/api/v1/refund/worker-groups/')
        data = response.json()

        # 기본 응답 구조 확인
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)

        # 목록 데이터 확인
        results = data['data']['results']
        self.assertGreater(len(results), 0)

        # 첫 번째 항목 구조 검증
        first_item = results[0]
        expected_fields = ['id', 'year', 'total_amount', 'status', 'created_at']
        for field in expected_fields:
            self.assertIn(field, first_item)

        # 값 검증
        self.assertEqual(first_item['year'], 2024)
        self.assertEqual(first_item['total_amount'], 1000000)
        self.assertEqual(first_item['status'], 'approved')
```

### Serializer 테스트

```python
from apps.user.serializers import UserProfileSerializer

class UserSerializerTestCase(TestCase):
    def test_user_profile_serializer_output(self):
        """사용자 프로필 Serializer 출력 형식 검증"""
        User = get_user_model()
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            phone_number="01012345678",
            name="테스트유저"
        )

        serializer = UserProfileSerializer(user)
        data = serializer.data

        # 예상 구조
        expected = {
            'id': user.id,
            'username': 'testuser',
            'email': 'test@example.com',
            'phone_number': '01012345678',
            'name': '테스트유저'
        }

        self.assertDictEqual(data, expected)
```

### Manager 메서드 테스트

```python
class WorkerRefundGroupManagerTestCase(TestCase):
    def test_get_user_summary(self):
        """사용자 환급 요약 조회 메서드 테스트"""
        User = get_user_model()
        user = User.objects.create_user(username="testuser")

        # 테스트 데이터 생성
        WorkerRefundGroup.objects.create(
            user=user,
            year=2024,
            total_amount=1000000,
            status='approved'
        )
        WorkerRefundGroup.objects.create(
            user=user,
            year=2023,
            total_amount=500000,
            status='completed'
        )

        # Manager 메서드 호출
        summary = WorkerRefundGroup.objects.get_user_summary(user=user)

        # 결과 검증
        expected_summary = {
            'user_id': user.id,
            'total_count': 2,
            'total_amount': 1500000,
            'years': [2024, 2023]
        }

        self.assertDictEqual(summary, expected_summary)
```

---

## 요약

### assertIn 사용 시점
- ✅ 키/값의 존재 여부를 확인할 때
- ✅ 여러 필드가 있는지 빠르게 확인할 때
- ✅ 간단한 멤버십 테스트가 필요할 때

### assertDictEqual 사용 시점
- ✅ 전체 딕셔너리 구조를 정확히 비교할 때
- ✅ API 응답 형식을 검증할 때
- ✅ Serializer 출력을 검증할 때
- ✅ 상세한 에러 메시지가 필요할 때

### 핵심 원칙
1. **명확성**: 테스트 의도가 명확하게 드러나는 메서드 선택
2. **에러 메시지**: 항상 의미 있는 커스텀 메시지 제공
3. **계층화**: assertIn으로 존재 확인 → assertDictEqual로 구조 검증
4. **재사용성**: 공통 패턴은 헬퍼 메서드로 추출

---

**작성일**: 2024-01-01
**버전**: 1.0
**관련 문서**: [CLAUDE.md](./CLAUDE.md)
