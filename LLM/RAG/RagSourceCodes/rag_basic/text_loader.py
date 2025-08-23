import os
from langchain_community.document_loaders import TextLoader

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "docs", "sample1.txt")

txt_loader = TextLoader(file_path=file_path, encoding="utf-8")
docs_txt = txt_loader.load()
print(type(docs_txt), len(docs_txt))
print(docs_txt[0].metadata.get("source"))  # 원본 파일 경로
print(docs_txt[0].page_content[:80])
