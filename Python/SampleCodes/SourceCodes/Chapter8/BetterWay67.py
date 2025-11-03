# BetterWay67 지역 시간에는 time보다는 datetime을 사용하라

# time 모듈

import time

now = 1598523184
local_tuple = time.localtime(now)
time_format = "%Y-%m-%d %H:%M:%S"
time_str = time.strftime(time_format, local_tuple)
print(time_str)
# 2020-08-27 19:13:04

time_tuple = time.strptime(time_str, time_format)
utc_now = time.mktime(time_tuple)
print(utc_now)
# 1598523184.0

import os

if os.name == "nt":
    print("이 예제는 윈도우에서 작동하지 않습니다.")
else:
    parse_format = "%Y-%m-%d %H:%M:%S %Z"  # %Z는 시간대를 뜻함
    depart_icn = "2020-08-27 19:13:04 KST"
    time_tuple = time.strptime(depart_icn, parse_format)
    time_str = time.strftime(time_format, time_tuple)
    print(time_str)
    # 2020-08-27 19:13:04

# datetime 모듈
# 여러 시간대 사이의 변환을 다룬다면 datetime 모듈을 사용하라.

from datetime import datetime, timezone

now = datetime(2020, 8, 27, 10, 13, 4)  # 시간대 설정이 안 된 시간을 만듦
now_utc = now.replace(tzinfo=timezone.utc)  # 시간대를 UTC로 강제 지정
now_local = now_utc.astimezone()  # UTC 시간을 디폴트 시간대로 변환
print(now_local)
# 2020-08-27 19:13:04+09:00

time_str = '2020-08-27 19:13:04'
now = datetime.strptime(time_str, time_format)  # 시간대 설정이 안 된 시간으로 문자열을 구문 분석
time_tuple = now.timetuple()  # 유닉스 시간 구조체로 변환
utc_now = time.mktime(time_tuple)  # 구조체로부터 유닉스 타임스탬프 생성
print(utc_now)
