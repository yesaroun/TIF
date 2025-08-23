import os
from langchain_community.document_loaders import PyPDFLoader

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "docs", "sample.pdf")

pdf_loader = PyPDFLoader(file_path=file_path)
docs_pdf = pdf_loader.load()
print(f"PDF에서 읽은 페이지 수(=문서 청크): {len(docs_pdf)}")
print(docs_pdf[0].metadata)
print(docs_pdf[0].page_content[:80])
