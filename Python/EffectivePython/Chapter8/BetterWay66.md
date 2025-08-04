# BetterWay66 재사용 가능한 try/finally 동작을 원한다면 contextlib과 with 문을 사용하라

`with` 문은 특정 컨텍스트(context)에서 코드가 실행됨을 나타내는 데 사용된다. 예를 들어, `threading.Lock`을 사용할 때 `with lock:` 구문을 사용하면 `try/finally` 블록으로 `lock.acquire()`와 `lock.release()`를 직접 작성하는 것보다 훨씬 간결하고 안전하다. `with` 블록이 시작될 때 잠금을 획득하고, 블록이 끝나면 (오류 발생 여부와 상관없이) 항상 잠금을 해제해주기 때문이다.

**기존 `try/finally` 방식:**

```python
lock.acquire()
try:
    # 공유 자원 작업
finally:
  lock.release()
```

**`with`문 사용:**

```python
with lock:
    # 공유 자원 작업
```

-----

### `@contextmanager`: 커스텀 `with`문 만들기

파이썬의 내장 모듈인 `contextlib`에 있는 `@contextmanager` 데코레이터를 사용하면, 복잡한 클래스 정의 없이도 간단한 제너레이터 함수를 `with` 문에서 사용할 수 있는 **컨텍스트 매니저**로 만들 수 있다.

- 함수 내에서 **`yield` 이전의 코드**는 `with` 블록이 시작될 때 실행됩니다.
- **`yield`** 시점에서 `with` 블록 내부의 코드가 실행됩니다.
- **`yield` 이후의 코드**는 `with` 블록이 끝날 때 `finally`처럼 항상 실행됩니다.

**예시: 임시로 로그 레벨을 변경하는 컨텍스트 매니저**

```python
from contextlib import contextmanager
import logging

@contextmanager
def debug_logging(level):
    logger = logging.getLogger()
    old_level = logger.getEffectiveLevel()
    logger.setLevel(level)  # with 블록 진입 전 실행
    try:
        yield               # with 블록 코드 실행
    finally:
        logger.setLevel(old_level) # with 블록 종료 후 실행

# 사용법
with debug_logging(logging.DEBUG):
    print('디버그 로그가 활성화된 구간입니다.')
    logging.debug('이 메시지는 출력됩니다.')

logging.debug('이 메시지는 출력되지 않습니다.')
```

-----

### `as` 키워드로 컨텍스트 객체 활용하기

`with` 문은 `as` 키워드를 통해 컨텍스트 매니저가 반환하는 객체를 변수로 받을 수 있다. 가장 대표적인 예는 파일을 다룰 때 사용하는 `with open(...) as f:` 구문이다.

`@contextmanager`로 만든 함수에서도 **`yield` 뒤에 특정 값을 반환**하면, 이 값을 `as` 절의 변수로 받아 `with` 블록 안에서 사용할 수 있다.

**예시: 특정 로거(Logger) 객체를 `yield`하기**

```python
@contextmanager
def log_level(level, name):
    logger = logging.getLogger(name)
    old_level = logger.getEffectiveLevel()
    logger.setLevel(level)
    try:
        yield logger  # 로거 객체를 반환
    finally:
        logger.setLevel(old_level)

# 사용법: 'my-log'라는 이름의 로거를 받아 사용
with log_level(logging.DEBUG, 'my-log') as logger:
    logger.debug(f'{logger.name}에 대한 디버그 메시지')
    logging.debug('이 메시지는 전역 로거라 출력되지 않음')
```

이 방식은 `with` 블록 내에서 사용할 특정 객체(상태)를 명확하게 전달하고 격리하는 데 매우 유용

-----

### 기억해야 할 내용

- `with` 문을 사용하면 `try/finally` 블록을 통해 사용해야 하는 로직을 재활용하면서 시각적인 잡음도 줄일 수 있다.
- `contextlib` 내장 모듈이 제공하는 `contextmanager` 데코레이터를 사용하면 여러분이 만든 함수를 `with` 문에 사용할 수 있다.
- 컨텍스트 매니저가 `yield` 하는 값은 `with` 문의 `as` 부분에 전달된다. 이를 활용하면 특별한 컨텍스트 내부에서 실행되는 코드 안에서 직접 그 컨텍스트에 접근할 수 있다.
