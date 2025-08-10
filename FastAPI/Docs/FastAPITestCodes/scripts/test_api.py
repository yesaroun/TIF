#!/usr/bin/env python3
"""API 테스트 스크립트"""

import requests
import sys
from time import sleep


def test_api():
    """API 엔드포인트들을 테스트합니다"""
    base_url = "http://localhost:8000"

    print("API 테스트를 시작합니다...")

    # 서버가 실행 중인지 확인
    try:
        # 1. 루트 엔드포인트 테스트
        print("\n루트 엔드포인트 테스트:")
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"   상태코드: {response.status_code}")
        print(f"   응답: {response.json()}")

        # 2. 헬스체크 테스트
        print("\n헬스체크 테스트:")
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   상태코드: {response.status_code}")
        print(f"   응답: {response.json()}")

        # 3. 아이템 엔드포인트 테스트
        print("\n아이템 엔드포인트 테스트:")
        response = requests.get(f"{base_url}/items/42?q=테스트", timeout=5)
        print(f"   상태코드: {response.status_code}")
        print(f"   응답: {response.json()}")

        print("\n모든 테스트가 성공했습니다!")

    except requests.exceptions.ConnectionError:
        print("서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        print("서버 실행: uv run python scripts/serve.py")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("서버 응답 시간이 초과되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"테스트 중 오류가 발생했습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_api()
