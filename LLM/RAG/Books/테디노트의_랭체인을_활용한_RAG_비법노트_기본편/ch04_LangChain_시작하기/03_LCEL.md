# LCEL

### `PromptTemplate`

그냥 문자열을 쓰는 대신 `PromptTemplate`을 사용한 이유는 **재사용성**과 **동적인 입력 처리** 때문이었다.

#### **예시: 여러 나라의 수도 물어보기**

예를 들어, 여러 나라의 수도를 물어보는 작업을 하고 싶었다. 이때 `PromptTemplate`을 사용해 질문의 뼈대를 만들었다.

```python
from langchain_core.prompts import PromptTemplate

# {country} 라는 변수가 포함된 템플릿 문자열을 정의했다.
template = "{country}의 수도는 어디인가요?"

# from_template 클래스 메소드로 간단하게 PromptTemplate 객체를 생성했다.
prompt_template = PromptTemplate.from_template(template)
```

이렇게 `prompt_template` 객체를 만들어두면, `{country}` 자리에 어떤 나라 이름을 넣든 일관된 형식의 질문을 생성할 준비가 끝난다. `.format()` 메소드를 써서 직접 확인해 볼 수도 있었다.

```python
# '대한민국'을 넣어 프롬프트를 완성해 보았다.
completed_prompt = prompt_template.format(country="대한민국")

print(completed_prompt)
# 출력: 대한민국의 수도는 어디인가요?
```

물론 체인을 사용하면 이 `.format()` 과정은 내부에서 자동으로 처리된다. 중요한 것은 **질문의 구조를 템플릿으로 정의**했다는 점이다.

-----

### LCEL로 연결하기 `|`

LCEL(LangChain Expression Language)는 **파이프(`|`) 연산자**를 쓰는 것이었다.

```python
from langchain_core.output_parsers import StrOutputParser

# 1. 프롬프트 템플릿과 모델을 연결했다.
chain = prompt_template | model

# 2. 모델의 출력(AIMessage)을 순수 텍스트로 바꿔줄 파서를 추가했다.
output_parser = StrOutputParser()

# 3. 최종 체인을 완성했다.
chain = prompt_template | model | output_parser
```

1.  사용자 입력(`{"country": "캐나다"}`)이 `prompt_template`으로 들어가 "캐나다의 수도는 어디인가요?" 라는 질문을 만든다.
2.  이 질문은 `|` 를 타고 `model`로 흘러 들어간다. 모델은 이 질문에 대한 답변(예: `AIMessage(content='캐나다의 수도는 오타와입니다.')`)을 생성한다.
3.  모델의 답변은 다시 `|` 를 타고 `output_parser`로 넘어간다. 파서는 복잡한 `AIMessage` 객체에서 내용물인 `'캐나다의 수도는 오타와입니다.'` 라는 순수 문자열만 쏙 뽑아낸다.

-----

### 완성된 체인 실행하기

#### **`.invoke()`: 한 번에 답변 받기**

`invoke` 메소드는 가장 일반적인 실행 방법이다. 체인에 입력을 던져주면 모든 과정을 거친 최종 결과물을 반환한다.

```python
# 'country' 변수에 '캐나다'를 넣어 체인을 실행했다.
response = chain.invoke({"country": "캐나다"})

print(response)
# 예상 출력: 캐나다의 수도는 오타와입니다.
```

#### **`.stream()`: 실시간으로 답변 스트리밍 받기**

`stream` 메소드는 챗봇처럼 답변이 생성되는 과정을 실시간으로 보여줄 때 유용했다.

```python
from langchain_teddynote.messages import stream_response

# '일본'을 주제로 스트리밍 실행
answer_stream = chain.stream({"country": "일본"})

# 스트리밍 응답을 실시간으로 출력했다.
stream_response(answer_stream)
# 출력: 일본의 수도는 도쿄입니다. (한 글자씩 나타남)
```
