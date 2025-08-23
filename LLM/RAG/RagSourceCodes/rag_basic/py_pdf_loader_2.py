import os

# 1) 임포트 (버전 호환)
try:
    from langchain_community.document_loaders import PyPDFLoader
except ImportError:
    from langchain.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "docs", "sample.pdf")

# 2) 로더 초기화
pdf_path = file_path
loader = PyPDFLoader(pdf_path)
# 일부 버전은 password 인자를 지원
# loader = PyPDFLoader(pdf_path, password="secret")

# 3) 페이지 단위 Document 로드
docs = loader.load()
print(f"문서 개수(페이지 수): {len(docs)}")
print(docs[0].page_content[:300])
print(docs[0].metadata)  # 예: {'source': 'docs/sample.pdf', 'page': 0, ...}


splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,  # 한국어/영문 혼용 문서면 600~1200 사이부터 탐색
    chunk_overlap=120,  # 문맥 끊김 완화
    separators=["\n\n", "\n", " ", ""],  # 문단/줄/공백 우선 분할
)

chunks = splitter.split_documents(docs)
print(len(chunks), chunks[0].metadata)
