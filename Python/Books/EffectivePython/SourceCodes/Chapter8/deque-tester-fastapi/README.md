# list와 deque의 성능 차이를 테스트하기 위한 대기열 서버

이 프로젝트는 파이썬에서 Producer-Consumer 패턴의 FIFO(First-In, First-Out) 큐를 구현할 때, 표준 list와 collections.deque의 성능 차이를 실제 웹 서비스 환경과 부하 테스트를 통해 명확히 증명하는 것을 목표로 합니다.

## 핵심 개념
- `list` 의 문제점: `list.pop(0)` 연산은 리스트의 첫 번째 요소를 제거한 후, 나머지 모든 요소를 한 칸씩 앞으로 이동시킵니다. 이 때문에 큐에 데이터가 많아질수록 처리 시간은 선형적으로 증가(`O(N)`)하여 성능에 병목을 유발합니다.
- `deque`의 해결책: `collections.deque`는 양방향 큐(Double-Ended Queue)로 양쪽 끝에서 데이터 추가 및 제거에 최적화되어 있습니다. `deque.poplesft()` 연산은 큐의 크기오 상관없이 항상 일정한 시간(`O(1)`)이 소요되어, FIFO 큐 구현에 이상적입니다.

## 프로젝트 구조
```
├── main_list.py      # list를 큐로 사용하는 FastAPI 애플리케이션
├── main_deque.py     # deque를 큐로 사용하는 FastAPI 애플리케이션
├── locustfile.py     # 부하 테스트를 위한 Locust 스크립트
├── README.md
```

- main_list.py / main_deque.py
    - 생산자(Producer): `/tasks` API 엔드포인트. 외부로부터 작업 요청(POST)을 받아 중앙 큐에 추가합니다.
    - 소비자(Consumer): 애플리케이션 시작 시 실행되는 백그라운드 스레드. 큐에서 작업을 하나씩 가져와 5초간 처리하는 것을 시뮬레이션합니다.

- locustfile.py: 가상 유저가 1~5초 간격으로 무작위 작업을 생성하여 `/tasks` 엔드포인트에 요청을 보내는 시나리오를 정의합니다.

## 패키지

- fastapi
- uvicorn
- locust


