# Know How to Use headpq for Priority Queues


class Book:
    def __init__(self, title, due_date):
        self.title = title
        self.due_date = due_date


def add_book(queue, book):
    queue.append(book)
    queue.sort(key=lambda x: x.due_date, reverse=True)


queue = []
add_book(queue, Book("Don Quixote", "2019-06-07"))
add_book(queue, Book("Frankenstein", "2019-06-05"))
add_book(queue, Book("Les Misérables", "2019-06-08"))
add_book(queue, Book("War and Peace", "2019-06-03"))


class NoOverdueBooks(Exception):
    pass


def next_overdue_book(queue, now):
    if queue:
        book = queue[-1]
        if book.due_date < now:
            queue.pop()
            return book

    raise NoOverdueBooks


now = "2019-06-10"

found = next_overdue_book(queue, now)
print(found.title)

found = next_overdue_book(queue, now)
print(found.title)


def return_book(queue, book):
    queue.remove(book)


queue = []
book = Book("Treasure Island", "2019-06-04")

add_book(queue, book)
print("Before return:", [x.title for x in queue])

return_book(queue, book)
print("After return: ", [x.title for x in queue])

try:
    next_overdue_book(queue, now)
except NoOverdueBooks:
    pass  # Expected
else:
    assert False  # Doesn't happen


import random
import timeit


def print_results(count, tests): ...


def print_delta(before, after): ...


def list_overdue_benchmark(count):
    def prepare():
        to_add = list(range(count))
        random.shuffle(to_add)
        return [], to_add

    def run(queue, to_add):
        for i in to_add:
            queue.append(i)
            queue.sort(reverse=True)

        while queue:
            queue.pop()

    tests = timeit.repeat(
        setup="queue, to_add = prepare()",
        stmt=f"run(queue, to_add)",
        globals=locals(),
        repeat=100,
        number=1,
    )

    return print_results(count, tests)


baseline = list_overdue_benchmark(500)
for count in (1_000, 1_500, 2_000):
    comparison = list_overdue_benchmark(count)
    print_delta(baseline, comparison)


def list_return_benchmark(count):
    def prepare():
        queue = list(range(count))
        random.shuffle(queue)

        to_return = list(range(count))
        random.shuffle(to_return)

        return queue, to_return

    def run(queue, to_return):
        for i in to_return:
            queue.remove(i)

    tests = timeit.repeat(
        setup="queue, to_return = prepare()",
        stmt=f"run(queue, to_return)",
        globals=locals(),
        repeat=100,
        number=1,
    )

    return print_results(count, tests)


baseline = list_return_benchmark(500)
for count in (1_000, 1_500, 2_000):
    comparison = list_return_benchmark(count)
    print_delta(baseline, comparison)


from heapq import heappush


def add_book(queue, book):
    heappush(queue, book)


# queue = []
# add_book(queue, Book("Little Women", "2019-06-05"))
# add_book(queue, Book("The Time Machine", "2019-05-30"))

import functools


@functools.total_ordering
class Book:
    def __init__(self, title, due_date):
        self.title = title
        self.due_date = due_date

    def __lt__(self, other):
        return self.due_date < other.due_date


queue = []
add_book(queue, Book("Pride and Prejudice", "2019-06-01"))
add_book(queue, Book("The Time Machine", "2019-05-30"))
add_book(queue, Book("Crime and Punishment", "2019-06-06"))
add_book(queue, Book("Wuthering Heights", "2019-06-12"))


queue = [
    Book("Pride and Prejudice", "2019-06-01"),
    Book("The Time Machine", "2019-05-30"),
    Book("Crime and Punishment", "2019-06-06"),
    Book("Wuthering Heights", "2019-06-12"),
]
queue.sort()


from heapq import heapify

queue = [
    Book("Pride and Prejudice", "2019-06-01"),
    Book("The Time Machine", "2019-05-30"),
    Book("Crime and Punishment", "2019-06-06"),
    Book("Wuthering Heights", "2019-06-12"),
]
heapify(queue)


from heapq import heappop


def next_overdue_book(queue, now):
    if queue:
        book = queue[0]  # Most overdue first
        if book.due_date < now:
            heappop(queue)  # Remove the overdue book
            return book

    raise NoOverdueBooks


now = "2019-06-02"

book = next_overdue_book(queue, now)
print(book.title)

book = next_overdue_book(queue, now)
print(book.title)

try:
    next_overdue_book(queue, now)
except NoOverdueBooks:
    pass  # Expected
else:
    assert False  # Doesn't happen


def heap_overdue_benchmark(count):
    def prepare():
        to_add = list(range(count))
        random.shuffle(to_add)
        return [], to_add

    def run(queue, to_add):
        for i in to_add:
            heappush(queue, i)
        while queue:
            heappop(queue)

    tests = timeit.repeat(
        setup="queue, to_add = prepare()",
        stmt=f"run(queue, to_add)",
        globals=locals(),
        repeat=100,
        number=1,
    )

    return print_results(count, tests)


baseline = heap_overdue_benchmark(500)
for count in (1_000, 1_500, 2_000):
    comparison = heap_overdue_benchmark(count)
    print_delta(baseline, comparison)


@functools.total_ordering
class Book:
    def __init__(self, title, due_date):
        self.title = title
        self.due_date = due_date
        self.returned = False  # New field


def next_overdue_book(queue, now):
    while queue:
        book = queue[0]
        if book.returned:
            heappop(queue)
            continue

        if book.due_date < now:
            heappop(queue)
            return book

        break

    raise NoOverdueBooks


def return_book(queue, book):
    book.returned = True
