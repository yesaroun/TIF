from langchain_community.document_loaders import WikipediaLoader
from langchain_text_splitters import CharacterTextSplitter

loader = WikipediaLoader(query="지진", lang="ko", load_max_docs=1)
docs = loader.load()

text_splitter = CharacterTextSplitter(
    separator="\\n\\n",  # 단락 기준
    chunk_size=100,  # 100문자(보통은 700~1200 토큰 권장)
    chunk_overlap=20,  # 청크 겹치는 부분
    length_function=len,  # 기본
    is_separator_regex=False,
)

# 청크 생성
splits = text_splitter.split_documents(docs)

for i, d in enumerate(splits[:5], start=1):
    content = d.page_content
    print(f"[{i}] len={len(content)} preview={content[:100]!r}")
