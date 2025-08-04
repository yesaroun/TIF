# Ch04 LangChain 시작하기

## 01 ChatOpenAI 주요 매개변수와 출력

`ChatOpenAI` 클래스는 OpenAI의 언어 모델과 상호 작용하는 데 사용된다. 모델의 동작을 제어하기 위해 여러 매개변수를 설정할 수 있다.

### **temperature**

  * `temperature`는 모델 출력의 **창의성 또는 무작위성**을 조절하는 매개변수이다.
  * 값의 범위는 **0과 2 사이**이며, 기본값은 0.7이다.
  * **높은 값**을 지정하면 모델이 더 다양하고 예상치 못한, 즉 무작위적인 텍스트를 생성할 가능성이 커진다.
  * 반대로 **낮은 값**(예: 0.1)으로 설정하면 모델은 더 일관성 있고 예측 가능한, 결정적인 답변을 생성한다.

### **max\_tokens**

  * `max_tokens`는 모델이 **생성할 수 있는 최대 토큰 수**를 지정하는 매개변수이다.
  * 이는 응답의 길이를 제어하는 데 사용된다. 예를 들어, `max_tokens=2048`로 설정하면 모델은 최대 2048개의 토큰으로 구성된 응답을 반환한다.

-----

### **logprob 활성화하기**

`logprob`(로그 프로버빌리티)는 GPT 모델이 특정 토큰을 예측할 확률의 로그 값이다. 이 값은 모델이 각 토큰을 얼마나 확신하고 생성했는지를 나타내는 지표로 활용될 수 있다.

`logprobs=True` 옵션을 `.bind()` 메서드에 추가하여 `logprob` 정보를 활성화하고 출력에서 확인할 수 있다.

```python
from langchain_openai import ChatOpenAI

# logprob를 활성화하여 llm 객체 생성
llm_with_logprob = ChatOpenAI(
    temperature=0.1,
    max_tokens=2048,
    model_name="gpt-4o-mini",
).bind(logprobs=True)

# 모델 호출
response = llm_with_logprob.invoke("LangChain에 대해 설명해주세요.")

# 출력에서 logprobs 정보 확인
print(response.response_metadata['logprobs'])
```
