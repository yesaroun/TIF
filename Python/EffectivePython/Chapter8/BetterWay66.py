from threading import Lock

lock = Lock()

# with 문이 시작될 때 lock 객체의 __enter__ 메서드가 호출되어 락을 획득
# with 블록 내무 코드 실행
# with 블록이 끝나면 lock 객체의 __exit__ 메서드가 호출되어 반드시 lock을 해제
with lock:
    ...


import logging


def my_function():
    logging.debug("디버깅 데이터")
    logging.error("이 부분은 오류 로그")
    logging.debug("추가 디버깅 데이터")


my_function()

# with 문과 함께 사용할 수 있는 커스텀 컨텍스트 매니저를 만들기 위해
from contextlib import contextmanager


# 해당 데코레이터는 제너레이터 함수를 컨텍스트 매니저로 변환해준다.
# 이 데코레이터를 사용하면 __enter__와 __exit__ 메서드를 가진 클래스를 만들 필요 없이 간단하게 구현할 수 있다.
@contextmanager
def debug_logging(level):
    """
    일시적으로 로깅 레벨을 변경하는 컨텍스트 매니저

    동작 원리
    1. with문이 시작되면 이 제너레이터 함수가 호출된다.
    2. yield 이전 코드(__enter__ 로직)가 실행된다.
    3. yield 에서 제어가 with 블록 안의 코드로 넘어간다.
    4. with 블록의 실행이 끝나면, yield 이후의 코드(__exit__ 로직)가 실행된다.
    """
    # 2. __enter__ 부분
    logger = logging.getLogger()  # 기존 루트 로거를 가져온다
    old_level = logger.getEffectiveLevel()  # 현재 로거 레벨을 저장
    logger.setLevel(level)  # 원하는 새 레벨로 설정
    try:
        # 3. 제어 양보
        # 이 지점에서 함수의 실행이 멈추고 with 블록 코드 실행
        # 'with ... as 변수' 형태로 사용하면 yield 뒤에 오는 값이 '변수'에 할당
        # 여기서는 아무것도 반환하지 않으므로 'as'없이 사용
        yield
    finally:
        # 4. __exit__ 부분
        # with 블록 코드가 모두 실행된 후(성공하든, 예외가 발생하든)
        # 반드시 실행되는 부분
        logger.setLevel(old_level)  # 기존 레벨로 설졍


with log_level(logging.DEBUG, "my-log") as logger:
    logger.debug(f"대상: {logger.name}!")
    logging.debug("이 메세지는 출력되지 않습니다")
