# Better Way 70 최적화하기 전에 프로파일링을 하라

from random import randint
from cProfile import Profile
from pstats import Stats
from bisect import bisect_left


def insertion_sort(data):
    result = []
    for value in data:
        insert_value(result, value)
    return result


def insert_value(array, value):
    for i, existing in enumerate(array):
        if existing > value:
            array.insert(i, value)
            return
    array.append(value)


def insert_value(array, value):
    i = bisect_left(array, value)
    array.insert(i, value)


max_size = 10**4
data = [randint(0, max_size) for _ in range(max_size)]
test = lambda: insertion_sort(data)

profiler = Profile()
profiler.runcall(test)

stats = Stats(profiler)
stats.strip_dirs()
stats.sort_stats("cumulative")  # 누적 통계
stats.print_stats()
"""
         20003 function calls in 1.399 seconds

   Ordered by: cumulative time
 함수호출횟수 함수실행시간         함수실행누적시간
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    1.399    1.399 BetterWay70.py:25(<lambda>)
        1    0.002    0.002    1.399    1.399 BetterWay70.py:8(insertion_sort)
    10000    1.393    0.000    1.397    0.000 BetterWay70.py:15(insert_value)
     9990    0.004    0.000    0.004    0.000 {method 'insert' of 'list' objects}
        1    0.000    0.000    0.000    0.000 {method 'disable' of '_lsprof.Profiler' objects}
       10    0.000    0.000    0.000    0.000 {method 'append' of 'list' objects}
"""
