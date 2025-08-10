# Better Way 71 생산자-소비자 큐로 deque를 사용하라
import timeit


class Email:
    def __init__(self, sender, receiver, message):
        self.sender = sender
        self.receiver = receiver
        self.message = message


class NoEmailError(Exception):
    pass


def try_receive_email(): ...


def produce_emails(queue):
    while True:
        try:
            email = try_receive_email()
        except NoEmailError:
            return
        else:
            queue.append(email)  # 생산자


def consume_one_email(queue):
    if not queue:
        return
    email = queue.pop(0)  # 소비자
    # 장기 보관을 위해 메시지를 인덱싱함


def loop(queue, keep_running):
    while keep_running():
        produce_emails(queue)
        consume_one_email(queue)


def my_end_func(): ...


# loop([], my_end_func)


def print_results(count, tests):
    avg_iteration = sum(tests) / len(tests)
    print(f"\n원소 수: {count:>5,} 걸린 시간: {avg_iteration:.6f}초")
    return count, avg_iteration


def list_append_benchmark(count):
    def run(queue):
        for i in range(count):
            queue.append(i)

    tests = timeit.repeat(
        setup="queue = []",
        stmt="run(queue)",
        globals=locals(),
        repeat=1000,
        number=1,
    )

    return print_results(count, tests)


def print_delta(before, after):
    before_count, before_time = before
    after_count, after_time = after
    growth = 1 + (after_count - before_count) / before_count
    slowdown = 1 + (after_time - before_time) / before_time
    print(f"데이터 크기 {growth:>4.1f}배, 걸린 시간 {slowdown:4.1f}배")


baseline = list_append_benchmark(500)
for count in (1_000, 2_000, 3_000, 4_000, 5_000):
    comparison = list_append_benchmark(count)
    print_delta(baseline, comparison)


def list_pop_benchmark(count):
    def prepare():
        return list(range(count))

    def run(queue):
        while queue:
            queue.pop(0)

    tests = timeit.repeat(
        setup="queue = prepare()",
        stmt="run(queue)",
        globals=locals(),
        repeat=1000,
        number=1,
    )

    return print_results(count, tests)


baseline = list_pop_benchmark(500)
for count in (1_000, 2_000, 3_000, 4_000, 5_000):
    comparison = list_pop_benchmark(count)
    print_delta(baseline, comparison)


import collections


def consume_one_email(queue):
    if not queue:
        return
    email = queue.popleft()  # Consumer
    # Process the email message
    ...


def my_end_func(): ...


loop(collections.deque(), my_end_func)


def deque_append_benchmark(count):
    def prepare():
        return collections.deque()

    def run(queue):
        for i in range(count):
            queue.append(i)

    tests = timeit.repeat(
        setup="queue = prepare()",
        stmt="run(queue)",
        globals=locals(),
        repeat=1000,
        number=1,
    )
    return print_results(count, tests)


baseline = deque_append_benchmark(500)
for count in (1_000, 2_000, 3_000, 4_000, 5_000):
    comparison = deque_append_benchmark(count)
    print_delta(baseline, comparison)


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


baseline = dequeue_popleft_benchmark(500)
for count in (1_000, 2_000, 3_000, 4_000, 5_000):
    comparison = dequeue_popleft_benchmark(count)
    print_delta(baseline, comparison)
