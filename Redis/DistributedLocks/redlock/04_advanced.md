# RedLock 고급 주제 및 최적화

## 목차

1. [모니터링과 메트릭](#모니터링과-메트릭)
2. [대규모 시스템 최적화](#대규모-시스템-최적화)
3. [장애 허용성과 복원력](#장애-허용성과-복원력)
4. [고급 패턴](#고급-패턴)
5. [다른 시스템과의 통합](#다른-시스템과의-통합)
6. [프로덕션 배포](#프로덕션-배포)

---

## 모니터링과 메트릭

### 1. 포괄적인 메트릭 수집

```python
import time
import redis
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict
import prometheus_client as prom
import json

@dataclass
class DetailedMetrics:
    """상세 메트릭 데이터"""
    acquisition_count: int = 0
    acquisition_failures: int = 0
    acquisition_timeouts: int = 0
    release_count: int = 0
    expired_locks: int = 0

    total_wait_time: float = 0
    total_hold_time: float = 0
    max_wait_time: float = 0
    max_hold_time: float = 0
    min_wait_time: float = float('inf')
    min_hold_time: float = float('inf')

    quorum_failures: int = 0
    network_errors: int = 0

    # 히스토그램 데이터
    wait_time_histogram: List[float] = field(default_factory=list)
    hold_time_histogram: List[float] = field(default_factory=list)

    # 타임스탬프
    first_acquisition: Optional[float] = None
    last_acquisition: Optional[float] = None

class MetricsCollector:
    """RedLock 메트릭 수집기"""

    def __init__(self, namespace="redlock"):
        # Prometheus 메트릭 정의
        self.prom_acquisition_total = prom.Counter(
            f'{namespace}_acquisition_total',
            'Total number of lock acquisition attempts',
            ['resource', 'status']
        )

        self.prom_wait_duration = prom.Histogram(
            f'{namespace}_wait_duration_seconds',
            'Time spent waiting for lock acquisition',
            ['resource'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10)
        )

        self.prom_hold_duration = prom.Histogram(
            f'{namespace}_hold_duration_seconds',
            'Time spent holding the lock',
            ['resource'],
            buckets=(0.01, 0.05, 0.1, 0.5, 1, 5, 10, 30, 60)
        )

        self.prom_active_locks = prom.Gauge(
            f'{namespace}_active_locks',
            'Number of currently held locks',
            ['resource']
        )

        self.prom_quorum_size = prom.Gauge(
            f'{namespace}_quorum_size',
            'Number of Redis instances that granted the lock',
            ['resource']
        )

        # 내부 메트릭 저장소
        self.metrics: Dict[str, DetailedMetrics] = defaultdict(DetailedMetrics)
        self.active_locks: Dict[str, float] = {}

    def record_acquisition_attempt(self, resource: str, success: bool,
                                   wait_time: float, quorum_size: int = 0):
        """락 획득 시도 기록"""
        metrics = self.metrics[resource]

        if success:
            metrics.acquisition_count += 1
            self.prom_acquisition_total.labels(resource=resource, status="success").inc()

            # 활성 락 추적
            self.active_locks[resource] = time.time()
            self.prom_active_locks.labels(resource=resource).inc()

            # Quorum 크기 기록
            self.prom_quorum_size.labels(resource=resource).set(quorum_size)

            # 타임스탬프 업데이트
            metrics.last_acquisition = time.time()
            if metrics.first_acquisition is None:
                metrics.first_acquisition = time.time()
        else:
            metrics.acquisition_failures += 1
            self.prom_acquisition_total.labels(resource=resource, status="failure").inc()

        # 대기 시간 기록
        metrics.total_wait_time += wait_time
        metrics.wait_time_histogram.append(wait_time)
        metrics.max_wait_time = max(metrics.max_wait_time, wait_time)
        metrics.min_wait_time = min(metrics.min_wait_time, wait_time)

        self.prom_wait_duration.labels(resource=resource).observe(wait_time)

    def record_release(self, resource: str):
        """락 해제 기록"""
        if resource in self.active_locks:
            hold_time = time.time() - self.active_locks[resource]
            del self.active_locks[resource]

            metrics = self.metrics[resource]
            metrics.release_count += 1
            metrics.total_hold_time += hold_time
            metrics.hold_time_histogram.append(hold_time)
            metrics.max_hold_time = max(metrics.max_hold_time, hold_time)
            metrics.min_hold_time = min(metrics.min_hold_time, hold_time)

            self.prom_hold_duration.labels(resource=resource).observe(hold_time)
            self.prom_active_locks.labels(resource=resource).dec()

    def record_timeout(self, resource: str):
        """타임아웃 기록"""
        self.metrics[resource].acquisition_timeouts += 1
        self.prom_acquisition_total.labels(resource=resource, status="timeout").inc()

    def record_network_error(self, resource: str):
        """네트워크 에러 기록"""
        self.metrics[resource].network_errors += 1
        self.prom_acquisition_total.labels(resource=resource, status="network_error").inc()

    def get_statistics(self, resource: str) -> dict:
        """통계 정보 반환"""
        metrics = self.metrics[resource]

        total_attempts = metrics.acquisition_count + metrics.acquisition_failures
        if total_attempts == 0:
            return {"message": "No data available"}

        success_rate = (metrics.acquisition_count / total_attempts) * 100
        avg_wait_time = metrics.total_wait_time / total_attempts

        stats = {
            "resource": resource,
            "success_rate": round(success_rate, 2),
            "total_attempts": total_attempts,
            "successful_acquisitions": metrics.acquisition_count,
            "failed_acquisitions": metrics.acquisition_failures,
            "timeouts": metrics.acquisition_timeouts,
            "network_errors": metrics.network_errors,
            "average_wait_time": round(avg_wait_time, 3),
            "max_wait_time": round(metrics.max_wait_time, 3),
            "active_locks": len(self.active_locks)
        }

        if metrics.release_count > 0:
            avg_hold_time = metrics.total_hold_time / metrics.release_count
            stats.update({
                "average_hold_time": round(avg_hold_time, 3),
                "max_hold_time": round(metrics.max_hold_time, 3),
                "min_hold_time": round(metrics.min_hold_time, 3)
            })

        return stats

    def export_percentiles(self, resource: str) -> dict:
        """백분위수 계산"""
        import numpy as np

        metrics = self.metrics[resource]

        if not metrics.wait_time_histogram:
            return {}

        wait_times = np.array(metrics.wait_time_histogram)
        hold_times = np.array(metrics.hold_time_histogram) if metrics.hold_time_histogram else np.array([])

        result = {
            "wait_time_percentiles": {
                "p50": np.percentile(wait_times, 50),
                "p75": np.percentile(wait_times, 75),
                "p90": np.percentile(wait_times, 90),
                "p95": np.percentile(wait_times, 95),
                "p99": np.percentile(wait_times, 99)
            }
        }

        if len(hold_times) > 0:
            result["hold_time_percentiles"] = {
                "p50": np.percentile(hold_times, 50),
                "p75": np.percentile(hold_times, 75),
                "p90": np.percentile(hold_times, 90),
                "p95": np.percentile(hold_times, 95),
                "p99": np.percentile(hold_times, 99)
            }

        return result
```

### 2. 실시간 모니터링 대시보드

```python
from flask import Flask, jsonify, render_template_string
import threading
import time

class RedLockMonitor:
    """실시간 모니터링 대시보드"""

    def __init__(self, metrics_collector: MetricsCollector, redis_instances: List[redis.Redis]):
        self.metrics = metrics_collector
        self.redis_instances = redis_instances
        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/metrics')
        def metrics_endpoint():
            """Prometheus 메트릭 엔드포인트"""
            return prom.generate_latest()

        @self.app.route('/health')
        def health_check():
            """헬스 체크 엔드포인트"""
            health_status = self.check_redis_health()
            is_healthy = all(status['healthy'] for status in health_status.values())

            return jsonify({
                "healthy": is_healthy,
                "redis_instances": health_status,
                "active_locks": len(self.metrics.active_locks),
                "timestamp": time.time()
            }), 200 if is_healthy else 503

        @self.app.route('/stats/<resource>')
        def resource_stats(resource):
            """리소스별 통계"""
            stats = self.metrics.get_statistics(resource)
            percentiles = self.metrics.export_percentiles(resource)

            return jsonify({
                **stats,
                **percentiles,
                "timestamp": time.time()
            })

        @self.app.route('/dashboard')
        def dashboard():
            """웹 대시보드"""
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>RedLock Monitor</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .metric { display: inline-block; margin: 10px; padding: 10px;
                             border: 1px solid #ddd; border-radius: 5px; }
                    .chart-container { width: 48%; display: inline-block; margin: 1%; }
                    h2 { color: #333; }
                </style>
            </head>
            <body>
                <h1>RedLock Monitor Dashboard</h1>

                <div id="health-status"></div>
                <div id="metrics-container"></div>

                <div class="chart-container">
                    <canvas id="successRateChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="waitTimeChart"></canvas>
                </div>

                <script>
                    // 실시간 업데이트 로직
                    function updateDashboard() {
                        fetch('/health')
                            .then(response => response.json())
                            .then(data => {
                                const healthDiv = document.getElementById('health-status');
                                healthDiv.innerHTML = `
                                    <h2>System Health</h2>
                                    <div class="metric">
                                        Status: ${data.healthy ? '✅ Healthy' : '❌ Unhealthy'}
                                    </div>
                                    <div class="metric">
                                        Active Locks: ${data.active_locks}
                                    </div>
                                `;
                            });
                    }

                    // 1초마다 업데이트
                    setInterval(updateDashboard, 1000);
                    updateDashboard();
                </script>
            </body>
            </html>
            ''')

    def check_redis_health(self) -> dict:
        """Redis 인스턴스 헬스 체크"""
        health_status = {}

        for i, redis_instance in enumerate(self.redis_instances):
            instance_key = f"redis_{i}"
            try:
                start = time.time()
                redis_instance.ping()
                latency = (time.time() - start) * 1000  # ms

                # 메모리 사용량 확인
                info = redis_instance.info('memory')
                memory_used = info.get('used_memory', 0)
                memory_max = info.get('maxmemory', 0)

                health_status[instance_key] = {
                    "healthy": True,
                    "latency_ms": round(latency, 2),
                    "memory_used_mb": round(memory_used / 1024 / 1024, 2),
                    "memory_usage_percent": round((memory_used / memory_max) * 100, 2) if memory_max > 0 else 0
                }
            except Exception as e:
                health_status[instance_key] = {
                    "healthy": False,
                    "error": str(e)
                }

        return health_status

    def run(self, host='0.0.0.0', port=5000):
        """모니터링 서버 실행"""
        self.app.run(host=host, port=port, threaded=True)
```

### 3. 알림 시스템

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from typing import Callable

class AlertManager:
    """RedLock 알림 관리자"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.alert_rules = []
        self.alert_channels = []

    def add_rule(self, name: str, condition: Callable, message: str):
        """알림 규칙 추가"""
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "message": message,
            "last_triggered": None
        })

    def add_slack_channel(self, webhook_url: str):
        """Slack 알림 채널 추가"""
        def send_slack(message):
            requests.post(webhook_url, json={"text": message})
        self.alert_channels.append(send_slack)

    def add_email_channel(self, smtp_server: str, from_email: str, to_emails: List[str]):
        """이메일 알림 채널 추가"""
        def send_email(message):
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = 'RedLock Alert'
            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP(smtp_server) as server:
                server.send_message(msg)

        self.alert_channels.append(send_email)

    def check_alerts(self):
        """알림 규칙 검사"""
        for rule in self.alert_rules:
            # 조건 검사
            if rule["condition"](self.metrics):
                # 중복 알림 방지 (5분 간격)
                now = time.time()
                if rule["last_triggered"] and now - rule["last_triggered"] < 300:
                    continue

                # 알림 발송
                alert_message = f"[{rule['name']}] {rule['message']}"
                for channel in self.alert_channels:
                    try:
                        channel(alert_message)
                    except Exception as e:
                        print(f"Failed to send alert: {e}")

                rule["last_triggered"] = now

    def setup_common_alerts(self):
        """일반적인 알림 규칙 설정"""

        # 높은 실패율 알림
        self.add_rule(
            "High Failure Rate",
            lambda m: any(
                m.get_statistics(r).get("success_rate", 100) < 50
                for r in m.metrics.keys()
            ),
            "Lock acquisition success rate dropped below 50%"
        )

        # 긴 대기 시간 알림
        self.add_rule(
            "Long Wait Time",
            lambda m: any(
                m.get_statistics(r).get("max_wait_time", 0) > 10
                for r in m.metrics.keys()
            ),
            "Lock wait time exceeded 10 seconds"
        )

        # 너무 많은 활성 락
        self.add_rule(
            "Too Many Active Locks",
            lambda m: len(m.active_locks) > 100,
            "More than 100 locks are currently active"
        )

# 사용 예시
metrics_collector = MetricsCollector()
alert_manager = AlertManager(metrics_collector)

# Slack 알림 설정
alert_manager.add_slack_channel("https://hooks.slack.com/services/YOUR/WEBHOOK/URL")

# 알림 규칙 설정
alert_manager.setup_common_alerts()

# 주기적으로 알림 검사 (별도 스레드에서)
def alert_checker():
    while True:
        alert_manager.check_alerts()
        time.sleep(30)  # 30초마다 검사

threading.Thread(target=alert_checker, daemon=True).start()
```

---

## 대규모 시스템 최적화

### 1. 계층적 락 시스템

```python
from enum import Enum
from typing import Optional, Set

class LockLevel(Enum):
    """락 레벨 정의"""
    GLOBAL = 1      # 전체 시스템
    TENANT = 2      # 테넌트 레벨
    RESOURCE = 3    # 리소스 레벨
    ENTITY = 4      # 개별 엔티티

class HierarchicalLockManager:
    """계층적 락 관리자"""

    def __init__(self, redis_instances: List[redis.Redis]):
        self.redis_instances = redis_instances
        self.lock_hierarchy = {
            LockLevel.GLOBAL: None,
            LockLevel.TENANT: LockLevel.GLOBAL,
            LockLevel.RESOURCE: LockLevel.TENANT,
            LockLevel.ENTITY: LockLevel.RESOURCE
        }
        self.held_locks: Dict[str, RedLock] = {}

    def acquire_hierarchical(self, level: LockLevel, *identifiers, ttl=10000) -> Optional[RedLock]:
        """계층적 락 획득"""

        # 상위 레벨 락이 필요한지 확인
        parent_level = self.lock_hierarchy[level]
        if parent_level and len(identifiers) > 1:
            parent_lock_key = self._build_lock_key(parent_level, identifiers[:-1])
            if parent_lock_key not in self.held_locks:
                # 상위 레벨 락을 먼저 획득
                parent_lock = self.acquire_hierarchical(
                    parent_level,
                    *identifiers[:-1],
                    ttl=ttl
                )
                if not parent_lock:
                    return None

        # 현재 레벨 락 획득
        lock_key = self._build_lock_key(level, identifiers)
        lock = RedLock(self.redis_instances, lock_key, ttl)

        if lock.acquire():
            self.held_locks[lock_key] = lock
            return lock

        return None

    def _build_lock_key(self, level: LockLevel, identifiers) -> str:
        """락 키 생성"""
        parts = [f"lock:{level.name.lower()}"]
        parts.extend(str(id) for id in identifiers)
        return ":".join(parts)

    def release_all(self):
        """모든 보유 락 해제 (하위 레벨부터)"""
        sorted_locks = sorted(
            self.held_locks.items(),
            key=lambda x: self._get_level_from_key(x[0]),
            reverse=True  # 하위 레벨부터
        )

        for lock_key, lock in sorted_locks:
            try:
                lock.release()
                del self.held_locks[lock_key]
            except Exception as e:
                print(f"Failed to release lock {lock_key}: {e}")

    def _get_level_from_key(self, lock_key: str) -> int:
        """락 키에서 레벨 추출"""
        for level in LockLevel:
            if level.name.lower() in lock_key:
                return level.value
        return 0

# 사용 예시
lock_manager = HierarchicalLockManager(redis_instances)

# 테넌트 > 리소스 > 엔티티 순으로 락 획득
entity_lock = lock_manager.acquire_hierarchical(
    LockLevel.ENTITY,
    "tenant_123",  # 테넌트 ID
    "orders",      # 리소스 타입
    "order_456"    # 엔티티 ID
)

if entity_lock:
    try:
        # 작업 수행
        process_order("order_456")
    finally:
        lock_manager.release_all()
```

### 2. 분산 락 풀 (Lock Pool)

```python
import queue
import threading
from contextlib import contextmanager

class LockPool:
    """락 풀 관리자 - 락 재사용으로 오버헤드 감소"""

    def __init__(self, redis_instances: List[redis.Redis], pool_size=100):
        self.redis_instances = redis_instances
        self.pool_size = pool_size
        self.available_locks = queue.Queue(maxsize=pool_size)
        self.in_use_locks: Set[str] = set()
        self.lock = threading.Lock()

        # 미리 락 객체 생성
        self._initialize_pool()

    def _initialize_pool(self):
        """락 풀 초기화"""
        for _ in range(self.pool_size):
            # 재사용 가능한 락 객체 생성
            lock_wrapper = ReusableRedLock(self.redis_instances)
            self.available_locks.put(lock_wrapper)

    @contextmanager
    def acquire_from_pool(self, resource_name: str, ttl=10000, timeout=30):
        """풀에서 락 획득"""
        lock_wrapper = None

        try:
            # 풀에서 락 객체 가져오기
            lock_wrapper = self.available_locks.get(timeout=timeout)

            # 리소스 이름과 TTL 설정
            lock_wrapper.configure(resource_name, ttl)

            # 락 획득
            if not lock_wrapper.acquire():
                raise LockAcquisitionError(f"Failed to acquire lock for {resource_name}")

            with self.lock:
                self.in_use_locks.add(resource_name)

            yield lock_wrapper

        finally:
            if lock_wrapper:
                try:
                    # 락 해제
                    lock_wrapper.release()

                    with self.lock:
                        self.in_use_locks.discard(resource_name)

                    # 풀에 반환
                    lock_wrapper.reset()
                    self.available_locks.put(lock_wrapper)
                except:
                    pass

    def get_pool_stats(self) -> dict:
        """풀 상태 조회"""
        return {
            "pool_size": self.pool_size,
            "available": self.available_locks.qsize(),
            "in_use": len(self.in_use_locks),
            "utilization": (len(self.in_use_locks) / self.pool_size) * 100
        }

class ReusableRedLock(RedLock):
    """재사용 가능한 RedLock"""

    def __init__(self, redis_instances):
        self.redis_instances = redis_instances
        self.configured = False

    def configure(self, resource_name: str, ttl: int):
        """락 설정"""
        self.resource_name = resource_name
        self.ttl = ttl
        self.lock_value = str(uuid.uuid4())
        self.quorum = len(self.redis_instances) // 2 + 1
        self.configured = True

    def reset(self):
        """락 초기화"""
        self.configured = False
        self.resource_name = None
        self.ttl = None
        self.lock_value = None
```

### 3. 적응형 TTL 관리

```python
import statistics
from collections import deque

class AdaptiveTTLManager:
    """작업 시간 기반 적응형 TTL 관리"""

    def __init__(self, initial_ttl=10000, window_size=100):
        self.base_ttl = initial_ttl
        self.window_size = window_size
        self.execution_times: Dict[str, deque] = {}
        self.ttl_multiplier = 3.0  # 안전 계수

    def record_execution(self, resource_name: str, execution_time: float):
        """실행 시간 기록"""
        if resource_name not in self.execution_times:
            self.execution_times[resource_name] = deque(maxlen=self.window_size)

        self.execution_times[resource_name].append(execution_time)

    def get_adaptive_ttl(self, resource_name: str) -> int:
        """적응형 TTL 계산"""
        if resource_name not in self.execution_times or len(self.execution_times[resource_name]) < 10:
            # 충분한 데이터가 없으면 기본값 사용
            return self.base_ttl

        times = list(self.execution_times[resource_name])

        # 통계 계산
        mean_time = statistics.mean(times)
        stdev_time = statistics.stdev(times) if len(times) > 1 else 0
        p95_time = sorted(times)[int(len(times) * 0.95)]

        # 적응형 TTL 계산 (P95 + 2*표준편차)
        adaptive_ttl = (p95_time + 2 * stdev_time) * self.ttl_multiplier * 1000  # ms 변환

        # 최소/최대값 제한
        min_ttl = self.base_ttl
        max_ttl = self.base_ttl * 10

        return int(max(min_ttl, min(adaptive_ttl, max_ttl)))

    def get_statistics(self, resource_name: str) -> dict:
        """통계 정보 반환"""
        if resource_name not in self.execution_times:
            return {}

        times = list(self.execution_times[resource_name])
        if not times:
            return {}

        return {
            "resource": resource_name,
            "sample_count": len(times),
            "mean_execution_time": statistics.mean(times),
            "median_execution_time": statistics.median(times),
            "max_execution_time": max(times),
            "min_execution_time": min(times),
            "recommended_ttl": self.get_adaptive_ttl(resource_name)
        }

# 적응형 TTL을 사용하는 RedLock
class AdaptiveRedLock(RedLock):
    def __init__(self, redis_instances, resource_name, ttl_manager: AdaptiveTTLManager):
        self.ttl_manager = ttl_manager
        adaptive_ttl = ttl_manager.get_adaptive_ttl(resource_name)
        super().__init__(redis_instances, resource_name, adaptive_ttl)
        self.start_time = None

    def acquire(self, *args, **kwargs):
        result = super().acquire(*args, **kwargs)
        if result:
            self.start_time = time.time()
        return result

    def release(self):
        if self.start_time:
            execution_time = time.time() - self.start_time
            self.ttl_manager.record_execution(self.resource_name, execution_time)
        super().release()
```

---

## 장애 허용성과 복원력

### 1. Circuit Breaker 패턴

```python
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # 정상 동작
    OPEN = "open"          # 차단
    HALF_OPEN = "half_open"  # 부분 허용

class CircuitBreaker:
    """RedLock Circuit Breaker"""

    def __init__(self, failure_threshold=5, recovery_timeout=60, success_threshold=2):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """Circuit Breaker를 통한 함수 호출"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                # 차단 상태 - 복구 시간 확인
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitOpenError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """성공 시 처리"""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def _on_failure(self):
        """실패 시 처리"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def get_state(self) -> dict:
        """현재 상태 조회"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count
        }

class ResilientRedLock:
    """Circuit Breaker가 적용된 RedLock"""

    def __init__(self, redis_instances, resource_name, ttl=10000):
        self.lock = RedLock(redis_instances, resource_name, ttl)
        self.circuit_breaker = CircuitBreaker()

    def acquire(self):
        """Circuit Breaker를 통한 락 획득"""
        return self.circuit_breaker.call(self.lock.acquire)

    def release(self):
        """락 해제"""
        try:
            self.lock.release()
        except:
            pass  # 해제 실패는 무시
```

### 2. Fallback 메커니즘

```python
class FallbackLockManager:
    """Fallback 메커니즘이 있는 락 관리자"""

    def __init__(self, primary_instances: List[redis.Redis],
                 backup_instances: Optional[List[redis.Redis]] = None):
        self.primary_instances = primary_instances
        self.backup_instances = backup_instances or []
        self.local_locks: Dict[str, threading.Lock] = {}
        self.lock_strategies = [
            self._try_primary_redlock,
            self._try_backup_redlock,
            self._try_local_lock
        ]

    def acquire_with_fallback(self, resource_name: str, ttl=10000) -> tuple:
        """Fallback을 사용한 락 획득"""

        for strategy_name, strategy in self.lock_strategies:
            try:
                lock = strategy(resource_name, ttl)
                if lock:
                    return (lock, strategy_name)
            except Exception as e:
                print(f"Strategy {strategy_name} failed: {e}")
                continue

        return (None, None)

    def _try_primary_redlock(self, resource_name: str, ttl: int):
        """기본 RedLock 시도"""
        lock = RedLock(self.primary_instances, resource_name, ttl)
        if lock.acquire():
            return lock
        return None

    def _try_backup_redlock(self, resource_name: str, ttl: int):
        """백업 RedLock 시도"""
        if not self.backup_instances:
            return None

        lock = RedLock(self.backup_instances, resource_name, ttl)
        if lock.acquire():
            return lock
        return None

    def _try_local_lock(self, resource_name: str, ttl: int):
        """로컬 락 시도 (최후의 수단)"""
        if resource_name not in self.local_locks:
            self.local_locks[resource_name] = threading.Lock()

        local_lock = self.local_locks[resource_name]
        if local_lock.acquire(blocking=False):
            # TTL 시뮬레이션을 위한 타이머
            def auto_release():
                time.sleep(ttl / 1000)
                try:
                    local_lock.release()
                except:
                    pass

            threading.Thread(target=auto_release, daemon=True).start()
            return local_lock

        return None
```

### 3. 자가 치유 시스템

```python
class SelfHealingLockManager:
    """자가 치유 기능이 있는 락 관리자"""

    def __init__(self, redis_instances: List[redis.Redis]):
        self.redis_instances = redis_instances
        self.unhealthy_instances: Set[int] = set()
        self.health_check_interval = 30  # 초
        self.recovery_attempts: Dict[int, int] = {}

        # 헬스 체크 스레드 시작
        self._start_health_monitor()

    def _start_health_monitor(self):
        """헬스 모니터링 시작"""
        def monitor():
            while True:
                self._check_and_heal()
                time.sleep(self.health_check_interval)

        threading.Thread(target=monitor, daemon=True).start()

    def _check_and_heal(self):
        """인스턴스 검사 및 복구"""
        for i, instance in enumerate(self.redis_instances):
            if i in self.unhealthy_instances:
                # 복구 시도
                if self._try_recovery(i, instance):
                    self.unhealthy_instances.remove(i)
                    self.recovery_attempts[i] = 0
                    print(f"Instance {i} recovered")
            else:
                # 헬스 체크
                if not self._is_healthy(instance):
                    self.unhealthy_instances.add(i)
                    print(f"Instance {i} marked as unhealthy")

    def _is_healthy(self, instance: redis.Redis) -> bool:
        """인스턴스 헬스 체크"""
        try:
            instance.ping()
            return True
        except:
            return False

    def _try_recovery(self, index: int, instance: redis.Redis) -> bool:
        """인스턴스 복구 시도"""
        self.recovery_attempts[index] = self.recovery_attempts.get(index, 0) + 1

        if self.recovery_attempts[index] > 3:
            # 3회 이상 실패 시 교체
            return self._replace_instance(index)

        return self._is_healthy(instance)

    def _replace_instance(self, index: int) -> bool:
        """인스턴스 교체"""
        try:
            # 새 연결 시도
            old_instance = self.redis_instances[index]
            new_instance = redis.Redis(
                host=old_instance.connection_pool.connection_kwargs['host'],
                port=old_instance.connection_pool.connection_kwargs['port'],
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 3,  # TCP_KEEPCNT
                }
            )

            if self._is_healthy(new_instance):
                self.redis_instances[index] = new_instance
                return True
        except:
            pass

        return False

    def get_healthy_instances(self) -> List[redis.Redis]:
        """건강한 인스턴스만 반환"""
        return [
            instance for i, instance in enumerate(self.redis_instances)
            if i not in self.unhealthy_instances
        ]

    def acquire_lock(self, resource_name: str, ttl=10000) -> Optional[RedLock]:
        """건강한 인스턴스만 사용하여 락 획득"""
        healthy_instances = self.get_healthy_instances()

        if len(healthy_instances) < 3:
            raise InsufficientHealthyInstances(
                f"Only {len(healthy_instances)} healthy instances available"
            )

        return RedLock(healthy_instances, resource_name, ttl)
```

---

## 고급 패턴

### 1. 조건부 락 (Conditional Lock)

```python
class ConditionalLock:
    """조건 기반 락"""

    def __init__(self, redis_instances: List[redis.Redis]):
        self.redis_instances = redis_instances

    def acquire_if(self, resource_name: str, condition: Callable,
                   ttl=10000, max_wait=30) -> Optional[RedLock]:
        """조건이 만족될 때만 락 획득"""

        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 조건 확인
            if not condition():
                time.sleep(0.5)
                continue

            # 조건 만족 - 락 획득 시도
            lock = RedLock(self.redis_instances, resource_name, ttl)

            if lock.acquire():
                # 다시 조건 확인 (double-check)
                if condition():
                    return lock
                else:
                    # 조건 변경됨 - 락 해제
                    lock.release()

            time.sleep(0.5)

        return None

# 사용 예시
def check_business_hours():
    """영업 시간 확인"""
    now = datetime.now()
    return 9 <= now.hour < 18

conditional_lock = ConditionalLock(redis_instances)

# 영업 시간에만 작업 수행
lock = conditional_lock.acquire_if(
    "lock:batch_job",
    check_business_hours,
    ttl=60000
)

if lock:
    try:
        run_batch_job()
    finally:
        lock.release()
```

### 2. 우선순위 큐 기반 락

```python
import heapq

class PriorityLock:
    """우선순위 기반 락"""

    def __init__(self, redis_instances: List[redis.Redis]):
        self.redis_instances = redis_instances
        self.redis = redis_instances[0]  # 큐 관리용

    def acquire_with_priority(self, resource_name: str, priority: int,
                              client_id: str, ttl=10000, max_wait=30) -> Optional[RedLock]:
        """우선순위를 고려한 락 획득"""

        queue_key = f"priority_queue:{resource_name}"
        processing_key = f"processing:{resource_name}"

        # 큐에 추가 (priority, timestamp, client_id)
        entry = json.dumps({
            "priority": priority,
            "timestamp": time.time(),
            "client_id": client_id
        })

        # Redis Sorted Set에 추가 (score = priority * -1 for min-heap)
        self.redis.zadd(queue_key, {entry: -priority})

        start_time = time.time()

        try:
            while time.time() - start_time < max_wait:
                # 큐의 첫 번째 항목 확인
                first_items = self.redis.zrange(queue_key, 0, 0)

                if not first_items:
                    continue

                first_item = json.loads(first_items[0])

                # 내 차례인지 확인
                if first_item["client_id"] == client_id:
                    # 락 획득 시도
                    lock = RedLock(self.redis_instances, resource_name, ttl)

                    if lock.acquire():
                        # 큐에서 제거
                        self.redis.zrem(queue_key, entry)

                        # 처리 중 표시
                        self.redis.set(processing_key, client_id, px=ttl)

                        return lock

                # 대기
                time.sleep(0.2)

        finally:
            # 타임아웃 시 큐에서 제거
            self.redis.zrem(queue_key, entry)

        return None
```

### 3. 분산 세마포어

```python
class DistributedSemaphore:
    """분산 세마포어 구현"""

    def __init__(self, redis_instances: List[redis.Redis], resource_name: str,
                 max_permits: int):
        self.redis_instances = redis_instances
        self.resource_name = resource_name
        self.max_permits = max_permits
        self.redis = redis_instances[0]

        # 세마포어 초기화
        self._initialize_semaphore()

    def _initialize_semaphore(self):
        """세마포어 초기화"""
        permits_key = f"semaphore:permits:{self.resource_name}"

        # 원자적 초기화
        lua_script = """
        if redis.call("exists", KEYS[1]) == 0 then
            redis.call("set", KEYS[1], ARGV[1])
            return 1
        end
        return 0
        """

        self.redis.eval(lua_script, 1, permits_key, self.max_permits)

    def acquire(self, timeout=30) -> Optional[str]:
        """퍼밋 획득"""
        permits_key = f"semaphore:permits:{self.resource_name}"
        holders_key = f"semaphore:holders:{self.resource_name}"

        permit_id = str(uuid.uuid4())
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 퍼밋 획득 시도 (Lua 스크립트로 원자성 보장)
            lua_script = """
            local permits = tonumber(redis.call("get", KEYS[1]) or 0)
            if permits > 0 then
                redis.call("decr", KEYS[1])
                redis.call("sadd", KEYS[2], ARGV[1])
                return 1
            end
            return 0
            """

            result = self.redis.eval(
                lua_script,
                2,
                permits_key,
                holders_key,
                permit_id
            )

            if result == 1:
                return permit_id

            time.sleep(0.1)

        return None

    def release(self, permit_id: str):
        """퍼밋 해제"""
        permits_key = f"semaphore:permits:{self.resource_name}"
        holders_key = f"semaphore:holders:{self.resource_name}"

        # 퍼밋 해제 (Lua 스크립트)
        lua_script = """
        if redis.call("srem", KEYS[2], ARGV[1]) == 1 then
            redis.call("incr", KEYS[1])
            return 1
        end
        return 0
        """

        self.redis.eval(
            lua_script,
            2,
            permits_key,
            holders_key,
            permit_id
        )

    def available_permits(self) -> int:
        """사용 가능한 퍼밋 수"""
        permits_key = f"semaphore:permits:{self.resource_name}"
        return int(self.redis.get(permits_key) or 0)

# 사용 예시
semaphore = DistributedSemaphore(redis_instances, "api_rate_limit", max_permits=10)

# 동시에 10개까지만 처리
permit = semaphore.acquire(timeout=5)
if permit:
    try:
        # API 호출
        call_external_api()
    finally:
        semaphore.release(permit)
```

---

## 다른 시스템과의 통합

### 1. Kubernetes 통합

```python
from kubernetes import client, config
import os

class KubernetesRedLock:
    """Kubernetes 환경에서의 RedLock"""

    def __init__(self, namespace="default"):
        # Kubernetes 설정
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            config.load_incluster_config()  # Pod 내부에서 실행
        else:
            config.load_kube_config()  # 로컬 개발

        self.v1 = client.CoreV1Api()
        self.namespace = namespace
        self.redis_instances = self._discover_redis_instances()

    def _discover_redis_instances(self) -> List[redis.Redis]:
        """Redis 서비스 자동 발견"""
        instances = []

        # Redis 서비스 검색
        services = self.v1.list_namespaced_service(
            self.namespace,
            label_selector="app=redis,role=master"
        )

        for service in services.items:
            # 서비스 엔드포인트 가져오기
            endpoints = self.v1.read_namespaced_endpoints(
                service.metadata.name,
                self.namespace
            )

            for subset in endpoints.subsets:
                for address in subset.addresses:
                    for port in subset.ports:
                        instance = redis.Redis(
                            host=address.ip,
                            port=port.port,
                            decode_responses=True
                        )
                        instances.append(instance)

        return instances

    def create_configmap_lock(self, resource_name: str, ttl=60):
        """ConfigMap 기반 락 (Kubernetes 네이티브)"""
        configmap_name = f"lock-{resource_name}"

        try:
            # ConfigMap 생성 시도 (락 획득)
            configmap = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(
                    name=configmap_name,
                    annotations={
                        "lock-holder": os.environ.get("HOSTNAME", "unknown"),
                        "lock-time": str(time.time()),
                        "ttl": str(ttl)
                    }
                ),
                data={"locked": "true"}
            )

            self.v1.create_namespaced_config_map(
                namespace=self.namespace,
                body=configmap
            )

            return True

        except client.ApiException as e:
            if e.status == 409:  # Already exists
                # TTL 확인
                try:
                    existing = self.v1.read_namespaced_config_map(
                        configmap_name,
                        self.namespace
                    )

                    lock_time = float(existing.metadata.annotations.get("lock-time", 0))
                    lock_ttl = float(existing.metadata.annotations.get("ttl", 60))

                    if time.time() - lock_time > lock_ttl:
                        # 만료된 락 - 삭제 후 재시도
                        self.v1.delete_namespaced_config_map(
                            configmap_name,
                            self.namespace
                        )
                        return self.create_configmap_lock(resource_name, ttl)

                except:
                    pass

            return False

# Kubernetes CronJob에서 사용
if __name__ == "__main__":
    k8s_lock = KubernetesRedLock()

    if k8s_lock.create_configmap_lock("daily-backup", ttl=300):
        try:
            perform_backup()
        finally:
            # ConfigMap 삭제 (락 해제)
            k8s_lock.v1.delete_namespaced_config_map(
                "lock-daily-backup",
                k8s_lock.namespace
            )
```

### 2. Apache Kafka 통합

```python
from kafka import KafkaProducer, KafkaConsumer
import json

class KafkaIntegratedLock:
    """Kafka와 통합된 RedLock"""

    def __init__(self, redis_instances: List[redis.Redis],
                 kafka_bootstrap_servers: str):
        self.redis_instances = redis_instances

        # Kafka 프로듀서/컨슈머
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        self.consumer = KafkaConsumer(
            'lock-events',
            bootstrap_servers=kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

    def acquire_and_publish(self, resource_name: str, ttl=10000) -> Optional[RedLock]:
        """락 획득 후 Kafka에 이벤트 발행"""

        lock = RedLock(self.redis_instances, resource_name, ttl)

        if lock.acquire():
            # Kafka에 이벤트 발행
            event = {
                "event_type": "lock_acquired",
                "resource": resource_name,
                "holder": os.environ.get("HOSTNAME", "unknown"),
                "timestamp": time.time(),
                "ttl": ttl
            }

            self.producer.send('lock-events', value=event)
            self.producer.flush()

            return lock

        return None

    def release_and_publish(self, lock: RedLock):
        """락 해제 후 Kafka에 이벤트 발행"""

        lock.release()

        # Kafka에 이벤트 발행
        event = {
            "event_type": "lock_released",
            "resource": lock.resource_name,
            "holder": os.environ.get("HOSTNAME", "unknown"),
            "timestamp": time.time()
        }

        self.producer.send('lock-events', value=event)
        self.producer.flush()
```

---

## 프로덕션 배포

### 1. Docker Compose 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Redis 마스터 인스턴스들
  redis-1:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis1-data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis-2:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    volumes:
      - redis2-data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru

  redis-3:
    image: redis:7-alpine
    ports:
      - "6381:6379"
    volumes:
      - redis3-data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru

  redis-4:
    image: redis:7-alpine
    ports:
      - "6382:6379"
    volumes:
      - redis4-data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru

  redis-5:
    image: redis:7-alpine
    ports:
      - "6383:6379"
    volumes:
      - redis5-data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru

  # 모니터링
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards

  # RedLock 모니터링 앱
  redlock-monitor:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_HOSTS=redis-1:6379,redis-2:6379,redis-3:6379,redis-4:6379,redis-5:6379
    depends_on:
      - redis-1
      - redis-2
      - redis-3
      - redis-4
      - redis-5

volumes:
  redis1-data:
  redis2-data:
  redis3-data:
  redis4-data:
  redis5-data:
  prometheus-data:
  grafana-data:
```

### 2. Kubernetes 배포

```yaml
# redlock-deployment.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: redlock-system

---
# Redis StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: redlock-system
spec:
  serviceName: redis-service
  replicas: 5
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
        role: master
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: data
          mountPath: /data
        command:
        - redis-server
        - --appendonly
        - "yes"
        - --maxmemory
        - "256mb"
        - --maxmemory-policy
        - "allkeys-lru"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 1Gi

---
# Headless Service for StatefulSet
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: redlock-system
spec:
  clusterIP: None
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379

---
# ConfigMap for application config
apiVersion: v1
kind: ConfigMap
metadata:
  name: redlock-config
  namespace: redlock-system
data:
  config.yaml: |
    redis_instances:
      - redis-0.redis-service:6379
      - redis-1.redis-service:6379
      - redis-2.redis-service:6379
      - redis-3.redis-service:6379
      - redis-4.redis-service:6379

    lock_defaults:
      ttl: 10000
      retry_count: 3
      retry_delay: 200

    monitoring:
      enabled: true
      prometheus_port: 9090

    alerts:
      slack_webhook: "${SLACK_WEBHOOK_URL}"
      email_smtp: "smtp.gmail.com:587"
```

### 3. 운영 스크립트

```python
#!/usr/bin/env python3
"""
RedLock 운영 관리 스크립트
"""

import argparse
import sys
import yaml
from typing import List
import redis

class RedLockOperations:
    """RedLock 운영 도구"""

    def __init__(self, config_file: str):
        with open(config_file) as f:
            self.config = yaml.safe_load(f)

        self.redis_instances = self._connect_redis()

    def _connect_redis(self) -> List[redis.Redis]:
        """Redis 연결"""
        instances = []
        for host in self.config['redis_instances']:
            host_parts = host.split(':')
            instance = redis.Redis(
                host=host_parts[0],
                port=int(host_parts[1]) if len(host_parts) > 1 else 6379,
                decode_responses=True
            )
            instances.append(instance)
        return instances

    def health_check(self):
        """전체 시스템 헬스 체크"""
        print("🔍 RedLock System Health Check")
        print("-" * 40)

        healthy_count = 0
        for i, instance in enumerate(self.redis_instances):
            try:
                instance.ping()
                info = instance.info('server')
                print(f"✅ Redis-{i}: Healthy (v{info['redis_version']})")
                healthy_count += 1
            except Exception as e:
                print(f"❌ Redis-{i}: Unhealthy ({str(e)})")

        quorum = len(self.redis_instances) // 2 + 1
        print("-" * 40)

        if healthy_count >= quorum:
            print(f"✅ System Status: OPERATIONAL ({healthy_count}/{len(self.redis_instances)} healthy)")
        else:
            print(f"❌ System Status: DEGRADED ({healthy_count}/{len(self.redis_instances)} healthy)")
            print(f"   Minimum required: {quorum}")

    def list_locks(self, pattern="lock:*"):
        """현재 활성 락 목록"""
        print(f"📋 Active Locks (pattern: {pattern})")
        print("-" * 40)

        all_locks = set()
        for i, instance in enumerate(self.redis_instances):
            try:
                keys = instance.keys(pattern)
                for key in keys:
                    ttl = instance.ttl(key)
                    if ttl > 0:
                        all_locks.add(f"{key} (TTL: {ttl}s on Redis-{i})")
            except:
                pass

        for lock in sorted(all_locks):
            print(f"  • {lock}")

        if not all_locks:
            print("  No active locks found")

    def force_unlock(self, resource_name: str):
        """강제 언락"""
        confirm = input(f"⚠️  Force unlock '{resource_name}'? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            return

        released_count = 0
        for i, instance in enumerate(self.redis_instances):
            try:
                if instance.delete(resource_name):
                    print(f"  ✅ Released on Redis-{i}")
                    released_count += 1
            except Exception as e:
                print(f"  ❌ Failed on Redis-{i}: {e}")

        print(f"Released on {released_count}/{len(self.redis_instances)} instances")

    def backup_state(self, output_file: str):
        """상태 백업"""
        import json

        state = {"locks": {}, "metadata": {}}

        for i, instance in enumerate(self.redis_instances):
            try:
                keys = instance.keys("lock:*")
                for key in keys:
                    value = instance.get(key)
                    ttl = instance.ttl(key)

                    if key not in state["locks"]:
                        state["locks"][key] = []

                    state["locks"][key].append({
                        "instance": i,
                        "value": value,
                        "ttl": ttl
                    })
            except:
                pass

        state["metadata"]["timestamp"] = time.time()
        state["metadata"]["instances"] = len(self.redis_instances)

        with open(output_file, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"✅ State backed up to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="RedLock Operations Tool")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Health check
    subparsers.add_parser("health", help="System health check")

    # List locks
    list_parser = subparsers.add_parser("list", help="List active locks")
    list_parser.add_argument("-p", "--pattern", default="lock:*", help="Key pattern")

    # Force unlock
    unlock_parser = subparsers.add_parser("unlock", help="Force unlock")
    unlock_parser.add_argument("resource", help="Resource name")

    # Backup
    backup_parser = subparsers.add_parser("backup", help="Backup state")
    backup_parser.add_argument("-o", "--output", default="backup.json", help="Output file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    ops = RedLockOperations(args.config)

    if args.command == "health":
        ops.health_check()
    elif args.command == "list":
        ops.list_locks(args.pattern)
    elif args.command == "unlock":
        ops.force_unlock(args.resource)
    elif args.command == "backup":
        ops.backup_state(args.output)

if __name__ == "__main__":
    main()
```

---

## 요약

RedLock의 고급 기능과 최적화를 위한 핵심 포인트:

### 모니터링
- 포괄적인 메트릭 수집 (Prometheus)
- 실시간 대시보드 (Grafana)
- 프로액티브 알림 시스템

### 최적화
- 계층적 락 시스템
- 락 풀링
- 적응형 TTL

### 복원력
- Circuit Breaker 패턴
- Fallback 메커니즘
- 자가 치유 시스템

### 통합
- Kubernetes 네이티브 지원
- 메시지 큐 통합 (Kafka)
- 클라우드 환경 최적화

### 운영
- 자동화된 배포 (Docker/K8s)
- 운영 도구 및 스크립트
- 백업 및 복구 전략

---

## 다음 단계

- `05_comparison.md`: 다른 분산 락 솔루션과의 비교
- `06_case_studies.md`: 실제 기업 사례 연구