from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter

text_splitter = CharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20,
)

loader = TextLoader("./docs/news.txt", encoding="utf-8")
documents = loader.load_and_split(text_splitter=text_splitter)

len(documents)
# 10

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

model_name = "BAAI/bge-m3"
hf_embeddings = HuggingFaceEmbeddings(model_name=model_name)

db = Chroma.from_documents(documents, hf_embeddings)
result = db.similarity_search("대선 후보 토론")

len(result)
# 4

result = db.similarity_search("해수면이 높아지고 있다.", k=2)

result = db.similarity_search_with_score("신종 바이러스")

result = db.similarity_search_with_relevance_scores('태양계 밖의 행성')

embedded_query = hf_embeddings.embed_query('AI 번역 기술')
embedded_query[:10]

result = db.similarity_search_by_vector(embedded_query)
