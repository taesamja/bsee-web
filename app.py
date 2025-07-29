import streamlit as st
import fitz  # PyMuPDF
import sqlite3
import google.generativeai as genai

# API 키 설정
genai.configure(api_key="AIzaSyD_2LlbeBlfwWH-TLAT0_jecWWN0yiyidQ")
model = genai.GenerativeModel("gemini-2.5-flash")

# DB 초기화
conn = sqlite3.connect("pdf_qa.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS pdf_texts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS quiz (id INTEGER PRIMARY KEY, question TEXT, options TEXT, answer TEXT)")
conn.commit()

# PDF 텍스트 추출
def extract_pdf_text(uploaded_file):
    text = ""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        text += page.get_text()
    return text

# 시험문제 출제
def generate_quiz(pdf_text):
    prompt = f"""
    다음 내용을 기반으로 객관식 시험문제 5개를 출제해 주세요. 각 문항은 다음 형식으로 작성해 주세요:

    질문:
    1) 보기1
    2) 보기2
    3) 보기3
    4) 보기4
    정답: 번호

    내용:
    {pdf_text}
    """
    response = model.generate_content(prompt)
    return response.text

# UI 시작
st.title("📚 PDF 질의응답 & 시험문제 생성기")

menu = st.sidebar.selectbox("메뉴 선택", ["📄 PDF 업로드", "❓ 질의응답", "📝 시험문제 출제", "📑 문제 보기"])

if menu == "📄 PDF 업로드":
    uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf")
    if uploaded_file:
        pdf_text = extract_pdf_text(uploaded_file)
        title = st.text_input("문서 제목 입력")
        if st.button("DB에 저장"):
            c.execute("INSERT INTO pdf_texts (title, content) VALUES (?, ?)", (title, pdf_text))
            conn.commit()
            st.success("PDF 내용이 저장되었습니다.")

elif menu == "❓ 질의응답":
    c.execute("SELECT id, title FROM pdf_texts")
    pdfs = c.fetchall()
    pdf_choice = st.selectbox("문서 선택", pdfs, format_func=lambda x: x[1])
    question = st.text_input("질문을 입력하세요:")
    if st.button("답변 생성"):
        c.execute("SELECT content FROM pdf_texts WHERE id = ?", (pdf_choice[0],))
        content = c.fetchone()[0]
        prompt = f"다음 내용을 기반으로 질문에 답해 주세요:\n\n{content}\n\n질문: {question}"
        response = model.generate_content(prompt)
        st.markdown("### 📘 답변:")
        st.write(response.text)

elif menu == "📝 시험문제 출제":
    c.execute("SELECT id, title FROM pdf_texts")
    pdfs = c.fetchall()
    pdf_choice = st.selectbox("출제할 문서 선택", pdfs, format_func=lambda x: x[1])
    if st.button("시험문제 생성"):
        c.execute("SELECT content FROM pdf_texts WHERE id = ?", (pdf_choice[0],))
        content = c.fetchone()[0]
        quiz_text = generate_quiz(content)
        st.text_area("출제된 문제", quiz_text, height=300)

        # 간단 파싱 및 저장
        for block in quiz_text.strip().split("질문:")[1:]:
            lines = block.strip().split("\n")
            question = lines[0]
            options = "\n".join(lines[1:5])
            answer_line = next((l for l in lines if "정답" in l), "정답: ?")
            answer = answer_line.split(":")[-1].strip()
            c.execute("INSERT INTO quiz (question, options, answer) VALUES (?, ?, ?)",
                      (question, options, answer))
        conn.commit()
        st.success("시험문제가 저장되었습니다.")

elif menu == "📑 문제 보기":
    c.execute("SELECT question, options, answer FROM quiz")
    rows = c.fetchall()
    for q, opts, ans in rows:
        st.markdown(f"**Q. {q}**")
        st.text(opts)
        st.markdown(f"✅ 정답: {ans}")
        st.markdown("---")
