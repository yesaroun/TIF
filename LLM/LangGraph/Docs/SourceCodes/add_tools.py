import json
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

tool = TavilySearch(max_results=2)  # 검색 결과는 최대 2개로 제한
# 나중에 사용하기 편하게 리스트 형태로 도구들을 관리
tools = [tool]


# result = tool.invoke("LangGraph에서 '노드'는 무엇인가요?")
# print("검색 결과:")
# print(result)


class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

# LLM에게 어떤 도구를 사용할 수 있는지 알려준다.
llm_with_toos = llm.bind_toos(tools)


# 챗봇 노드는 이제 도구를 사용할 수 있는 LLM을 호출
def chatbot(state: State):
    return {"messages": [llm_with_toos.invoke(state["messages"])]}


graph_builder.add_node("chatbot", chatbot)


# 도구 실행을 담당하는 노드를 클래스로 정의
class BasicToolNode:
    """마지막 AI 메시지에서 요청된 도구를 실행하는 노드입니다."""

    def __init__(self, tools: list) -> None:
        # 도구들을 이름으로 쉽게 찾아 쓸 수 있도록 딕셔너리 형태로 저장
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("입력에서 메세지를 찾을 수 없습니다.")

        outputs = []
        # 마지막 메시지에 포함된 모든 도구 호출 요청을 순회
        for tool_call in message.tool_calls:
            # 요청된 이름의 도구를 찾아 실행하고 결과를 받는다.
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            # 도구 실행 결과를 ToolMessage 형태로 만들어 리스트에 추가
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        # 도구 실행 결과 메시지들을 반환
        return {"messages": outputs}


# 위에서 정의한 클래스로 'tools' 노드를 생성
tool_node = BasicToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)


def route_tools(state: State) -> str:
    """
    조건부 엣지에서 사용될 함수
    마지막 메시지에 도구 호출이 있으면 'tools' 노드로, 없으면 'END'로 라우팅합니다.
    """
    # 상태에서 마지막 메시지를 가져옵니다.
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"도구 엣지의 입력 상태에서 메시지를 찾을 수 없습니다: {state}")

    # 마지막 메시지에 tool_calls 속성이 있고, 그 안에 내용이 있으면 'tools'를 반환
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    # 그렇지 않으면 END(종료)를 반환
    return END


# 'chatbot' 노드에서 끝난 후, 어디로 갈지 결정하는 조건부 엣지를 추가
graph_builder.add_conditional_edges(
    "chatbot",  # 시작 노드
    route_tools,  # 경로 결정 함수
    # 경로 함수의 출력값("tools" 또는 END)을 실제 노드 이름에 매핑합니다.
    # "tools"가 나오면 "tools" 노드로, END가 나오면 그래프를 종료합니다.
    {"tools": "tools", END: END},
)

# 'tools' 노드가 실행된 후에는 항상 'chatbot' 노드로 돌아가 다음 단계를 결정하게 합니다.
graph_builder.add_edge("tools", "chatbot")
# 그래프의 시작점은 'chatbot' 노드입니다.
graph_builder.add_edge(START, "chatbot")

# 그래프 설계도롤 실행 가능한 객체로 컴파일합니다.
graph = graph_builder.compile()

while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        # 사용자 메시지를 담아 그래프 실행
        for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
            # 이벤트 값들을 순회하며 출력
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)
    except:
        print("An error occurred while running the graph.")
        break
