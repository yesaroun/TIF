from dotenv import load_dotenv
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chat_models import init_chat_model

load_dotenv()

# llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")
llm = init_chat_model("google_genai:gemini-2.0-flash")
