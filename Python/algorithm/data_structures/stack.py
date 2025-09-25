"""
스택(Stack) 자료구조 - 개념 및 패턴
"""

# 기본 스택 구현
class Stack:
    def __init__(self):
        self.items = []
    
    def push(self, item):
        self.items.append(item)
    
    def pop(self):
        if not self.is_empty():
            return self.items.pop()
        return None
    
    def peek(self):
        if not self.is_empty():
            return self.items[-1]
        return None
    
    def is_empty(self):
        return len(self.items) == 0
    
    def size(self):
        return len(self.items)


# Python 리스트를 스택으로 활용
def stack_with_list():
    stack = []
    
    # push
    stack.append(1)
    stack.append(2)
    stack.append(3)
    
    # pop
    top = stack.pop()  # 3
    
    # peek
    if stack:
        peek = stack[-1]  # 2
    
    # is_empty
    is_empty = len(stack) == 0


# 패턴 1: 괄호 매칭 템플릿
def bracket_matching_template(s: str) -> bool:
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in pairs.values():  # 여는 괄호
            stack.append(char)
        elif char in pairs:  # 닫는 괄호
            if not stack or stack[-1] != pairs[char]:
                return False
            stack.pop()
    
    return len(stack) == 0

# 패턴 2: 단조 스택 (Monotonic Stack) 템플릿
def monotonic_stack_template(nums):
    stack = []  # 인덱스를 저장
    result = [0] * len(nums)
    
    for i, num in enumerate(nums):
        # 현재 값보다 작은 값들을 pop (단조 증가 스택)
        while stack and nums[stack[-1]] < num:
            idx = stack.pop()
            # idx 위치의 답은 현재 인덱스 i
            result[idx] = i - idx
        stack.append(i)
    
    return result


# 패턴 3: 히스토그램 최대 직사각형 템플릿
def histogram_template(heights):
    stack = []  # 인덱스를 저장
    max_area = 0
    
    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            height_idx = stack.pop()
            height = heights[height_idx]
            # 너비 계산
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)
    
    # 남은 막대 처리
    while stack:
        height_idx = stack.pop()
        height = heights[height_idx]
        width = len(heights) if not stack else len(heights) - stack[-1] - 1
        max_area = max(max_area, height * width)
    
    return max_area


# 패턴 4: 후위 표기식 계산 템플릿
def postfix_evaluation_template(tokens):
    stack = []
    operators = {'+', '-', '*', '/'}
    
    for token in tokens:
        if token in operators:
            # 주의: 순서가 중요 (second가 먼저 pop)
            second = stack.pop()
            first = stack.pop()
            
            if token == '+':
                stack.append(first + second)
            elif token == '-':
                stack.append(first - second)
            elif token == '*':
                stack.append(first * second)
            elif token == '/':
                # 정수 나눗셈 (0 방향으로 truncate)
                stack.append(int(first / second))
        else:
            stack.append(int(token))
    
    return stack[0]


# 추가 팁: 스택 문제 접근법
"""
1. 스택이 유용한 상황:
   - 가장 최근 것과 비교가 필요할 때
   - 순서가 중요한 매칭 문제
   - 이전 상태로 되돌아가야 할 때
   - 중첩된 구조를 처리할 때

2. 스택에 무엇을 저장할지 결정:
   - 값 자체를 저장할지
   - 인덱스를 저장할지
   - (값, 인덱스) 튜플을 저장할지

3. 언제 push/pop 할지 결정:
   - 조건을 명확히 정의
   - while문으로 연속 pop이 필요한지 확인
"""
