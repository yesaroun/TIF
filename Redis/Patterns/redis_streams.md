
# Redis Streams & Redlock로 설계하는 블랙프라이데이 주문 처리

> 시나리오: 블랙프라이데이 순간 **100명 이상이 동시에 같은 상품을 주문**하는 상황.  
> 목표: **중복 주문 방지**, **재고 초과 판매 방지**, **장애 시 재처리 가능**, **응답 속도 유지**.

---

## 1. 왜 Redis Streams가 필요한가?

### 1.1 현재 구조(가정)

대부분 처음에 이런 식으로 구현함:

1. HTTP 요청 진입
2. Redis Redlock 획득 (상품/유저 단위 락)
3. 재고 확인 → 재고 감소 → 주문 DB insert → 결제 준비
4. 락 해제
5. 응답 반환

**문제**  

- 재고 확인부터 주문/결제 로직까지 전부 **락 안에서 실행**  
- 동시 접속자가 100명만 넘어서도:
  - 락 대기 시간이 급격히 증가
  - 타임아웃/재시도 증가
  - 전체 처리량(throughput) 하락

Redlock 은 **“동시에 딱 하나만 돌려야 하는 짧은 critical section”** 에 적합하지,  
**고처리량 큐 + 비동기 작업 처리**에 최적화된 도구는 아님.

### 1.2 여기에 Streams를 추가하면

HTTP 요청의 역할을 **“검증 + 큐에 적재”로 끝내고**,  
실제 무거운 작업(재고 감소, 결제, 주문 생성)은 **워커가 비동기 처리**한다:

```text
[100명 동시 요청]
      │
      ▼
[API 서버: 최소 검증 + XADD]
      │
      ▼
[Redis Streams에 순차 저장]
      │
      ▼
[여러 워커(Consumer)가 병렬 처리]
```

- **Redlock**: 사용자/상품 단위 중복 요청 최소화, 아주 짧은 구간 보호
- **Redis Streams**: 요청을 **안전하게 쌓고**, 여러 워커가 **나눠 처리**


API 서버는 “큐에 넣기만” 하기 때문에, **응답 지연 시간이 고정되고 예측 가능**해진다.


## 2. Redlock vs Redis Streams: 언제 무엇을 쓸까?

|항목|Redlock|Redis Streams|
|---|---|---|
|목적|분산 락, 경쟁 상태 방지|메시지 큐 / 이벤트 로그|
|단위|코드 블록 단위의 상호 배제|메시지(이벤트) 단위 처리|
|처리 방식|요청이 끝날 때까지 동기 처리|요청은 메시지 쌓기, 실제 작업은 워커가 비동기 처리|
|강점|“이 구간은 1개만 돌려야 한다” 보장|고처리량, 재처리, 장애 복구, 모니터링|
|단점|락 범위가 크면 throughput 급감|at-least-once → 멱등성 설계 필요|

실전 패턴:

- **Streams + 워커 풀**로 전체 처리량 담당
    
- 필요한 최소 구간에만 **Redlock or Lua script or DB unique 제약** 사용
    

---

## 3. Redis Streams 개요

### 3.1 Streams란?

Redis Streams는 Redis 5.0부터 도입된 **append-only 로그 기반 메시지 브로커** 데이터 구조.

- 메시지를 **시간 순서대로 쌓는 로그**
    
- 각 메시지(entry)는 `ID + field/value 쌍`으로 구성
    
- Consumer Group으로 여러 워커에게 **하나의 메시지를 딱 한 번만** 배분 가능
    
- Pending 리스트, ACK, 재전달 기능으로 장애 복구까지 지원
    

### 3.2 Streams 구조

```text
Stream: "orders"
├── 1699876543210-0  → {"user": "user1", "product": "A", "qty": "2"}
├── 1699876543211-0  → {"user": "user2", "product": "B", "qty": "1"}
├── 1699876543212-0  → {"user": "user3", "product": "A", "qty": "5"}
└── ...
```

- **Entry ID**: `<밀리초 타임스탬프>-<시퀀스 번호>`
    
- **Field-Value**: JSON-like 구조지만 실제로는 문자열 필드/값 쌍
    

### 3.3 Consumer Group

```text
Stream: "orders"
│
├── Consumer Group: "order-processors"
│   ├── Consumer: "worker-1" (처리 중: 1699876543210-0)
│   ├── Consumer: "worker-2" (처리 중: 1699876543211-0)
│   └── Consumer: "worker-3" (대기)
│
└── Consumer Group: "analytics"
    └── Consumer: "analyzer-1"
```

- `order-processors` 그룹 안에 워커 여러 개 (worker-1, worker-2, …)
    
- **그룹 내에서 하나의 메시지는 오직 한 워커에게만 전달**
    
- 같은 스트림을 다른 그룹(예: `analytics`)이 **독립적으로 다시 소비**할 수도 있음
    

### 3.4 Entry ID 전략

- `XADD orders * ...`  
    → Redis가 `<밀리초>-<시퀀스>`를 자동 생성
    
- 서버 시간이 다소 튀어도, 내부적으로 시퀀스 번호를 보정해서 전체 순서를 유지
    
- 멀티 리전 환경이라면, 비즈니스용 타임스탬프를 별도 필드 (`event_ts`)로 두고  
    ID는 단순 시퀀스 용도로만 사용하는 전략도 있음
    

### 3.5 보존·트림 정책

- Streams는 기본적으로 **지우지 않으면 영구 보존**
    
- 메모리 관리용으로 보통:
    

```bash
XADD orders MAXLEN ~ 1_000_000 * user user1 product A qty 2
```

- `MAXLEN ~` : **근사치 트리밍(soft limit)** → 성능에 유리
    
- 장기 분석은 별도 파이프라인으로 Logs/데이터레이크에 내보내고,
    Redis는 "최근 일정량만 유지"하는 패턴이 일반적

#### MAXLEN 옵션 상세

**`~` (틸드) vs 정확값 비교:**

```bash
# 정확한 제한 (느림)
XADD orders MAXLEN 1000 * user user1 product A
→ 정확히 1000개 유지, 매번 체크 (성능 저하)

# 근사치 제한 (빠름, 권장)
XADD orders MAXLEN ~ 1000 * user user1 product A
→ 약 1000~1100개 정도 유지
→ 효율적 배치 삭제로 성능 유리
```

**실전 권장값:**
- 소규모(1만 건/일): `MAXLEN ~ 10000`
- 중규모(10만 건/일): `MAXLEN ~ 100000`
- 대규모(100만 건/일): `MAXLEN ~ 1000000`

**동작 방식:**
- 새 메시지 추가 시 자동으로 오래된 메시지 삭제
- ACK 여부와 무관하게 삭제됨 (주의!)
- 메모리 OOM 방지용 필수 설정


---

## 4. Redis Lists vs Streams

|항목|Redis Lists|Redis Streams|
|---|---|---|
|데이터 모델|단순 FIFO 큐|Append-only 로그 + 필드/값 구조|
|컨슈머 모델|`BRPOP` 등 단일 소비자 중심|Consumer Group으로 다중 소비자|
|처리 추적|처리 완료 상태 추적 불가|Pending + ACK로 처리 상태 추적|
|재처리|애플리케이션에서 직접 구현|XCLAIM/XAUTOCLAIM 지원|
|조회/검색|인덱스 기반 `LINDEX`|ID/시간 기반 `XRANGE`|

- 단순 큐/작업 분배만 필요하면 Lists도 가능
    
- **주문/결제** 같이 장애 후 재처리·모니터링·리플레이가 중요한 경우 → **Streams 추천**
    

---

## 5. 핵심 개념: PEL, ACK, At-least-once

### 5.1 Pending Entries List(PEL)

- 특정 Group에서 “읽었지만 아직 ACK 안 된 메시지 목록”
    
- 워커가 죽었거나, 예외로 처리가 중단된 메시지들이 여기에 남음
    
- `XPENDING`, `XCLAIM`, `XAUTOCLAIM`으로 재할당·재처리 가능


### 5.1.1 Pending 자동 생성 및 제거 메커니즘

**중요:** Pending은 미리 설정하는 것이 아니라 **자동으로 생성/제거**됩니다.

#### 자동 생성 (읽기 시)

```bash
# XREADGROUP으로 메시지를 읽는 순간 → 자동으로 Pending에 추가
XREADGROUP GROUP order-processors worker-1 COUNT 10 STREAMS orders >
```

- 메시지를 읽으면 Redis가 자동으로 해당 메시지를 **Pending Entries List(PEL)**에 추가
- Pending 상태 = "워커에게 할당됨, 아직 처리 결과를 모름"
- 별도의 설정이나 명령어 필요 없음

#### 자동 제거 (ACK 시)

```bash
# XACK로 처리 완료를 명시하면 → Pending에서 자동 제거
XACK orders order-processors 1699876543210-0
```

- 워커가 `XACK`를 호출하면 Redis가 자동으로 PEL에서 제거
- 스트림의 실제 데이터는 여전히 존재 (별도로 `XDEL`로 삭제 필요)

#### 상태 전환 흐름

```text
[새 메시지]
    │
    ▼
┌─────────────────┐
│ Stream에 존재    │  ← XADD로 추가됨
│ (Pending 아님)   │
└─────────────────┘
    │
    │ XREADGROUP 실행
    ▼
┌─────────────────┐
│ Pending 상태!    │  ← 자동으로 PEL에 추가됨
│ Consumer: worker-1
│ Status: 처리 중   │
└─────────────────┘
    │
    ├─ XACK 성공 ──→ [PEL에서 제거] ✅
    │
    └─ 워커 죽음/실패 ──→ [PEL에 계속 남음] ⚠️
                         └→ XAUTOCLAIM으로 재처리
```

#### Python 예시

```python
import redis
r = redis.Redis(decode_responses=True)

# 1. XREADGROUP으로 읽기 → Pending 자동 추가
messages = r.xreadgroup(
    groupname='order-processors',
    consumername='worker-1',
    streams={'orders': '>'},
    count=10
)
# 이 순간 메시지가 자동으로 Pending 상태로 변경됨!

# 2. 비즈니스 로직 실행
for stream, entries in messages:
    for entry_id, data in entries:
        try:
            process_order(data)  # 재고 감소, 결제 등

            # 3. 성공 시 XACK → Pending 자동 제거
            r.xack('orders', 'order-processors', entry_id)

        except Exception as e:
            # 실패 시 ACK 안 함 → Pending에 계속 남음
            # 나중에 XAUTOCLAIM이 재처리
            print(f"실패: {e}")
```

#### 주요 특징

- **자동 추적**: Redis가 알아서 Pending 상태 관리
- **타임아웃 없음**: ACK 안 하면 영원히 Pending (주기적 모니터링 필수)
- **MAXLEN과 독립적**: MAXLEN으로 스트림 데이터 삭제돼도 Pending 참조는 남음
- **재처리 가능**: 워커 장애 시 `XAUTOCLAIM`으로 다른 워커에게 재할당


### 5.2 At-least-once Delivery

- **최소 한 번은 전달 보장** (at-least-once)
    
- 워커가 메시지를 처리하다가 죽으면:
    
    - ACK를 못해서 PEL에 남음
        
    - 나중에 다른 워커가 XCLAIM/XAUTOCLAIM으로 가져가 재처리
        
- 결과적으로 **동일 메시지가 두 번 처리될 수 있음 → 멱등성 필수**
    

### 5.3 멱등성 패턴

- **주문 ID**를 미리 생성하고, DB에 UNIQUE 제약
    
- `order:done:<order_id>`를 `SETNX`로 관리해서 중복 처리 방지
    
- "이미 처리된 주문이면 그냥 스킵"하는 처리가 필요


### 5.4 MAXLEN vs ACK: 서로 다른 역할

**ACK**와 **MAXLEN**은 전혀 다른 목적으로 사용됩니다:

|항목|ACK (XACK)|MAXLEN|
|---|---|---|
|목적|처리 상태 추적|메모리 관리|
|동작|PEL에서 "처리 완료" 표시|스트림에서 오래된 메시지 삭제|
|영향 범위|Pending 리스트|실제 스트림 데이터|
|타이밍|워커가 처리 완료 후 수동 호출|XADD 시 자동 트리밍|

#### 주의사항: ACK 안 된 메시지도 삭제될 수 있음

```text
시나리오:
1. 메시지 1000개가 Pending 상태 (ACK 안 됨)
2. XADD ... MAXLEN ~ 1000으로 새 메시지 추가
3. → 오래된 메시지가 스트림에서 삭제됨
4. → 하지만 PEL에는 여전히 참조가 남음
5. → XAUTOCLAIM 시도 시 에러 발생 가능
```

**권장 패턴:**
- MAXLEN은 "처리 완료된 메시지 보관 기간" 기준으로 설정
- 워커 처리 속도를 고려해서 충분히 여유있게 설정
- 예: 분당 1000건 처리 → MAXLEN 최소 100,000 (100분치 보관)

---

## 6. 필수 명령어 요약

### 6.1 메시지 추가 – XADD (Producer)

```bash
# 자동 ID 생성
XADD orders * user user1 product A qty 2
#  저장 구조
#  Stream: "orders"
#  ├── 1699876543210-0  ← Redis가 자동 생성한 ID
#  │   ├── user: "user1"
#  │   ├── product: "A"
#  │   └── qty: "2"
#
#  상세 설명
#  XADD orders * user user1 product A qty 2
#  #    ^^^^^^ ^ ^^^^ ^^^^^ ^^^^^^^ ^ ^^^ ^
#  #    │      │ └────┴─────┴───────┴─┴───┴─ field-value 쌍들
#  #    │      └─ * : ID 자동 생성 (밀리초 타임스탬프-시퀀스)
#  #    └─ 스트림 이름
#
#  실제 저장된 모습
#  Entry ID: 1699876543210-0
#            │             └─ 시퀀스 번호 (같은 밀리초에 여러 개 들어올 때 구분)
#            └─ 밀리초 타임스탬프
#
#  Data: {
#    "user": "user1",
#    "product": "A",
#    "qty": "2"
#  }

# 특정 ID 지정
XADD orders 1699876543210-0 user user2 product B qty 1

# 스트림 길이 제한 (근사치 1000개 유지)
# → 새 메시지 추가 시 오래된 메시지 자동 삭제
# → 약 1000개 정도 유지 (ACK 여부와 무관)
# → 메모리 관리 필수 설정
XADD orders MAXLEN ~ 1000 * user user3 product C qty 3
```

**💡 MAXLEN 팁:**
- `~`는 근사치 제한 (성능 좋음, 권장)
- 정확값(`MAXLEN 1000`)은 성능 저하 가능
- 실환경: `MAXLEN ~ 100000` 이상 권장 (워커 처리 시간 고려)

---

### 6.2 Consumer Group 생성 – XGROUP

```bash
# Stream이 없으면 생성하면서 Group 만들기
XGROUP CREATE orders order-processors 0 MKSTREAM
#             ^^^^^^ ^^^^^^^^^^^^^^^^ ^ ^^^^^^^^
#             │      │                │ └─ 옵션: 스트림이 없으면 자동 생성
#             │      │                └─ 시작 위치 (Entry ID)
#             │      └─ Consumer Group 이름
#             └─ Stream 이름

# Group 정보
XINFO GROUPS orders

# Consumer 정보
XINFO CONSUMERS orders order-processors

# Group 오프셋 조정
XGROUP SETID orders order-processors 1699876543215-0
```

---

### 6.3 읽기 – XREAD / XREADGROUP

#### 단순 읽기

```bash
# 처음부터 2개
XREAD COUNT 2 STREAMS orders 0

# 마지막 ID 이후부터
XREAD COUNT 10 STREAMS orders 1699876543210-0

# 블로킹 읽기 (5초 대기)
XREAD BLOCK 5000 COUNT 1 STREAMS orders $
```

#### Consumer Group 기반

```bash
# Group 생성 (최초 1회)
XGROUP CREATE orders order-processors 0 MKSTREAM

# worker-1이 새 메시지 읽기
XREADGROUP GROUP order-processors worker-1 COUNT 10 BLOCK 5000 STREAMS orders >
#                ^^^^^^^^^^^^^^^^ ^^^^^^^^
#                │                └─ Consumer 이름 (자동 생성됨!)
#                └─ Consumer Group 이름 (미리 생성 필요)
```

- `>` : 아직 아무 Consumer에게도 배정되지 않은 새 메시지만 가져옴
    
---

### 6.4 처리 완료 – XACK

```bash
XACK orders order-processors 1699876543210-0
```

- PEL(대기 리스트)에서 제거
    
- 스트림에서 실제 데이터 삭제는 아님 (`XDEL` 별도)
    

---

### 6.5 Pending / 재처리 – XPENDING, XCLAIM, XAUTOCLAIM

#### Pending 생명 주기 한눈에 보기

Pending은 자동으로 생성/관리되며, 아래 단계를 거칩니다:

|단계|상태|명령어|결과|
|---|---|---|---|
|1|스트림에만 존재|`XADD`|메시지 추가, Pending 아님|
|2|Pending 추가|`XREADGROUP`|**자동으로 PEL에 추가**|
|3|처리 중|비즈니스 로직 실행|Pending 유지|
|4|처리 완료|`XACK`|**자동으로 PEL에서 제거**|
|5|모니터링|`XPENDING`|Pending 상태 확인|
|6|재처리 필요|`XCLAIM/XAUTOCLAIM`|다른 워커로 재할당|

**핵심:** `XREADGROUP` → Pending 추가(자동), `XACK` → Pending 제거(자동)

```bash
# 그룹 전체 Pending 요약
XPENDING orders order-processors

# 특정 consumer의 Pending 상세
XPENDING orders order-processors - + 10 worker-1
#        ^^^^^^ ^^^^^^^^^^^^^^^^ ^ ^ ^^ ^^^^^^^^
#        │      │                │ │ │  └─ Consumer 이름 (선택)
#        │      │                │ │ └─ 최대 개수
#        │      │                │ └─ 끝 ID (+ = 마지막까지)
#        │      │                └─ 시작 ID (- = 처음부터)
#        │      └─ Consumer Group 이름
#        └─ Stream 이름

# 오래된 메시지를 다른 consumer로 소유권 변경
XCLAIM orders order-processors worker-2 600000 1699876543210-0

# Redis 6.2+ : 오래된 메시지를 자동으로 가져오기
XAUTOCLAIM orders order-processors recovery-worker 600000 0-0 COUNT 20
```

---

### 6.6 범위 조회 / 유지보수 – XRANGE, XREVRANGE, XTRIM, XDEL

```bash
# ID/시간 구간 조회
XRANGE orders 1699876543210-0 1699876543999-*

# 최신 5개 역순 조회
XREVRANGE orders + - COUNT 5

# 길이 기준 트림
XTRIM orders MAXLEN ~ 100000

# 특정 메시지 수동 삭제
XDEL orders 1699876543210-0
```

#### 특수 ID 기호: `-`와 `+`

범위 조회 시 사용하는 특수 기호:

| 기호 | 의미 | 설명 |
|------|------|------|
| **`-`** | 가장 작은 ID | 스트림의 처음 (oldest) |
| **`+`** | 가장 큰 ID | 스트림의 끝 (newest) |

**정순 vs 역순:**

```bash
# 정순 (XRANGE): 처음 → 끝
XRANGE orders - +
#             ^ ^
#             처음→끝 (오래된 것부터)

# 역순 (XREVRANGE): 끝 → 처음
XREVRANGE orders + -
#                ^ ^
#                끝→처음 (최신 것부터)
```

**실전 예시:**

```bash
# 처음부터 10개
XRANGE orders - + COUNT 10

# 최신 10개 (역순)
XREVRANGE orders + - COUNT 10

# 특정 ID부터 끝까지
XRANGE orders 1699876543210-0 +

# 특정 시간 범위만
XRANGE orders 1699876543000-0 1699876544000-0
```

**XPENDING에서도 동일:**

```bash
# worker-1의 모든 Pending 조회 (처음부터 끝까지)
XPENDING orders order-processors - + 100 worker-1
```

---

## 7. 블랙프라이데이 주문 처리 아키텍처

### 7.1 전체 플로우

```text
[사용자들] 
   │
   ▼
[API 서버]
   1) 기본 검증 (로그인, 파라미터)
   2) (선택) Redlock으로 유저/상품 단위 중복 요청 방지
   3) XADD로 'orders' 스트림에 주문 이벤트 적재
   4) "주문 접수됨" 응답
   │
   ▼
[Redis Streams: orders]
   │
   ▼
[Worker Pool (order-processors 그룹)]
   5) XREADGROUP으로 메시지 가져오기
   6) 재고 확인 & 감소 (Lua/DB 트랜잭션)
   7) 결제/주문 생성
   8) XACK
   9) 실패 시 ACK 생략 → Pending → 나중에 재처리
```

### 7.2 Redlock을 어디까지 쓸 것인가?

- API 단계에서:
    
    - 같은 유저가 같은 상품을 여러 번 찍지 않도록  
        `order:lock:<user_id>:<product_id>` 로 3~10초 정도 가벼운 락
        
- 재고 감소 단계:
    
    - Redis `DECRBY` + 재고 체크를 **Lua script**로 한 번에 처리하는 것도 방법:
        

```lua
-- KEYS[1] = "stock:A"
-- ARGV[1] = "1"  (주문 수량)

local stock = tonumber(redis.call('GET', KEYS[1]) or "0")
local dec = tonumber(ARGV[1])

if stock >= dec then
  redis.call('DECRBY', KEYS[1], dec)
  return 1
else
  return 0
end
```

이렇게 하면 **락 없이도 재고 감소를 원자적으로 처리**할 수 있음.

---

## 8. Python 구현 예시

### 8.1 Producer (API 서버 쪽)

```python
import redis
import uuid

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def create_order(user_id: str, product_id: str, quantity: int):
    """
    주문 생성 API 핸들러 예시
    - (선택) Redlock으로 유저/상품 단위 중복 요청 방지
    - Streams에 주문 이벤트 적재
    """

    lock_key = f"order:lock:{user_id}:{product_id}"
    # 10초 동안 동일 user+product 요청 1개만 허용
    locked = r.set(lock_key, "1", nx=True, ex=10)

    if not locked:
        return {"error": "이미 처리 중인 요청입니다."}

    try:
        order_id = str(uuid.uuid4())

        stream_id = r.xadd(
            'orders',
            {
                'order_id': order_id,
                'user_id': user_id,
                'product_id': product_id,
                'quantity': str(quantity),
                'status': 'pending',
                'schema_version': '1',
            },
            maxlen=100000,
            approximate=True,
        )

        return {
            "success": True,
            "order_id": order_id,
            "stream_id": stream_id,
        }

    finally:
        r.delete(lock_key)
```

### 8.2 Consumer (Worker – 주문 처리)

```python
import redis
import time

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

STREAM_KEY = 'orders'
GROUP_NAME = 'order-processors'


def init_group():
    try:
        r.xgroup_create(STREAM_KEY, GROUP_NAME, id='0', mkstream=True)
    except redis.exceptions.ResponseError as e:
        # 이미 그룹이 있으면 에러 발생하므로 무시
        if "BUSYGROUP" not in str(e):
            raise


def process_payment(order_id, product_id, quantity):
    """
    실제 결제 + 재고 감소 + 주문 상태 업데이트 로직을 여기에 넣기
    - 재고: Redis/Lua 또는 DB 트랜잭션
    - 결제: 외부 PG 연동
    """
    time.sleep(0.5)  # 예시용 딜레이
    print(f"[BIZ] 결제 완료: order_id={order_id}, product={product_id}, qty={quantity}")


def record_metric(worker_name: str, entry_id: str, success: bool):
    """모니터링/로그용"""
    status = 'success' if success else 'failed'
    print(f"[metric] worker={worker_name} entry={entry_id} status={status}")


def consume_orders(consumer_name: str, count: int = 10, block_ms: int = 5000):
    """
    주문 처리 워커
    - 새 메시지: STREAMS {STREAM_KEY: '>'}
    """
    while True:
        resp = r.xreadgroup(
            groupname=GROUP_NAME,
            consumername=consumer_name,
            streams={STREAM_KEY: '>'},
            count=count,
            block=block_ms,
        )

        if not resp:
            continue

        for stream_key, entries in resp:
            for entry_id, data in entries:
                success = False
                try:
                    order_id = data['order_id']
                    product_id = data['product_id']
                    quantity = int(data['quantity'])

                    # 멱등성: 이미 처리된 주문인지 체크
                    if r.setnx(f"order:done:{order_id}", "1"):
                        # 처음 처리하는 주문
                        process_payment(order_id, product_id, quantity)
                    else:
                        print(f"[{consumer_name}] 이미 처리된 주문: {order_id}")

                    r.xack(STREAM_KEY, GROUP_NAME, entry_id)
                    success = True
                    print(f"[{consumer_name}] 처리 완료: {entry_id}")

                except Exception as e:
                    # 실패 시 ACK 하지 않음 → Pending에 남는다
                    print(f"[{consumer_name}] 에러: {e}")

                finally:
                    record_metric(consumer_name, entry_id, success)
```

---

## 9. 장애 복구 전략

### 9.1 Pending 메시지 재처리

워커가 메시지를 읽고 죽은 경우:

```python
def recover_pending_messages():
    """
    Pending 상태인 메시지를 재할당/재처리
    - 간단 버전: 오래된 메시지를 recovery-worker로 XAUTOCLAIM
    """
    messages, next_id = r.xautoclaim(
        name=STREAM_KEY,
        groupname=GROUP_NAME,
        consumername='recovery-worker',
        min_idle_time=600_000,  # 10분 이상 처리 안 된 메시지
        start_id='0-0',
        count=20,
    )

    for entry_id, data in messages:
        print(f"[recovery] 재처리 대상: {entry_id}, data={data}")
        # 여기서 process_payment(...) 다시 호출 후 XACK 수행
        # 멱등성 체크는 동일하게 적용
```

### 9.2 Recovery 워커 루프

```python
import threading

def recovery_loop():
    while True:
        recover_pending_messages()
        time.sleep(60)  # 1분마다 체크

# 데몬 스레드로 실행
threading.Thread(target=recovery_loop, daemon=True).start()
```

### 9.3 Dead Letter Stream(DLQ)

- 재시도 횟수를 `retry_count` 필드에 저장
    
- 임계치 초과 시 `orders:dlq`로 이동:
    

```python
r.xadd('orders:dlq', data)
```

- DLQ는 사람이 직접 보거나, 별도 툴로 분석/수동 재처리
    

---

## 10. 모니터링 & 운영

### 10.1 XINFO 기반 점검

```bash
# Stream 정보
XINFO STREAM orders

# Group 정보
XINFO GROUPS orders

# Consumer별 정보
XINFO CONSUMERS orders order-processors
```

주요 지표:

- `length` : 총 메시지 수
    
- `lag` : 아직 처리되지 않은 메시지 수
    
- `pending` : Pending 개수
    

### 10.2 Python으로 간단 모니터링

```python
def monitor_stream():
    stream_len = r.xlen(STREAM_KEY)
    pending_info = r.xpending(STREAM_KEY, GROUP_NAME)
    pending_count = pending_info['pending']

    consumers = r.xinfo_consumers(STREAM_KEY, GROUP_NAME)

    print(f"총 메시지: {stream_len}")
    print(f"Pending: {pending_count}")
    for consumer in consumers:
        print(f"  {consumer['name']}: pending={consumer['pending']}")
```

### 10.3 알람 기준 예시

- Pending 수가 워커 수 × 허용 지연 시간 기준을 넘으면 알람
    
- 특정 메시지가 `time_since_delivered` 기준 N분 이상 Pending이면 알람
    
- Group `lag`가 일정 임계치 이상으로 계속 증가하면 워커 증설 or `count` 조정 고려
    

---

## 11. Streams vs 다른 메시징 솔루션

|항목|Redis Streams|Kafka|RabbitMQ|
|---|---|---|---|
|성능|매우 빠름 (메모리 기반)|빠름 (디스크 기반)|중간|
|영속성|RDB/AOF 선택|디스크 기본|디스크 기본|
|확장성|Redis Cluster|매우 높음|중간|
|설정 난이도|낮음|높음|중간|
|Consumer Group|지원|지원|지원|
|사용 목적|중/대규모 웹, 백오피스, 실시간 이벤트|대규모 로그, 분석 파이프라인|복잡한 라우팅/패턴|

너 지금 블랙프라이데이용 주문/재고 처리가 목적이라면:

- 이미 Redis 쓰고 있고,
    
- 초당 수천 건 수준을 안정적으로 처리하고 싶다
    
- 장애 재처리/모니터링도 필요하다
    

→ Redis Streams가 **구현 난이도 대비 효율이 가장 좋은 선택**에 가깝다.

---

## 12. 실전 팁 & 체크리스트

### 12.1 실전 팁

- **MAXLEN**으로 스트림 크기 제한 (운영 환경 필수)
    
- Consumer는 **배치 처리(count 10~50)**로 효율을 높임
    
- 외부 API(PG, 외부 서비스) 연동은 항상 **타임아웃 + 재시도 + 멱등성**을 같이 설계
    
- `schema_version` 필드를 넣어 스키마 변경 시 혼선을 줄임
    
- 트래픽이 크면 `orders:shard-1`, `orders:shard-2`처럼 스트림 샤딩 + 워커 분리
    

### 12.2 블랙프라이데이 사전 체크리스트

1. **API 서버**
    
    - 요청 검증 → Streams 적재까지의 평균 응답 시간 측정
        
    - 100~1000 동시 요청 부하 테스트
        
2. **워커**
    
    - 소비 속도: `count`, 워커 개수 조합으로 분당 처리량 계산
        
    - 장애 시 XAUTOCLAIM 기반 재처리 동작 검증
        
3. **재고 로직**
    
    - Lua/DB 트랜잭션으로 oversell 방지 확인
        
    - 멱등성(중복 주문 방지) 시나리오 테스트
        
4. **모니터링**
    
    - Pending, lag, 소비 속도 지표를 Grafana/Cloud Monitoring 등으로 대시보드화
        
    - 임계값 넘을 때 알람 세팅
        
5. **운영 플랜**
    
    - Streams 트림 전략 (`MAXLEN ~`) 적용 여부
        
    - DLQ(`orders:dlq`)와 수동 재처리 플로우 마련
        

---

이 문서만 잘 이해하면,  
지금 하고 있는 “블랙프라이데이 순간 100명 동시 주문” 시나리오는 Streams + 워커 풀 구조로 꽤 안정적으로 설계할 수 있어.

원하면 **너 지금 프로젝트 코드 구조(장고/패스트API/Worker)** 기준으로

- 폴더 구조
    
- 설정 파일(redis, worker 실행 스크립트)
    
- 로컬 부하 테스트 시나리오
    

까지 이어서 설계해줄게.

```
::contentReference[oaicite:0]{index=0}
```