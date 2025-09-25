# 스택 활용 패턴 - 깊이 있는 이해

## 패턴 1: 괄호 매칭 (Bracket Matching)

### 핵심 아이디어
괄호 문제는 스택의 가장 직관적인 응용입니다. 왜일까요?

**중첩 구조의 본질**
- 가장 최근에 열린 괄호가 가장 먼저 닫혀야 함
- 이것이 바로 LIFO의 완벽한 예시

### 수학적 배경
```
유효한 괄호: ( ( ) ( ) )
스택 변화:  
1. ( → stack: ['(']
2. ( → stack: ['(', '(']
3. ) → stack: ['(']     # 가장 최근 '('와 매칭
4. ( → stack: ['(', '(']
5. ) → stack: ['(']
6. ) → stack: []

무효한 괄호: ( ( ) ) )
마지막 ')'에서 스택이 비어있음 → 매칭 실패
```

### 확장된 개념
```python
def is_valid_expression(expr):
    """
    괄호뿐만 아니라 begin/end, if/endif 등도 처리
    """
    stack = []
    pairs = {
        'end': 'begin',
        'endif': 'if',
        'endfor': 'for',
        ')': '(',
        '}': '{',
        ']': '['
    }
    
    tokens = expr.split()
    for token in tokens:
        if token in ['begin', 'if', 'for', '(', '{', '[']:
            stack.append(token)
        elif token in pairs:
            if not stack or stack[-1] != pairs[token]:
                return False
            stack.pop()
    
    return len(stack) == 0
```

### 실제 응용
1. **프로그래밍 언어 파서**: 코드 구문 검증
2. **HTML/XML 검증**: 태그 쌍 확인
3. **수식 검증**: 수학 표현식 유효성

---

## 패턴 2: 단조 스택 (Monotonic Stack)

### 핵심 아이디어
스택에 원소를 **단조증가** 또는 **단조감소** 상태로 유지하는 기법

**왜 필요한가?**
- "나보다 큰/작은 다음 원소 찾기" 문제를 O(n)에 해결
- 브루트포스 O(n²) → 단조 스택 O(n)

### 수학적 원리
```
배열: [2, 1, 2, 4, 3]
목표: 각 원소의 오른쪽에서 처음으로 큰 원소 찾기

단조 감소 스택 사용:
i=0, val=2: stack=[0]
i=1, val=1: stack=[0,1]
i=2, val=2: 1 < 2, pop(1) → ans[1]=2
           stack=[0,2]
i=3, val=4: 2 < 4, pop(2) → ans[2]=4
           2 < 4, pop(0) → ans[0]=4
           stack=[3]
i=4, val=3: stack=[3,4]

결과: [4, 2, 4, -1, -1]
```

### 패턴의 변형
```python
def next_greater_element(nums):
    """오른쪽의 첫 번째 큰 원소 찾기"""
    n = len(nums)
    result = [-1] * n
    stack = []  # 인덱스 저장
    
    for i in range(n):
        # 현재 원소보다 작은 원소들을 pop
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)
    
    return result

def daily_temperatures(temps):
    """며칠 후 더 따뜻해지는지"""
    n = len(temps)
    result = [0] * n
    stack = []
    
    for i in range(n):
        while stack and temps[stack[-1]] < temps[i]:
            idx = stack.pop()
            result[idx] = i - idx  # 날짜 차이
        stack.append(i)
    
    return result
```

### 단조 스택의 종류
1. **단조 증가 스택**: 작은 원소가 들어오면 pop
2. **단조 감소 스택**: 큰 원소가 들어오면 pop
3. **응용**: 슬라이딩 윈도우 최대/최소값

---

## 패턴 3: 히스토그램 최대 직사각형

### 핵심 아이디어
각 막대를 높이로 하는 직사각형의 최대 너비를 구하는 문제

**기하학적 통찰**
- 낮은 막대가 나타나면, 이전의 높은 막대들로 만들 수 있는 직사각형이 확정됨
- 스택을 사용해 "아직 확정되지 않은" 막대들을 관리

### 알고리즘의 직관
```
히스토그램: [2, 1, 5, 6, 2, 3]

높이 2: 너비를 확장 가능 → 스택에 저장
높이 1: 이전 막대(2)의 직사각형 확정 → 넓이 계산
높이 5: 너비를 확장 가능 → 스택에 저장
높이 6: 너비를 확장 가능 → 스택에 저장
높이 2: 이전 막대들(6, 5)의 직사각형 확정 → 넓이 계산
...
```

### 구현의 핵심
```python
def largest_rectangle_histogram(heights):
    """
    핵심: 스택에는 높이가 증가하는 인덱스만 유지
    """
    stack = []
    max_area = 0
    
    for i, h in enumerate(heights):
        # 현재 높이보다 큰 막대들 처리
        while stack and heights[stack[-1]] > h:
            height_idx = stack.pop()
            height = heights[height_idx]
            
            # 너비 계산이 핵심
            if not stack:
                width = i  # 처음부터 i-1까지
            else:
                width = i - stack[-1] - 1  # stack[-1]+1부터 i-1까지
            
            area = height * width
            max_area = max(max_area, area)
        
        stack.append(i)
    
    # 남은 막대 처리 (끝까지 확장 가능)
    while stack:
        height_idx = stack.pop()
        height = heights[height_idx]
        width = len(heights) if not stack else len(heights) - stack[-1] - 1
        max_area = max(max_area, height * width)
    
    return max_area
```

### 변형 문제
1. **최대 정사각형**: 2D 배열에서 최대 정사각형
2. **빗물 담기**: 높이 배열에서 담을 수 있는 물의 양
3. **스카이라인**: 건물들의 스카이라인 구하기

---

## 패턴 4: 후위 표기식과 수식 처리

### 컴파일러 이론 배경
컴파일러는 중위 표기식을 후위 표기식으로 변환하여 계산합니다.

**왜 후위 표기식인가?**
1. 괄호가 필요 없음
2. 연산 우선순위가 자동으로 처리됨
3. 스택 하나로 계산 가능

### 중위 → 후위 변환 (Shunting Yard Algorithm)
```python
def infix_to_postfix(expression):
    """
    Dijkstra의 Shunting Yard 알고리즘
    """
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3}
    associativity = {'+': 'L', '-': 'L', '*': 'L', '/': 'L', '^': 'R'}
    
    output = []
    operator_stack = []
    
    tokens = expression.split()
    
    for token in tokens:
        if token.isdigit():
            output.append(token)
        elif token == '(':
            operator_stack.append(token)
        elif token == ')':
            while operator_stack and operator_stack[-1] != '(':
                output.append(operator_stack.pop())
            operator_stack.pop()  # '(' 제거
        elif token in precedence:
            while (operator_stack and 
                   operator_stack[-1] != '(' and
                   operator_stack[-1] in precedence and
                   (precedence[operator_stack[-1]] > precedence[token] or
                    (precedence[operator_stack[-1]] == precedence[token] and 
                     associativity[token] == 'L'))):
                output.append(operator_stack.pop())
            operator_stack.append(token)
    
    while operator_stack:
        output.append(operator_stack.pop())
    
    return ' '.join(output)
```

### 후위 표기식 계산
```python
def evaluate_postfix(tokens):
    """
    후위 표기식 계산의 우아함
    """
    stack = []
    
    for token in tokens:
        if token not in '+-*/^':
            stack.append(float(token))
        else:
            # 주의: 순서가 중요 (b가 먼저 pop)
            b = stack.pop()
            a = stack.pop()
            
            if token == '+': stack.append(a + b)
            elif token == '-': stack.append(a - b)
            elif token == '*': stack.append(a * b)
            elif token == '/': stack.append(a / b)
            elif token == '^': stack.append(a ** b)
    
    return stack[0]
```

---

## 패턴 5: 백트래킹과 상태 저장

### 미로 찾기 예제
```python
def solve_maze(maze, start, end):
    """
    스택을 사용한 DFS 미로 탐색
    """
    stack = [(start, [start])]  # (현재 위치, 경로)
    visited = set()
    
    while stack:
        (x, y), path = stack.pop()
        
        if (x, y) == end:
            return path
        
        if (x, y) in visited:
            continue
        
        visited.add((x, y))
        
        # 상하좌우 탐색
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < len(maze) and 
                0 <= ny < len(maze[0]) and 
                maze[nx][ny] != '#' and 
                (nx, ny) not in visited):
                stack.append(((nx, ny), path + [(nx, ny)]))
    
    return None
```

---

## 🎯 패턴 인식 가이드

### 언제 스택을 사용할까?

1. **"가장 가까운" 문제**
   - 가장 가까운 큰 원소
   - 가장 최근의 매칭

2. **중첩 구조**
   - 괄호, 태그
   - 함수 호출

3. **되돌아가기**
   - 백트래킹
   - Undo 기능

4. **순서 역전**
   - 문자열 뒤집기
   - 역순 처리

### 스택 패턴 체크리스트
- [ ] LIFO 특성이 필요한가?
- [ ] 가장 최근 것과 비교가 필요한가?
- [ ] 중첩된 구조를 처리하는가?
- [ ] 이전 상태로 되돌아가야 하는가?
- [ ] O(n²)를 O(n)으로 최적화 가능한가?

---

## 📚 심화 학습 자료

1. **단조 스택 마스터하기**
   - Largest Rectangle in Histogram (LeetCode 84)
   - Maximal Rectangle (LeetCode 85)
   - Trapping Rain Water (LeetCode 42)

2. **표현식 처리**
   - Basic Calculator 시리즈
   - Decode String (LeetCode 394)

3. **그래프와 스택**
   - DFS의 반복적 구현
   - 위상 정렬
   - 강한 연결 요소 (Kosaraju's Algorithm)