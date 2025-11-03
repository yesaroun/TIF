# unittest.mock.patch

`patch`는 테스트 중 특정 객체를 임시로 교체해 원하는 행동을 강제하거나 외부 의존성을 끊어내는 기능을 제공합니다. Python 내장 라이브러리인 `unittest.mock` 모듈에 포함되어 있으며, 테스트 범위 내에서만 교체가 유지되고 블록을 벗어나면 자동으로 원래 객체로 복원됩니다.

## 기본 개념

- **대상(target)**: `"패키지.모듈.객체"` 형식의 문자열로, *사용되는 위치*를 기준으로 지정합니다.
- **대체 객체(new)**: 대상 대신 사용할 객체. 지정하지 않으면 `MagicMock` 인스턴스가 자동으로 생성됩니다.
- **범위(scope)**: 데코레이터, 컨텍스트 매니저, `start()/stop()`으로 관리할 수 있습니다.

## 대표 사용 패턴

### 1. 컨텍스트 매니저

컨텍스트 매니저는 `with` 블록을 사용하여 **패치가 적용되는 범위를 명확히 제한**하는 방식입니다.

#### 왜 `patch`를 사용하는가?

테스트할 때 실제 외부 API를 호출하면:
- **느립니다** (네트워크 왕복 시간)
- **비용이 발생**할 수 있습니다 (API 호출 요금)
- **불안정합니다** (네트워크 장애, 서버 다운타임)
- **테스트 환경을 오염**시킵니다 (실제 데이터베이스 변경 등)

`patch`를 사용하면 외부 의존성을 가짜 객체로 교체하여 **빠르고 안정적이며 격리된 테스트**를 작성할 수 있습니다.

#### 기본 예제: 클래스 메서드 패치

```python
from unittest.mock import patch

# 실제 API 클라이언트 클래스
class ApiClient:
    def get_user(self):
        # 실제로는 네트워크 요청을 보냄 (느리고 의존성이 있음)
        raise Exception("실제 API 호출!")

# API를 사용하는 비즈니스 로직
def fetch_username(api_client):
    return api_client.get_user()["name"]

# 테스트 코드
def test_fetch_username():
    client = ApiClient()

    # ApiClient.get_user 메서드를 패치
    with patch.object(ApiClient, 'get_user', return_value={"name": "Alice", "age": 30}):
        # with 블록 안에서는 get_user()가 실제 API를 호출하지 않고
        # return_value로 지정한 {"name": "Alice", "age": 30}을 즉시 반환
        result = fetch_username(client)
        assert result == "Alice"  # 성공!
```

#### `with` 블록이 하는 일

```python
# with 블록 밖: 원래 객체 사용
client = ApiClient()
# client.get_user()  # 여기서 호출하면 실제 API 호출 → 에러!

with patch.object(ApiClient, 'get_user', return_value={"name": "Bob"}):
    # ✅ with 블록 안: 패치된 가짜 객체 사용
    result = client.get_user()  # {"name": "Bob"} 반환
    print(result)  # {"name": "Bob"}

# ✅ with 블록 밖: 자동으로 원래 객체로 복원
# client.get_user()  # 다시 실제 API 호출 → 에러!
```

**핵심 포인트:**
- `with` 블록 **안에서만** 패치가 적용됩니다
- 블록을 벗어나면 **자동으로 원래 객체로 복원**됩니다
- 테스트 실패/예외가 발생해도 **항상 복원이 보장**됩니다

#### `return_value`의 역할

`return_value`는 **패치된 함수/메서드가 호출될 때 반환할 값**을 지정합니다:

```python
with patch.object(ApiClient, 'get_user', return_value={"name": "Charlie"}):
    result1 = client.get_user()  # {"name": "Charlie"}
    result2 = client.get_user()  # {"name": "Charlie"} (매번 같은 값)
```

`return_value`를 지정하지 않으면 `MagicMock` 객체가 반환됩니다:

```python
with patch.object(ApiClient, 'get_user'):  # return_value 없음
    result = client.get_user()  # <MagicMock ...> 반환
```

#### 모듈 함수 패치 예제

```python
# my_module.py
def call_external_api():
    raise Exception("실제 네트워크 호출!")

def process_data():
    data = call_external_api()
    return f"결과: {data['status']}"

# test.py
from unittest.mock import patch
import my_module

def test_process_data():
    # my_module.call_external_api 함수를 패치
    with patch('my_module.call_external_api', return_value={"status": "ok"}):
        result = my_module.process_data()
        assert result == "결과: ok"
```

### 2. 함수/메서드 데코레이터

데코레이터 방식은 **테스트 함수 전체에 걸쳐 패치를 적용**하고, 생성된 mock 객체를 함수 인자로 자동 주입해줍니다. `with` 블록 없이 깔끔하게 작성할 수 있어 많이 사용됩니다.

#### 기본 예제: 단일 데코레이터

```python
from unittest.mock import patch

# 외부 의존성을 가진 함수들
def send_email(to, subject, body):
    """실제로 이메일을 보내는 함수 (느리고 외부 의존성 있음)"""
    raise Exception("실제 이메일 전송!")

def process_signup(email, username):
    """회원가입 처리 - 이메일 전송 포함"""
    # ... 회원가입 로직 ...
    send_email(to=email, subject="환영합니다!", body=f"{username}님 가입을 환영합니다")
    return True

# 테스트 코드
@patch("__main__.send_email")  # send_email 함수를 패치
def test_signup(mock_send_email):
    """회원가입 시 이메일이 전송되는지 테스트"""
    # 테스트 실행
    result = process_signup("user@example.com", "Alice")

    # 검증: send_email이 올바른 인자로 호출되었는지 확인
    mock_send_email.assert_called_once_with(
        to="user@example.com",
        subject="환영합니다!",
        body="Alice님 가입을 환영합니다"
    )
    assert result is True
```

**데코레이터의 동작:**
1. `@patch` 데코레이터가 `send_email`을 `MagicMock` 객체로 교체
2. 교체된 mock 객체를 `mock_send_email` 인자로 주입
3. 테스트 함수 실행 (`process_signup` 내부에서 `send_email` 호출은 mock이 받음)
4. mock 객체로 호출 여부, 호출 인자 등을 검증
5. 테스트 종료 후 자동으로 원래 `send_email`로 복원

#### Mock 객체 검증 메서드

```python
@patch("__main__.send_email")
def test_email_assertions(mock_send_email):
    send_email("test@example.com", "Hello", "World")
    send_email("test@example.com", "Hello", "World")

    # 호출 횟수 검증
    assert mock_send_email.call_count == 2

    # 최소 1회 호출 검증
    mock_send_email.assert_called()

    # 정확히 1회 호출 검증 (실패 - 2회 호출됨)
    # mock_send_email.assert_called_once()  # AssertionError!

    # 특정 인자로 호출되었는지 검증
    mock_send_email.assert_called_with("test@example.com", "Hello", "World")

    # 특정 인자로 정확히 1회 호출 검증 (실패 - 2회 호출됨)
    # mock_send_email.assert_called_once_with("test@example.com", "Hello", "World")

    # 호출 이력 확인
    print(mock_send_email.call_args_list)
    # [call('test@example.com', 'Hello', 'World'),
    #  call('test@example.com', 'Hello', 'World')]
```

#### 여러 데코레이터 사용 (중요!)

여러 패치가 필요한 경우 데코레이터를 여러 개 쌓을 수 있습니다. **주의: 인자 주입 순서는 아래에서 위로(가장 안쪽 데코레이터가 첫 번째 인자)**입니다.

```python
import time

def send_sms(phone, message):
    """SMS 전송 함수"""
    raise Exception("실제 SMS 전송!")

def get_current_time():
    """현재 시간 반환"""
    return time.time()

def process_order(user_phone, item):
    """주문 처리 - SMS 전송 및 시간 기록"""
    order_time = get_current_time()
    send_sms(user_phone, f"{item} 주문이 접수되었습니다")
    send_email("admin@shop.com", "새 주문", f"{order_time}에 {item} 주문")
    return order_time

# 여러 패치 사용
@patch("__main__.send_email")      # 3번째 인자 (위에서 3번째)
@patch("__main__.send_sms")        # 2번째 인자 (위에서 2번째)
@patch("__main__.get_current_time") # 1번째 인자 (가장 안쪽)
def test_order_processing(mock_time, mock_sms, mock_email):
    """주문 처리 시 모든 외부 호출이 올바르게 이루어지는지 테스트"""
    # 시간을 고정값으로 설정
    mock_time.return_value = 1234567890.0

    # 주문 처리
    result = process_order("010-1234-5678", "노트북")

    # 검증
    assert result == 1234567890.0
    mock_time.assert_called_once()
    mock_sms.assert_called_once_with("010-1234-5678", "노트북 주문이 접수되었습니다")
    mock_email.assert_called_once_with(
        "admin@shop.com",
        "새 주문",
        "1234567890.0에 노트북 주문"
    )
```

**핵심 포인트:**
- 데코레이터 순서와 인자 순서가 **반대**입니다
- 가장 **안쪽(아래쪽)** 데코레이터가 **첫 번째** 인자
- 가장 **바깥쪽(위쪽)** 데코레이터가 **마지막** 인자

#### `@patch.multiple` 사용

같은 모듈의 여러 객체를 패치할 때 더 간결하게 작성할 수 있습니다:

```python
@patch.multiple("__main__",
                send_email=patch.DEFAULT,
                send_sms=patch.DEFAULT)
def test_with_patch_multiple(send_email, send_sms):
    """patch.multiple을 사용한 예제"""
    process_signup("user@test.com", "Bob")
    send_email.assert_called_once()
    # send_sms는 호출되지 않음
    send_sms.assert_not_called()
```

### 3. 클래스 수준 패치

클래스의 **여러 테스트 메서드에서 동일한 패치를 공유**해야 할 때 `setUp` 메서드에서 `start()`/`stop()` 패턴을 사용합니다. 각 테스트마다 데코레이터를 반복하지 않아도 되어 코드 중복을 줄일 수 있습니다.

#### 왜 클래스 수준 패치가 필요한가?

여러 테스트 메서드에서 같은 외부 의존성을 패치해야 하는 경우:

```python
# ❌ 데코레이터를 매번 반복 (중복 코드)
class PaymentTests(TestCase):
    @patch("payments.gateway.charge")
    def test_successful_payment(self, mock_charge):
        # 테스트 코드...
        pass

    @patch("payments.gateway.charge")
    def test_failed_payment(self, mock_charge):
        # 테스트 코드...
        pass

    @patch("payments.gateway.charge")
    def test_refund(self, mock_charge):
        # 테스트 코드...
        pass
```

위 코드는 `@patch` 데코레이터가 계속 반복됩니다. 클래스 수준 패치로 개선할 수 있습니다.

#### 완전한 예제: `setUp`과 `start()/stop()` 사용

```python
from unittest import TestCase
from unittest.mock import patch, MagicMock

# 외부 결제 게이트웨이 (실제로는 네트워크 호출)
class PaymentGateway:
    @staticmethod
    def charge(card_number, amount):
        """실제 결제 처리 (외부 API 호출)"""
        raise Exception("실제 결제 API 호출!")

    @staticmethod
    def refund(transaction_id, amount):
        """환불 처리 (외부 API 호출)"""
        raise Exception("실제 환불 API 호출!")

# 결제 서비스
def process_payment(card, amount):
    """결제 처리 로직"""
    result = PaymentGateway.charge(card, amount)
    if result["status"] == "success":
        return {"success": True, "transaction_id": result["transaction_id"]}
    return {"success": False, "error": result["error"]}

def process_refund(transaction_id, amount):
    """환불 처리 로직"""
    result = PaymentGateway.refund(transaction_id, amount)
    return result["status"] == "success"

# 테스트 클래스
class PaymentTests(TestCase):
    """결제 관련 테스트 모음"""

    def setUp(self):
        """각 테스트 메서드 실행 전에 호출됨"""
        # PaymentGateway.charge 메서드를 패치
        self.charge_patcher = patch.object(PaymentGateway, 'charge')
        self.mock_charge = self.charge_patcher.start()

        # PaymentGateway.refund 메서드를 패치
        self.refund_patcher = patch.object(PaymentGateway, 'refund')
        self.mock_refund = self.refund_patcher.start()

        # 테스트가 끝나면 (성공/실패 상관없이) 자동으로 패치 해제
        self.addCleanup(self.charge_patcher.stop)
        self.addCleanup(self.refund_patcher.stop)

    def test_successful_payment(self):
        """성공적인 결제 테스트"""
        # mock_charge가 반환할 값 설정
        self.mock_charge.return_value = {
            "status": "success",
            "transaction_id": "TXN-12345"
        }

        # 결제 처리
        result = process_payment("1234-5678-9012-3456", 10000)

        # 검증
        assert result["success"] is True
        assert result["transaction_id"] == "TXN-12345"
        self.mock_charge.assert_called_once_with("1234-5678-9012-3456", 10000)

    def test_failed_payment(self):
        """실패한 결제 테스트"""
        # 결제 실패 시나리오 설정
        self.mock_charge.return_value = {
            "status": "failed",
            "error": "카드 잔액 부족"
        }

        # 결제 처리
        result = process_payment("1234-5678-9012-3456", 10000)

        # 검증
        assert result["success"] is False
        assert result["error"] == "카드 잔액 부족"
        self.mock_charge.assert_called_once()

    def test_refund_success(self):
        """환불 성공 테스트"""
        # 환불 성공 시나리오 설정
        self.mock_refund.return_value = {"status": "success"}

        # 환불 처리
        result = process_refund("TXN-12345", 10000)

        # 검증
        assert result is True
        self.mock_refund.assert_called_once_with("TXN-12345", 10000)

    def test_multiple_payments(self):
        """여러 번 결제하는 테스트"""
        # 각 호출마다 다른 값 반환 (side_effect 사용)
        self.mock_charge.side_effect = [
            {"status": "success", "transaction_id": "TXN-001"},
            {"status": "success", "transaction_id": "TXN-002"},
            {"status": "failed", "error": "네트워크 오류"},
        ]

        # 3번의 결제 시도
        result1 = process_payment("1111-2222-3333-4444", 5000)
        result2 = process_payment("5555-6666-7777-8888", 3000)
        result3 = process_payment("9999-0000-1111-2222", 7000)

        # 검증
        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is False
        assert self.mock_charge.call_count == 3
```

#### `setUp`과 `addCleanup`의 역할

**`setUp`:**
- 각 테스트 메서드 **실행 전**에 자동으로 호출됩니다
- 테스트에 필요한 공통 설정을 수행합니다
- `patcher.start()`로 패치를 활성화하고 mock 객체를 받습니다

**`addCleanup`:**
- 테스트 종료 후 **반드시 실행되어야 하는 정리 작업**을 등록합니다
- 테스트가 **성공하든 실패하든 예외가 발생하든** 항상 실행됩니다
- `patcher.stop()`으로 패치를 해제하여 다른 테스트에 영향을 주지 않도록 합니다

```python
def setUp(self):
    self.patcher = patch("module.function")
    self.mock_func = self.patcher.start()
    # ✅ addCleanup 사용 - 테스트 실패해도 자동 정리
    self.addCleanup(self.patcher.stop)

    # ❌ tearDown 사용 - 테스트 실패 시 정리 안될 수 있음
    # def tearDown(self):
    #     self.patcher.stop()
```

#### `start()/stop()` vs 데코레이터 비교

| 방식 | 장점 | 단점 |
|------|------|------|
| **데코레이터** | 간결하고 명확함, 자동 정리 | 각 메서드마다 반복 필요 |
| **start()/stop()** | 여러 테스트에서 재사용, 유연한 제어 | 명시적 정리 필요 (addCleanup) |

**권장 사용 시나리오:**
- **단일 테스트**: 데코레이터 사용 (`@patch`)
- **여러 테스트에서 공유**: `setUp`에서 `start()/stop()` 사용
- **테스트마다 다른 패치**: 각각 데코레이터 사용

## target 선택 요령

- 패치 대상은 **정의된 위치가 아니라 실제로 import 되어 사용되는 위치**를 기준으로 합니다.
- 예: `module_a`가 `from external import service`로 가져온 후 `service.call()`을 사용한다면, 테스트에서는 `"module_a.service.call"`을 패치해야 합니다.
- 존재하지 않는 경로를 지정하면 `AttributeError`가 발생하며, `patch(..., create=True)`로 누락된 속성을 임시로 만들 수 있습니다.

## 자주 쓰는 옵션

| 옵션 | 설명 |
| --- | --- |
| `return_value` | 호출 시 반환할 값 지정 (`MagicMock`이 기본 반환) |
| `side_effect` | 호출 시 예외를 던지거나, iterable을 순회하며 반환하도록 구성 |
| `autospec=True` | 실제 객체의 시그니처를 기반으로 모의 객체를 생성해 오타를 조기 발견 |
| `new_callable` | 기본 `MagicMock` 대신 다른 클래스/팩토리로 교체 |

## 베스트 프랙티스 & 주의 사항

- 테스트가 끝나면 항상 원래 객체로 복원되는지 확인하세요. 컨텍스트 매니저, 데코레이터, `addCleanup` 등을 활용하면 안전합니다.
- `autospec=True`를 기본 선택으로 두면 인자 실수를 줄일 수 있습니다.
- 외부 API 호출, 데이터베이스, 시간/난수 생성 등 테스트를 느리게 하거나 비결정적으로 만드는 요소에 패치를 적용하세요.
- 너무 많은 패치를 남용하면 테스트가 실제 동작을 충분히 검증하지 못할 수 있으므로, 통합 테스트와 균형을 맞추세요.

## 추가 참고

- 공식 문서: [unittest.mock — mock 객체 라이브러리](https://docs.python.org/3/library/unittest.mock.html)
- `patch.object`, `patch.dict`, `patch.multiple` 등 상황별 도우미도 함께 살펴보면 복잡한 모킹 시나리오를 다루기 쉽습니다.
