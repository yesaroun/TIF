# 인공지는 PDF Q&A 챗봇 프로젝트

import gradio as gr
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini")

# 텍스트 분리
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

# 임베딩 모델
hf_embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-me")

# 46-6:52 이어서 하기

def load_pdf(file):
    pass


def answer_question(question):
    pass


with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 인공지는 PDF Q&A 챗봇
    **PDF 파일을 업로드하고 질문을 입력하면 AI 가 답변을 입력합니다.**
    """)
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="PDF 파일 업로드")
            upload_button = gr.Button("업로드 및 처리")

        with gr.Column(scale=2):
            status_output = gr.Textbox(label="상태 메시지")
            question_input = gr.Textbox(label="질문 입력", placeholder="궁금한 내용을 적어주세요.")
            submit_button = gr.Button("답변 받기")
            answer_output = gr.Textbox(label="AI 답변")

    upload_button.click(load_pdf, inputs=file_input, outputs=status_output)
    submit_button.click(answer_question, inputs=question_input, outputs=answer_output)

demo.launch()
