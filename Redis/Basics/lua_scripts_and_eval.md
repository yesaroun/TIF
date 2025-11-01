# Redis Lua 스크립트와 EVAL 함수 완전 가이드

## 목차
1. [Redis에서 Lua가 필요한 이유](#1-redis에서-lua가-필요한-이유)
2. [EVAL 함수 기본](#2-eval-함수-기본)
3. [KEYS와 ARGV 파라미터 이해](#3-keys와-argv-파라미터-이해)
4. [실전 예제: 분산 락 release 함수 완전 분석](#4-실전-예제-분산-락-release-함수-완전-분석)
5. [더 많은 실용 예제](#5-더-많은-실용-예제)
6. [성능 최적화: EVALSHA](#6-성능-최적화-evalsha)
7. [주의사항과 제약사항](#7-주의사항과-제약사항)

---

## 1. Redis에서 Lua가 필요한 이유

### 1.1 원자성(Atomicity) 보장의 중요성

Redis는 단일 명령어는 원자적으로 실행되지만, 여러 명령어를 조합하면 경쟁 조건(Race Condition)이 발생할 수 있습니다.

**문제 상황 예시: 락 해제**

```python
# 잘못된 방법 - 경쟁 조건 발생 가능
def release_lock_wrong(redis_client, lock_name, lock_value):
    # 1. 먼저 값을 확인
    current_value = redis_client.get(lock_name)

    # 2. 내가 소유한 락인지 확인
    if current_value == lock_value:
        # ⚠️ 문제: 여기서 다른 프로세스가 개입할 수 있음!
        # 시나리오:
        # - 현재 시점에서 내 락이 만료됨
        # - 다른 프로세스가 같은 이름으로 새 락을 획득
        # - 그런데 나는 아래에서 그 락을 삭제해버림!
        redis_client.delete(lock_name)
```

**타임라인으로 보는 문제:**

```
시간  | 프로세스 A                    | 프로세스 B
----------------------------------------------------------
t1    | GET lock:order -> "uuid-A"   |
t2    | 값 확인: 맞음                 |
t3    | [락 만료됨]                   |
t4    |                              | SET lock:order "uuid-B"
t5    | DEL lock:order               | [내 락이 삭제됨! 💥]
      | (B의 락을 삭제해버림)         |
```

### 1.2 Lua 스크립트가 제공하는 해결책

Lua 스크립트는 **전체 스크립트가 하나의 원자적 단위**로 실행됩니다:
- 스크립트 실행 중에는 다른 명령어가 끼어들 수 없음
- GET과 DEL이 하나의 트랜잭션처럼 동작
- 경쟁 조건 완전 차단

---

## 2. EVAL 함수 기본

### 2.1 Redis EVAL 명령어 구조

```
EVAL script numkeys key [key ...] arg [arg ...]
```

**파라미터 설명:**
- `script`: 실행할 Lua 스크립트 문자열
- `numkeys`: KEYS 배열의 크기 (몇 개의 키를 전달하는지)
- `key [key ...]`: KEYS 배열에 들어갈 키들
- `arg [arg ...]`: ARGV 배열에 들어갈 인자들

### 2.2 Python redis 클라이언트에서 사용법

```python
import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# 기본 사용법
result = r.eval(
    script,      # Lua 스크립트 문자열
    numkeys,     # KEYS 배열 크기
    *keys,       # 키들 (가변 인자)
    *args        # 인자들 (가변 인자)
)
```

**간단한 예제:**

```python
# Lua 스크립트: 두 숫자를 더하기
script = """
return ARGV[1] + ARGV[2]
"""

result = r.eval(script, 0, 10, 20)
print(result)  # 30
```

### 2.3 반환값

Lua 스크립트는 다양한 타입을 반환할 수 있습니다:

```python
# 숫자 반환
script = "return 42"
result = r.eval(script, 0)  # result = 42

# 문자열 반환
script = "return 'Hello'"
result = r.eval(script, 0)  # result = 'Hello'

# 테이블(배열) 반환
script = "return {1, 2, 3}"
result = r.eval(script, 0)  # result = [1, 2, 3]

# nil 반환 (Python의 None)
script = "return nil"
result = r.eval(script, 0)  # result = None
```

---

## 3. KEYS와 ARGV 파라미터 이해

### 3.1 KEYS vs ARGV의 차이

**KEYS:**
- Redis 키 이름을 전달할 때 사용
- Lua에서 `KEYS[1]`, `KEYS[2]`, ... 로 접근
- Redis 클러스터 모드에서 중요 (샤딩 힌트로 사용)

**ARGV:**
- 일반 값(value)을 전달할 때 사용
- Lua에서 `ARGV[1]`, `ARGV[2]`, ... 로 접근
- 키가 아닌 모든 인자

**⚠️ 중요:** Lua는 1-indexed입니다 (0이 아닌 1부터 시작)

### 3.2 Python에서 전달하는 방법

```python
# 예제 1: 1개의 키, 2개의 인자
script = """
local key = KEYS[1]
local value1 = ARGV[1]
local value2 = ARGV[2]
redis.call('SET', key, value1 .. ':' .. value2)
return 'OK'
"""

r.eval(
    script,
    1,              # numkeys = 1 (KEYS 배열 크기)
    'mykey',        # KEYS[1] = 'mykey'
    'hello',        # ARGV[1] = 'hello'
    'world'         # ARGV[2] = 'world'
)
# 결과: Redis에 mykey = "hello:world" 저장
```

```python
# 예제 2: 3개의 키, 1개의 인자
script = """
for i, key in ipairs(KEYS) do
    redis.call('SET', key, ARGV[1])
end
return #KEYS
"""

r.eval(
    script,
    3,                      # numkeys = 3
    'key1', 'key2', 'key3', # KEYS[1], KEYS[2], KEYS[3]
    'same_value'            # ARGV[1]
)
# 결과: key1, key2, key3 모두 'same_value'로 설정
```

### 3.3 왜 KEYS와 ARGV를 구분하는가?

1. **가독성**: 키와 값을 명확히 구분
2. **클러스터 모드**: Redis 클러스터는 KEYS를 보고 어느 샤드에서 실행할지 결정
3. **최적화**: Redis가 키 접근 패턴을 분석 가능

---

## 4. 실전 예제: 분산 락 release 함수 완전 분석

이제 `Redis/DistributedLocks/redlock/sources/02_basic.py`의 release 함수를 완전히 이해해봅시다.

### 4.1 전체 코드

```python
def release(self):
    """락 해제 (Lua 스크립트 사용)"""
    # lua 스크립트로 원자성 보장
    lua_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    self.redis_client.eval(lua_script, 1, self.resource_name, self.lock_value)
```

### 4.2 파라미터 매핑 상세 분석

```python
self.redis_client.eval(
    lua_script,           # Lua 스크립트
    1,                    # numkeys = 1 (KEYS 배열에 원소 1개)
    self.resource_name,   # KEYS[1] = "lock:order:123" (예시)
    self.lock_value       # ARGV[1] = "uuid-12345" (고유 식별자)
)
```

**실제 값 예시:**
- `self.resource_name` = `"lock:order:123"`
- `self.lock_value` = `"f47ac10b-58cc-4372-a567-0e02b2c3d479"` (UUID)

### 4.3 Lua 스크립트 한 줄씩 분석

```lua
if redis.call("get", KEYS[1]) == ARGV[1] then
```

**동작:**
1. `redis.call("get", KEYS[1])`: Redis GET 명령 실행
   - `KEYS[1]` = `"lock:order:123"`
   - 현재 락의 값을 가져옴
2. `== ARGV[1]`: 가져온 값과 내가 가진 lock_value 비교
   - `ARGV[1]` = `"f47ac10b-58cc-4372-a567-0e02b2c3d479"`
   - **목적:** 내가 소유한 락인지 확인

```lua
    return redis.call("del", KEYS[1])
```

**동작:**
- 조건이 참이면 (내 락이 맞으면) 키 삭제
- `redis.call("del", KEYS[1])`: DELETE 명령 실행
- 반환값: 1 (삭제된 키 개수)

```lua
else
    return 0
end
```

**동작:**
- 조건이 거짓이면 (내 락이 아니면) 0 반환
- **중요:** 다른 프로세스의 락을 삭제하지 않음!

### 4.4 왜 이 방식이 안전한가?

**원자성 보장:**
```
[Lua 스크립트 시작 - 원자적 실행 구간]
  1. GET lock:order:123 -> 값 확인
  2. 값 비교
  3. 조건 만족 시 DEL 실행
[Lua 스크립트 종료]
```

**다른 클라이언트는 절대 끼어들 수 없음!**

### 4.5 완전한 시나리오 예시

**성공 케이스:**
```python
# 초기 상태: Redis에 lock:order:123 = "uuid-A" (내 락)
lock = SimpleLock(r, "lock:order:123", ttl=30000)
lock.lock_value = "uuid-A"

lock.release()
# Lua 실행:
# 1. GET lock:order:123 -> "uuid-A"
# 2. "uuid-A" == "uuid-A" -> True
# 3. DEL lock:order:123 -> 1 (성공)
# 결과: 락 정상 해제
```

**실패 케이스 (이미 만료됨):**
```python
# 초기 상태:
#   - 내 락(uuid-A)은 만료됨
#   - 다른 프로세스가 lock:order:123 = "uuid-B"로 새로 획득

lock.lock_value = "uuid-A"
lock.release()
# Lua 실행:
# 1. GET lock:order:123 -> "uuid-B"
# 2. "uuid-B" == "uuid-A" -> False
# 3. return 0 (삭제하지 않음)
# 결과: 다른 프로세스의 락 보호 ✅
```

---

## 5. 더 많은 실용 예제

### 5.1 원자적 카운터 증가 (조건부)

```python
# 최대값 제한이 있는 카운터
script = """
local current = tonumber(redis.call('GET', KEYS[1]) or 0)
local max = tonumber(ARGV[1])

if current < max then
    redis.call('INCR', KEYS[1])
    return current + 1
else
    return current
end
"""

result = r.eval(script, 1, 'counter', 100)
print(f"현재 카운터: {result}")
```

### 5.2 리스트에 중복 없이 추가

```python
script = """
local exists = redis.call('LPOS', KEYS[1], ARGV[1])
if exists == false then
    redis.call('RPUSH', KEYS[1], ARGV[1])
    return 1
else
    return 0
end
"""

result = r.eval(script, 1, 'mylist', 'item1')
if result == 1:
    print("추가 성공")
else:
    print("이미 존재함")
```

### 5.3 TTL이 있는 카운터 (Rate Limiting)

```python
script = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""

# 60초 동안 최대 10번 요청 허용
user_id = "user:123"
window = 60
count = r.eval(script, 1, f'ratelimit:{user_id}', window)

if count > 10:
    print("Rate limit exceeded!")
else:
    print(f"요청 허용 ({count}/10)")
```

### 5.4 복잡한 비즈니스 로직: 재고 차감

```python
script = """
local stock = tonumber(redis.call('GET', KEYS[1]) or 0)
local quantity = tonumber(ARGV[1])

if stock >= quantity then
    redis.call('DECRBY', KEYS[1], quantity)
    redis.call('LPUSH', KEYS[2], ARGV[2])  -- 주문 기록
    return stock - quantity
else
    return -1  -- 재고 부족
end
"""

result = r.eval(
    script,
    2,                          # 2개의 키
    'stock:product:123',        # KEYS[1]: 재고 키
    'orders:product:123',       # KEYS[2]: 주문 목록
    5,                          # ARGV[1]: 차감할 수량
    'order-456'                 # ARGV[2]: 주문 ID
)

if result == -1:
    print("재고 부족")
else:
    print(f"주문 성공, 남은 재고: {result}")
```

---

## 6. 성능 최적화: EVALSHA

### 6.1 문제점

매번 긴 Lua 스크립트 문자열을 Redis에 전송하면 네트워크 오버헤드가 발생합니다.

```python
# 매번 전체 스크립트를 전송
long_script = """
-- 100줄의 복잡한 스크립트
...
"""
r.eval(long_script, 1, 'key')  # 전체 스크립트 전송
```

### 6.2 해결책: EVALSHA

Redis는 스크립트를 SHA1 해시로 캐싱합니다.

```python
import hashlib

# 1. 스크립트를 LOAD로 등록
script = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# 스크립트 해시 계산
script_sha = hashlib.sha1(script.encode()).hexdigest()

# 2. 스크립트 등록 (한 번만)
r.script_load(script)

# 3. SHA로 실행 (훨씬 빠름)
result = r.evalsha(script_sha, 1, 'lock:order:123', 'uuid-A')
```

### 6.3 자동 fallback 패턴

```python
def eval_with_fallback(redis_client, script, numkeys, *keys_and_args):
    """EVALSHA 시도 후 실패하면 EVAL로 fallback"""
    script_sha = hashlib.sha1(script.encode()).hexdigest()

    try:
        # 먼저 EVALSHA 시도
        return redis_client.evalsha(script_sha, numkeys, *keys_and_args)
    except redis.exceptions.NoScriptError:
        # 스크립트가 없으면 EVAL 사용 (자동 등록됨)
        return redis_client.eval(script, numkeys, *keys_and_args)
```

### 6.4 Python redis-py의 register_script

더 간편한 방법:

```python
# 스크립트 객체 생성
release_script = r.register_script("""
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
""")

# 사용 (자동으로 EVALSHA 사용, 필요시 fallback)
result = release_script(keys=['lock:order:123'], args=['uuid-A'])
```

---

## 7. 주의사항과 제약사항

### 7.1 Lua 스크립트는 블로킹

Lua 스크립트 실행 중에는 Redis가 다른 명령을 처리하지 못합니다.

**⚠️ 주의:**
```lua
-- 나쁜 예: 무한 루프
while true do
    -- Redis가 완전히 멈춤!
end
```

**권장 사항:**
- 스크립트는 짧고 빠르게 실행되어야 함
- 복잡한 계산은 애플리케이션 레벨에서 수행
- 일반적으로 밀리초 단위로 완료되어야 함

### 7.2 사용 가능한 Redis 명령어 제한

Lua에서는 `redis.call()` 또는 `redis.pcall()`로 Redis 명령 실행:

```lua
-- redis.call(): 에러 시 스크립트 중단
local value = redis.call('GET', KEYS[1])

-- redis.pcall(): 에러를 반환값으로 처리
local value, err = redis.pcall('GET', KEYS[1])
if err then
    -- 에러 처리
end
```

**차이점:**
- `redis.call()`: 에러 발생 시 즉시 중단하고 클라이언트에 에러 반환
- `redis.pcall()`: 에러를 Lua 값으로 반환하여 스크립트 내에서 처리 가능

### 7.3 비결정적 명령어 사용 금지

Redis는 복제(replication)를 위해 스크립트가 항상 같은 결과를 내야 합니다.

**금지된 명령어:**
- `RANDOMKEY`
- `SRANDMEMBER`
- `TIME`
- 현재 시간에 의존하는 작업

**대안:**
```lua
-- 나쁜 예
local time = redis.call('TIME')

-- 좋은 예: 시간을 인자로 전달
local time = ARGV[1]
```

### 7.4 전역 변수 사용 주의

```lua
-- 나쁜 예: 전역 변수
myvar = 123

-- 좋은 예: local 변수
local myvar = 123
```

### 7.5 반환값 타입 변환

Lua와 Redis 간 타입 변환 규칙:

| Lua 타입 | Redis 타입 | Python 타입 |
|---------|-----------|------------|
| number  | integer   | int        |
| string  | string    | str        |
| table   | array     | list       |
| nil     | nil       | None       |
| boolean | (특수)    | int (0/1)  |

**주의:**
```lua
-- boolean은 정수로 변환됨
return true   -- Python에서 1
return false  -- Python에서 0 (None 아님!)
```

### 7.6 스크립트 크기 제한

Redis는 기본적으로 스크립트 크기를 제한하지 않지만, 실용적으로는:
- 수 KB 이내로 유지 권장
- 너무 큰 스크립트는 여러 개로 분할

---

## 8. 참고 자료

- [Redis EVAL 공식 문서](https://redis.io/commands/eval)
- [Redis Lua 스크립팅 가이드](https://redis.io/docs/manual/programmability/eval-intro/)
- [redis-py 문서](https://redis-py.readthedocs.io/)
- 관련 문서: `Redis/DistributedLocks/redlock/02_implementations.md`

---

## 요약

### 핵심 포인트

1. **원자성**: Lua 스크립트는 전체가 하나의 원자적 단위로 실행
2. **KEYS vs ARGV**: 키는 KEYS로, 값은 ARGV로 전달
3. **1-indexed**: Lua는 배열이 1부터 시작
4. **성능**: EVALSHA로 최적화 가능
5. **제약사항**: 블로킹, 비결정적 명령 금지

### 실전 사용 패턴

```python
# 1. 스크립트 정의
script = """
-- Lua 로직
"""

# 2. 등록 (선택사항, 성능 최적화)
script_obj = redis_client.register_script(script)

# 3. 실행
result = script_obj(keys=['key1'], args=['arg1'])

# 또는 직접 실행
result = redis_client.eval(script, 1, 'key1', 'arg1')
```

이제 `02_basic.py`의 release 함수에 있는 Lua 스크립트와 eval 함수를 완전히 이해하셨을 것입니다!
