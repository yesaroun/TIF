from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,  # 한국어/영문 혼용 문서면 600~1200 사이부터 탐색
    chunk_overlap=120,  # 문맥 끊김 완화
    separators=["\n\n", "\n", " ", ""],  # 문단/줄/공백 우선 분할
)

chunks = splitter.split_documents(docs)
