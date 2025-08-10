#!/usr/bin/env python3
"""프로덕션 서버 실행 스크립트"""

import subprocess
import sys


def main():
    """FastAPI 프로덕션 서버를 실행합니다 (reload 없음)"""
    cmd = ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

    print("FastAPI 프로덕션 서버를 시작합니다...")
    print("URL: http://localhost:8000")
    print("️종료하려면 Ctrl+C를 누르세요")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
        sys.exit(0)


if __name__ == "__main__":
    main()
