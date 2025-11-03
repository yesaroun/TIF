from unittest.mock import patch

# 실제 API 클라이언트 클래스
class ApiClient:
    def get_user(self):
        # 실제로는 네트워크 요청을 보냄
        raise Exception("실제 API 호출!")

# API를 사용하는 비즈니스 로직
def fetch_username(api_client):
    return api_client.get_user()["name"]

# 테스트 코드
def test_fetch_username():
    client = ApiClient

    # ApiClient.get_user 메서드를 패치
    with patch.object(ApiClient, 'get_user', return_value={"name": "Alice", "age": 30}):
        # with 블록 안에서는 get_user()가 실제 API를 호출하지 않고
        # return_value로 지정한 {"name": "Alice", "age": 30}을 즉시 반환
        result = fetch_username(client)
        assert result == "Alice"  # 성공

# 데코레이터

# 외부 의존성을 가진 함수들
def send_email(to, subject, body):
    """이메일을 보내는 함수"""
    raise Exception("이메일 전송")

def process_signup(email, username):
    """회원가입 처리"""
    send_email(to=email, subject="환영합니다!", body=f"{username}님 가입을 환영합니다.")
    return True

# 테스트 코드
@patch("__main__.send_email")  # send_email 함수를 패치
def test_signup(mock_send_email):
    """회원 가입 시 이메일이 전송되는지 테스트"""
    # 테스트 실행
    result = process_signup("user@example.com", "Alice")

    # 검증: send_email이 올바른 인자로 호출되었는지 확인
    mock_send_email.assert_called_once_with(
        to="user@example.com",
        subject="환영합니다!",
        body="Alice님 가입을 환영합니다."
    )
    assert result is True


