from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

model_name = "BAAI/bge-m3"
hf_embeddings = HuggingFaceEmbeddings(model_name=model_name)

db = Chroma(persist_directory="./news_chroma_db", embedding_function=hf_embeddings)

result = db.similarity_search("신종 바이러스")
result = db.similarity_search_with_score("중국 미국 갈등")
result = db.similarity_search_with_relevance_scores("새로운 형태 공연 예술")
