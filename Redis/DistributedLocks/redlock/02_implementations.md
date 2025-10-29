# RedLock 구현

## 목차

1. [단일 Redis 락 (Simple Lock)](#단일-redis-락)
2. [RedLock 알고리즘 구현](#redlock-알고리즘-구현)
3. [실전 구현 with redis-py](#실전-구현)
4. [테스트](#테스트)

---

## 단일 Redis 락

RedLock을 이해하기 위해 먼저 간단한 단일 Redis 락부터 살펴봅시다.

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

---

## RedLock 알고리즘 구현

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

---

## 실전 구현

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

---

## 실전 라이브러리

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

---

## 다음 단계

- `03_patterns.md`: 실무 사용 패턴 및 모범 사례
- `04_advanced.md`: 최적화, 트러블슈팅, 모니터링
