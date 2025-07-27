### **LangGraph: 도구 추가하기 튜토리얼**

챗봇이 "기억(학습 데이터)"만으로는 대답할 수 없는 질문을 처리하기 위해, 웹 검색 도구를 통합해 보겠습니다. 챗봇은 이 도구를 사용해 관련 정보를 찾고 더 나은 답변을 제공할 수 있게 됩니다.

> 참고
>
> 이 튜토리얼은 [기본 챗봇 만들기] 튜토리얼에 이어서 진행됩니다.

---

### **사전 준비 사항**

튜토리얼을 시작하기 전에 다음이 준비되어 있는지 확인하세요.

- [Tavily 검색 엔진](https://tavily.com/)의 API 키

---

### **1. 검색 엔진 설치하기**

**Tavily 검색 엔진**을 사용하기 위해 필요한 패키지를 설치합니다.

```bash
pip install -U langchain-tavily
```

---

### **2. 환경 설정하기**

검색 엔진 API 키로 환경을 설정합니다. 아래 코드는 API 키를 안전하게 입력받기 위한 코드입니다.

```python
import os
import getpass

def _set_env(var: str):
  # 환경변수가 설정되어 있지 않다면, 사용자에게 입력을 받습니다.
  if not os.environ.get(var):
    os.environ[var] = getpass.getpass(f"{var}: ")

# TAVILY_API_KEY를 설정합니다.
_set_env("TAVILY_API_KEY")
```

---

### **3. 도구 정의하기**

웹 검색 도구를 정의합니다.

>  **💡 쉽게 이해하기: 도구(Tool)란?**
>
> 챗봇에게 부여하는 **특별한 능력**입니다. 여기서는 `TavilySearch`라는 웹 검색 능력을 부여합니다. `max_results=2`는 검색 결과를 최대 2개까지 가져오라는 의미입니다.

```python
# langchain_tavily에서 TavilySearch를 가져옵니다.
from langchain_tavily import TavilySearch

# 검색 도구를 생성합니다. 검색 결과는 최대 2개로 제한합니다.
tool = TavilySearch(max_results=2)
# 나중에 사용하기 편하게 리스트 형태로 도구들을 관리합니다.
tools = [tool]

# 도구가 잘 작동하는지 테스트해봅니다.
result = tool.invoke("LangGraph에서 '노드'는 무엇인가요?")
print(result)
```

결과:
위 코드를 실행하면, 챗봇이 질문에 답하는 데 사용할 수 있는 페이지 요약 정보가 결과로 나옵니다.

```json
{'query': "What's a 'node' in LangGraph?",
 'results': [{'title': "Introduction to LangGraph: A Beginner's Guide - Medium",
   'url': 'https://medium.com/@cplog/introduction-to-langgraph-a-beginners-guide-14f9be027141',
   'content': '...LangGraph는 상태를 가진 그래프(stateful graph)라는 개념을 중심으로... 그래프의 각 노드(node)는 계산의 한 단계를 나타내며...'},
  {'title': 'LangGraph Tutorial: What Is LangGraph and How to Use It?',
   'url': 'https://www.datacamp.com/tutorial/langgraph-tutorial',
   'content': 'LangGraph는 LangChain 생태계 내의 라이브러리로, 여러 LLM 에이전트(또는 체인)를 구조화되고 효율적인 방식으로 정의, 조정 및 실행하기 위한 프레임워크를 제공합니다... '}]}
```

---

### **4. 그래프 정의하기**

**첫 번째 튜토리얼**에서 만들었던 `StateGraph`에 `bind_tools`를 LLM에 추가합니다. 이렇게 하면 LLM이 검색 엔진을 사용하고 싶을 때 어떤 JSON 형식을 사용해야 하는지 알게 됩니다.

먼저 사용할 LLM을 선택합니다. (OpenAI 예시)

```bash
pip install -U "langchain[openai]"
```

```python
import os
from langchain_openai import ChatOpenAI

# OpenAI API 키를 설정합니다.
os.environ["OPENAI_API_KEY"] = "sk-..."

llm = ChatOpenAI(model="gpt-4o")
```

이제 `StateGraph`에 도구를 통합합니다.

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 그래프의 상태를 정의합니다.
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 상태 그래프의 설계도를 생성합니다.
graph_builder = StateGraph(State)

# === 중요: 이전 코드에서 수정된 부분 ===
# LLM에게 어떤 도구들을 사용할 수 있는지 알려줍니다.
# highlight-next-line
llm_with_tools = llm.bind_tools(tools)

# 챗봇 노드는 이제 도구를 사용할 수 있는 LLM을 호출합니다.
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 'chatbot'이라는 이름으로 노드를 추가합니다.
graph_builder.add_node("chatbot", chatbot)
```

>  **💡 쉽게 이해하기: `llm.bind_tools(tools)`**
>
> 이 코드는 LLM에게 **"너는 이제부터 `tools` 리스트에 있는 도구들을 사용할 수 있어!"** 라고 알려주는 과정입니다. 마치 사람에게 연장 상자를 주면서 각 연장의 사용법을 알려주는 것과 같습니다. 이제 LLM은 대화 중에 웹 검색이 필요하다고 판단하면, 약속된 형식에 맞춰 "검색 도구를 사용해줘!"라고 요청할 수 있게 됩니다.

---

### **5. 도구를 실행할 함수 만들기**

이제, LLM이 도구를 사용하겠다고 요청했을 때 실제로 도구를 실행할 함수를 만듭니다. `BasicToolNode`라는 새로운 노드를 추가하여 이 작업을 수행합니다. 이 노드는 상태의 가장 최근 메시지를 확인하고, 만약 메시지에 `tool_calls`(도구 호출 요청)가 포함되어 있다면 해당 도구를 실행합니다.

```python
import json
from langchain_core.messages import ToolMessage

# 도구 실행을 담당하는 노드를 클래스로 정의합니다.
class BasicToolNode:
    """마지막 AI 메시지에서 요청된 도구를 실행하는 노드입니다."""

    def __init__(self, tools: list) -> None:
        # 도구들을 이름으로 쉽게 찾아 쓸 수 있도록 딕셔너리 형태로 저장합니다.
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        # 입력값에서 메시지 리스트를 가져옵니다. 없으면 오류를 발생시킵니다.
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("입력에서 메시지를 찾을 수 없습니다.")

        outputs = []
        # 마지막 메시지에 포함된 모든 도구 호출 요청을 순회합니다.
        for tool_call in message.tool_calls:
            # 요청된 이름의 도구를 찾아 실행하고 결과를 받습니다.
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            # 도구 실행 결과를 ToolMessage 형태로 만들어 리스트에 추가합니다.
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        # 도구 실행 결과 메시지들을 반환합니다.
        return {"messages": outputs}

# 위에서 정의한 클래스로 'tools' 노드를 생성합니다.
tool_node = BasicToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)
```

> 참고
>
> 나중에 직접 이 코드를 작성하고 싶지 않다면, LangGraph에 내장된 ToolNode를 사용할 수 있습니다.

> [질문](obsidian://open?vault=Programing&file=LangGraph%2FDocs%2F2.%20%EC%A7%88%EB%AC%B8-1)
---

### **6. 조건부 엣지(Conditional Edges) 정의하기**

도구 노드를 추가했으니, 이제 **조건부 엣지**를 정의할 차례입니다.

**엣지**는 제어 흐름을 한 노드에서 다음 노드로 안내합니다. **조건부 엣지**는 하나의 노드에서 시작하여, 현재 그래프 상태에 따라 다른 노드로 경로를 지정하는 "if" 문을 포함합니다.

`route_tools`라는 라우터 함수를 정의하여 챗봇의 출력에 `tool_calls`가 있는지 확인합니다. 이 함수를 `add_conditional_edges`를 호출하여 그래프에 제공하면, 그래프는 `chatbot` 노드가 완료될 때마다 이 함수를 확인하여 다음에 어디로 가야 할지 결정합니다.

이 조건은 **도구 호출이 있으면 `tools` 노드로**, **없으면 `END`로** 경로를 지정합니다.

```python
def route_tools(state: State) -> str:
    """
    조건부 엣지에서 사용될 함수.
    마지막 메시지에 도구 호출이 있으면 'tools' 노드로, 없으면 'END'(종료)로 라우팅합니다.
    """
    # 상태에서 마지막 메시지를 가져옵니다.
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"도구 엣지의 입력 상태에서 메시지를 찾을 수 없습니다: {state}")

    # 마지막 메시지에 tool_calls 속성이 있고, 그 안에 내용이 있으면 'tools'를 반환합니다.
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    # 그렇지 않으면 END(종료)를 반환합니다.
    return END

# 'chatbot' 노드에서 끝난 후, 어디로 갈지 결정하는 조건부 엣지를 추가합니다.
graph_builder.add_conditional_edges(
    "chatbot",  # 시작 노드: 'chatbot'
    route_tools,  # 경로 결정 함수
    # 경로 함수의 출력값("tools" 또는 END)을 실제 노드 이름에 매핑합니다.
    # "tools"가 나오면 "tools" 노드로, END가 나오면 그래프를 종료합니다.
    {"tools": "tools", END: END},
)

# 'tools' 노드가 실행된 후에는 항상 'chatbot' 노드로 돌아가 다음 단계를 결정하게 합니다.
graph_builder.add_edge("tools", "chatbot")
# 그래프의 시작점은 'chatbot' 노드입니다.
graph_builder.add_edge(START, "chatbot")

# 그래프 설계도를 실행 가능한 객체로 컴파일합니다.
graph = graph_builder.compile()
```

> 참고
>
> 이 코드는 LangGraph에 내장된 tools_condition으로 대체하여 더 간결하게 만들 수 있습니다.

---

### **7. 그래프 시각화하기 (선택 사항)**

그래프의 구조를 시각화하여 확인할 수 있습니다.

```python
from IPython.display import Image, display

try:
    display(Image(graph.get_graph().draw_mermaid_png()))
except Exception:
    # 이 기능은 추가 패키지 설치가 필요하며, 선택 사항입니다.
    pass
```

**(결과 이미지)**

```code
graph TD
    __start__ --> chatbot;
    chatbot --"route_tools"--> tools;
    chatbot --"route_tools"--> __end__;
    tools --> chatbot;
```

- 이제 `chatbot` 노드에서 `tools` 노드로 갔다가 다시 `chatbot`으로 돌아오는 **루프(loop)** 가 생긴 것을 볼 수 있습니다. 이것이 바로 **에이전트 루프**입니다.

---

### **8. 봇에게 질문하기**

이제 챗봇의 훈련 데이터에 없는 질문을 할 수 있습니다.

```python
# 사용자 입력을 받아 그래프를 실행하고 결과를 스트리밍으로 출력하는 루프
while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        # 사용자의 메시지를 담아 그래프를 실행합니다.
        for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
            # 이벤트 값들을 순회하며 출력합니다.
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)
    except:
        # 입력 함수가 작동하지 않을 경우를 위한 대체 코드
        user_input = "LangGraph에 대해 아는 거 있어?"
        print("User: " + user_input)
        for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)
        break
```

**실행 결과 예시:**

```
User: LangGraph에 대해 아는 거 있어?
Assistant: [{'text': "LangGraph에 대한 정확하고 최신 정보를 제공하기 위해, 최신 내용을 검색해야 합니다. 잠시만요.", 'type': 'text'}, {'id': 'toolu_01...', 'input': {'query': 'LangGraph AI tool information'}, 'name': 'tavily_search_results_json', 'type': 'tool_use'}]
Assistant: [{"url": "https://www.langchain.com/langgraph", "content": "LangGraph는..."}, {"url": "https://github.com/langchain-ai/langgraph", "content": "개요. LangGraph는..."}]
Assistant: 검색 결과를 바탕으로 LangGraph에 대한 정보를 알려드릴게요:

1. 목적:
   LangGraph는 대규모 언어 모델(LLM)을 사용하여 상태를 가진(stateful) 다중 행위자(multi-actor) 애플리케이션을 구축하기 위해 설계된 라이브러리입니다. 특히 에이전트 및 다중 에이전트 워크플로우를 만드는 데 유용합니다.
... (이하 생략)
Goodbye!
```

---

### **9. 내장 기능 사용하기**

사용의 편의를 위해, 직접 만들었던 코드를 LangGraph 내장 컴포넌트로 교체해 봅시다. 내장 컴포넌트에는 병렬 API 실행과 같은 기능이 포함되어 있습니다.

- `BasicToolNode`는 내장된 **`ToolNode`** 로 교체
- `route_tools`는 내장된 **`tools_condition`** 으로 교체

(LLM 선택 및 설정 코드는 위와 동일합니다.)

```python
from typing import Annotated
from langchain_tavily import TavilySearch
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
# 내장된 ToolNode와 tools_condition을 가져옵니다.
from langgraph.prebuilt import ToolNode, tools_condition

# --- 아래 코드는 훨씬 더 간결해집니다 ---

# 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 그래프 빌더 생성
graph_builder = StateGraph(State)

# 도구 설정
tool = TavilySearch(max_results=2)
tools = [tool]
# LLM에 도구 바인딩
llm_with_tools = llm.bind_tools(tools)

# 챗봇 노드 정의
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 챗봇 노드 추가
graph_builder.add_node("chatbot", chatbot)

# 내장된 ToolNode를 사용하여 도구 노드 추가
tool_node = ToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)

# 내장된 tools_condition을 사용하여 조건부 엣지 추가
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

# 도구 노드에서 챗봇 노드로 엣지 추가
graph_builder.add_edge("tools", "chatbot")
# 시작점에서 챗봇 노드로 엣지 추가
graph_builder.add_edge(START, "chatbot")

# 그래프 컴파일
graph = graph_builder.compile()
```

**축하합니다!** 필요할 때 검색 엔진을 사용하여 최신 정보를 검색할 수 있는 대화형 에이전트를 LangGraph로 만들었습니다. 이제 더 넓은 범위의 사용자 질문을 처리할 수 있습니다.

---

### **다음 단계**

챗봇은 아직 과거의 상호작용을 스스로 기억할 수 없어, 여러 턴에 걸친 일관성 있는 대화를 나누는 데 한계가 있습니다. 다음 파트에서는 이 문제를 해결하기 위해 **메모리(기억력)를 추가**할 것입니다.