# Consider Searching Sorted Sequences with bisect

정렬된 데이터를 검색할 때 Python의 `bisect` 모듈을 사용하면 효율적입니다. 일반적으로 리스트에서 값을 검색하려면 `index` 메서드나 `for` 루프를 사용해 선형 시간(linear time)이 소요됩니다. 반면, `bisect_left`를 사용하면 로그 시간(logarithmic time) 안에 검색할 수 있어 훨씬 빠릅니다. 이진 검색 알고리즘을 활용하여 리스트의 특정 값 또는 그 값보다 크거나 같은 값을 효율적으로 찾을 수 있습니다. `bisect`는 리스트뿐만 아니라 시퀀스처럼 동작하는 다른 Python 객체에서도 사용할 수 있습니다.

**예제 코드:**

```python
from bisect import bisect_left

# 정렬된 리스트에서 특정 값을 검색
data = list(range(10**5))

# 정확히 일치하는 값을 찾는 경우
index = bisect_left(data, 91234)
assert index == 91234

# 특정 값보다 크거나 같은 가장 가까운 값을 찾는 경우
index = bisect_left(data, 91234.56)
assert index == 91235

```

**속도 비교:**

`index` 메서드나 `for` 루프를 사용한 선형 검색은 시간이 오래 걸리지만, `bisect`는 훨씬 더 빠릅니다. 아래는 속도 비교를 보여주는 코드입니다.

```python
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

```

출력 예시:

```
Linear search takes 2.737229s
Bisect search takes 0.002587s
1058.1x time

```

- `index` 메서드나 `for` 루프를 사용한 정렬된 데이터 검색은 선형 시간이 소요됩니다.
- `bisect` 모듈의 `bisect_left` 함수는 로그 시간에 검색이 가능하며, 이는 훨씬 더 빠릅니다.