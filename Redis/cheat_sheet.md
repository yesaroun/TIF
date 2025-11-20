# Redis Cheat Sheet

## 1. 기본 접속 & 진단
- `redis-cli -h <host> -p <port> -a <password>`: 원격 서버 접속
- `AUTH <password>`: 인증 (Redis 6 이상 ACL과 병행 가능)
- `PING` / `ECHO <msg>`: 생존 여부 확인
- `INFO server|memory|stats`: 섹션별 메트릭 확인
- `MONITOR` / `SLOWLOG GET 10`: 실시간 명령 감시와 느린 쿼리 분석
- `CLIENT LIST` + `CLIENT KILL <addr>`: 연결 추적 및 차단

## 2. 키 & 만료 관리
- `SET key value [NX|XX] [EX|PX <ttl>] [KEEPTTL]`: 조건부 설정 + 만료
- `GETSET key value` / `GETDEL key`: 원자적 교체 또는 삭제
- `DEL key1 key2` vs `UNLINK key`: 동기 삭제 vs 백그라운드 삭제
- `EXPIRE key <sec>` / `PEXPIRE key <ms>` / `PERSIST key`
- `TTL key` / `PTTL key`: 남은 만료 시간 확인, -1=없음, -2=존재하지 않음
- `SCAN cursor MATCH pattern COUNT 100`: 점진적 키 탐색 (KEYS 금지)

## 3. 주요 자료구조 패턴
### Strings
- `SET/GET/INCRBYFLOAT/APPEND` 등 기본 연산
- `MSET` + `MGET`로 배치 처리, 파이프라인으로 RTT 줄이기
- Bit patterns: `SETBIT key offset 1`, `BITCOUNT key`, `BITFIELD`

### Lists (작업 큐)
- `LPUSH` + `RPOP` (단순 스택/큐)
- `BRPOP key timeout`: 소비자 블로킹 poll
- `LPOS key element RANK 1`: 중복 요소 탐색
- `LTRIM key start stop`: 고정 길이 큐 유지

### Hashes (문서/객체)
- `HSET user:1 name seoul age 29`
- `HINCRBY account:1 balance 100`
- `HSCAN hash 0 MATCH profile:* COUNT 50`: 큰 해시 탐색

### Sets (유일 집합)
- `SADD`, `SREM`, `SISMEMBER`
- 관계 연산: `SINTER`, `SUNION`, `SDIFF`
- 확률적 추정: `PFADD`, `PFCOUNT` (HyperLogLog)

### Sorted Sets (랭킹)
- `ZADD leaderboard 900 score:alice`
- `ZRANGE leaderboard 0 9 WITHSCORES` (정방향) / `ZREVRANGE`
- `ZINCRBY leaderboard 15 score:alice`
- `ZPOPMAX leaderboard`: 상위 N 추출

### Streams (로그/이벤트)
- `XADD mystream * user alice action login`
- `XREAD BLOCK 5000 STREAMS mystream $`: 실시간 읽기
- Consumer Group: `XGROUP CREATE mystream group1 $ MKSTREAM`
- `XREADGROUP GROUP group1 c1 BLOCK 0 STREAMS mystream >`
- `XACK mystream group1 <id>`: 처리 완료 표시, 미처리 확인은 `XPENDING`

## 4. Pub/Sub vs Streams
- Pub/Sub: `SUBSCRIBE channel`, `PUBLISH channel message` (stateless, 유실 가능)
- Streams: 영속 로그, 재처리/재플레이 가능, backpressure 제어
- 실시간 알람은 Pub/Sub, 업무 이벤트는 Streams 추천

## 5. 트랜잭션 & 동시성
- `MULTI` → 커맨드 적재 → `EXEC` / `DISCARD`
- 옵티미스틱 락: `WATCH key1 key2` 후 조건 변경 감지
- 분산 락: `SET resource uuid NX PX 30000`, Lua 스크립트로 안전 해제
- Pipeline: RTT 감소, 필요 시 `MULTI`와 조합 가능

## 6. Lua & 원자 스크립트
```lua
-- 예: 조건부 감소 (재고 0 이하 금지)
local stock = redis.call('GET', KEYS[1]) or '0'
if tonumber(stock) <= 0 then
    return {err = 'OUT_OF_STOCK'}
end
redis.call('DECR', KEYS[1])
return redis.call('GET', KEYS[1])
```
- 실행: `EVAL <script> 1 inventory:sku123`
- 반복 사용 시 `SCRIPT LOAD` → `EVALSHA sha 1 key`
- `redis.replicate_commands()` 호출로 리플리케이션 보장 (Redis 5+)

## 7. 백업 & 영속성
- RDB 스냅샷: `SAVE` (블로킹) / `BGSAVE` (비동기)
- AOF: `CONFIG SET appendonly yes`, 재작성은 `BGREWRITEAOF`
- 하이브리드: RDB + AOF 동시 사용, `appendfsync everysec` 권장
- `MEMORY DOCTOR` / `MEMORY STATS`로 메모리 병목 진단

## 8. 클러스터 & 샤딩 핵심
- 해시 태그: `SET user:{42}:profile {...}` → 동일 슬롯 보장
- `CLUSTER NODES`, `CLUSTER INFO`, `CLUSTER KEYSLOT key`
- 리밸런스: `CLUSTER SETSLOT <slot> IMPORTING <node-id>` 등 단계적 이동
- 멀티키 명령은 동일 슬롯 키에만 허용 (또는 `redis-cli --cluster` 유틸 사용)

## 9. 운영 체크리스트
- 모니터링: latency spike → `LATENCY LATEST`
- 메모리 압박 시 `maxmemory` 정책 선택 (`volatile-lru`, `allkeys-lfu` 등)
- 복제 지연 감시: `INFO replication`의 `master_link_status`, `slave_repl_offset`
- 보안: 기본 포트 변경, `rename-command CONFIG ""`, ACL 로깅 (`ACL LOG`)
- 업그레이드 순서: replica 추가 → sync → failover → 구버전 제거

## 10. 자주 보는 패턴 키 설계
- `entity:{id}:field` (ex. `order:{20240101}:status`)
- TTL 있는 캐시: `cache:profile:{userId}` + `EX 300`
- 분산 잠금: `lock:{resource}`
- 작업 큐: `queue:email:pending`, 처리 후 `queue:email:done`
- 슬라이딩 윈도우 레이트 리밋: `incr` + `expire` 또는 Sorted Set timestamp 윈도우

> 빠른 기억을 위한 요약: 키 설계(네임스페이스) → 만료 정책 → 자료구조 선택 → 동시성 보호 → 운영 모니터링 순으로 점검하면 대부분의 Redis 이슈를 예방할 수 있다.
