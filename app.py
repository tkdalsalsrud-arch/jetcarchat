import streamlit as st
import google.generativeai as genai
import os
import pandas as pd # 'pandas' (CSV/Excel 리더기)
from pathlib import Path

# --- 1. API 키 설정 (오직 Gemini 키 하나만!) ---
try:
    # Secrets에서 API 키 불러오기
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    # 로컬 secrets.toml 파일이 없거나 키가 잘못되었을 때
    st.error("🚨 [Gemini API 키]를 설정하는 데 실패했습니다. Secrets를 확인하세요.")
    st.stop() # 오류 발생 시 앱 실행 중지

# --- 2. 앱 제목 및 모델 설정 ---
st.title("🚗 jetcar 챗봇 (v5: Excel RAG)")
st.caption("Powered by Streamlit & Google Gemini")

# 🚨 (새 기능 v5) 'Excel 참고 자료' 불러오기
try:
    # app.py와 같은 위치에 있는 'cars_data.xlsx' 파일을 읽습니다.
    context_file = Path("cars_data.xlsx") # 🚨 .csv에서 .xlsx로 변경
    if not context_file.exists():
        st.error("🚨 'cars_data.xlsx' 파일을 찾을 수 없습니다. app.py와 같은 위치에 만들어주세요.")
        st.stop()
    
    # 🚨 (수정된 부분!) pd.read_excel을 사용합니다.
    # 엑셀 파일을 읽기 위해 'engine="openpyxl"'이 필요합니다.
    df = pd.read_excel(context_file, engine="openpyxl")
    
    # '참고 자료'를 LLM이 이해하기 쉬운 텍스트로 변환
    context = "--- [jetcar 참고 자료] ---\n\n"
    
    # CSV 버전(v4)과 동일: 모든 열 제목을 가져옵니다.
    column_headers = df.columns.tolist() 

    for index, row in df.iterrows():
        # 첫 번째 열의 값을 '제목'처럼 사용 (예: 차량명)
        context += f"[{row[column_headers[0]]}]\n" 
        
        # 나머지 모든 열의 정보를 '키: 값' 쌍으로 동적 추가
        for col_name in column_headers[1:]: # 첫 번째 열 제외
            context += f"- {col_name}: {row[col_name]}\n"
        
        context += "\n" # 각 항목 사이에 줄바꿈 추가
            
    context += "--- [참고 자료 끝] ---"

    st.info("✅ 'cars_data.xlsx' (차량 정보) 로딩 완료!")

except Exception as e:
    st.error(f"🚨 'cars_data.xlsx' 파일 로딩 중 오류 발생: {e}")
    st.stop()


# 세션 상태(session_state)에 모델과 채팅 기록 초기화
if "model" not in st.session_state:
    # 1.0 세대의 표준 모델
    st.session_state.model = genai.GenerativeModel('gemini-2.5-pro')

if "chat" not in st.session_state:
    # 모델의 채팅 세션 시작 (대화 기록 유지를 위함)
    st.session_state.chat = st.session_state.model.start_chat(history=[])

if "messages" not in st.session_state:
    # UI에 표시할 채팅 기록
    st.session_state.messages = []

# --- 3. 이전 대화 내용 표시 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 4. 사용자 입력 및 AI 응답 처리 (v4와 동일) ---
if prompt := st.chat_input("무엇이든 물어보세요"):
    
    # 1. 사용자 메시지 저장 및 UI에 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. AI에게 응답 요청 (🚨 '참고 자료'와 함께 질문하도록 수정됨)
    with st.spinner("jetcar가 생각 중... 🚙💨"):
        try:
            # 🚨 '참고 자료'와 '질문'을 합쳐서 '오픈북 시험' 문제로 만듭니다.
            final_prompt = f"""
            {context}
            
            [사용자 질문]
            {prompt}
            
            [지시]
            위 [jetcar 참고 자료]에 기반해서 [사용자 질문]에 대답해 줘. 
            만약 [참고 자료]에 답이 없다면, "제가 아는 정보 중에는 없습니다."라고 대답해.
            """

            # chat.send_message를 사용해야 대화 맥락이 유지됩니다.
            response = st.session_state.chat.send_message(final_prompt)
            
            # 3. AI 응답 저장 및 UI에 표시
            ai_response = response.text
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.markdown(ai_response)
                
        except Exception as e:
            st.error(f"AI 응답 중 오류가 발생했습니다: {e}")