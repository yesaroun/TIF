from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage

from basic_graph import graph_builder

memory = InMemorySaver()

# graph_builder에 memory 배정해서 컴파일
# 이제 그래프는 대화 내용 기억할 수 있다.
graph = graph_builder.compile(checkpointer=memory)

# 앞으로 1번 대화방(thread_id)에서 기록할거라고 알려주는 열쇠(config)
config = {"configurable": {"thread_id": "1"}}

user_input = "Hi! my name is Bob"

# stream -> 실시간 소통
events = graph.stream(
    {"messages": [HumanMessage(content=user_input)]},
    config,
    stream_mode="values",
)

# 실시간으로 전달 받은 이벤트를 화면에 출력
for event in events:
    event["messages"][-1].pretty_print()

user_input = "Do you remember my name?"

events = graph.stream(
    {"messages": [HumanMessage(content=user_input)]},
    config,
    stream_mode="values",
)

for event in events:
    event["messages"][-1].pretty_print()

# 그래프의 상태 확인 가능
snapshot = graph.get_state(config)
print(snapshot)
