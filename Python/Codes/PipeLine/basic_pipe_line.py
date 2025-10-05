class Pipe:
    def __init__(self, value):
        self.value = value

    def __or__(self, func):
        """| 연산자를 파이프라인으로 사용"""
        return Pipe(func(self.value))

    def __ror__(self, value):
        """역방향 | 연산자"""
        return Pipe(value)

    def get(self):
        """최종 값 추출"""
        return self.value

def add_10(x):
    return x + 10

def multiply_2(x):
    return x * 2

def subtract_5(x):
    return x - 5

result = (5 | Pipe 
          | add_10      # 5 + 10 = 15
          | multiply_2  # 15 * 2 = 30
          | subtract_5  # 30 - 5 = 25
          ).get()

print(result)  # 25

