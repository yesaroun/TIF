# Custom Load Shape - 사용자 정의 부하 패턴

## 개요
Custom Load Shape는 Locust에서 시간에 따라 동적으로 변화하는 부하 패턴을 정의할 수 있는 고급 기능입니다. 기본적인 일정한 증가율 대신, 실제 트래픽 패턴을 모방하거나 특정 시나리오를 테스트할 수 있습니다.

## 왜 Custom Load Shape를 사용하는가?

### 실제 트래픽 패턴 모사
- 일반적인 웹 서비스는 시간대별로 트래픽이 다름
- 피크 시간대와 유휴 시간대의 패턴을 재현
- 이벤트나 프로모션 시의 급격한 트래픽 증가 시뮬레이션

### 다양한 테스트 시나리오
- **Spike Test**: 갑작스러운 부하 증가
- **Step Load**: 단계적 부하 증가
- **Wave Pattern**: 주기적인 부하 변동
- **Custom Pattern**: 비즈니스 요구사항에 맞는 패턴

## 기본 구현

### 1. LoadTestShape 클래스 상속

```python
from locust import HttpUser, task, between, LoadTestShape
import math

class MyCustomShape(LoadTestShape):
    """
    Custom Load Shape 기본 구조
    tick() 메서드는 매초 호출되며, (user_count, spawn_rate) 튜플을 반환
    None을 반환하면 테스트 종료
    """

    time_limit = 600  # 10분 테스트
    spawn_rate = 20   # 초당 사용자 생성률

    def tick(self):
        run_time = self.get_run_time()

        if run_time < self.time_limit:
            # 실행 시간에 비례하여 사용자 수 증가
            user_count = run_time // 10
            return (user_count, self.spawn_rate)

        return None  # 테스트 종료
```

## 실전 예제

### 2. 단계적 부하 증가 (Step Load Pattern)

```python
from locust import HttpUser, task, between, LoadTestShape

class StepLoadShape(LoadTestShape):
    """
    단계적으로 부하를 증가시키는 패턴
    각 단계마다 일정 시간 유지
    """

    step_time = 60  # 각 단계 유지 시간 (초)
    step_load = 10  # 각 단계별 사용자 증가량
    spawn_rate = 10  # 사용자 생성 속도
    max_users = 100  # 최대 사용자 수
    time_limit = 600  # 전체 테스트 시간

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        current_step = math.floor(run_time / self.step_time) + 1
        user_count = min(current_step * self.step_load, self.max_users)

        return (user_count, self.spawn_rate)

# 사용자 정의
class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def index(self):
        self.client.get("/")

    @task(3)
    def products(self):
        self.client.get("/products")
```

### 3. 스파이크 테스트 (Spike Test Pattern)

```python
from locust import HttpUser, task, between, LoadTestShape

class SpikeTestShape(LoadTestShape):
    """
    갑작스러운 부하 증가와 감소를 시뮬레이션
    """

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 10},    # Warm up
        {"duration": 120, "users": 10, "spawn_rate": 10},   # 안정 상태
        {"duration": 10, "users": 100, "spawn_rate": 100},  # 스파이크!
        {"duration": 120, "users": 100, "spawn_rate": 10},  # 피크 유지
        {"duration": 10, "users": 10, "spawn_rate": 50},    # 급격한 감소
        {"duration": 120, "users": 10, "spawn_rate": 10},   # 복구 확인
    ]

    def tick(self):
        run_time = self.get_run_time()
        total_time = 0

        for stage in self.stages:
            total_time += stage["duration"]
            if run_time < total_time:
                return (stage["users"], stage["spawn_rate"])

        return None
```

### 4. 웨이브 패턴 (Wave Pattern)

```python
from locust import HttpUser, task, between, LoadTestShape
import math

class WaveLoadShape(LoadTestShape):
    """
    사인파 형태로 부하가 증감하는 패턴
    일일 트래픽 패턴 시뮬레이션에 유용
    """

    min_users = 10
    max_users = 100
    wave_duration = 180  # 한 주기 시간 (초)
    time_limit = 900  # 전체 테스트 시간
    spawn_rate = 5

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        # 사인파 계산
        wave_progress = (run_time % self.wave_duration) / self.wave_duration
        user_count = self.min_users + (self.max_users - self.min_users) * \
                     (1 + math.sin(2 * math.pi * wave_progress - math.pi/2)) / 2

        return (int(user_count), self.spawn_rate)
```

### 5. 실제 트래픽 패턴 모사

```python
from locust import HttpUser, task, between, LoadTestShape
from datetime import datetime, timedelta

class RealisticTrafficShape(LoadTestShape):
    """
    실제 서비스의 하루 트래픽 패턴을 모사
    """

    # 시간대별 트래픽 비율 (0-24시)
    hourly_traffic_pattern = [
        30,   # 00:00
        20,   # 01:00
        15,   # 02:00
        10,   # 03:00
        10,   # 04:00
        15,   # 05:00
        25,   # 06:00
        40,   # 07:00
        60,   # 08:00
        80,   # 09:00
        90,   # 10:00
        95,   # 11:00
        100,  # 12:00 - 점심 피크
        95,   # 13:00
        85,   # 14:00
        80,   # 15:00
        75,   # 16:00
        70,   # 17:00
        65,   # 18:00
        70,   # 19:00
        85,   # 20:00 - 저녁 피크
        90,   # 21:00
        75,   # 22:00
        50,   # 23:00
    ]

    max_users = 1000
    spawn_rate = 20
    test_duration = 3600  # 1시간 테스트 (실제로는 24시간 패턴을 1시간으로 압축)

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.test_duration:
            return None

        # 실행 시간을 24시간 기준으로 매핑
        simulated_hour = int((run_time / self.test_duration) * 24)
        traffic_ratio = self.hourly_traffic_pattern[simulated_hour] / 100

        user_count = int(self.max_users * traffic_ratio)

        return (user_count, self.spawn_rate)
```

### 6. 복합 시나리오 패턴

```python
from locust import HttpUser, task, between, LoadTestShape
import random

class ComplexScenarioShape(LoadTestShape):
    """
    여러 이벤트가 복합적으로 일어나는 시나리오
    - 기본 트래픽
    - 주기적인 배치 작업
    - 랜덤 스파이크
    """

    base_users = 50
    max_users = 500
    spawn_rate = 10
    time_limit = 1200  # 20분

    # 배치 작업 시간 (5분마다)
    batch_interval = 300
    batch_additional_users = 100
    batch_duration = 30

    # 랜덤 스파이크 확률
    spike_probability = 0.01  # 1% 확률
    spike_users = 200

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        user_count = self.base_users

        # 배치 작업 체크
        if run_time % self.batch_interval < self.batch_duration:
            user_count += self.batch_additional_users

        # 랜덤 스파이크
        if random.random() < self.spike_probability:
            user_count += self.spike_users

        # 최대 사용자 수 제한
        user_count = min(user_count, self.max_users)

        return (user_count, self.spawn_rate)
```

## 고급 기능

### 7. 외부 데이터 기반 Load Shape

```python
import json
from locust import HttpUser, task, between, LoadTestShape

class DataDrivenLoadShape(LoadTestShape):
    """
    외부 설정 파일이나 API에서 부하 패턴 읽기
    """

    def __init__(self):
        super().__init__()
        self.load_pattern_from_file()

    def load_pattern_from_file(self):
        """JSON 파일에서 부하 패턴 로드"""
        with open('load_pattern.json', 'r') as f:
            self.pattern = json.load(f)

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.pattern['stages']:
            if run_time < stage['time']:
                return (stage['users'], stage['spawn_rate'])

        return None

# load_pattern.json 예제
"""
{
    "stages": [
        {"time": 60, "users": 10, "spawn_rate": 5},
        {"time": 180, "users": 50, "spawn_rate": 10},
        {"time": 300, "users": 100, "spawn_rate": 20},
        {"time": 420, "users": 50, "spawn_rate": 10},
        {"time": 480, "users": 10, "spawn_rate": 5}
    ]
}
"""
```

### 8. 적응형 Load Shape

```python
from locust import HttpUser, task, between, LoadTestShape, events
import statistics

class AdaptiveLoadShape(LoadTestShape):
    """
    응답 시간에 따라 부하를 자동 조절
    """

    target_response_time = 1000  # 목표 응답 시간 (ms)
    initial_users = 10
    max_users = 500
    min_users = 1
    spawn_rate = 5
    adjustment_interval = 30  # 조정 간격 (초)

    def __init__(self):
        super().__init__()
        self.current_users = self.initial_users
        self.response_times = []
        self.last_adjustment_time = 0

        # 응답 시간 수집을 위한 이벤트 리스너
        @events.request.add_listener
        def on_request(request_type, name, response_time, response_length, **kwargs):
            self.response_times.append(response_time)

    def tick(self):
        run_time = self.get_run_time()

        # 조정 간격마다 사용자 수 조절
        if run_time - self.last_adjustment_time > self.adjustment_interval:
            self.adjust_user_count()
            self.last_adjustment_time = run_time

        return (self.current_users, self.spawn_rate)

    def adjust_user_count(self):
        """응답 시간 기반으로 사용자 수 조정"""
        if not self.response_times:
            return

        avg_response_time = statistics.mean(self.response_times[-100:])  # 최근 100개 평균

        if avg_response_time > self.target_response_time * 1.2:
            # 응답 시간이 목표보다 20% 이상 높으면 사용자 감소
            self.current_users = max(
                self.min_users,
                int(self.current_users * 0.9)
            )
        elif avg_response_time < self.target_response_time * 0.8:
            # 응답 시간이 목표보다 20% 이상 낮으면 사용자 증가
            self.current_users = min(
                self.max_users,
                int(self.current_users * 1.1)
            )
```

## 실행 방법

### Custom Load Shape 사용하기

```bash
# locustfile.py에 Custom Shape 클래스 포함
locust -f locustfile.py --host=http://localhost:8000

# 헤드리스 모드
locust -f locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    --run-time 10m
```

### 여러 Shape 중 선택하기

```python
# locustfile.py
import os
from locust import HttpUser, task, between

# Shape 선택을 위한 환경 변수
shape_type = os.environ.get('LOCUST_SHAPE', 'step')

if shape_type == 'step':
    from shapes.step_load import StepLoadShape as CustomShape
elif shape_type == 'spike':
    from shapes.spike_test import SpikeTestShape as CustomShape
elif shape_type == 'wave':
    from shapes.wave_pattern import WaveLoadShape as CustomShape
else:
    CustomShape = None  # 기본 모드 사용

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def index(self):
        self.client.get("/")
```

```bash
# 실행 시 Shape 선택
LOCUST_SHAPE=spike locust -f locustfile.py --host=http://localhost:8000
```

## 모니터링 및 분석

### 실시간 모니터링

```python
from locust import events
import logging

class MonitoredLoadShape(LoadTestShape):
    """모니터링 기능이 추가된 Load Shape"""

    def __init__(self):
        super().__init__()
        self.setup_monitoring()

    def setup_monitoring(self):
        """모니터링 설정"""
        @events.test_start.add_listener
        def on_test_start(environment, **kwargs):
            logging.info(f"Test started with shape: {self.__class__.__name__}")

        @events.user_add.add_listener
        def on_user_add(**kwargs):
            logging.info(f"User added. Total: {kwargs.get('user_count')}")

        @events.user_remove.add_listener
        def on_user_remove(**kwargs):
            logging.info(f"User removed. Total: {kwargs.get('user_count')}")

    def tick(self):
        run_time = self.get_run_time()
        user_count = self.calculate_users(run_time)

        # 로깅
        if run_time % 10 == 0:  # 10초마다
            logging.info(f"Time: {run_time}s, Users: {user_count}")

        return (user_count, 10)

    def calculate_users(self, run_time):
        # 실제 계산 로직
        return min(100, run_time // 5)
```

## 모범 사례

### 1. 점진적인 부하 증가
- 급격한 부하 변화는 비현실적인 결과를 낳을 수 있음
- spawn_rate를 적절히 조절하여 자연스러운 증가 구현

### 2. 충분한 워밍업
- 테스트 시작 시 워밍업 단계 포함
- 캐시, 연결 풀 등이 안정화되도록 함

### 3. 현실적인 패턴
- 실제 프로덕션 트래픽 데이터 기반으로 패턴 설계
- 비즈니스 이벤트나 계절성 고려

### 4. 에러 처리
```python
def tick(self):
    try:
        run_time = self.get_run_time()
        # 로직 구현
        return (user_count, spawn_rate)
    except Exception as e:
        logging.error(f"Error in load shape: {e}")
        return (10, 5)  # 안전한 기본값
```

## 트러블슈팅

### 일반적인 문제

1. **Shape가 적용되지 않음**
   - 클래스 이름이 정확한지 확인
   - LoadTestShape를 올바르게 상속했는지 확인
   - tick() 메서드가 올바른 형식으로 값을 반환하는지 확인

2. **예상과 다른 부하 패턴**
   - tick() 메서드의 로직 검증
   - spawn_rate가 너무 낮거나 높지 않은지 확인
   - 로깅을 추가하여 디버깅

3. **메모리 누수**
   - tick() 메서드에서 무거운 객체 생성 피하기
   - 이벤트 리스너에서 데이터 축적 주의

## 다음 학습 내용

### 1. 분산 환경에서의 Custom Load Shape
- Master-Worker 구조에서 Load Shape 동기화
- 여러 지역에서 동시 테스트

### 2. 성능 메트릭과 연동
- Prometheus/Grafana와 통합
- 실시간 부하 조절 대시보드 구축

### 3. CI/CD 파이프라인 통합
- Jenkins/GitLab CI에서 Custom Shape 실행
- 자동화된 성능 회귀 테스트

### 4. Machine Learning 기반 패턴
- 과거 트래픽 데이터로 패턴 학습
- 예측 모델 기반 부하 테스트

### 참고 자료
- [Locust LoadTestShape Documentation](https://docs.locust.io/en/stable/custom-load-shape.html)
- [Real-world Load Testing Patterns](https://www.blazemeter.com/blog/load-testing-patterns)
- [Performance Testing Best Practices](https://www.guru99.com/performance-testing.html)