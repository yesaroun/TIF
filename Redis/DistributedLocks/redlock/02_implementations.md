# RedLock 구현

## 목차

1. [단일 Redis 락 (Simple Lock)](#단일-redis-락)
2. [RedLock 알고리즘 구현](#redlock-알고리즘-구현)
3. [실전 구현 with redis-py](#실전-구현)
4. [테스트](#테스트)

---

## 단일 Redis 락

RedLock을 이해하기 위해 먼저 간단한 단일 Redis 락부터 살펴봅시다.

단일 인스턴스 락은 구현이 단순하고 빠르지만 하나의 Redis 노드에 모든 신뢰를 의존합니다. TTL(Time To Live)이 지나면 락이 자동으로 해제되어 데드락을 방지할 수 있지만, 너무 짧게 잡으면 실제 작업이 끝나기도 전에 락이 풀려 잘못된 동시 실행이 발생할 수 있고, 너무 길게 잡으면 장애 복구 시간이 늘어납니다. 따라서 단일 락을 사용할 때부터 업무 로직의 평균/최대 수행 시간을 측정해 TTL과 재시도 전략을 명확히 정해 두어야 합니다.

또한 Redis는 네트워크 지연, 재시작, 복제 지연 등의 이유로 명령이 성공했는지 확신하기 어려운 상황이 생길 수 있습니다. `set` 명령이 타임아웃으로 실패했는데 실제로는 서버에 적용되었을 수도 있고, 반대로 성공 응답을 받았지만 직후 장애로 인해 데이터를 잃을 수도 있습니다. 이런 경우를 대비해 애플리케이션 레벨에서 실패 시 재시도 간격, 최대 재시도 횟수, 동일 리소스를 잡고 있는 다른 프로세스를 어떻게 식별할지에 대한 정책을 먼저 세워두면 이후 RedLock 구현 시에도 일관성을 유지할 수 있습니다.

### 기본 구현

```python
import redis
import uuid
import time

class SimpleLock:
    def __init__(self, redis_client, resource_name, ttl=10000):
        """
        Args:
            redis_client: Redis 클라이언트
            resource_name: 락을 걸 리소스 이름
            ttl: Time To Live (밀리초)
        """
        self.redis_client = redis_client
        self.resource_name = resource_name
        self.ttl = ttl
        self.lock_value = str(uuid.uuid4())  # 고유 식별자

    def acquire(self):
        """락 획득"""
        # SET key value NX PX milliseconds
        # NX: key가 존재하지 않을 때만 설정
        # PX: 만료 시간 (밀리초)
        result = self.redis_client.set(
            self.resource_name,
            self.lock_value,
            nx=True,
            px=self.ttl
        )
        return result is not None

    def release(self):
        """락 해제 (Lua 스크립트 사용)"""
        # Lua 스크립트로 원자성 보장
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis_client.eval(lua_script, 1, self.resource_name, self.lock_value)

# 사용 예시
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
lock = SimpleLock(r, "lock:order:123", ttl=30000)

if lock.acquire():
    try:
        # 임계 영역 (Critical Section)
        print("작업 수행 중...")
        time.sleep(5)
    finally:
        lock.release()
else:
    print("락 획득 실패")
```

### 왜 Lua 스크립트를 사용하는가?

**잘못된 방법 (Race Condition 발생):**

```python
def release_wrong(self):
    # 1. 값 확인
    if self.redis_client.get(self.resource_name) == self.lock_value:
        # ⚠️ 여기서 다른 프로세스가 락을 획득할 수 있음!
        # 2. 삭제
        self.redis_client.delete(self.resource_name)
```

**문제 상황:**

```
시간 순서:
1. Client A: GET으로 값 확인 → 일치
2. Client A: 락 만료
3. Client B: 락 획득 (같은 key에 새로운 값)
4. Client A: DEL 실행 → Client B의 락을 삭제!
```

**올바른 방법 (Lua 스크립트):**

```lua
-- 확인과 삭제를 원자적으로 수행
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
```

락 해제는 간단해 보여도, 실제 서비스에서는 다른 클라이언트가 이미 새로운 락을 획득했는데 이전 소유자가 뒤늦게 삭제하는 사고가 자주 발생합니다. Lua 스크립트를 통해 **락을 획득할 때 사용한 값이 동일한 경우에만 삭제**하도록 강제하면 이러한 경쟁 조건을 예방할 수 있습니다. 이때 `lock_value`는 매번 고유해야 하며, 단일 Redis 락이라도 이 규칙을 지켜야 향후 RedLock 구성에서도 동일한 보증을 유지할 수 있습니다.

---

## RedLock 알고리즘 구현

단일 노드 락이 단순한 직렬화(Serialization) 기법이라면, RedLock은 여러 노드에 걸친 **과반수 합의(quorum)** 로 락의 소유권을 결정하는 접근 방식입니다. 목표는 일부 노드가 다운되거나 네트워크 분할이 발생하더라도 동일한 리소스에 대한 배타성(exclusivity)을 유지하는 것입니다. 공식 제안에서는 최소 5개의 독립적인 Redis 인스턴스를 권장하며, 서로 다른 가용 영역에 배치해 공통 장애 지점을 줄이는 것이 바람직합니다.

또한 RedLock에서는 “락을 가져왔다”는 사실만으로는 충분하지 않습니다. 락을 획득하는 동안 소비한 시간이 TTL에 비해 너무 길면 안전하게 작업을 끝낼 여유가 없을 수 있기 때문입니다. 따라서 정확한 시작 시각을 기록하고, 과반수 노드에서 성공한 뒤에도 남은 유효 시간을 계산한 다음 충분하지 않으면 즉시 모든 인스턴스에서 락을 해제하도록 설계합니다. 이 과정에서 시계 오차(clock drift)를 고려하지 않으면 노드 간 시간이 어긋나 잘못된 판단을 내릴 수 있습니다.

### 핵심 단계 복습

1. 현재 시간 기록
2. N개 Redis 인스턴스에 순차적으로 락 획득 시도 (짧은 타임아웃)
3. 과반수(N/2 + 1) 이상에서 획득 성공했는지 확인
4. 성공 시 락 사용, 실패 시 모든 락 해제

### 기본 구현

```python
import redis
import uuid
import time
from typing import List

class RedLock:
    # 시계 오차 허용 범위 (밀리초)
    CLOCK_DRIFT_FACTOR = 0.01

    # 각 Redis 인스턴스 락 획득 시도 시간 (밀리초)
    RETRY_DELAY = 200
    RETRY_JITTER = 50

    def __init__(self, redis_instances: List[redis.Redis], resource_name: str, ttl: int = 10000):
        """
        Args:
            redis_instances: Redis 인스턴스 리스트 (최소 3개, 권장 5개)
            resource_name: 락을 걸 리소스 이름
            ttl: Time To Live (밀리초)
        """
        self.redis_instances = redis_instances
        self.resource_name = resource_name
        self.ttl = ttl
        self.lock_value = str(uuid.uuid4())
        self.quorum = len(redis_instances) // 2 + 1  # 과반수

    def acquire(self, retry_count: int = 3, retry_delay: int = 200) -> bool:
        """
        락 획득 시도

        Args:
            retry_count: 재시도 횟수
            retry_delay: 재시도 간격 (밀리초)

        Returns:
            bool: 락 획득 성공 여부
        """
        for _ in range(retry_count):
            if self._try_acquire():
                return True

            # 랜덤 딜레이 (Thundering Herd 방지)
            import random
            delay = retry_delay + random.randint(0, self.RETRY_JITTER)
            time.sleep(delay / 1000.0)

        return False

    def _try_acquire(self) -> bool:
        """단일 락 획득 시도"""
        # 1. 시작 시간 기록
        start_time = int(time.time() * 1000)  # 밀리초

        # 2. 모든 Redis 인스턴스에 락 획득 시도
        locked_instances = 0

        for redis_instance in self.redis_instances:
            if self._lock_instance(redis_instance):
                locked_instances += 1

        # 3. 경과 시간 계산
        elapsed_time = int(time.time() * 1000) - start_time

        # 4. 유효 시간 계산 (시계 오차 고려)
        validity_time = self.ttl - elapsed_time - int(self.ttl * self.CLOCK_DRIFT_FACTOR)

        # 5. 과반수 획득 & 유효 시간 체크
        if locked_instances >= self.quorum and validity_time > 0:
            self.validity_time = validity_time
            return True
        else:
            # 실패 시 모든 락 해제
            self.release()
            return False

    def _lock_instance(self, redis_instance: redis.Redis, timeout: int = 50) -> bool:
        """
        단일 Redis 인스턴스에 락 획득 시도

        Args:
            redis_instance: Redis 인스턴스
            timeout: 타임아웃 (밀리초)
        """
        try:
            # 짧은 타임아웃 설정
            redis_instance.connection_pool.connection_kwargs['socket_timeout'] = timeout / 1000.0

            result = redis_instance.set(
                self.resource_name,
                self.lock_value,
                nx=True,
                px=self.ttl
            )
            return result is not None
        except (redis.RedisError, TimeoutError):
            return False

    def release(self):
        """모든 Redis 인스턴스에서 락 해제"""
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        for redis_instance in self.redis_instances:
            try:
                redis_instance.eval(lua_script, 1, self.resource_name, self.lock_value)
            except redis.RedisError:
                # 실패해도 계속 진행 (다른 인스턴스도 해제 시도)
                pass
```

### 성공 조건과 실패 처리 전략

위 구현에서 `validity_time`을 계산하는 이유는 락을 획득하는 데 걸린 시간과 시계 오차를 고려했을 때 실제로 안전하게 사용할 수 있는 시간이 얼마나 남았는지 확인하기 위함입니다. 예를 들어 TTL이 10초인데 네트워크 지연 탓에 락 획득에 8초가 소요되었다면, 남은 2초 동안 임계 구역을 수행하기 어렵다고 판단해 즉시 모든 락을 해제하고 재시도하는 편이 낫습니다. 반대로 남은 시간이 충분하다면, 그 순간부터 유효 시간이 만료되기 전에 작업을 마쳐야 합니다.

과반수 이상의 노드에서 락에 성공했더라도, 이후 작업 도중 일부 노드가 장애로 응답하지 못할 수 있습니다. `release` 단계에서는 가능한 한 모든 인스턴스에 해제 요청을 보내되, 특정 인스턴스가 실패하더라도 나머지 해제를 계속 진행합니다. 만약 장애가 길어져 특정 노드의 락이 계속 남아 있다면, TTL 만료를 기다리거나 운영자가 수동으로 제거해야 합니다. 이 과정에서 **노드 간 시계 동기화가 되어 있지 않다면 TTL 만료 시점 예측이 어려우므로 NTP 등으로 서버 시간을 정기적으로 맞춰 두는 것**이 필수입니다.

### 사용 예시

```python
# 5개의 독립적인 Redis 인스턴스 설정
redis_instances = [
    redis.Redis(host='redis1.example.com', port=6379, decode_responses=True),
    redis.Redis(host='redis2.example.com', port=6379, decode_responses=True),
    redis.Redis(host='redis3.example.com', port=6379, decode_responses=True),
    redis.Redis(host='redis4.example.com', port=6379, decode_responses=True),
    redis.Redis(host='redis5.example.com', port=6379, decode_responses=True),
]

# RedLock 사용
lock = RedLock(redis_instances, "lock:order:123", ttl=30000)

if lock.acquire():
    try:
        print(f"락 획득 성공! 유효 시간: {lock.validity_time}ms")
        # 임계 영역
        process_order(123)
    finally:
        lock.release()
        print("락 해제 완료")
else:
    print("락 획득 실패 - 다른 프로세스가 사용 중")
```

실무에서는 TTL을 **작업 예상 시간 + 안전 여유 시간**으로 산정한 뒤, 예외적으로 시간이 더 필요한 경우 락 연장(renewal) 혹은 임시 해제 전략을 별도로 마련합니다. 또한 RedLock은 네트워크 품질에 민감하므로, 재시도 간격과 최대 재시도 횟수를 실제 트래픽 패턴에 맞춰 조정하고, 실패 횟수나 지연 시간을 모니터링 시스템에 기록해 이상 징후를 조기에 감지하는 것이 좋습니다.

---

## 실전 구현

서비스 코드에 RedLock을 녹여 넣을 때는 개발자가 반복적으로 작성해야 하는 보일러플레이트를 최소화하고, 예외 상황이 명확히 드러나도록 API를 설계해야 합니다. `with` 문이나 데코레이터는 락 획득과 해제 로직을 깔끔하게 감싸 실수를 줄이는 반면, 세밀한 제어(예: 재시도 간격 조절, 모니터링 훅 삽입)가 어려울 수 있습니다. 따라서 조직 내에서는 사용 패턴에 따라 고수준/저수준 인터페이스를 구분해 제공하는 방향이 권장됩니다.

### Context Manager 패턴

Python의 `with` 문을 사용할 수 있도록 개선:

```python
class RedLock:
    # ... (기존 코드) ...

    def __enter__(self):
        """Context Manager 진입"""
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire lock: {self.resource_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료"""
        self.release()
        return False  # 예외를 재발생

# 사용 예시
try:
    with RedLock(redis_instances, "lock:order:123", ttl=30000):
        print("락 획득! 작업 수행 중...")
        process_order(123)
except RuntimeError as e:
    print(f"락 획득 실패: {e}")
```

### 데코레이터 패턴

함수에 쉽게 락을 적용:

```python
from functools import wraps

def with_redlock(redis_instances, resource_name, ttl=10000):
    """RedLock 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lock = RedLock(redis_instances, resource_name, ttl)
            if lock.acquire():
                try:
                    return func(*args, **kwargs)
                finally:
                    lock.release()
            else:
                raise RuntimeError(f"Failed to acquire lock: {resource_name}")
        return wrapper
    return decorator

# 사용 예시
@with_redlock(redis_instances, "lock:daily_report", ttl=60000)
def generate_daily_report():
    print("일일 보고서 생성 중...")
    # 보고서 생성 로직
    return "report.pdf"

# 호출
try:
    report = generate_daily_report()
    print(f"보고서 생성 완료: {report}")
except RuntimeError as e:
    print(f"다른 서버에서 이미 생성 중: {e}")
```

데코레이터 패턴을 사용할 때는 리소스 키가 고정인지, 함수 인자에 따라 달라져야 하는지를 먼저 정의해야 합니다. 주문 ID와 같이 매번 다른 리소스를 보호해야 한다면 함수 인자를 조합해 키를 만들어야 하며, 실패 시 예외를 그대로 전달해 상위 레벨에서 장애 여부를 판단할 수 있게끔 설계하는 것이 중요합니다. 또한 데코레이터 내부에서 재시도 정책을 통일해 두면 팀 전체가 일관된 방식으로 락을 사용할 수 있습니다.

### 비동기 구현 (asyncio)

```python
import asyncio
import aioredis
from typing import List

class AsyncRedLock:
    def __init__(self, redis_instances: List[aioredis.Redis], resource_name: str, ttl: int = 10000):
        self.redis_instances = redis_instances
        self.resource_name = resource_name
        self.ttl = ttl
        self.lock_value = str(uuid.uuid4())
        self.quorum = len(redis_instances) // 2 + 1

    async def acquire(self, retry_count: int = 3, retry_delay: int = 200) -> bool:
        """비동기 락 획득"""
        for _ in range(retry_count):
            if await self._try_acquire():
                return True

            import random
            delay = retry_delay + random.randint(0, 50)
            await asyncio.sleep(delay / 1000.0)

        return False

    async def _try_acquire(self) -> bool:
        """단일 락 획득 시도"""
        start_time = int(time.time() * 1000)

        # 병렬로 모든 인스턴스에 시도
        tasks = [self._lock_instance(r) for r in self.redis_instances]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        locked_instances = sum(1 for r in results if r is True)
        elapsed_time = int(time.time() * 1000) - start_time
        validity_time = self.ttl - elapsed_time - int(self.ttl * 0.01)

        if locked_instances >= self.quorum and validity_time > 0:
            self.validity_time = validity_time
            return True
        else:
            await self.release()
            return False

    async def _lock_instance(self, redis_instance: aioredis.Redis) -> bool:
        """단일 인스턴스 락 획득"""
        try:
            result = await asyncio.wait_for(
                redis_instance.set(
                    self.resource_name,
                    self.lock_value,
                    nx=True,
                    px=self.ttl
                ),
                timeout=0.05  # 50ms
            )
            return result is not None
        except (aioredis.RedisError, asyncio.TimeoutError):
            return False

    async def release(self):
        """락 해제"""
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        tasks = []
        for redis_instance in self.redis_instances:
            task = redis_instance.eval(lua_script, 1, self.resource_name, self.lock_value)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

# 사용 예시
async def main():
    redis_instances = [
        aioredis.from_url('redis://redis1.example.com:6379'),
        aioredis.from_url('redis://redis2.example.com:6379'),
        aioredis.from_url('redis://redis3.example.com:6379'),
    ]

    lock = AsyncRedLock(redis_instances, "lock:order:123", ttl=30000)

    if await lock.acquire():
        try:
            print("락 획득 성공!")
            await process_order_async(123)
        finally:
            await lock.release()
    else:
        print("락 획득 실패")

# 실행
asyncio.run(main())
```

비동기 환경에서는 동일한 이벤트 루프에서 수십 개의 코루틴이 동시에 락을 요청할 수 있으므로, 개별 Redis 인스턴스에 대한 타임아웃을 명시적으로 설정해 지연을 빠르게 감지하는 것이 특히 중요합니다. `asyncio.gather(..., return_exceptions=True)`를 사용하면 일부 인스턴스에서 발생한 예외를 한 번에 모아볼 수 있고, 실패한 노드가 있더라도 나머지 노드에서의 결과를 기반으로 판단을 내릴 수 있습니다. 락을 해제할 때도 비동기적으로 호출해 특정 노드의 장애가 전체 해제 절차를 가로막지 않게 만드는 것이 좋습니다.

---

## 실전 라이브러리

기존 오픈 소스 라이브러리를 활용하면 락 구현에 드는 시간을 줄일 수 있지만, 각 라이브러리가 제공하는 보증 범위와 실패 처리 방식이 다릅니다. 따라서 어떤 라이브러리를 선택하든 **락이 어디까지 안전한지(단일 인스턴스인지, RedLock을 지원하는지), 재시도 정책이 어떻게 동작하는지, 예외를 어떻게 전달하는지**를 문서와 소스 코드로 확인한 뒤 도입해야 합니다.

### python-redis-lock

```bash
pip install python-redis-lock
```

```python
import redis
import redis_lock

# Redis 연결
conn = redis.Redis(host='localhost', port=6379)

# 간단한 사용
with redis_lock.Lock(conn, "lock:my_resource", expire=60):
    print("임계 영역")
    # 작업 수행
```

`python-redis-lock`은 단일 Redis 기반으로 동작하지만, 블로킹 모드/논블로킹 모드를 선택하거나 `auto_renewal` 기능으로 TTL 연장을 수행하는 등 실무에서 바로 사용할 만한 기능을 갖추고 있습니다. 다만 RedLock 알고리즘을 그대로 구현한 것은 아니므로, 고가용성을 요구한다면 여러 Redis 인스턴스를 직접 관리하는 방식이나 다른 라이브러리를 검토해야 합니다.

### pottery (RedLock 지원)

```bash
pip install pottery
```

```python
from redis import Redis
from pottery import Redlock

# Redis 인스턴스들
masters = {
    Redis(host='redis1.example.com', port=6379),
    Redis(host='redis2.example.com', port=6379),
    Redis(host='redis3.example.com', port=6379),
}

# RedLock 사용
with Redlock(key='lock:order:123', masters=masters, auto_release_time=30):
    print("작업 수행 중...")
    process_order(123)
```

`pottery`는 Redis 클러스터에 대한 연결 풀을 내부에서 관리하며, 자동으로 과반수 원칙을 적용해 RedLock을 제공합니다. 설정이 간편한 대신, 네트워크 타임아웃이나 재시도 정책을 세밀하게 제어하려면 추가 설정이 필요하므로 서비스 특성에 맞게 파라미터를 조정해야 합니다. 또한 내부 구현이 일정 주기로 락을 갱신하거나, 예외를 던지는 방식이 애플리케이션의 기대와 다를 수 있으므로 도입 전에 반드시 문서를 확인하고 테스트를 거치는 것이 좋습니다.

---

## 테스트

### 단위 테스트

```python
import pytest
import fakeredis
from redlock import RedLock

class TestRedLock:
    @pytest.fixture
    def redis_instances(self):
        """테스트용 Fake Redis 인스턴스"""
        return [fakeredis.FakeRedis() for _ in range(5)]

    def test_acquire_lock_success(self, redis_instances):
        """락 획득 성공 테스트"""
        lock = RedLock(redis_instances, "test:lock", ttl=10000)
        assert lock.acquire() is True
        lock.release()

    def test_acquire_lock_failure(self, redis_instances):
        """락 획득 실패 테스트 (이미 락이 존재)"""
        lock1 = RedLock(redis_instances, "test:lock", ttl=10000)
        lock2 = RedLock(redis_instances, "test:lock", ttl=10000)

        assert lock1.acquire() is True
        assert lock2.acquire() is False

        lock1.release()

    def test_lock_auto_expiry(self, redis_instances):
        """락 자동 만료 테스트"""
        lock1 = RedLock(redis_instances, "test:lock", ttl=1000)  # 1초
        lock2 = RedLock(redis_instances, "test:lock", ttl=10000)

        assert lock1.acquire() is True

        # 1초 대기
        time.sleep(1.1)

        # 만료 후 다른 클라이언트가 획득 가능
        assert lock2.acquire() is True
        lock2.release()

    def test_lock_quorum(self, redis_instances):
        """과반수 미달 시 실패 테스트"""
        # 3개 인스턴스만 사용 (5개 중)
        partial_instances = redis_instances[:3]

        # 2개에 미리 락 설정
        for instance in partial_instances[:2]:
            instance.set("test:lock", "other_value", px=10000)

        lock = RedLock(partial_instances, "test:lock", ttl=10000)
        # 1개만 획득 가능 → 과반수(2) 미달 → 실패
        assert lock.acquire() is False
```

단위 테스트에서는 성공/실패 케이스뿐 아니라 TTL 만료, 과반수 미달과 같은 에지 케이스도 반드시 검증해야 합니다. 특히 시계 오차나 네트워크 지연은 테스트 환경에서 재현하기 어렵기 때문에, `time.sleep`을 이용해 TTL을 넘겨보거나, 특정 인스턴스에 미리 값을 설정해 두고 쿼럼이 깨지는 상황을 만들어 봄으로써 구현이 기대대로 동작하는지 확인할 수 있습니다.

### 통합 테스트 (멀티프로세싱)

```python
from multiprocessing import Process
import redis
import time

def worker(worker_id, redis_instances, resource_name):
    """워커 프로세스"""
    lock = RedLock(redis_instances, resource_name, ttl=5000)

    if lock.acquire():
        print(f"Worker {worker_id}: 락 획득!")
        time.sleep(2)  # 작업 시뮬레이션
        lock.release()
        print(f"Worker {worker_id}: 락 해제")
    else:
        print(f"Worker {worker_id}: 락 획득 실패")

def test_concurrent_access():
    """동시 접근 테스트"""
    redis_instances = [
        redis.Redis(host='localhost', port=6379),
        redis.Redis(host='localhost', port=6380),
        redis.Redis(host='localhost', port=6381),
    ]

    # 5개 워커 동시 실행
    processes = []
    for i in range(5):
        p = Process(target=worker, args=(i, redis_instances, "test:concurrent"))
        processes.append(p)
        p.start()

    # 모든 프로세스 종료 대기
    for p in processes:
        p.join()

if __name__ == '__main__':
    test_concurrent_access()
```

예상 출력:
```
Worker 0: 락 획득!
Worker 1: 락 획득 실패
Worker 2: 락 획득 실패
Worker 3: 락 획득 실패
Worker 4: 락 획득 실패
Worker 0: 락 해제
```

이러한 통합 테스트는 단순히 성공 메시지를 보는 것을 넘어, 실제로는 얼마나 자주 실패하거나 지연이 발생하는지 로그와 메트릭을 통해 파악하는 계기가 됩니다. 운영 환경과 유사하게 여러 포트에 Redis를 띄우고 네트워크 지연을 인위적으로 추가하면, 재시도 정책이나 TTL을 조정해야 하는 상황을 미리 발견할 수 있습니다. 테스트를 자동화해 CI 파이프라인에 포함시키면 변경 사항이 락의 일관성을 해치지 않았는지 빠르게 확인할 수 있습니다.

### 성능 테스트

```python
import time
import redis

def benchmark_lock_performance():
    """락 성능 벤치마크"""
    redis_instances = [redis.Redis(host='localhost', port=6379) for _ in range(5)]

    iterations = 1000
    start_time = time.time()

    for i in range(iterations):
        lock = RedLock(redis_instances, f"bench:lock:{i}", ttl=5000)
        if lock.acquire():
            lock.release()

    elapsed = time.time() - start_time
    print(f"총 시간: {elapsed:.2f}초")
    print(f"평균 락 획득 시간: {elapsed/iterations*1000:.2f}ms")
    print(f"처리량: {iterations/elapsed:.2f} locks/sec")

benchmark_lock_performance()
```

벤치마크 결과를 통해 평균 지연과 초당 처리량을 추적하면, Redis 인스턴스 수나 재시도 간격을 조정해야 하는 시점을 파악할 수 있습니다. RedLock은 노드 수가 많을수록 락 획득 비용이 커지므로, 실제 요구사항에 맞는 최소 인스턴스 수를 선택하고, 모니터링 시스템에 락 획득/해제 지표를 기록해 이상 징후를 조기에 감지하도록 구성하는 것이 좋습니다.

---

## 다음 단계

- `03_patterns.md`: 실무 사용 패턴 및 모범 사례
- `04_advanced.md`: 최적화, 트러블슈팅, 모니터링
