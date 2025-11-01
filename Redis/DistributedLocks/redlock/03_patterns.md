# RedLock 실무 패턴 및 모범 사례

## 목차

1. [실무 사용 패턴](#실무-사용-패턴)
2. [모범 사례 (Best Practices)](#모범-사례)
3. [안티 패턴](#안티-패턴)
4. [성능 최적화](#성능-최적화)
5. [실제 사례 코드](#실제-사례-코드)
6. [트러블슈팅 가이드](#트러블슈팅-가이드)

---

## 실무 사용 패턴

### 1. 크론잡/스케줄러 중복 실행 방지

여러 서버에서 동일한 스케줄러가 실행될 때, 한 서버만 작업을 수행하도록 보장합니다.

```python
import schedule
import time
from redlock import RedLock

def daily_report_with_lock(redis_instances):
    """일일 보고서 생성 (중복 실행 방지)"""
    lock_name = f"lock:daily_report:{datetime.now().strftime('%Y%m%d')}"
    lock = RedLock(redis_instances, lock_name, ttl=300000)  # 5분

    if lock.acquire():
        try:
            print(f"[{socket.gethostname()}] 보고서 생성 시작")
            generate_report()
            send_email_report()
            print(f"[{socket.gethostname()}] 보고서 생성 완료")
        finally:
            lock.release()
    else:
        print(f"[{socket.gethostname()}] 다른 서버에서 이미 실행 중")

# 모든 서버에서 동일한 스케줄 설정
schedule.every().day.at("09:00").do(daily_report_with_lock, redis_instances)
```

### 2. 캐시 스탬피드(Cache Stampede) 방지

캐시 만료 시 여러 요청이 동시에 DB를 조회하는 것을 방지합니다.

```python
import json
import hashlib

class CacheWithLock:
    def __init__(self, redis_instances, cache_redis):
        self.redis_instances = redis_instances
        self.cache = cache_redis

    def get_or_compute(self, key, compute_func, ttl=3600):
        """캐시에서 가져오거나 계산 후 저장"""
        # 1. 캐시 확인
        cached = self.cache.get(key)
        if cached:
            return json.loads(cached)

        # 2. 캐시 미스 - 락 획득 시도
        lock_key = f"lock:cache:{key}"
        lock = RedLock(self.redis_instances, lock_key, ttl=30000)  # 30초

        if lock.acquire():
            try:
                # 3. 다시 캐시 확인 (다른 프로세스가 방금 설정했을 수 있음)
                cached = self.cache.get(key)
                if cached:
                    return json.loads(cached)

                # 4. 실제 계산 수행
                result = compute_func()

                # 5. 캐시에 저장
                self.cache.setex(key, ttl, json.dumps(result))
                return result
            finally:
                lock.release()
        else:
            # 락 획득 실패 - 잠시 대기 후 캐시 재확인
            time.sleep(0.1)
            cached = self.cache.get(key)
            if cached:
                return json.loads(cached)

            # 여전히 없다면 직접 계산 (fallback)
            return compute_func()

# 사용 예시
cache = CacheWithLock(redis_instances, cache_redis)

def expensive_calculation():
    """비용이 많이 드는 계산"""
    time.sleep(5)  # 시뮬레이션
    return {"result": "complex data", "timestamp": time.time()}

# 여러 요청이 동시에 와도 한 번만 계산됨
result = cache.get_or_compute("expensive_key", expensive_calculation, ttl=3600)
```

### 3. 분산 작업 큐 처리

여러 워커가 같은 작업을 중복 처리하지 않도록 합니다.

```python
class DistributedTaskQueue:
    def __init__(self, redis_instances, queue_redis):
        self.redis_instances = redis_instances
        self.queue = queue_redis

    def enqueue(self, task_id, task_data):
        """작업 추가"""
        self.queue.lpush("task_queue", json.dumps({
            "id": task_id,
            "data": task_data,
            "status": "pending"
        }))

    def process_next(self, worker_id):
        """다음 작업 처리 (중복 방지)"""
        while True:
            # 1. 큐에서 작업 가져오기
            task_json = self.queue.rpop("task_queue")
            if not task_json:
                return None

            task = json.loads(task_json)
            task_id = task["id"]

            # 2. 작업별 락 획득 시도
            lock = RedLock(
                self.redis_instances,
                f"lock:task:{task_id}",
                ttl=600000  # 10분
            )

            if lock.acquire():
                try:
                    # 3. 작업 상태 확인 (이미 처리됐을 수 있음)
                    if self.queue.get(f"task_completed:{task_id}"):
                        continue

                    # 4. 작업 처리
                    print(f"Worker {worker_id} processing task {task_id}")
                    result = self.process_task(task["data"])

                    # 5. 완료 표시
                    self.queue.setex(
                        f"task_completed:{task_id}",
                        86400,  # 24시간
                        json.dumps(result)
                    )

                    return result
                finally:
                    lock.release()
            else:
                # 다른 워커가 처리 중 - 큐에 다시 넣고 다음 작업으로
                self.queue.lpush("task_queue", task_json)
                continue

    def process_task(self, task_data):
        """실제 작업 처리 로직"""
        # 작업 처리...
        return {"status": "completed", "result": "..."}
```

### 4. 재고/결제 시스템의 동시성 제어

```python
class InventoryManager:
    def __init__(self, redis_instances, db):
        self.redis_instances = redis_instances
        self.db = db

    def reserve_stock(self, product_id, quantity, order_id):
        """재고 예약 (동시성 제어)"""
        lock = RedLock(
            self.redis_instances,
            f"lock:inventory:{product_id}",
            ttl=5000  # 5초
        )

        max_retries = 3
        for attempt in range(max_retries):
            if lock.acquire():
                try:
                    # 1. 현재 재고 확인
                    current_stock = self.db.get_stock(product_id)

                    if current_stock < quantity:
                        return {
                            "success": False,
                            "reason": "insufficient_stock",
                            "available": current_stock
                        }

                    # 2. 재고 차감
                    self.db.update_stock(product_id, current_stock - quantity)

                    # 3. 예약 기록
                    self.db.create_reservation(order_id, product_id, quantity)

                    return {
                        "success": True,
                        "reservation_id": order_id,
                        "remaining_stock": current_stock - quantity
                    }
                finally:
                    lock.release()
            else:
                # 재시도 전 대기 (지수 백오프)
                wait_time = (2 ** attempt) * 0.1  # 0.1s, 0.2s, 0.4s
                time.sleep(wait_time)

        return {
            "success": False,
            "reason": "lock_timeout"
        }
```

---

## 모범 사례

### 1. 적절한 TTL 설정

```python
def calculate_ttl(expected_duration, safety_factor=2.0):
    """
    TTL 계산 함수

    Args:
        expected_duration: 예상 작업 시간 (초)
        safety_factor: 안전 계수 (기본 2.0)
    """
    # 기본 공식: 예상 시간 * 안전 계수 + 네트워크 지연
    base_ttl = expected_duration * safety_factor
    network_overhead = 1  # 1초

    # 최소/최대값 제한
    min_ttl = 5  # 최소 5초
    max_ttl = 300  # 최대 5분

    return max(min_ttl, min(base_ttl + network_overhead, max_ttl))

# 사용 예시
ttl_quick_task = calculate_ttl(2)  # 2초 작업 → 5초 TTL (최소값)
ttl_medium_task = calculate_ttl(30)  # 30초 작업 → 61초 TTL
ttl_long_task = calculate_ttl(180)  # 3분 작업 → 300초 TTL (최대값)
```

### 2. 재시도 전략

```python
import random
import time

class RetryStrategy:
    @staticmethod
    def exponential_backoff(attempt, base_delay=0.1, max_delay=10):
        """지수 백오프 + 지터"""
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, delay * 0.3)  # 30% 지터
        return delay + jitter

    @staticmethod
    def linear_backoff(attempt, increment=0.5, max_delay=10):
        """선형 백오프"""
        delay = min(increment * attempt, max_delay)
        jitter = random.uniform(0, 0.1)  # 100ms 지터
        return delay + jitter

def acquire_with_retry(lock, strategy="exponential", max_attempts=5):
    """재시도 전략을 적용한 락 획득"""
    for attempt in range(max_attempts):
        if lock.acquire():
            return True

        if attempt < max_attempts - 1:  # 마지막 시도가 아니면
            if strategy == "exponential":
                delay = RetryStrategy.exponential_backoff(attempt)
            else:
                delay = RetryStrategy.linear_backoff(attempt)

            print(f"Attempt {attempt + 1} failed, waiting {delay:.2f}s")
            time.sleep(delay)

    return False
```

### 3. 데드락 방지

```python
class LockManager:
    """락 순서를 보장하여 데드락 방지"""

    def __init__(self, redis_instances):
        self.redis_instances = redis_instances
        self.held_locks = []

    def acquire_multiple(self, resource_names, ttl=10000):
        """여러 락을 정렬된 순서로 획득"""
        # 1. 락 이름을 정렬 (일관된 순서 보장)
        sorted_names = sorted(resource_names)

        acquired_locks = []
        try:
            for name in sorted_names:
                lock = RedLock(self.redis_instances, name, ttl)
                if not lock.acquire():
                    # 실패 시 이미 획득한 락들 해제
                    for acquired in acquired_locks:
                        acquired.release()
                    return None
                acquired_locks.append(lock)

            self.held_locks = acquired_locks
            return acquired_locks
        except Exception as e:
            # 예외 발생 시 모든 락 해제
            for lock in acquired_locks:
                try:
                    lock.release()
                except:
                    pass
            raise e

    def release_all(self):
        """모든 락 해제"""
        for lock in self.held_locks:
            try:
                lock.release()
            except:
                pass
        self.held_locks = []
```

### 4. 모니터링 및 메트릭

```python
import time
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class LockMetrics:
    """락 메트릭"""
    acquisition_count: int = 0
    acquisition_failures: int = 0
    total_wait_time: float = 0
    total_hold_time: float = 0
    timeout_count: int = 0

class MonitoredRedLock(RedLock):
    metrics = defaultdict(LockMetrics)

    def acquire(self, retry_count=3, retry_delay=200):
        start_time = time.time()
        resource = self.resource_name

        result = super().acquire(retry_count, retry_delay)

        wait_time = time.time() - start_time
        self.metrics[resource].total_wait_time += wait_time

        if result:
            self.metrics[resource].acquisition_count += 1
            self.acquisition_time = time.time()
        else:
            self.metrics[resource].acquisition_failures += 1

        return result

    def release(self):
        if hasattr(self, 'acquisition_time'):
            hold_time = time.time() - self.acquisition_time
            self.metrics[self.resource_name].total_hold_time += hold_time

        super().release()

    @classmethod
    def get_metrics(cls, resource_name=None):
        """메트릭 조회"""
        if resource_name:
            return cls.metrics[resource_name]
        return dict(cls.metrics)

    @classmethod
    def report_metrics(cls):
        """메트릭 리포트"""
        print("\n=== Lock Metrics Report ===")
        for resource, metrics in cls.metrics.items():
            if metrics.acquisition_count > 0:
                avg_wait = metrics.total_wait_time / (metrics.acquisition_count + metrics.acquisition_failures)
                avg_hold = metrics.total_hold_time / metrics.acquisition_count
                success_rate = metrics.acquisition_count / (metrics.acquisition_count + metrics.acquisition_failures) * 100

                print(f"\nResource: {resource}")
                print(f"  Success Rate: {success_rate:.1f}%")
                print(f"  Avg Wait Time: {avg_wait:.3f}s")
                print(f"  Avg Hold Time: {avg_hold:.3f}s")
                print(f"  Total Acquisitions: {metrics.acquisition_count}")
                print(f"  Total Failures: {metrics.acquisition_failures}")
```

---

## 안티 패턴

### 1. ❌ 락 안에서 외부 API 호출

```python
# 나쁜 예
def bad_pattern():
    lock = RedLock(redis_instances, "lock:api", ttl=10000)
    if lock.acquire():
        try:
            # ❌ 외부 API는 언제든 지연될 수 있음
            response = requests.get("https://slow-api.example.com/data", timeout=30)
            process_data(response.json())
        finally:
            lock.release()

# 좋은 예
def good_pattern():
    # ✓ 먼저 데이터를 가져옴
    response = requests.get("https://slow-api.example.com/data", timeout=30)
    data = response.json()

    # ✓ 그다음 락을 획득하고 빠르게 처리
    lock = RedLock(redis_instances, "lock:process", ttl=5000)
    if lock.acquire():
        try:
            process_data(data)  # 빠른 로컬 처리만
        finally:
            lock.release()
```

### 2. ❌ 너무 긴 락 유지

```python
# 나쁜 예
def bad_long_lock():
    lock = RedLock(redis_instances, "lock:batch", ttl=3600000)  # 1시간!
    if lock.acquire():
        try:
            for item in huge_dataset:  # 수백만 개
                process_item(item)  # 각각 1초씩 걸림
        finally:
            lock.release()

# 좋은 예 - 배치를 작은 청크로 분할
def good_chunked_processing():
    CHUNK_SIZE = 100

    for chunk_id in range(0, len(huge_dataset), CHUNK_SIZE):
        chunk = huge_dataset[chunk_id:chunk_id + CHUNK_SIZE]

        lock = RedLock(redis_instances, f"lock:batch:{chunk_id}", ttl=10000)
        if lock.acquire():
            try:
                for item in chunk:
                    process_item(item)
            finally:
                lock.release()

        # 다른 프로세스가 작업할 기회를 줌
        time.sleep(0.1)
```

### 3. ❌ 락 없는 무조건적 fallback

```python
# 나쁜 예
def bad_fallback():
    lock = RedLock(redis_instances, "lock:critical", ttl=5000)
    if lock.acquire():
        try:
            update_critical_data()
        finally:
            lock.release()
    else:
        # ❌ 락 실패 시 그냥 진행 - 데이터 불일치 위험!
        update_critical_data()

# 좋은 예 - 안전한 fallback
def good_fallback():
    lock = RedLock(redis_instances, "lock:update", ttl=5000)

    for attempt in range(3):
        if lock.acquire():
            try:
                return update_critical_data()
            finally:
                lock.release()

        time.sleep(0.5 * (attempt + 1))

    # ✓ 실패 시 명확한 에러 처리
    raise LockAcquisitionError("Failed to acquire lock after 3 attempts")
```

### 4. ❌ 락 릴리즈 누락

```python
# 나쁜 예
def bad_no_release():
    lock = RedLock(redis_instances, "lock:resource", ttl=30000)
    if lock.acquire():
        result = process_data()
        if result.success:
            # ❌ 성공 케이스에서만 release - 실패 시 락이 남음!
            lock.release()
            return result
        else:
            raise ProcessingError()  # 락이 해제되지 않음!

# 좋은 예 - try/finally 사용
def good_with_finally():
    lock = RedLock(redis_instances, "lock:resource", ttl=30000)
    if lock.acquire():
        try:
            result = process_data()
            if not result.success:
                raise ProcessingError()
            return result
        finally:
            # ✓ 예외 발생 여부와 관계없이 항상 해제
            lock.release()

# 더 좋은 예 - Context Manager
def best_with_context():
    with RedLock(redis_instances, "lock:resource", ttl=30000):
        result = process_data()
        if not result.success:
            raise ProcessingError()
        return result
```

---

## 성능 최적화

### 1. 락 경합 최소화

```python
class ShardedLock:
    """락을 여러 개로 분할하여 경합 감소"""

    def __init__(self, redis_instances, base_name, shard_count=10):
        self.redis_instances = redis_instances
        self.base_name = base_name
        self.shard_count = shard_count

    def get_shard_id(self, key):
        """키를 기반으로 샤드 ID 계산"""
        return hash(key) % self.shard_count

    def acquire_for_key(self, key, ttl=10000):
        """특정 키에 대한 락 획득"""
        shard_id = self.get_shard_id(key)
        lock_name = f"{self.base_name}:shard:{shard_id}"

        return RedLock(self.redis_instances, lock_name, ttl)

# 사용 예시
sharded_lock = ShardedLock(redis_instances, "lock:user_update", shard_count=10)

# user_id에 따라 다른 샤드 사용 - 경합 1/10로 감소
user_id = "user_12345"
lock = sharded_lock.acquire_for_key(user_id)
if lock.acquire():
    try:
        update_user_data(user_id)
    finally:
        lock.release()
```

### 2. Read/Write 락 패턴

```python
class ReadWriteLock:
    """읽기는 동시에, 쓰기는 독점적으로"""

    def __init__(self, redis_instances, resource_name):
        self.redis_instances = redis_instances
        self.resource_name = resource_name
        self.redis = redis_instances[0]  # 카운터용

    def acquire_read(self, ttl=10000):
        """읽기 락 획득"""
        # 쓰기 락이 없는지 확인
        write_lock = RedLock(
            self.redis_instances,
            f"{self.resource_name}:write",
            ttl=100  # 짧은 체크용
        )

        if write_lock.acquire():
            # 쓰기 락이 없음 - 즉시 해제하고 읽기 카운터 증가
            write_lock.release()
            self.redis.incr(f"{self.resource_name}:readers")
            return True

        return False

    def release_read(self):
        """읽기 락 해제"""
        self.redis.decr(f"{self.resource_name}:readers")

    def acquire_write(self, ttl=10000):
        """쓰기 락 획득"""
        write_lock = RedLock(
            self.redis_instances,
            f"{self.resource_name}:write",
            ttl=ttl
        )

        if not write_lock.acquire():
            return None

        # 모든 읽기가 끝날 때까지 대기
        max_wait = 5  # 5초
        start = time.time()

        while time.time() - start < max_wait:
            readers = int(self.redis.get(f"{self.resource_name}:readers") or 0)
            if readers == 0:
                return write_lock
            time.sleep(0.1)

        # 타임아웃 - 쓰기 락 해제
        write_lock.release()
        return None
```

### 3. 락 대기 시간 최적화

```python
class OptimizedLock:
    """대기 시간 최적화된 락"""

    def __init__(self, redis_instances, resource_name, ttl=10000):
        self.lock = RedLock(redis_instances, resource_name, ttl)
        self.resource_name = resource_name
        self.redis = redis_instances[0]

    def acquire_with_queue(self, max_wait=30):
        """큐 기반 공정한 락 획득"""
        ticket = str(uuid.uuid4())
        queue_key = f"queue:{self.resource_name}"

        # 1. 큐에 티켓 추가
        position = self.redis.lpush(queue_key, ticket)

        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 2. 내 차례인지 확인
            first_ticket = self.redis.lindex(queue_key, -1)

            if first_ticket == ticket:
                # 3. 내 차례 - 락 획득 시도
                if self.lock.acquire():
                    # 큐에서 제거
                    self.redis.rpop(queue_key)
                    return True

            # 4. 예상 대기 시간 계산
            position = self.redis.lpos(queue_key, ticket)
            if position:
                estimated_wait = position * 0.5  # 각 작업당 평균 0.5초 가정
                print(f"Queue position: {position}, estimated wait: {estimated_wait:.1f}s")

            time.sleep(0.2)

        # 타임아웃 - 큐에서 제거
        self.redis.lrem(queue_key, 1, ticket)
        return False
```

---

## 실제 사례 코드

### 1. 주문 처리 시스템

```python
from enum import Enum
from datetime import datetime
import logging

class OrderStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class OrderProcessor:
    def __init__(self, redis_instances, db, payment_gateway):
        self.redis_instances = redis_instances
        self.db = db
        self.payment = payment_gateway
        self.logger = logging.getLogger(__name__)

    def process_order(self, order_id):
        """주문 처리 - 중복 처리 방지"""

        # 1. 주문별 락 획득
        lock = MonitoredRedLock(
            self.redis_instances,
            f"lock:order:{order_id}",
            ttl=60000  # 1분
        )

        if not acquire_with_retry(lock):
            self.logger.warning(f"Failed to acquire lock for order {order_id}")
            return {"status": "retry_later", "order_id": order_id}

        try:
            # 2. 주문 상태 확인
            order = self.db.get_order(order_id)

            if order.status != OrderStatus.PENDING:
                self.logger.info(f"Order {order_id} already processed: {order.status}")
                return {"status": order.status, "order_id": order_id}

            # 3. 상태를 PROCESSING으로 변경
            self.db.update_order_status(order_id, OrderStatus.PROCESSING)

            # 4. 재고 확인 및 예약
            for item in order.items:
                inventory_result = self.reserve_inventory(
                    item.product_id,
                    item.quantity,
                    order_id
                )

                if not inventory_result["success"]:
                    # 재고 부족 - 롤백
                    self.rollback_order(order_id)
                    return {
                        "status": "failed",
                        "reason": "insufficient_inventory",
                        "product_id": item.product_id
                    }

            # 5. 결제 처리
            payment_result = self.process_payment(order)

            if payment_result["success"]:
                # 6. 주문 완료
                self.db.update_order_status(order_id, OrderStatus.COMPLETED)
                self.send_confirmation_email(order)

                return {
                    "status": "completed",
                    "order_id": order_id,
                    "transaction_id": payment_result["transaction_id"]
                }
            else:
                # 결제 실패 - 롤백
                self.rollback_order(order_id)
                return {
                    "status": "failed",
                    "reason": "payment_failed",
                    "error": payment_result["error"]
                }

        except Exception as e:
            self.logger.error(f"Error processing order {order_id}: {str(e)}")
            self.rollback_order(order_id)
            raise
        finally:
            lock.release()

    def reserve_inventory(self, product_id, quantity, order_id):
        """재고 예약 (별도 락 사용)"""
        inventory_lock = RedLock(
            self.redis_instances,
            f"lock:inventory:{product_id}",
            ttl=5000
        )

        if inventory_lock.acquire():
            try:
                current = self.db.get_inventory(product_id)
                if current >= quantity:
                    self.db.decrease_inventory(product_id, quantity)
                    self.db.create_reservation(product_id, quantity, order_id)
                    return {"success": True}
                return {"success": False, "available": current}
            finally:
                inventory_lock.release()

        return {"success": False, "reason": "lock_timeout"}
```

### 2. 일일 보고서 생성

```python
import schedule
from datetime import datetime, timedelta

class ReportGenerator:
    def __init__(self, redis_instances, db, storage):
        self.redis_instances = redis_instances
        self.db = db
        self.storage = storage
        self.logger = logging.getLogger(__name__)

    def generate_daily_report(self, date=None):
        """일일 보고서 생성 (중복 방지)"""

        if date is None:
            date = datetime.now().date()

        report_key = f"report:daily:{date.strftime('%Y%m%d')}"
        lock_key = f"lock:{report_key}"

        # 이미 생성된 보고서가 있는지 확인
        existing = self.storage.get(report_key)
        if existing:
            self.logger.info(f"Report for {date} already exists")
            return existing

        # 락 획득
        lock = RedLock(
            self.redis_instances,
            lock_key,
            ttl=300000  # 5분
        )

        if not lock.acquire():
            self.logger.warning(f"Another instance is generating report for {date}")

            # 최대 5분 대기하며 보고서 생성 확인
            for _ in range(60):  # 60 * 5초 = 5분
                time.sleep(5)
                existing = self.storage.get(report_key)
                if existing:
                    return existing

            raise TimeoutError(f"Report generation timeout for {date}")

        try:
            # 다시 한번 확인 (double-check)
            existing = self.storage.get(report_key)
            if existing:
                return existing

            self.logger.info(f"Starting report generation for {date}")

            # 보고서 생성
            report_data = {
                "date": date.isoformat(),
                "generated_at": datetime.now().isoformat(),
                "metrics": self._collect_metrics(date),
                "summary": self._generate_summary(date),
                "charts": self._generate_charts(date)
            }

            # 저장
            report_url = self.storage.save(report_key, report_data)

            # 이메일 발송
            self._send_report_email(date, report_url)

            self.logger.info(f"Report for {date} generated successfully")
            return report_url

        except Exception as e:
            self.logger.error(f"Failed to generate report for {date}: {str(e)}")
            # 실패 마커 설정 (재시도 방지)
            self.storage.set(f"{report_key}:failed", str(e), ttl=3600)
            raise
        finally:
            lock.release()

    def _collect_metrics(self, date):
        """메트릭 수집"""
        return {
            "orders": self.db.count_orders(date),
            "revenue": self.db.sum_revenue(date),
            "new_users": self.db.count_new_users(date),
            "active_users": self.db.count_active_users(date)
        }

    def _generate_summary(self, date):
        """요약 생성"""
        metrics = self._collect_metrics(date)
        yesterday_metrics = self._collect_metrics(date - timedelta(days=1))

        return {
            "order_growth": (metrics["orders"] - yesterday_metrics["orders"]) / max(yesterday_metrics["orders"], 1) * 100,
            "revenue_growth": (metrics["revenue"] - yesterday_metrics["revenue"]) / max(yesterday_metrics["revenue"], 1) * 100,
            "user_growth": (metrics["new_users"] - yesterday_metrics["new_users"]) / max(yesterday_metrics["new_users"], 1) * 100
        }
```

### 3. 멀티테넌트 환경

```python
class MultiTenantLockManager:
    """멀티테넌트 환경에서의 락 관리"""

    def __init__(self, redis_instances):
        self.redis_instances = redis_instances
        self.tenant_limits = {}  # 테넌트별 제한

    def set_tenant_limit(self, tenant_id, max_concurrent_locks=10):
        """테넌트별 동시 락 제한 설정"""
        self.tenant_limits[tenant_id] = max_concurrent_locks

    def acquire_tenant_lock(self, tenant_id, resource_name, ttl=10000):
        """테넌트별 락 획득"""

        # 1. 테넌트 락 제한 확인
        if not self._check_tenant_limit(tenant_id):
            raise TenantLimitExceeded(f"Tenant {tenant_id} exceeded lock limit")

        # 2. 테넌트별 네임스페이스 사용
        lock_name = f"lock:tenant:{tenant_id}:{resource_name}"
        lock = RedLock(self.redis_instances, lock_name, ttl)

        if lock.acquire():
            # 3. 테넌트 락 카운터 증가
            self._increment_tenant_counter(tenant_id)

            # 락 객체에 테넌트 정보 저장
            lock.tenant_id = tenant_id
            return lock

        return None

    def release_tenant_lock(self, lock):
        """테넌트 락 해제"""
        if hasattr(lock, 'tenant_id'):
            self._decrement_tenant_counter(lock.tenant_id)
        lock.release()

    def _check_tenant_limit(self, tenant_id):
        """테넌트 락 제한 확인"""
        limit = self.tenant_limits.get(tenant_id, 10)
        current = self._get_tenant_counter(tenant_id)
        return current < limit

    def _get_tenant_counter(self, tenant_id):
        """현재 테넌트가 보유한 락 수"""
        return int(self.redis_instances[0].get(f"tenant:locks:{tenant_id}") or 0)

    def _increment_tenant_counter(self, tenant_id):
        """테넌트 락 카운터 증가"""
        self.redis_instances[0].incr(f"tenant:locks:{tenant_id}")

    def _decrement_tenant_counter(self, tenant_id):
        """테넌트 락 카운터 감소"""
        self.redis_instances[0].decr(f"tenant:locks:{tenant_id}")

# 사용 예시
lock_manager = MultiTenantLockManager(redis_instances)
lock_manager.set_tenant_limit("tenant_123", max_concurrent_locks=5)

# 테넌트별로 격리된 락
lock = lock_manager.acquire_tenant_lock(
    "tenant_123",
    "resource:update",
    ttl=15000
)

if lock:
    try:
        # 테넌트 리소스 업데이트
        update_tenant_resource("tenant_123", "resource_data")
    finally:
        lock_manager.release_tenant_lock(lock)
```

---

## 트러블슈팅 가이드

### 1. 일반적인 문제와 해결법

```python
class LockTroubleshooter:
    """락 관련 문제 진단 도구"""

    def __init__(self, redis_instances):
        self.redis_instances = redis_instances

    def diagnose_lock_issues(self, resource_name):
        """락 문제 진단"""
        issues = []

        # 1. Redis 연결 확인
        for i, redis in enumerate(self.redis_instances):
            try:
                redis.ping()
            except Exception as e:
                issues.append(f"Redis instance {i} connection failed: {e}")

        # 2. 락 존재 여부 확인
        locked_count = 0
        for redis in self.redis_instances:
            try:
                if redis.get(resource_name):
                    locked_count += 1
            except:
                pass

        if locked_count > len(self.redis_instances) // 2:
            issues.append(f"Lock {resource_name} is currently held")

        # 3. TTL 확인
        for i, redis in enumerate(self.redis_instances):
            try:
                ttl = redis.ttl(resource_name)
                if ttl == -1:
                    issues.append(f"Instance {i}: Lock has no TTL (infinite)")
                elif ttl > 0:
                    issues.append(f"Instance {i}: Lock expires in {ttl}s")
            except:
                pass

        return issues

    def force_unlock(self, resource_name, safety_check=True):
        """강제 언락 (주의해서 사용)"""
        if safety_check:
            confirm = input(f"Force unlock {resource_name}? (yes/no): ")
            if confirm.lower() != "yes":
                return False

        released = 0
        for redis in self.redis_instances:
            try:
                if redis.delete(resource_name):
                    released += 1
            except:
                pass

        return released > 0
```

### 2. 디버깅 헬퍼

```python
import functools

def debug_lock(func):
    """락 디버깅 데코레이터"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import inspect

        # 함수 정보
        func_name = func.__name__
        module = inspect.getmodule(func).__name__

        # 락 관련 변수 찾기
        frame = inspect.currentframe()
        lock_info = {}

        for var_name, var_value in frame.f_locals.items():
            if isinstance(var_value, RedLock):
                lock_info[var_name] = {
                    "resource": var_value.resource_name,
                    "ttl": var_value.ttl,
                    "value": var_value.lock_value[:8] + "..."
                }

        print(f"\n[DEBUG] Function: {module}.{func_name}")
        print(f"[DEBUG] Locks: {lock_info}")

        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            print(f"[DEBUG] Success - Duration: {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[DEBUG] Failed - Duration: {elapsed:.3f}s, Error: {e}")
            raise

    return wrapper

# 사용 예시
@debug_lock
def critical_operation():
    lock = RedLock(redis_instances, "lock:critical", ttl=10000)
    if lock.acquire():
        try:
            # 작업 수행
            process_data()
        finally:
            lock.release()
```

### 3. 로깅 전략

```python
import logging
import json
from datetime import datetime

class LockLogger:
    """구조화된 락 로깅"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def log_acquisition(self, resource_name, success, duration, metadata=None):
        """락 획득 로그"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "lock_acquisition",
            "resource": resource_name,
            "success": success,
            "duration_ms": duration * 1000,
            "metadata": metadata or {}
        }

        if success:
            self.logger.info(json.dumps(log_entry))
        else:
            self.logger.warning(json.dumps(log_entry))

    def log_release(self, resource_name, hold_time, metadata=None):
        """락 해제 로그"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "lock_release",
            "resource": resource_name,
            "hold_time_ms": hold_time * 1000,
            "metadata": metadata or {}
        }

        self.logger.info(json.dumps(log_entry))

    def log_timeout(self, resource_name, wait_time, metadata=None):
        """락 타임아웃 로그"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "lock_timeout",
            "resource": resource_name,
            "wait_time_ms": wait_time * 1000,
            "metadata": metadata or {}
        }

        self.logger.error(json.dumps(log_entry))

# 로깅이 통합된 락 클래스
class LoggedRedLock(RedLock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_logger = LockLogger()

    def acquire(self, *args, **kwargs):
        start = time.time()
        result = super().acquire(*args, **kwargs)
        duration = time.time() - start

        self.lock_logger.log_acquisition(
            self.resource_name,
            result,
            duration,
            {"attempt_count": kwargs.get("retry_count", 1)}
        )

        if result:
            self.acquisition_time = time.time()

        return result

    def release(self):
        if hasattr(self, 'acquisition_time'):
            hold_time = time.time() - self.acquisition_time
            self.lock_logger.log_release(self.resource_name, hold_time)

        super().release()
```

---

## 요약

RedLock을 실무에서 효과적으로 사용하기 위한 핵심 포인트:

1. **적절한 TTL 설정**: 작업 시간의 2-3배
2. **재시도 전략**: 지수 백오프 + 지터
3. **모니터링**: 메트릭 수집 및 로깅
4. **안티 패턴 회피**: 락 안에서 외부 API 호출 금지
5. **성능 최적화**: 락 분할, Read/Write 락
6. **에러 처리**: try/finally 또는 Context Manager 사용

---

## 다음 단계

- `04_advanced.md`: 대규모 시스템 최적화, 모니터링, 고급 패턴
- `05_comparison.md`: 다른 분산 락 솔루션과의 비교