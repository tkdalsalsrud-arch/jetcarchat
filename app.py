import streamlit as st
import google.generativeai as genai
import os

# --- 1. API 키 설정 (가장 중요한 부분) ---
# Streamlit의 'Secrets' 기능을 사용합니다.
# 
# [로컬에서 테스트할 때]
# 1. app.py 파일과 같은 위치에 .streamlit 폴더를 만듭니다.
# 2. 그 안에 secrets.toml 파일을 만듭니다.
# 3. secrets.toml 파일 안에 GOOGLE_API_KEY = "AIza..." (내 API 키)
#    이렇게 한 줄을 추가하고 저장합니다.
#
# [나중에 배포할 때]
# Streamlit Community Cloud의 설정창에서 Secrets에 
# GOOGLE_API_KEY = "..." 값을 등록하면 됩니다.

try:
    # Secrets에서 API 키 불러오기
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    # 로컬 secrets.toml 파일이 없거나 키가 잘못되었을 때
    st.error("🚨 API 키를 설정하는 데 실패했습니다. secrets.toml 파일을 확인하세요.")
    st.stop() # 오류 발생 시 앱 실행 중지

# --- 2. 앱 제목 및 모델 설정 ---
st.title("🚗 jetcar 챗봇")
st.caption("Powered by Streamlit & Google Gemini")

# 세션 상태(session_state)에 모델과 채팅 기록 초기화
if "model" not in st.session_state:
    # 사용할 모델 선택 (flash가 빠르고 저렴합니다)
    st.session_state.model = genai.GenerativeModel('gemini-2.5-flash')

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

# --- 4. 사용자 입력 및 AI 응답 처리 ---
if prompt := st.chat_input("무엇이든 물어보세요"):
    
    # 1. 사용자 메시지 저장 및 UI에 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. AI에게 응답 요청
    with st.spinner("jetcar가 생각 중... 🚙💨"):
        try:
            # chat.send_message를 사용해야 대화 맥락이 유지됩니다.
            response = st.session_state.chat.send_message(prompt)
            
            # 3. AI 응답 저장 및 UI에 표시
            ai_response = response.text
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.markdown(ai_response)
                
        except Exception as e:
            st.error(f"AI 응답 중 오류가 발생했습니다: {e}")