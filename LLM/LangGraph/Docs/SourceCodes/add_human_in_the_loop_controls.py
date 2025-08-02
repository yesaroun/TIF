from typing import Annotated

from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

from gemini_llm import llm


class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)


# @tool 데코레이터 사용해서 해당 함수를 LLM이 사용할 수 있는 도구로 만든다.
@tool
def human_assistance(query: str) -> str:
    # interrupt() 함수를 호출해 그래프 실행을 중지 한다.
    # interrupt() 함수 인자(딕셔너리)는 사람에게 전달한 정보
    human_response = interrupt({"query": query})
    # 나중에 사람이 Command 객체로 응답을 보내면, 그 응답이 human_response 에 담긴다.
    return human_response["data"]


tool = TavilySearch(max_results=2)
tools = [tool, human_assistance]
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State):
    pass