# try/except/else/finally의 각 블록을 잘 활용하라


def try_finally_example(filename):
    print("* 파일 열기")
    handle = open(filename, encoding="utf-8")
    try:
        print("* 데이터 읽기")
        return handle.read()
    finally:
        print("* close() 호출")
        handle.close()


filename = "random_data.txt"

# with open(filename, "wb") as f:
#     f.write(b"\xf1\xf2\xf3\xf4\xf5")  # 잘못된 utf-8 이진 문자열

# data = try_finally_example(filename)

import json


def load_json_key(data, key):
    try:
        print("json 데이터 읽기")
        result_dict = json.loads(data)
    except ValueError as e:
        print("ValueError 처리")
        raise KeyError(key) from e
    else:
        print("키 검색")
        return result_dict[key]


UNDEFINED = object()


def divide_json(path):
    print("파일 열기")
    handle = open(path, "r+")
    try:
        print("데이터 읽기")
        data = handle.read()
        print("json 데이터 읽기")
        op = json.loads(data)
        print("계산 수행")
        value = op["numerator"] / op["denominator"]
    except ZeroDivisionError as e:
        print("ZeroDivisionError 처리")
        return UNDEFINED
    else:
        print("계산 결과 쓰기")
        op["result"] = value
        result = json.dumps(op)
        handle.seek(0)
        handle.write(result)
        return value
    finally:
        print("close() 호출")
        handle.close()


temp_path = "radom_data.json"

with open(temp_path, "w") as f:
    f.write('{"numberator": 1, "denominator": 10}')
assert divide_json(temp_path) == 0.1
