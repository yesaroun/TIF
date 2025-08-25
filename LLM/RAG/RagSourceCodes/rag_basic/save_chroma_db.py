from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

text_splitter = CharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20,
)

loader = TextLoader("./docs/news.txt", encoding="utf-8")
documents = loader.load_and_split(text_splitter=text_splitter)

model_name = "BAAI/bge-m3"
hf_embeddings = HuggingFaceEmbeddings(model_name=model_name)

db = Chroma.from_documents(
    documents, hf_embeddings, persist_directory="./news_chroma_db"
)

result = db.similarity_search("신종 바이러스", k=1)
