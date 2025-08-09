# Prefer deque for Producer-Consumer Queues

Producer-Consumer 큐(FIFO 큐)는 프로그래밍에서 자주 사용되는 데이터 구조입니다. 파이썬에서는 두 가지 방법으로 구현할 수 있습니다

- **list 사용:** 생산자는 `append()`로 항목을 추가하고, 소비자는 `pop(0)`으로 항목을 가져옵니다. 그러나 큐의 길이가 늘어날수록 `pop(0)`의 성능이 초선형적으로 저하됩니다.
- **collections.deque 사용:** 생산자는 `append()`로 항목을 추가하고, 소비자는 `popleft()`로 항목을 가져옵니다. 큐의 길이에 관계없이 일정한 시간이 소요되므로 FIFO 큐에 이상적입니다.

## 예제 코드

**1. 이메일 처리 클래스 정의:**

```python
class Email:
    def __init__(self, sender, receiver, message):
        self.sender = sender
        self.receiver = receiver
        self.message = message

```

**2. deque를 사용한 소비자 함수:**

```python
import collections

def consume_one_email(queue):
    if not queue:
        return
    email = queue.popleft()  # Consumer
    # Process the email message
    ...

def my_end_func(): ...

loop(collections.deque(), my_end_func)

```

**3. deque의 성능 벤치마크:**

```python
def dequeue_popleft_benchmark(count):
    def prepare():
        return collections.deque(range(count))

    def run(queue):
        while queue:
            queue.popleft()

    tests = timeit.repeat(
        setup="queue = prepare()",
        stmt="run(queue)",
        globals=locals(),
        repeat=1000,
        number=1,
    )

    return print_results(count, tests)

```

## 결론

Producer-Consumer 큐를 구현할 때는 `list` 대신 `collections.deque`를 사용하는 것이 성능상 훨씬 좋습니다. `deque`는 큐의 길이에 관계없이 `append()`와 `popleft()` 연산이 일정한 시간복잡도를 가지므로, 효율적인 FIFO 큐 구현에 이상적입니다.
