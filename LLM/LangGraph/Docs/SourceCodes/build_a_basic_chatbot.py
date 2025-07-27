import os
from typing import Annotated
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
# from IPython.display import Image, display


load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

# response = llm.invoke("안녕!")
# print(response.content)


# State 클래스는 그래프의 '상태'가 어떤 구조를 가질지 정의
class State(TypedDict):
    # 'messages'라는 키는 리스트 형태의 메세지들을 담는다.
    messages: Annotated[list, add_messages]
    # add_messages 함수는 기존 메시지를 덮어쓰는 대신 새로운 메시지를 추가한다.


graph_builder = StateGraph(State)


def chatbot(state: State):
    # state 에 있는 메시지들을 llm에 넘겨주고, 응답을 받는다.
    return {"messages": [llm.invoke(state["messages"])]}


# graph_builder 에 'chatbot'이라는 이름으로 노드 추가
# 두 번째 인자는 이 노드가 호출될 때 실행될 함수
graph_builder.add_node("chatbot", chatbot)

graph_builder.add_edge(START, "chatbot")
# START는 시작을 의미하는 키워드
# -> 이 코드는 '그래프가 시작되면 무조건 'chatbot'노드부터 실행하라는 의미
graph_builder.add_edge("chatbot", END)
# 어디서 실행을 마쳐야 하는지를 나타내는 종료점
# chatbot 노드가 실행된 후에 그래프를 종료하라는 의미

graph = graph_builder.compile()
# graph를 실행하기 전에 컴파일 해야한다.

#try:
#    # 그래프의 구조를 이미지로 그려서 보여줄 수 있다.
#    display(Image(graph.get_graph().draw_mermaid_png()))
#except Exception:
#    pass

while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
    # 사용자의 입력을 포함하여 그래프를 스트리밍 방식으로 실행한다.
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            # LLM이 생성하는 답변의 마지막 부분을 실시간으로 출력
            print("Assistant:", value["messages"][-1].content)
