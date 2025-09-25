# 스택의 심화 개념 - 시스템 레벨 이해

## 1. 함수 호출 스택 (Call Stack)

### 프로그램 실행의 핵심
모든 프로그램은 함수 호출 스택 위에서 실행됩니다.

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

result = factorial(5)
```

### 스택 프레임의 구조
```
factorial(5) 호출 시 메모리 구조:

High Memory
┌─────────────────┐
│ factorial(1)    │ ← 스택 프레임 5
├─────────────────┤   - 지역 변수: n=1
│ factorial(2)    │ ← 스택 프레임 4   - 반환 주소
├─────────────────┤   - 지역 변수: n=2
│ factorial(3)    │ ← 스택 프레임 3
├─────────────────┤   
│ factorial(4)    │ ← 스택 프레임 2
├─────────────────┤
│ factorial(5)    │ ← 스택 프레임 1
├─────────────────┤
│ main()          │ ← 베이스 프레임
└─────────────────┘
Low Memory
```

### 스택 프레임의 구성 요소
1. **반환 주소**: 함수 종료 후 돌아갈 위치
2. **매개변수**: 함수에 전달된 인자
3. **지역 변수**: 함수 내에서 선언된 변수
4. **이전 프레임 포인터**: 호출자의 스택 프레임

---

## 2. 스택 오버플로우의 이해

### 발생 원인
```python
# 1. 무한 재귀
def infinite_recursion():
    return infinite_recursion()  # RecursionError

# 2. 깊은 재귀
def deep_recursion(n):
    if n == 0:
        return 0
    return 1 + deep_recursion(n-1)

# Python의 기본 재귀 한계: 약 1000
import sys
print(sys.getrecursionlimit())  # 1000

# 한계 변경 (주의: 실제 스택 크기는 OS가 제한)
sys.setrecursionlimit(10000)
```

### 스택 vs 힙
```
메모리 구조:
┌─────────────────┐
│     Stack       │ ← 함수 호출, 지역 변수 (아래로 증가)
│       ↓         │
│                 │
│                 │
│       ↑         │
│     Heap        │ ← 동적 할당 (위로 증가)
├─────────────────┤
│      Data       │ ← 전역 변수, 정적 변수
├─────────────────┤
│      Text       │ ← 프로그램 코드
└─────────────────┘
```

### 재귀를 반복문으로 변환
```python
# 재귀 버전 (스택 오버플로우 위험)
def fibonacci_recursive(n):
    if n <= 1:
        return n
    return fibonacci_recursive(n-1) + fibonacci_recursive(n-2)

# 반복문 버전 (명시적 스택 사용)
def fibonacci_iterative(n):
    if n <= 1:
        return n
    
    stack = [n]
    result = 0
    memo = {}
    
    while stack:
        curr = stack[-1]
        
        if curr in memo:
            stack.pop()
            continue
        
        if curr <= 1:
            memo[curr] = curr
            stack.pop()
        else:
            if curr-1 in memo and curr-2 in memo:
                memo[curr] = memo[curr-1] + memo[curr-2]
                stack.pop()
            else:
                if curr-1 not in memo:
                    stack.append(curr-1)
                if curr-2 not in memo:
                    stack.append(curr-2)
    
    return memo[n]
```

---

## 3. 꼬리 재귀 최적화 (Tail Recursion)

### 개념
함수의 마지막 동작이 재귀 호출인 경우, 현재 스택 프레임을 재사용 가능

```python
# 일반 재귀 (스택 누적)
def factorial_normal(n, acc=1):
    if n <= 1:
        return acc
    return n * factorial_normal(n-1)  # 곱셈이 마지막 연산

# 꼬리 재귀 (최적화 가능)
def factorial_tail(n, acc=1):
    if n <= 1:
        return acc
    return factorial_tail(n-1, n*acc)  # 재귀가 마지막 연산

# Python은 꼬리 재귀 최적화를 지원하지 않음
# 하지만 수동으로 반복문으로 변환 가능
def factorial_iterative(n):
    acc = 1
    while n > 1:
        acc *= n
        n -= 1
    return acc
```

---

## 4. 스택과 코루틴

### 실행 컨텍스트 저장
```python
def coroutine_example():
    """
    제너레이터는 실행 상태를 저장하는 특별한 스택 구조
    """
    print("시작")
    x = yield 1
    print(f"받은 값: {x}")
    y = yield 2
    print(f"받은 값: {y}")
    return 3

# 코루틴 사용
gen = coroutine_example()
print(next(gen))        # "시작" 출력 후 1 반환
print(gen.send(10))     # "받은 값: 10" 출력 후 2 반환
try:
    gen.send(20)        # "받은 값: 20" 출력 후 StopIteration
except StopIteration as e:
    print(f"반환값: {e.value}")  # 3
```

---

## 5. 스택 기반 가상 머신

### 간단한 스택 머신 구현
```python
class StackMachine:
    """
    바이트코드를 실행하는 간단한 스택 머신
    """
    def __init__(self):
        self.stack = []
        self.program_counter = 0
        self.instructions = []
    
    def run(self, bytecode):
        self.instructions = bytecode
        self.program_counter = 0
        
        while self.program_counter < len(self.instructions):
            instruction = self.instructions[self.program_counter]
            self.execute(instruction)
            self.program_counter += 1
        
        return self.stack[-1] if self.stack else None
    
    def execute(self, instruction):
        opcode, *args = instruction
        
        if opcode == "PUSH":
            self.stack.append(args[0])
        elif opcode == "POP":
            return self.stack.pop()
        elif opcode == "ADD":
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a + b)
        elif opcode == "MUL":
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a * b)
        elif opcode == "DUP":
            self.stack.append(self.stack[-1])
        elif opcode == "SWAP":
            self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]

# 사용 예: (2 + 3) * 4 계산
vm = StackMachine()
bytecode = [
    ("PUSH", 2),
    ("PUSH", 3),
    ("ADD",),
    ("PUSH", 4),
    ("MUL",)
]
result = vm.run(bytecode)  # 20
```

---

## 6. 비동기 프로그래밍과 스택

### 이벤트 루프와 콜 스택
```python
import asyncio

async def async_operation(name, delay):
    """
    비동기 함수는 실행을 중단하고 나중에 재개
    """
    print(f"{name} 시작")
    await asyncio.sleep(delay)  # 여기서 스택을 보존하고 중단
    print(f"{name} 완료")
    return f"{name} 결과"

async def main():
    # 동시 실행 - 각각 독립적인 실행 컨텍스트
    results = await asyncio.gather(
        async_operation("작업1", 2),
        async_operation("작업2", 1),
        async_operation("작업3", 3)
    )
    print(results)

# asyncio.run(main())
```

---

## 7. 스택 보안

### 스택 버퍼 오버플로우
```c
// C 코드 예제 (Python에서는 발생하지 않음)
void vulnerable_function(char *input) {
    char buffer[64];  // 스택에 64바이트 할당
    strcpy(buffer, input);  // 위험: 크기 검사 없음
}

// 공격자가 64바이트 이상 입력 시:
// - 반환 주소 덮어쓰기 가능
// - 임의 코드 실행 가능
```

### 보호 기법
1. **스택 카나리**: 버퍼와 반환 주소 사이에 특수 값 배치
2. **ASLR**: 스택 주소 랜덤화
3. **NX 비트**: 스택 영역 실행 금지

---

## 8. 실전 최적화 기법

### 1. 스택 크기 예측
```python
def optimize_stack_size():
    """
    필요한 스택 크기를 미리 계산
    """
    # 최대 깊이를 알고 있을 때
    MAX_DEPTH = 1000
    stack = [None] * MAX_DEPTH
    top = -1
    
    # push
    top += 1
    stack[top] = value
    
    # pop
    value = stack[top]
    top -= 1
```

### 2. 스택 캐싱
```python
class CachedStack:
    """
    pop된 노드를 재사용하여 메모리 할당 최소화
    """
    def __init__(self):
        self.top = None
        self.free_list = []  # 재사용 가능한 노드
    
    def push(self, value):
        if self.free_list:
            node = self.free_list.pop()
            node.value = value
            node.next = self.top
        else:
            node = Node(value)
            node.next = self.top
        self.top = node
    
    def pop(self):
        if not self.top:
            return None
        node = self.top
        self.top = node.next
        value = node.value
        self.free_list.append(node)  # 재사용을 위해 보관
        return value
```

---

## 9. 디버깅과 스택 트레이스

### 스택 트레이스 읽기
```python
import traceback

def function_a():
    function_b()

def function_b():
    function_c()

def function_c():
    raise ValueError("에러 발생!")

try:
    function_a()
except ValueError:
    traceback.print_exc()
    
# 출력:
# Traceback (most recent call last):
#   File "example.py", line 12, in <module>
#     function_a()
#   File "example.py", line 2, in function_a
#     function_b()
#   File "example.py", line 5, in function_b
#     function_c()
#   File "example.py", line 8, in function_c
#     raise ValueError("에러 발생!")
# ValueError: 에러 발생!
```

### 커스텀 스택 트레이스
```python
import inspect

def print_call_stack():
    """현재 호출 스택 출력"""
    for frame_info in inspect.stack():
        print(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
```

---

## 10. 함수형 프로그래밍과 스택

### Continuation-Passing Style (CPS)
```python
def factorial_cps(n, continuation):
    """
    연속 전달 스타일로 스택 사용 제어
    """
    if n <= 1:
        return continuation(1)
    else:
        return factorial_cps(n - 1, lambda result: continuation(n * result))

# 사용
result = factorial_cps(5, lambda x: x)  # 120
```

---

## 🎯 핵심 정리

1. **스택은 프로그램 실행의 기반**
   - 함수 호출, 지역 변수, 실행 컨텍스트 관리

2. **메모리 구조 이해가 중요**
   - 스택 vs 힙의 차이
   - 스택 오버플로우의 원인과 해결

3. **최적화 기법 활용**
   - 꼬리 재귀, 반복문 변환
   - 메모리 재사용, 캐싱

4. **보안 고려사항**
   - 버퍼 오버플로우 방지
   - 안전한 재귀 깊이 설정

5. **디버깅 능력**
   - 스택 트레이스 분석
   - 실행 흐름 추적

스택은 단순한 자료구조가 아닌, 컴퓨터 과학의 핵심 개념입니다.