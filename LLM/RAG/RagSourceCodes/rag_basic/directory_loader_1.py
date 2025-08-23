import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "docs", "sample1.txt")
dir_path = os.path.join(script_dir, "docs")

txt_dir_loader = DirectoryLoader(
    path=dir_path,
    glob="*.txt",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
)
docs_many_txt = txt_dir_loader.load()
print(f"TXT 문서 수: {len(docs_many_txt)}")

txt_dir_loader_recursive = DirectoryLoader(
    path=dir_path,
    glob="**/*.txt",  # 모든 하위 폴더의 .txt
    recursive=True,
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
)
docs_many_txt_recursive = txt_dir_loader_recursive.load()
print(f"재귀 TXT 문서 수: {len(docs_many_txt_recursive)}")
