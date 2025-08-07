# LCEL Advanced

## LCEL 인터페이스: invoke, stream, batch, 병렬 처리

LangChain으로 커스텀 체인을 만들다 보면, 모든 컴포넌트가 `Runnable`이라는 표준 프로토콜을 따른다는 것을 알게 되었다. 이 프로토콜 덕분에 어떤 컴포넌트든 일관된 방식으로 호출하고, 조합하고, 확장할 수 있었다.

-----

### 테스트를 위한 기본 체인 준비

먼저, 다양한 인터페이스를 테스트하기 위해 간단한 체인을 하나 만들었다. 특정 주제(`topic`)를 입력받아 세 문장으로 설명해 주는 체인이다.

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ChatOpenAI 모델을 인스턴스화했다.
model = ChatOpenAI()

# 주어진 토픽에 대한 설명을 요청하는 프롬프트 템플릿을 생성했다.
prompt = PromptTemplate.from_template("{topic} 에 대하여 3문장으로 설명해줘.")

# 프롬프트, 모델, 출력 파서를 파이프(|)로 연결하여 체인을 완성했다.
chain = prompt | model | StrOutputParser()
```

이 `chain` 객체를 가지고 이제부터 LangChain의 기본 호출 방식들을 하나씩 확인한다.

-----

### 동기(Synchronous) 인터페이스

동기적으로 작동하는 세 가지 핵심 메소드

#### **`invoke`: 가장 기본적인 호출**

`invoke`는 **하나의 입력을 받아 하나의 완전한 결과**를 반환하는, 가장 직관적인 메소드다.

```python
# chain 객체의 invoke 메서드를 호출하고, 'ChatGPT'라는 주제를 전달했다.
response = chain.invoke({"topic": "ChatGPT"})

print(response)
```

이 코드를 실행하자, 체인은 "ChatGPT"라는 주제에 대한 세 문장의 설명을 생성하여 하나의 완전한 문자열로 반환해 주었다.

#### **`stream`: 실시간 응답 스트리밍**

`stream`은 챗봇처럼 답변이 생성되는 과정을 **실시간으로 보여줄 때** 유용  
전체 답변이 완성될 때까지 기다릴 필요 없이, 생성되는 토큰을 즉시 받아 처리할 수 있다.

```python
# '멀티모달' 토픽에 대한 스트림을 생성하고, 각 토큰을 실시간으로 출력했다.
for token in chain.stream({"topic": "멀티모달"}):
    # 스트림에서 받은 데이터의 내용을 출력했다. 줄바꿈 없이 이어서 출력하고, 버퍼를 즉시 비웠다.
    print(token, end="", flush=True)
```

답변이 한 글자씩 화면에 나타나는 것을 볼 수 있다.

#### **`batch`: 여러 입력을 한 번에 효율적으로**

`batch` 메소드는 **여러 개의 입력을 리스트로 받아 한 번에 처리**하는 방식이다. `for` 루프 안에서 `invoke`를 여러 번 호출하는 것보다 훨씬 효율적

```python
# 두 개의 토픽을 리스트에 담아 batch로 처리했다.
results = chain.batch([{"topic": "ChatGPT"}, {"topic": "Instagram"}])

print(results)
```

여기에 `max_concurrency` 옵션을 추가하면 **동시 요청 수**를 제어할 수도 있다. 이는 API 서버에 과부하를 주지 않으면서 최대한 빠르게 여러 작업을 처리해야 할 때 유용한 기능

```python
# 5개의 입력을 최대 3개씩 동시에 처리하도록 설정하여 배치 작업을 실행했다.
chain.batch(
    [
        {"topic": "ChatGPT"},
        {"topic": "Instagram"},
        {"topic": "멀티모달"},
        {"topic": "프로그래밍"},
        {"topic": "머신러닝"},
    ],
    config={"max_concurrency": 3},
)
```

-----

### 비동기(Asynchronous) 인터페이스

이들은 `async`와 `await` 키워드와 함께 사용되며, 여러 작업을 동시에 처리해야 하는 웹 애플리케이션 등에서 프로그램이 멈추는 것을 방지하고 성능을 극대화하는 데 필수적

* **`astream` / `ainvoke` / `abatch`**: 각각 `stream`, `invoke`, `batch`의 비동기 버전이다. `await` 키워드로 호출하여 작업이 완료될 때까지 기다리는 방식으로 사용

```python
# astream: 비동기 스트림 처리
async for token in chain.astream({"topic": "YouTube"}):
    print(token, end="", flush=True)

# ainvoke: 비동기 호출
nvda_explanation = await chain.ainvoke({"topic": "NVDA"})
print(nvda_explanation)


# abatch: 비동기 배치 처리
social_media_explanations = await chain.abatch(
    [{"topic": "YouTube"}, {"topic": "Instagram"}, {"topic": "Facebook"}]
)
print(social_media_explanations)
```

-----

### 병렬(Parallel) 처리

`RunnableParallel`을 사용하면, **하나의 입력에 대해 여러 체인을 동시에 실행**하고 그 결과를 깔끔하게 묶어서 받을 수 있다.

#### **예시: 국가별 수도와 면적 동시에 물어보기**

한 국가의 이름(`country`)을 입력받아, 그 나라의 '수도'를 묻는 체인과 '면적'을 묻는 체인을 각각 만들었다.

```python
from langchain_core.runnables import RunnableParallel

# 1. {country}의 수도를 물어보는 체인 생성
chain1 = (
    PromptTemplate.from_template("{country} 의 수도는 어디야?")
    | model
    | StrOutputParser()
)

# 2. {country}의 면적을 물어보는 체인 생성
chain2 = (
    PromptTemplate.from_template("{country} 의 면적은 얼마야?")
    | model
    | StrOutputParser()
)
```

그리고 `RunnableParallel`을 이용해 이 두 체인을 하나로 묶었다.

```python
# 두 체인을 'capital'과 'area'라는 키로 묶어 병렬 실행 체인을 만들었다.
combined = RunnableParallel(capital=chain1, area=chain2)

# '대한민국'을 입력하여 병렬 체인을 실행했다.
result = combined.invoke({"country": "대한민국"})

print(result)
```

결과는 `chain1`과 `chain2`의 실행 결과를 각각 `capital`과 `area` 키에 담은 딕셔너리 형태로 반환되었다. LangChain이 내부적으로 두 체인을 **동시에 실행**하고 결과를 보기 좋게 정리해 준 것이다.

이 병렬 처리는 **배치 처리와 결합**되었을 때 더욱 강력했다. `combined.batch()`를 호출하면, 여러 국가에 대해 각각 수도와 면적을 묻는 작업을 동시에 처리하는, 즉 배치의 병렬 처리가 가능

```python
# 여러 국가에 대해 수도와 면적을 동시에, 그리고 일괄적으로 처리했다.
batch_results = combined.batch([{"country": "대한민국"}, {"country": "미국"}])

print(batch_results)
```
