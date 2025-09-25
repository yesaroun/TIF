"""
스택 연습 문제
직접 구현해보면서 스택 활용법을 익혀보세요!
"""
from typing import List


def problem1_valid_parentheses(s: str) -> bool:
    """
    문제 1: 유효한 괄호 (기본)
    
    주어진 문자열 s가 유효한 괄호 문자열인지 판단하세요.
    괄호는 '(', ')', '{', '}', '[', ']' 6종류입니다.
    
    유효한 조건:
    1. 여는 괄호는 같은 타입의 닫는 괄호로 닫혀야 함
    2. 괄호는 올바른 순서로 닫혀야 함
    3. 모든 닫는 괄호는 대응하는 여는 괄호가 있어야 함
    
    입력: s = "()[]{}"
    출력: True
    
    입력: s = "([)]"
    출력: False
    
    입력: s = "{[]}"
    출력: True
    """
    # 구현해보세요
    pass


def problem2_daily_temperatures(temperatures: List[int]) -> List[int]:
    """
    문제 2: 일일 온도 (단조 스택)
    
    매일의 온도 리스트가 주어질 때, 각 날짜별로 더 따뜻한 날까지 
    며칠을 기다려야 하는지를 담은 리스트를 반환하세요.
    더 따뜻한 날이 없다면 0을 반환합니다.
    
    입력: temperatures = [73,74,75,71,69,72,76,73]
    출력: [1,1,4,2,1,1,0,0]
    
    설명: 
    - 73도(0일)는 다음날 74도가 더 따뜻하므로 1일
    - 75도(2일)는 4일 후 76도가 더 따뜻하므로 4일
    - 76도(6일)는 이후 더 따뜻한 날이 없으므로 0일
    
    힌트: 스택에 인덱스를 저장하면서, 현재 온도가 스택 top의 온도보다 
          높으면 pop하면서 결과를 기록하세요.
    """
    # 구현해보세요
    pass


def problem3_largest_rectangle(heights: List[int]) -> int:
    """
    문제 3: 히스토그램에서 최대 직사각형 (히스토그램 패턴)
    
    히스토그램의 높이 배열이 주어질 때, 만들 수 있는 
    최대 직사각형의 넓이를 구하세요.
    
    입력: heights = [2,1,5,6,2,3]
    출력: 10
    
    설명: 인덱스 2,3의 막대(높이 5,6)를 포함하는 
          너비 2, 높이 5인 직사각형의 넓이가 10으로 최대
    
    입력: heights = [2,4]
    출력: 4
    
    힌트: 
    1. 스택에 인덱스를 저장
    2. 현재 높이가 스택 top의 높이보다 낮으면, 
       스택에서 pop하면서 직사각형 넓이 계산
    3. 너비는 현재 인덱스와 스택의 새로운 top 사이의 거리
    """
    # 구현해보세요
    pass


def problem4_eval_rpn(tokens: List[str]) -> int:
    """
    문제 4: 후위 표기식 계산 (응용)
    
    후위 표기식(Reverse Polish Notation)으로 표현된 
    수식을 계산하세요.
    
    유효한 연산자는 '+', '-', '*', '/' 입니다.
    나눗셈은 0 방향으로 truncate 합니다.
    
    입력: tokens = ["2","1","+","3","*"]
    출력: 9
    설명: ((2 + 1) * 3) = 9
    
    입력: tokens = ["4","13","5","/","+"]
    출력: 6
    설명: (4 + (13 / 5)) = 4 + 2 = 6
    
    입력: tokens = ["10","6","9","3","+","-11","*","/","*","17","+","5","+"]
    출력: 22
    설명: ((10 * (6 / ((9 + 3) * -11))) + 17) + 5
          = ((10 * (6 / -132)) + 17) + 5
          = ((10 * 0) + 17) + 5
          = 22
    
    힌트: 
    1. 숫자는 스택에 push
    2. 연산자를 만나면 스택에서 2개 pop (순서 주의!)
    3. 계산 결과를 다시 스택에 push
    """
    # 구현해보세요
    pass


def test_problems():
    """
    작성한 함수들을 테스트하는 코드입니다.
    각 문제를 구현한 후 이 함수를 실행해보세요.
    """
    print("=== 문제 1: 유효한 괄호 ===")
    test_cases_1 = [
        ("()[]{}", True),
        ("([)]", False),
        ("{[]}", True),
        ("(", False),
        ("(){}}{", False)
    ]
    for s, expected in test_cases_1:
        result = problem1_valid_parentheses(s)
        status = "✓" if result == expected else "✗"
        print(f"{status} Input: {s:15} Expected: {expected:5} Got: {result}")
    
    print("\n=== 문제 2: 일일 온도 ===")
    temps = [73,74,75,71,69,72,76,73]
    expected = [1,1,4,2,1,1,0,0]
    result = problem2_daily_temperatures(temps)
    print(f"Input:    {temps}")
    print(f"Expected: {expected}")
    print(f"Got:      {result}")
    print(f"Result: {'✓' if result == expected else '✗'}")
    
    print("\n=== 문제 3: 최대 직사각형 ===")
    test_cases_3 = [
        ([2,1,5,6,2,3], 10),
        ([2,4], 4),
        ([1], 1),
        ([1,1,1,1], 4)
    ]
    for heights, expected in test_cases_3:
        result = problem3_largest_rectangle(heights)
        status = "✓" if result == expected else "✗"
        print(f"{status} Input: {str(heights):20} Expected: {expected:3} Got: {result}")
    
    print("\n=== 문제 4: 후위 표기식 ===")
    test_cases_4 = [
        (["2","1","+","3","*"], 9),
        (["4","13","5","/","+"], 6),
        (["10","6","9","3","+","-11","*","/","*","17","+","5","+"], 22)
    ]
    for tokens, expected in test_cases_4:
        result = problem4_eval_rpn(tokens)
        status = "✓" if result == expected else "✗"
        print(f"{status} Expected: {expected:3} Got: {result}")
        print(f"   Tokens: {' '.join(tokens)}")


if __name__ == "__main__":
    # 문제를 모두 구현한 후 주석을 해제하고 실행해보세요
    # test_problems()
    pass