from dotenv import load_dotenv
from langchain.globals import set_llm_cache
from langchain_community.cache import InMemoryCache
from langchain.chat_models import init_chat_model

load_dotenv()

set_llm_cache(InMemoryCache())

llm = init_chat_model("google_genai:gemini-2.0-flash")

# 첫 번째 호출
# 이 시점에는 캐시에 내용이 없으므로, 실제 gemini를 호출
print("첫 번째 호출 시작...")
response1 = llm.invoke("langchin 전역 캐시에 대해 한 문장으로 설명해줘.")
print(response1)
print("첫 번째 호출 완료")

# 두 번째 호출
# 이전에 동일한 입력으로 호출한 기록이 캐시에 남아 있다.
# 따라서 api를 다시 호출하지 않고 캐시에서 즉시 결과를 가져온다.
# 실행 시간이 거의 걸리지 않는다.
print("\n두 번째 호출 시작...")
response2 = llm.invoke("langchin 전역 캐시에 대해 한 문장으로 설명해줘.")
print(response2)
print("두 번째 호출 완료")
