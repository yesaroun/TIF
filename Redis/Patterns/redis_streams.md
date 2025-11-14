# Redis Streams

## 1. 개요

Redis Streams는 Redis 5.0부터 도입된 **로그 기반의 메시지 브로커** 데이터 구조입니다. 대량의 메시지를 순차적으로 저장하고, 여러 컨슈머가 병렬로 처리할 수 있는 기능을 제공합니다.

### 1.1 왜 블랙프라이데이에 필요한가?

블랙프라이데이처럼 순간적으로 **100명이 동시에 몰리는 상황**에서:

```
[100명의 동시 요청] → [Redis Streams에 순차 저장] → [워커들이 순차 처리]
```

- **Redlock**: 중복 요청 방지 (동시성 제어)
- **Redis Streams**: 요청을 안전하게 큐에 저장하고 순차 처리

### 1.2 주요 특징

| 특징 | 설명 |
|------|------|
| **Append-only Log** | 메시지가 순차적으로 추가되며 삭제되지 않음 |
| **Consumer Groups** | 여러 워커가 작업을 분산 처리 가능 |
| **메시지 확인 (ACK)** | 처리 완료 확인으로 at-least-once 보장 |
| **Pending Entries** | 처리 중인 메시지 추적 가능 |
| **자동 ID 생성** | 타임스탬프 기반 고유 ID 자동 부여 |

### 1.3 Redis Lists와의 차이

| 항목 | Redis Lists | Redis Streams |
|------|-------------|---------------|
| **데이터 모델** | 단순 FIFO 큐 | Append-only 로그 + 필드/값 구조 |
| **컨슈머 모델** | BRPOP 등 단일 소비자 중심 | Consumer Group으로 다중 소비자 지원 |
| **메시지 추적** | 처리 완료 상태 추적 불가 | Pending, ACK로 추적 가능 |
| **재처리** | 직접 구현 필요 | XCLAIM/XAUTOCLAIM으로 제공 |
| **메시지 검색** | 인덱스 기반 LINDEX | 타임스탬프 기반 XRANGE |

Streams는 단순 이벤트 큐를 넘어 **장애 복구·재처리·모니터링**까지 포함한 메시징 레이어다. 단순 작업 분배라면 List도 충분하지만, SLA가 엄격한 주문/결제 시나리오라면 Streams가 훨씬 안전하다.

---

## 2. 핵심 개념

### 2.1 Stream 구조

```
Stream: "orders"
├── 1699876543210-0  → {"user": "user1", "product": "A", "qty": 2}
├── 1699876543211-0  → {"user": "user2", "product": "B", "qty": 1}
├── 1699876543212-0  → {"user": "user3", "product": "A", "qty": 5}
└── ...
```

- **Entry ID**: `<밀리초 타임스탬프>-<시퀀스 번호>`
- **Field-Value 쌍**: 각 엔트리는 여러 필드를 가질 수 있음

### 2.2 Consumer Groups

```
Stream: "orders"
│
├── Consumer Group: "order-processors"
│   ├── Consumer: "worker-1" (처리 중: 1699876543210-0)
│   ├── Consumer: "worker-2" (처리 중: 1699876543211-0)
│   └── Consumer: "worker-3" (유휴 상태)
│
└── Consumer Group: "analytics"
    └── Consumer: "analyzer-1"
```

**Consumer Group의 장점**:
- 각 메시지는 그룹 내 **한 컨슈머에게만** 전달
- 여러 워커가 병렬로 처리 (수평 확장)
- 한 스트림을 여러 그룹이 독립적으로 소비 가능

### 2.3 Entry ID 전략

- `*`를 사용하면 Redis가 `<밀리초>-<시퀀스>`를 자동 생성한다. 서버 시간이 역행하면 시퀀스 번호가 급증할 수 있으나, 전체 정렬 순서는 유지된다.
- 애플리케이션에서 직접 ID를 지정하려면 단조 증가를 보장해야 한다. `XSETID`로 다음 ID 기준을 강제로 조정할 수 있다.
- 서로 다른 리전에서 XADD를 호출하면 시계 드리프트가 발생할 수 있다. 이때는 `0-1`, `0-2`처럼 인위적 시퀀스를 사용하고, 비즈니스 타임스탬프는 별도 필드(`event_ts`)에 저장하는 전략이 안전하다.

### 2.4 보존·트림 정책

- Streams는 기본적으로 영구 보존되므로, **길이 제한(MAXLEN)** 또는 **ID 기준(MINID)**으로 주기적 트리밍이 필요하다.
- `XADD orders MAXLEN ~ 1_000_000 * ...`처럼 근사치 트리밍을 사용하면 성능 저하를 줄일 수 있다.
- 중요 이벤트는 AOF/RDB 스냅샷으로 보존하고, 장기 분석이 필요하면 주기적으로 XRANGE 결과를 파일/데이터 레이크로 내보내는 파이프라인을 구성한다.

---

## 3. 기본 명령어

### 3.1 메시지 추가 (Producer)

```bash
# 자동 ID 생성
XADD orders * user user1 product A qty 2
# 반환: "1699876543210-0"

# 특정 ID 지정
XADD orders 1699876543210-0 user user2 product B qty 1

# 스트림 길이 제한 (최대 1000개 유지)
XADD orders MAXLEN ~ 1000 * user user3 product C qty 3
```

### 3.2 메시지 읽기

#### 단순 읽기 (Consumer Group 없이)
```bash
# 처음부터 2개 읽기
XREAD COUNT 2 STREAMS orders 0

# 마지막 읽은 ID 이후부터 읽기
XREAD COUNT 10 STREAMS orders 1699876543210-0

# 블로킹 읽기 (새 메시지 대기, 5초 타임아웃)
XREAD BLOCK 5000 COUNT 1 STREAMS orders $
```

#### Consumer Group으로 읽기
```bash
# Consumer Group 생성
XGROUP CREATE orders order-processors 0

# 메시지 읽기 (worker-1이 읽음)
XREADGROUP GROUP order-processors worker-1 COUNT 1 STREAMS orders >

# 반환 예시:
# 1) 1) "orders"
#    2) 1) 1) "1699876543210-0"
#          2) 1) "user"
#             2) "user1"
#             3) "product"
#             4) "A"
```

### 3.3 메시지 확인 (ACK)

```bash
# 메시지 처리 완료 확인
XACK orders order-processors 1699876543210-0
```

### 3.4 Pending Entries 확인

```bash
# 그룹의 처리 중인 메시지 확인
XPENDING orders order-processors

# 특정 컨슈머의 Pending 메시지 상세 조회
XPENDING orders order-processors - + 10 worker-1
```

### 3.5 범위 조회 (XRANGE/XREVRANGE)

```bash
# 타임스탬프 구간 조회
XRANGE orders 1699876543210-0 1699876543999-*

# 최신 메시지 5개 역순 조회
XREVRANGE orders + - COUNT 5
```

운영 중 장애 조사를 할 때 **특정 주문 ID가 언제 들어왔는지**, **필드 스키마가 일관적인지**를 확인하는 가장 빠른 방법이다.

### 3.6 스트림 유지보수

```bash
# 오래된 메시지 삭제 (길이 기준)
XTRIM orders MAXLEN ~ 100000

# 특정 메시지 수동 삭제
XDEL orders 1699876543210-0

# Consumer Group 오프셋 조정
XGROUP SETID orders order-processors 1699876543215-0
```

`XTRIM`은 CPU 비용이 크므로 트래픽이 적은 시간대나 백그라운드 작업으로 수행한다. Consumer Group 오프셋을 되감으면 ACK되지 않은 메시지가 재전달되는 점에 유의한다.

---

## 4. 블랙프라이데이 주문 처리 예시

### 4.1 아키텍처

```
[사용자들] → [API 서버]
                 ↓
            [Redlock으로 중복 방지]
                 ↓
            [XADD로 Streams에 추가]
                 ↓
        [Worker-1, Worker-2, Worker-3]
                 ↓
            [XREADGROUP으로 읽기]
                 ↓
            [주문 처리 (재고 차감, 결제)]
                 ↓
            [XACK로 완료 확인]
```

아키텍처 핵심 포인트
- API 서버는 가능한 한 빠르게 Streams에 적재만 수행하고, 장시간 작업은 워커로 넘겨 **응답 지연을 고정**시킨다.
- Consumer Group은 "동시에 여러 워커를 붙여도 한 메시지는 한 번만 처리"되도록 보장한다.
- Redlock과 Lua 스크립트를 조합하면 **중복 요청 차단 → 재고 차감 → 상태 업데이트** 단계를 각각 안전하게 보호할 수 있다.

### 4.2 Python 구현 예시

#### Producer (API 서버)

```python
import redis
import uuid

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def create_order(user_id: str, product_id: str, quantity: int):
    """주문 생성 - Redlock으로 중복 방지 후 Streams에 추가"""

    # 1. Redlock으로 중복 요청 방지
    lock_key = f"order:lock:{user_id}:{product_id}"
    lock = r.set(lock_key, "1", nx=True, ex=10)  # 10초 동안 잠금

    if not lock:
        return {"error": "이미 처리 중인 요청입니다"}

    try:
        # 2. Streams에 주문 추가
        order_id = str(uuid.uuid4())
        stream_id = r.xadd(
            'orders',
            {
                'order_id': order_id,
                'user_id': user_id,
                'product_id': product_id,
                'quantity': str(quantity),
                'status': 'pending'
            }
        )

        return {
            "success": True,
            "order_id": order_id,
            "stream_id": stream_id
        }

    finally:
        # 3. 락 해제
        r.delete(lock_key)
```

#### Consumer (Worker)

```python
import redis
import time

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Consumer Group 생성 (최초 1회만)
try:
    r.xgroup_create('orders', 'order-processors', id='0', mkstream=True)
except redis.exceptions.ResponseError:
    pass  # 이미 존재하면 무시

def process_orders(worker_name: str):
    """주문 처리 워커"""

    while True:
        # 1. 새 메시지 읽기 (블로킹, 5초 대기)
        messages = r.xreadgroup(
            groupname='order-processors',
            consumername=worker_name,
            streams={'orders': '>'},
            count=1,
            block=5000
        )

        if not messages:
            continue

        for stream_name, entries in messages:
            for entry_id, data in entries:
                success = False
                try:
                    # 2. 주문 처리
                    print(f"[{worker_name}] 처리 중: {data}")

                    order_id = data['order_id']
                    product_id = data['product_id']
                    quantity = int(data['quantity'])

                    # 실제 비즈니스 로직
                    # - 재고 확인 및 차감
                    # - 결제 처리
                    # - 주문 상태 업데이트
                    process_payment(order_id, product_id, quantity)

                    # 3. 처리 완료 확인
                    r.xack('orders', 'order-processors', entry_id)
                    print(f"[{worker_name}] 완료: {entry_id}")
                    success = True

                except Exception as e:
                    print(f"[{worker_name}] 에러: {e}")
                    # 에러 발생 시 ACK 하지 않음
                    # → Pending 상태로 남아 재처리 가능
                finally:
                    record_metric(worker_name, entry_id, success)

def process_payment(order_id, product_id, quantity):
    """실제 결제 처리 로직"""
    time.sleep(1)  # 결제 처리 시뮬레이션
    print(f"결제 완료: {order_id}")

def record_metric(worker_name: str, entry_id: str, success: bool):
    """모니터링 시스템으로 처리 결과를 전송하는 예시"""
    status = 'success' if success else 'failed'
    print(f"[metric] worker={worker_name} entry={entry_id} status={status}")
```

컨슈머는 **비즈니스 처리 → ACK → 모니터링** 단계를 명확히 분리해야 장애 분석이 쉬워진다. 메트릭 수집 실패가 ACK를 방해하지 않도록 비동기 전송 또는 별도 큐를 사용하는 것도 좋은 전략이다.

#### 실행

```python
# Worker 1 실행
import threading
threading.Thread(target=process_orders, args=('worker-1',)).start()

# Worker 2 실행
threading.Thread(target=process_orders, args=('worker-2',)).start()

# Worker 3 실행
threading.Thread(target=process_orders, args=('worker-3',)).start()
```

### 4.3 부하 테스트 체크리스트

- `XRANGE`로 스트림에 기록된 샘플을 추출해 **필수 필드가 모두 채워졌는지**부터 검증한다.
- `xreadgroup(..., count=n)`에서 `n` 값을 1→10→50으로 늘리며 워커가 배치 처리 시 안정적인지 관찰한다.
- 테스트 데이터는 `XTRIM`이나 별도 `orders:test` 스트림을 만들어 분리한다.

---

## 5. 장애 복구 (Failure Handling)

### 5.1 Pending Entries 재처리

워커가 메시지를 읽었지만 처리 중 죽은 경우:

```python
def recover_pending_messages():
    """Pending 상태인 메시지 재처리"""

    # 1. Pending 메시지 조회 (10분 이상 처리 안 된 것)
    pending = r.xpending_range(
        'orders',
        'order-processors',
        min='-',
        max='+',
        count=10
    )

    for entry in pending:
        entry_id = entry['message_id']
        idle_time = entry['time_since_delivered']

        # 10분(600000ms) 이상 처리 안 됐으면 재할당
        if idle_time > 600000:
            # 2. 다른 워커에게 재할당
            r.xclaim(
                'orders',
                'order-processors',
                'recovery-worker',
                min_idle_time=600000,
                message_ids=[entry_id]
            )
```

### 5.2 자동 복구 워커

```python
import time

def recovery_worker():
    """주기적으로 Pending 메시지 재처리"""
    while True:
        recover_pending_messages()
        time.sleep(60)  # 1분마다 체크

# 별도 스레드로 실행
threading.Thread(target=recovery_worker, daemon=True).start()
```

### 5.3 XAUTOCLAIM으로 자동 재할당

Redis 6.2 이상에서는 `XAUTOCLAIM`으로 **오래된 Pending 메시지를 다른 컨슈머에게 자동 이관**할 수 있다.

```python
messages, next_cursor = r.xautoclaim(
    name='orders',
    groupname='order-processors',
    consumername='recovery-worker',
    min_idle_time=600000,
    start_id='0-0',
    count=20
)

for entry_id, data in messages:
    handle_recovered_order(entry_id, data)
```

`next_cursor`를 저장해 두면 다음 스캔에서 이어서 순회할 수 있다. Pending이 많을수록 XAUTOCLAIM이 XCLAIM 대비 훨씬 단순하다.

### 5.4 멱등성과 재시도 전략

- 주문 ID를 기준으로 **멱등성 키**를 저장해 중복 처리를 차단한다. (예: `SETNX order:done:<order_id> 1`)
- 실패 횟수(`retry_count`) 필드를 증가시키고, 임계치 초과 시 Dead Letter Stream(`orders:dlq`)으로 옮겨 수동 조치한다.
- 외부 API 호출은 타임아웃/재시도 정책을 명확히 하고, 실패 시 메시지에 오류 코드와 타임스탬프를 남겨 후속 분석이 가능하게 한다.

---

## 6. 모니터링

### 6.1 스트림 상태 확인

```bash
# 스트림 정보 확인
XINFO STREAM orders

# Consumer Group 정보
XINFO GROUPS orders

# Consumer 정보
XINFO CONSUMERS orders order-processors
```

### 6.2 Python으로 모니터링

```python
def monitor_stream():
    """스트림 모니터링"""

    # 전체 메시지 수
    stream_len = r.xlen('orders')

    # Pending 메시지 수
    pending_info = r.xpending('orders', 'order-processors')
    pending_count = pending_info['pending']

    # Consumer별 처리량
    consumers = r.xinfo_consumers('orders', 'order-processors')

    print(f"총 메시지: {stream_len}")
    print(f"Pending: {pending_count}")
    for consumer in consumers:
        print(f"  {consumer['name']}: {consumer['pending']} pending")

```

### 6.3 알람 지표 예시

- `Pending` 수가 워커 수 × 허용 지연시간을 넘으면 즉시 알람을 발생시킨다.
- `time_since_delivered`가 일정 값 이상 유지되면 워커 장애 또는 장시간 블로킹 작업을 의심한다.
- `XINFO GROUPS`의 `lag` 값(소비 대기 중 메시지 수)을 타임시리즈 DB로 내보내면 SLA 이탈을 빠르게 감지할 수 있다.

---

## 7. Redis Streams vs 다른 솔루션

| 항목 | Redis Streams | Kafka | RabbitMQ |
|------|---------------|-------|----------|
| **성능** | 매우 빠름 (메모리) | 빠름 (디스크) | 중간 |
| **영속성** | AOF/RDB (선택) | 디스크 기본 | 디스크 기본 |
| **확장성** | Redis Cluster | 뛰어남 | 중간 |
| **설정 복잡도** | 낮음 | 높음 | 중간 |
| **Consumer Groups** | ✅ | ✅ | ✅ |
| **메시지 순서** | ✅ 보장 | ✅ 파티션 내 | ✅ |
| **적합한 케이스** | 중소규모, 빠른 처리 | 대규모 로그 | 복잡한 라우팅 |

---

## 8. 실전 팁

### 8.1 스트림 크기 제한

```python
# MAXLEN으로 메모리 관리
r.xadd('orders', {'data': 'value'}, maxlen=10000, approximate=True)
```

- `approximate=True` (`~`): 정확한 크기가 아닌 근사치로 관리 (성능 향상)

### 8.2 배치 처리

```python
# 한 번에 여러 메시지 읽기
messages = r.xreadgroup(
    groupname='order-processors',
    consumername='worker-1',
    streams={'orders': '>'},
    count=10  # 10개씩 처리
)
```

### 8.3 메시지 TTL 설정

Redis Streams는 기본적으로 TTL이 없지만, 별도 필드로 관리 가능:

```python
import time

# 메시지에 타임스탬프 추가
r.xadd('orders', {
    'data': 'value',
    'created_at': str(int(time.time()))
})

# 오래된 메시지 제거 (백그라운드 작업)
def cleanup_old_messages():
    now = int(time.time())
    threshold = now - 86400  # 24시간 전

    # XTRIM으로 오래된 메시지 삭제
    r.xtrim('orders', maxlen=100000, approximate=True)
```

### 8.4 멱등 컨슈머 패턴

- 메시지에 `dedupe_key`(예: `order:{order_id}:status`)를 포함시키고, Redis `SETNX` 또는 DB UNIQUE 제약으로 **한 번만 처리**되도록 한다.
- 부작용이 있는 외부 연동(결제, 쿠폰, 포인트)은 반드시 멱등성을 확보한 후 ACK해야 한다.

### 8.5 백프레셔와 워커 스케일링

- 워커의 처리 시간을 주기적으로 측정해 P95 지연을 추적한다.
- Pending이 일정 시간 이상 증가하면 `count` 값을 키우거나 워커 프로세스를 수평 확장한다.
- API 서버는 `XLEN`이 임계치를 넘으면 임시로 요청을 큐잉하거나 리전에 분산시키는 백프레셔 로직을 준비한다.

### 8.6 스트림 샤딩

- 트래픽이 크면 `orders:region-a`, `orders:region-b`처럼 스트림을 쪼개고, 각 샤드에는 동일한 Consumer Group 이름을 부여한다.
- 워커는 자신이 담당하는 샤드만 소비하게 구성하면 **락 경합 없이 선형 확장**이 가능하다.

---

## 9. 블랙프라이데이 시나리오 요약

### 문제 상황
```
100명이 동시에 같은 상품 주문 → 재고 100개
```

### 해결 방법

1. **Redlock**: 사용자당 중복 요청 방지
   ```
   lock_key = f"order:{user_id}:{product_id}"
   ```

2. **Redis Streams**: 주문을 큐에 안전하게 저장
   ```
   XADD orders * user_id 1 product_id A qty 1
   ```

3. **Consumer Group**: 여러 워커가 병렬 처리
   ```
   Worker-1, Worker-2, Worker-3 → 각각 다른 주문 처리
   ```

4. **재고 차감**: Lua Script로 원자적 처리
   ```lua
   local stock = redis.call('GET', 'stock:A')
   if tonumber(stock) >= 1 then
       redis.call('DECRBY', 'stock:A', 1)
       return 1
   else
       return 0
   end
   ```

### 결과
- ✅ 중복 주문 방지
- ✅ 순차적 안전한 처리
- ✅ 워커 장애 시 자동 복구
- ✅ 초당 수천 건 처리 가능

### 운영 체크리스트

- API 서버/워커가 동일한 **필수 필드와 스키마 버전**을 사용하도록 `schema_version` 필드를 기록한다.
- 장애 분석용으로 `orders:dlq`, `orders:audit` 같은 보조 스트림을 미리 만들어 두고, 재처리 도구를 준비한다.
- 배포 전 `XGROUP SETID orders order-processors 0`로 리플레이 테스트를 수행하고, `XRANGE`로 메시지 스키마를 검수한다.
- 정기적으로 `XAUTOCLAIM` 보고서를 확인해 장기 Pending 메시지가 누적되지 않는지 점검한다.

---

## 10. 참고 자료

- [Redis Streams 공식 문서](https://redis.io/docs/data-types/streams/)
- [Redis Streams Tutorial](https://redis.io/docs/manual/data-types/streams-tutorial/)
- [Consumer Groups](https://redis.io/docs/manual/data-types/streams-tutorial/#consumer-groups)
- [redis-py Streams 예제](https://redis-py.readthedocs.io/en/stable/examples/redis_streams.html)
- [XAUTOCLAIM 소개](https://redis.com/blog/redis-streams-xautoclaim/)
- [Redis Streams 내부 구조 (RedisConf)](https://redis.com/blog/redis-streams-101/)
