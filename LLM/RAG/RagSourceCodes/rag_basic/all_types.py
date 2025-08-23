import glob, os
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
)

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "docs", "sample1.txt")
dir_path = os.path.join(script_dir, "docs")

txt_loader_all = DirectoryLoader(
    path=dir_path,
    glob="**/*.txt",
    recursive=True,
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
)
docs_all_txt = txt_loader_all.load()

# PyPDFLoader는 DirectoryLoader와 함께 쓰기보다는 개별 파일 또는 직접 반복 처리 권장
docs_all_pdf = []
for pdf_path in glob.glob(os.path.join("./docs", "**", "*.pdf"), recursive=True):
    loader = PyPDFLoader(pdf_path)
    docs_all_pdf.extend(loader.load())

docs_all = docs_all_txt + docs_all_pdf
print(docs_all_txt, docs_all_pdf)
print(f"총 문서 수: {len(docs_all)}")
