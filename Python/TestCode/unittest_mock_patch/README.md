# unittest.mock.patch

`patch`는 테스트 중 특정 객체를 임시로 교체해 원하는 행동을 강제하거나 외부 의존성을 끊어내는 기능을 제공합니다. Python 내장 라이브러리인 `unittest.mock` 모듈에 포함되어 있으며, 테스트 범위 내에서만 교체가 유지되고 블록을 벗어나면 자동으로 원래 객체로 복원됩니다.

## 기본 개념

- **대상(target)**: `"패키지.모듈.객체"` 형식의 문자열로, *사용되는 위치*를 기준으로 지정합니다.
- **대체 객체(new)**: 대상 대신 사용할 객체. 지정하지 않으면 `MagicMock` 인스턴스가 자동으로 생성됩니다.
- **범위(scope)**: 데코레이터, 컨텍스트 매니저, `start()/stop()`으로 관리할 수 있습니다.

## 대표 사용 패턴

### 1. 컨텍스트 매니저

```python
from unittest.mock import patch

def fetch_username(api_client):
    return api_client.get_user()["name"]

def test_fetch_username():
    with patch("path.to.module.api_client.get_user", return_value={"name": "Alice"}):
        assert fetch_username(api_client=None) == "Alice"
```

`with` 블록 안에서만 `get_user`가 모의 객체로 교체됩니다.

### 2. 함수/메서드 데코레이터

```python
from unittest.mock import patch

@patch("app.services.send_email")
def test_signup(mock_send_email):
    process_signup()
    mock_send_email.assert_called_once()
```

여러 패치를 추가하려면 데코레이터를 여러 개 쌓거나 `@patch.multiple`을 사용할 수 있습니다. 데코레이터는 내부 함수 인수에 모의 객체를 순서대로 주입합니다(가장 안쪽 데코레이터가 첫 번째 인수).

### 3. 클래스 수준 패치

```python
from unittest import TestCase
from unittest.mock import patch

class PaymentTests(TestCase):
    def setUp(self):
        patcher = patch("payments.gateway.charge")
        self.mock_charge = patcher.start()
        self.addCleanup(patcher.stop)
```

`start()`/`stop()` 패턴은 `setUp`과 같은 라이프사이클 훅에서 유용하며, `addCleanup`을 사용하면 테스트가 실패해도 자동으로 정리됩니다.

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
