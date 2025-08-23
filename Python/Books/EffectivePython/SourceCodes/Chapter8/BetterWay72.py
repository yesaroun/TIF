# Better Way 72 Consider Searching Sorted Sequences with bisect

data = list(range(10**5))
index = data.index(91234)
assert index == 91234


def find_closest(sequence, goal):
    for index, value in enumerate(sequence):
        if goal < value:
            return index
    raise ValueError(f"{goal} is out of bounds")


index = find_closest(data, 91234.56)
assert index == 91235

from bisect import bisect_left

index = bisect_left(data, 91234)  # Exact match
assert index == 91234

index = bisect_left(data, 91234.56)  # Closest match
assert index == 91235


import random
import timeit

size = 10**5
iterations = 1000

data = list(range(size))
to_lookup = [random.randint(0, size) for _ in range(iterations)]


def run_linear(data, to_lookup):
    for index in to_lookup:
        data.index(index)


def run_bisect(data, to_lookup):
    for index in to_lookup:
        bisect_left(data, index)


baseline = timeit.timeit(
    stmt="run_linear(data, to_lookup)", globals=globals(), number=10
)
print(f"Linear search takes {baseline:.6f}s")

comparison = timeit.timeit(
    stmt="run_bisect(data, to_lookup)", globals=globals(), number=10
)
print(f"Bisect search takes {comparison:.6f}s")

slowdown = 1 + ((baseline - comparison) / comparison)
print(f"{slowdown:.1f}x time")
