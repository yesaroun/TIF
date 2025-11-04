# Locust 사용법 가이드

## 개요
Locust는 Python으로 작성된 오픈소스 성능 테스트 도구입니다. 웹 애플리케이션이나 API에 대한 부하 테스트를 쉽고 직관적으로 수행할 수 있으며, 실시간으로 테스트 결과를 모니터링할 수 있는 웹 UI를 제공합니다.

### 주요 특징
- Python 코드로 테스트 시나리오 작성
- 분산 테스트 지원
- 실시간 웹 기반 모니터링
- 다양한 프로토콜 지원 (HTTP, WebSocket, gRPC 등)
- 확장 가능한 아키텍처

## 설치

### pip를 사용한 설치
```bash
pip install locust
```

### uv를 사용한 설치
```bash
uv pip install locust
```

### 설치 확인
```bash
locust --version
```

## 기본 사용법

### 1. 기본 테스트 파일 작성 (locustfile.py)

```python
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    # 각 요청 사이의 대기 시간 (1초 ~ 3초 사이)
    wait_time = between(1, 3)

    @task
    def index_page(self):
        """홈페이지 접속 테스트"""
        self.client.get("/")

    @task(3)  # 가중치 3 (다른 task보다 3배 많이 실행)
    def view_products(self):
        """제품 목록 페이지 테스트"""
        self.client.get("/products")

    @task(2)
    def view_product_detail(self):
        """제품 상세 페이지 테스트"""
        product_id = 1
        self.client.get(f"/products/{product_id}")

    def on_start(self):
        """테스트 시작 시 실행 (로그인 등)"""
        self.client.post("/login", json={
            "username": "testuser",
            "password": "testpass"
        })
```

### 2. Locust 실행

#### 웹 UI 모드로 실행
```bash
locust -f locustfile.py --host=http://localhost:8000
```
- 브라우저에서 http://localhost:8089 접속
- 사용자 수와 증가율 설정 후 테스트 시작

#### 헤드리스 모드로 실행
```bash
locust -f locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 60s \
    --headless
```

### 3. 고급 시나리오 작성

```python
from locust import HttpUser, task, between, events
import random

class AdvancedUser(HttpUser):
    wait_time = between(1, 2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.token = None

    def on_start(self):
        """사용자별 초기화 로직"""
        # 로그인 및 토큰 획득
        response = self.client.post("/api/auth/login",
            json={
                "email": f"user_{random.randint(1, 1000)}@test.com",
                "password": "password123"
            },
            catch_response=True  # 응답 검증 활성화
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token")
            self.user_id = data.get("user_id")
            response.success()
        else:
            response.failure(f"Login failed: {response.status_code}")

    @task(5)
    def get_user_profile(self):
        """사용자 프로필 조회"""
        if self.token:
            with self.client.get(
                f"/api/users/{self.user_id}",
                headers={"Authorization": f"Bearer {self.token}"},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Got status code {response.status_code}")

    @task(3)
    def create_post(self):
        """게시글 작성"""
        if self.token:
            post_data = {
                "title": f"Test Post {random.randint(1, 1000)}",
                "content": "This is a test post content.",
                "tags": ["test", "locust", "performance"]
            }

            with self.client.post(
                "/api/posts",
                json=post_data,
                headers={"Authorization": f"Bearer {self.token}"},
                catch_response=True
            ) as response:
                if response.status_code == 201:
                    response.success()
                else:
                    response.failure(f"Failed to create post: {response.text}")

    @task(10)
    def browse_posts(self):
        """게시글 목록 조회 (페이지네이션)"""
        page = random.randint(1, 10)
        limit = 20

        self.client.get(
            f"/api/posts?page={page}&limit={limit}",
            name="/api/posts?page=[page]&limit=[limit]"  # 통계 그룹화
        )

    @task(2)
    def search_posts(self):
        """게시글 검색"""
        search_terms = ["python", "javascript", "testing", "performance"]
        term = random.choice(search_terms)

        self.client.get(
            f"/api/posts/search?q={term}",
            name="/api/posts/search?q=[term]"
        )
```

## 분산 테스트

### Master 노드 실행
```bash
locust -f locustfile.py --master --host=http://target-server.com
```

### Worker 노드 실행
```bash
# 다른 머신에서 실행
locust -f locustfile.py --worker --master-host=192.168.1.100
```

## 커스텀 클라이언트 사용

### WebSocket 테스트 예제
```python
from locust import User, task, between
import websocket
import json

class WebSocketUser(User):
    wait_time = between(1, 3)

    def on_start(self):
        self.ws = websocket.WebSocket()
        self.ws.connect("ws://localhost:8000/ws")

    @task
    def send_message(self):
        message = {
            "type": "chat",
            "content": "Hello from Locust!"
        }
        self.ws.send(json.dumps(message))
        response = self.ws.recv()
        # 응답 처리

    def on_stop(self):
        self.ws.close()
```

## 성능 지표 분석

### 주요 지표
1. **RPS (Requests Per Second)**: 초당 요청 수
2. **Response Time**: 응답 시간 (중앙값, 평균, 95%, 99%)
3. **Number of Users**: 동시 사용자 수
4. **Failure Rate**: 실패율
5. **Response Size**: 응답 크기

### 결과 내보내기
```bash
# CSV 형식으로 결과 저장
locust -f locustfile.py \
    --host=http://localhost:8000 \
    --csv=results \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 300s
```

## 테스트 최적화 팁

### 1. 연결 재사용
```python
class OptimizedUser(HttpUser):
    # HTTP 연결 풀 설정
    def on_start(self):
        self.client.mount("https://",
            requests.adapters.HTTPAdapter(
                pool_connections=100,
                pool_maxsize=100
            )
        )
```

### 2. 데이터 파라미터화
```python
import csv

class DataDrivenUser(HttpUser):
    def on_start(self):
        # CSV 파일에서 테스트 데이터 로드
        with open('test_data.csv', 'r') as f:
            reader = csv.DictReader(f)
            self.test_data = list(reader)

    @task
    def test_with_data(self):
        data = random.choice(self.test_data)
        self.client.post("/api/endpoint", json=data)
```

### 3. 이벤트 핸들러 활용
```python
from locust import events

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("테스트 시작!")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, **kwargs):
    # 커스텀 로깅 또는 메트릭 수집
    if response_time > 1000:
        print(f"Slow request: {name} took {response_time}ms")
```

## 트러블슈팅

### 일반적인 문제와 해결방법

1. **Too many open files 오류**
   ```bash
   # macOS/Linux에서 파일 디스크립터 한계 증가
   ulimit -n 10000
   ```

2. **메모리 부족**
   - User 클래스에서 불필요한 데이터 저장 피하기
   - 응답 본문 저장 최소화
   - 분산 모드 사용 고려

3. **네트워크 타임아웃**
   ```python
   class TimeoutUser(HttpUser):
       # 타임아웃 설정
       def on_start(self):
           self.client.timeout = 30  # 30초 타임아웃
   ```

## 다음 학습 내용

### 1. 고급 Locust 기능
- **Custom Load Shape**: 시간에 따른 부하 패턴 커스터마이징
- **FastHttpUser**: 더 높은 성능을 위한 경량 HTTP 클라이언트
- **Plugins**: Locust 확장 플러그인 개발
- **Kubernetes Integration**: K8s 환경에서 분산 테스트

### 2. 관련 도구 학습
- **Grafana + InfluxDB**: 실시간 모니터링 대시보드 구성
- **Jenkins Integration**: CI/CD 파이프라인에 성능 테스트 통합
- **Artillery**: Node.js 기반 성능 테스트 도구 (비교 학습)
- **K6**: Go 기반 현대적 부하 테스트 도구

### 3. 성능 테스트 방법론
- **Spike Testing**: 갑작스러운 부하 증가 테스트
- **Soak Testing**: 장시간 지속 부하 테스트
- **Stress Testing**: 시스템 한계 테스트
- **Capacity Planning**: 용량 계획 수립

### 4. 실전 프로젝트
- **마이크로서비스 테스트**: 분산 시스템 성능 테스트 전략
- **API Gateway 테스트**: Rate limiting 및 throttling 검증
- **Database 성능 테스트**: 쿼리 최적화 및 연결 풀 튜닝
- **CDN 효과 측정**: 정적 자원 배포 전략 검증

### 5. 추가 학습 리소스
- [Locust 공식 문서](https://docs.locust.io/)
- [Locust GitHub Repository](https://github.com/locustio/locust)
- [Performance Testing Fundamentals](https://www.guru99.com/performance-testing.html)
- [Real-world Locust Examples](https://github.com/locustio/locust/tree/master/examples)