"""
스택의 다양한 구현 방법
각 구현의 장단점과 사용 케이스를 이해하는 것이 중요합니다.
"""

# ============================================
# 1. 배열 기반 스택 (고정 크기)
# ============================================
class ArrayStack:
    """
    배열(리스트)을 사용한 고정 크기 스택
    
    장점:
    - 메모리 지역성이 좋음 (캐시 친화적)
    - 구현이 단순함
    - 임의 접근 가능 (필요시)
    
    단점:
    - 크기가 고정됨
    - 스택 오버플로우 가능
    - 메모리 낭비 가능 (미사용 공간)
    """
    
    def __init__(self, capacity=100):
        self.capacity = capacity
        self.data = [None] * capacity  # 고정 크기 배열
        self.top = -1  # 스택이 비어있을 때 -1
    
    def push(self, item):
        if self.is_full():
            raise OverflowError("Stack is full")
        self.top += 1
        self.data[self.top] = item
    
    def pop(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        item = self.data[self.top]
        self.data[self.top] = None  # 메모리 정리
        self.top -= 1
        return item
    
    def peek(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self.data[self.top]
    
    def is_empty(self):
        return self.top == -1
    
    def is_full(self):
        return self.top == self.capacity - 1
    
    def size(self):
        return self.top + 1
    
    def __str__(self):
        if self.is_empty():
            return "Stack: []"
        return f"Stack: {self.data[:self.top+1]} <- top"


# ============================================
# 2. 연결 리스트 기반 스택 (동적 크기)
# ============================================
class Node:
    """연결 리스트의 노드"""
    def __init__(self, data):
        self.data = data
        self.next = None

class LinkedListStack:
    """
    연결 리스트를 사용한 동적 스택
    
    장점:
    - 동적 크기 (메모리가 허용하는 한 무한)
    - 스택 오버플로우 없음
    - 메모리 효율적 (필요한 만큼만 사용)
    
    단점:
    - 추가 메모리 오버헤드 (포인터)
    - 메모리 지역성이 나쁨
    - 임의 접근 불가능
    """
    
    def __init__(self):
        self.top = None
        self._size = 0
    
    def push(self, item):
        new_node = Node(item)
        new_node.next = self.top
        self.top = new_node
        self._size += 1
    
    def pop(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        item = self.top.data
        self.top = self.top.next
        self._size -= 1
        return item
    
    def peek(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self.top.data
    
    def is_empty(self):
        return self.top is None
    
    def size(self):
        return self._size
    
    def __str__(self):
        if self.is_empty():
            return "Stack: []"
        
        result = []
        current = self.top
        while current:
            result.append(str(current.data))
            current = current.next
        return f"Stack: [{' -> '.join(result)}] <- top"


# ============================================
# 3. 이진 트리 기반 스택 (학술적 구현)
# ============================================
class TreeNode:
    """이진 트리의 노드"""
    def __init__(self, data):
        self.data = data
        self.left = None   # 이전 원소를 가리킴
        self.right = None  # 사용하지 않음 (학술적 목적)

class TreeStack:
    """
    이진 트리를 사용한 스택 (학술적 구현)
    
    이것은 일반적이지 않은 구현이지만, 
    자료구조의 유연성을 보여주는 예시입니다.
    
    장점:
    - 트리 구조의 다른 특성 활용 가능
    - 학술적 가치 (자료구조 변형 이해)
    
    단점:
    - 불필요하게 복잡함
    - 메모리 오버헤드 (사용하지 않는 right 포인터)
    - 성능상 이점 없음
    """
    
    def __init__(self):
        self.root = None  # 트리의 루트 = 스택의 top
        self._size = 0
    
    def push(self, item):
        new_node = TreeNode(item)
        if self.root:
            new_node.left = self.root  # 이전 top을 left로
        self.root = new_node
        self._size += 1
    
    def pop(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        item = self.root.data
        self.root = self.root.left  # left가 새로운 top
        self._size -= 1
        return item
    
    def peek(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self.root.data
    
    def is_empty(self):
        return self.root is None
    
    def size(self):
        return self._size
    
    def __str__(self):
        if self.is_empty():
            return "Stack: []"
        
        result = []
        current = self.root
        while current:
            result.append(str(current.data))
            current = current.left
        return f"Stack: [{' -> '.join(result)}] <- top"


# ============================================
# 4. 동적 배열 기반 스택 (Python 리스트)
# ============================================
class DynamicArrayStack:
    """
    Python 리스트를 사용한 동적 스택
    
    장점:
    - 구현이 매우 간단
    - 동적 크기
    - Python 내장 최적화 활용
    
    단점:
    - 리사이징시 O(n) 시간 (amortized O(1))
    - Python 리스트의 오버헤드
    """
    
    def __init__(self):
        self.data = []
    
    def push(self, item):
        self.data.append(item)
    
    def pop(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self.data.pop()
    
    def peek(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self.data[-1]
    
    def is_empty(self):
        return len(self.data) == 0
    
    def size(self):
        return len(self.data)
    
    def __str__(self):
        if self.is_empty():
            return "Stack: []"
        return f"Stack: {self.data} <- top"


# ============================================
# 5. 두 개의 스택을 하나의 배열로 구현
# ============================================
class TwoStacksInOne:
    """
    하나의 배열에 두 개의 스택을 구현
    메모리를 효율적으로 사용하는 기법
    
    사용 케이스:
    - 메모리가 제한적인 임베디드 시스템
    - 두 스택의 크기가 상호 보완적일 때
    """
    
    def __init__(self, capacity=100):
        self.capacity = capacity
        self.data = [None] * capacity
        self.top1 = -1  # 스택1: 왼쪽에서 시작
        self.top2 = capacity  # 스택2: 오른쪽에서 시작
    
    def push1(self, item):
        if self.top1 + 1 == self.top2:
            raise OverflowError("Stack is full")
        self.top1 += 1
        self.data[self.top1] = item
    
    def push2(self, item):
        if self.top2 - 1 == self.top1:
            raise OverflowError("Stack is full")
        self.top2 -= 1
        self.data[self.top2] = item
    
    def pop1(self):
        if self.top1 == -1:
            raise IndexError("Stack 1 is empty")
        item = self.data[self.top1]
        self.data[self.top1] = None
        self.top1 -= 1
        return item
    
    def pop2(self):
        if self.top2 == self.capacity:
            raise IndexError("Stack 2 is empty")
        item = self.data[self.top2]
        self.data[self.top2] = None
        self.top2 += 1
        return item
    
    def __str__(self):
        stack1 = self.data[:self.top1+1] if self.top1 >= 0 else []
        stack2 = self.data[self.top2:] if self.top2 < self.capacity else []
        return f"Stack1: {stack1}\nStack2: {stack2}"


# ============================================
# 테스트 및 비교
# ============================================
def test_all_stacks():
    """모든 스택 구현을 테스트하고 비교"""
    
    stacks = [
        ("Array Stack", ArrayStack(10)),
        ("Linked List Stack", LinkedListStack()),
        ("Tree Stack", TreeStack()),
        ("Dynamic Array Stack", DynamicArrayStack())
    ]
    
    print("=" * 50)
    print("스택 구현 테스트")
    print("=" * 50)
    
    for name, stack in stacks:
        print(f"\n{name}:")
        print("-" * 30)
        
        # Push 테스트
        for i in range(1, 4):
            stack.push(i * 10)
            print(f"Push {i * 10}: {stack}")
        
        # Peek 테스트
        print(f"Peek: {stack.peek()}")
        
        # Pop 테스트
        print(f"Pop: {stack.pop()}")
        print(f"After pop: {stack}")
        
        # Size 테스트
        print(f"Size: {stack.size()}")
        print(f"Is empty: {stack.is_empty()}")
    
    # Two Stacks 테스트
    print("\n" + "=" * 50)
    print("Two Stacks in One Array:")
    print("-" * 30)
    
    two_stacks = TwoStacksInOne(10)
    two_stacks.push1(10)
    two_stacks.push1(20)
    two_stacks.push2(100)
    two_stacks.push2(200)
    print(two_stacks)
    print(f"Pop from stack1: {two_stacks.pop1()}")
    print(f"Pop from stack2: {two_stacks.pop2()}")
    print(two_stacks)


def performance_comparison():
    """각 구현의 성능 비교"""
    import time
    
    n = 100000
    stacks = [
        ("Array Stack", ArrayStack(n + 1)),
        ("Linked List Stack", LinkedListStack()),
        ("Dynamic Array Stack", DynamicArrayStack())
    ]
    
    print("\n" + "=" * 50)
    print(f"성능 비교 (n = {n:,})")
    print("=" * 50)
    
    for name, stack in stacks:
        # Push 성능
        start = time.time()
        for i in range(n):
            stack.push(i)
        push_time = time.time() - start
        
        # Pop 성능
        start = time.time()
        for i in range(n):
            stack.pop()
        pop_time = time.time() - start
        
        print(f"\n{name}:")
        print(f"  Push time: {push_time:.4f} seconds")
        print(f"  Pop time:  {pop_time:.4f} seconds")
        print(f"  Total:     {push_time + pop_time:.4f} seconds")


if __name__ == "__main__":
    # 기본 테스트 실행
    test_all_stacks()
    
    # 성능 비교 (주석 해제하여 실행)
    # performance_comparison()