# Better Way 70 최적화하기 전에 프로파일링을 하라

파이썬의 동적인 특성은 실행 성능 면에서 예상치 못한 동작을 유발하곤 한다. 느릴 것이라고 예상했던 연산(예: 문자열 처리, 제너레이터)이 실제로는 매우 빠르기도 하고, 빠를 것이라고 예상했던 기능(예: 속성 접근, 함수 호출)이 실제로는 매우 느리기도 하다. 이처럼 파이썬 프로그램에서 성능 저하의 진짜 원인은 찾기 어려울 수 있다.

가장 좋은 접근법은 직관을 무시하고, 코드를 최적화하기 전에 프로그램의 성능을 직접 측정하는 것이다. 파이썬은 프로그램의 어느 부분이 실행 시간을 차지하는지 분석할 수 있는 내장 **프로파일러(profiler)** 를 제공한다. 이를 통해 가장 큰 문제를 일으키는 부분에 최적화 노력을 집중하고, 속도에 거의 영향을 미치지 않는 부분은 무시할 수 있다.

예를 들어, 삽입 정렬(insertion sort) 알고리즘의 성능을 프로파일링해 보자. 먼저 비효율적인 선형 탐색 방식으로 동작하는 `insert_value` 함수와 이를 사용하는 `insertion_sort` 함수를 정의했다.

```python
# 비효율적인 삽입 정렬 함수
def insert_value(array, value):
    for i, existing in enumerate(array):
        if existing > value:
            array.insert(i, value)
            return
    array.append(value)

def insertion_sort(data):
    result = []
    for value in data:
        insert_value(result, value)
    return result
```

프로파일링을 위해 무작위 데이터셋과 테스트 함수를 만들었다. 파이썬은 순수 파이썬으로 작성된 `profile`과 C 확장 모듈인 `cProfile` 두 가지 프로파일러를 제공한다. `cProfile`은 프로파일링 중 프로그램 성능에 미치는 영향이 적어 더 정확한 결과를 제공하므로 `cProfile`을 사용하는 것이 좋다.

```python
from cProfile import Profile
from pstats import Stats
from random import randint

# 테스트 데이터 준비
max_size = 10**4
data = [randint(0, max_size) for _ in range(max_size)]
test = lambda: insertion_sort(data)

# 프로파일링 실행
profiler = Profile()
profiler.runcall(test)

# 결과 분석 및 출력
stats = Stats(profiler)
stats.strip_dirs()
stats.sort_stats('cumulative') # 누적 시간을 기준으로 정렬
stats.print_stats()
```

출력된 통계표의 각 열은 다음을 의미한다.

  * `ncalls`: 함수가 호출된 횟수
  * `tottime`: 다른 함수 실행 시간을 제외한, 해당 함수 자체의 총 실행 시간
  * `percall` (`tottime`): `tottime`을 `ncalls`로 나눈 값
  * `cumtime`: 해당 함수가 호출한 다른 모든 함수들의 실행 시간을 포함한 누적 실행 시간
  * `percall` (`cumtime`): `cumtime`을 `ncalls`로 나눈 값

초기 실행 결과, `insert_value` 함수의 누적 시간(`cumtime`)이 가장 큰 것을 확인하여 이 함수가 병목 지점임을 알 수 있었다.

```
         20003 function calls in 1.320 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    1.320    1.320 <stdin>:1(<lambda>)
        1    0.003    0.003    1.320    1.320 main.py:10(insertion_sort)
    10000    1.306    0.000    1.317    0.000 main.py:20(insert_value)
     ...
```

이제 `bisect` 모듈을 사용해 `insert_value` 함수를 훨씬 효율적으로 개선했다.

```python
from bisect import bisect_left

def insert_value(array, value):
    i = bisect_left(array, value)
    array.insert(i, value)
```

개선된 코드로 다시 프로파일링을 실행하자, 누적 실행 시간이 이전보다 거의 100배나 빨라진 것을 확인할 수 있었다. 이처럼 프로파일링은 최적화가 필요한 부분을 정확히 알려준다.

때로는 여러 곳에서 호출되는 공통 유틸리티 함수가 전체 실행 시간의 대부분을 차지할 수 있다. 기본 출력만으로는 어떤 함수가 이 유틸리티 함수를 많이 호출해서 문제를 일으키는지 알기 어렵다.

이때는 `stats.print_callers()` 메서드를 사용하면 된다. 이 메서드는 각 함수가 어떤 다른 함수에 의해 호출되었는지, 그리고 그 호출이 전체 시간에 얼마나 기여했는지를 명확히 보여주어 문제의 근본 원인을 찾는 데 도움을 주었다.

#### 기억해야 할 내용

  * 파이썬 프로그램의 성능 저하 원인은 직관과 다른 경우가 많으므로, 최적화하기 전에 반드시 프로파일링을 해야 한다.
  * `profile` 모듈보다 오버헤드가 적어 더 정확한 정보를 제공하는 `cProfile` 모듈을 사용하라.
  * `Profile` 객체의 `runcall` 메서드는 특정 함수 호출 트리를 격리하여 프로파일링하는 데 필요한 모든 것을 제공한다.
  * `Stats` 객체를 사용하면 프로파일링 정보 중에서 필요한 부분만 선택하고 정렬하여 프로그램 성능을 이해하는 데 도움을 받을 수 있다.