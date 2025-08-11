import time
from dotenv import load_dotenv
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse.langchain import CallbackHandler
from langfuse import Langfuse

load_dotenv()


langfuse = Langfuse(host="https://us.cloud.langfuse.com")

# 캐시 설정
set_llm_cache(SQLiteCache(database_path=".test_langfuse.db"))

# LLM 및 핸들러 설정
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
handler = CallbackHandler()

query = "LLM 애플리케이션에서 캐싱의 중요성은? 자세히 설명해줘."

# --- 첫 번째 호출 ---
print("첫 번째 호출 (Langfuse 추적 시작)")
# config 딕셔너리에 callbacks를 전달합니다.
response1 = llm.invoke(query, config={"callbacks": [handler]})
print(f"응답: {response1.content}")
print("첫 번째 호출 완료. Langfuse 대시보드를 확인하세요.\n")

# 약간의 시간 간격을 둡니다.
time.sleep(2)

# --- 두 번째 호출 ---
print("두 번째 호출 (캐시 적용 확인)")
# 동일한 핸들러를 다시 전달하여 같은 세션으로 묶습니다.
response2 = llm.invoke(query, config={"callbacks": [handler]})
print(f"응답: {response2.content}")
print("두 번째 호출 완료. Langfuse 대시보드를 확인하세요.")
