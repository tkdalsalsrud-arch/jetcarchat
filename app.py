import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
from pathlib import Path

# --- 0. 페이지 설정 및 스타일 ---
st.set_page_config(page_title="JETCAR 챗봇", page_icon="🚗")

st.markdown("""
<style>
    /* 챗 메시지 컨테이너 */
    div[data-testid="chat-message-container"] {
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 10px;
    }
    
    /* 사용자(user) 메시지 */
    div[data-testid="chat-message-container"]:has(div[data-testid="stChatMessageContent-user"]) {
        background-color: #F0F2F6;
        color: #333;
    }

    /* 어시스턴트(assistant) 메시지 */
    div[data-testid="chat-message-container"]:has(div[data-testid="stChatMessageContent-assistant"]) {
        background-color: #4A90E2;
        color: white;
    }
    
    /* 채팅 입력창 주변 여백 줄이기 */
    .stChatInputContainer {
        padding-top: 15px !important;
    }
    
    /* 입력 필드 스타일 (Expander 내부) */
    div[data-testid="stExpander"] {
        background-color: #f9f9f9;
        border: 1px solid #ddd;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. API 키 설정 ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error("🚨 [Gemini API 키] 설정을 확인하세요.")
    st.stop()

# --- 2. 앱 제목 ---
st.title("🚗 jetcar 맞춤형 챗봇")
st.caption("고객님의 상황에 딱 맞는 장기렌트카를 추천해 드립니다.")

# --- 3. [NEW] 고객 정보 입력 패널 (조건 설정) ---
# 채팅창 위에 조건을 설정하는 구역을 만듭니다.
with st.expander("📝 고객 맞춤 조건 설정 (여기를 눌러 정보를 입력하세요)", expanded=True):
    st.info("아래 정보를 입력하시면 더 정확한 차량을 추천받을 수 있습니다!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        user_age = st.number_input("나이 (만)", min_value=20, max_value=80, value=26, step=1, help="만 나이를 입력해주세요.")
        user_married = st.radio("결혼 유무", ["미혼", "기혼"], horizontal=True)
        
    with col2:
        user_income = st.selectbox("월 급여 구간", ["200만원 미만", "200~300만원", "300~400만원", "400~500만원", "500만원 이상"])
        user_purpose = st.multiselect("차량 사용 용도 (복수 선택 가능)", ["출퇴근", "패밀리카", "업무용/영업용", "레저/여행/캠핑", "마트/장보기"], default=["출퇴근"])

    # 입력받은 정보를 하나의 문자열로 정리 (AI에게 전달용)
    user_profile_text = f"""
    [현재 고객 프로필]
    - 나이: 만 {user_age}세
    - 결혼 유무: {user_married}
    - 월 급여: {user_income}
    - 사용 용도: {', '.join(user_purpose)}
    """

# --- 4. 엑셀 데이터 로딩 ---
try:
    context_file = Path("cars_data.xlsx")
    if not context_file.exists():
        st.error("🚨 'cars_data.xlsx' 파일이 없습니다.")
        st.stop()
    
    df = pd.read_excel(context_file, engine="openpyxl")
    
    context = "--- [제트카 보유 차량 데이터] ---\n\n"
    column_headers = df.columns.tolist() 

    for index, row in df.iterrows():
        context += f"[{row[column_headers[0]]}]\n" 
        for col_name in column_headers[1:]:
            context += f"- {col_name}: {row[col_name]}\n"
        context += "\n"
            
    context += "--- [차량 데이터 끝] ---"

except Exception as e:
    st.error(f"🚨 데이터 로딩 오류: {e}")
    st.stop()

# --- 5. 세션 상태 초기화 ---
if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel('gemini-2.5-flash')

if "chat" not in st.session_state:
    st.session_state.chat = st.session_state.model.start_chat(history=[])

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 6. 이전 대화 표시 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 7. 채팅 입력 및 처리 ---
# 여기가 사용자가 자유롭게 적는 공간입니다.
if prompt := st.chat_input("예: 제 조건에 맞는 가성비 좋은 차 추천해주세요!"):
    
    # 사용자 메시지 UI 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI 응답 처리
    with st.spinner("조건을 분석하여 차량을 찾는 중... 🚙💨"):
        try:
            # 🚨 프롬프트에 [고객 프로필]을 포함시킴
            final_prompt = f"""
            {context}
            
            {user_profile_text}
            
            [사용자 질문]
            {prompt}
            
            [지시사항]
                        1. [사용자 질문]에 대한 답변을 **먼저** [jetcar 참고 자료]에서 찾아보세요.
            2. 만약 [참고 자료]에 질문과 **관련된 정보(예: 특정 차량 정보)가 있다면**, 그 자료를 기반으로 정확하게 대답해 주세요.
            3. 만약 [참고 자료]에 **답이 없거나 관련성이 낮다면** (예: "장기렌트카의 장점은 무엇인가요?" 또는 "제트카 회사는 어디에 있나요?" 같은 일반 상식 및 자료 외 질문), "제가 아는 정보 중에는 없습니다."라고 말하지 **말고**, **당신의 일반 지식을 활용하여 친절하게 답변해 주세요.**
            4. 만약 사용자 질문이 차량번호(또는 차량명)만 입력하는 경우, [참고 자료]에서 그 차량을 찾아 아래 서식에 맞춰 요약해 주세요. 이 때 '이런 분들께 추천 !' 부분은 당신이 자료를 참고하여 창의적으로 직접 작성해야 합니다.
                (기존 서식은 여기에 그대로 둡니다...)
                제조사 연식 차량명 신용 무관 전국 출고 

신용 무관 / 만 26세 이상 ~ 60세이하 / 운전경력 1년이상 / 전국탁송 

📌 차량정보
차량명: 
주행거리 : 
연식: 
연료 : 

✨ 적용옵션 

기본형

💸 렌트비용
보증금 80만원
정비 포함 여부 : 정비 미포함
탁송료 : 별도 

📆 12개월 만원

📆 24개월 만원

📆 36개월 만원

📆 48개월 만원

📆 60개월 만원


👍 이런 분들께 추천 ! 

✔️ 신용등급 상관없이 차량이 필요한 분

✔️ 짐 싣는 공간이 충분한 차량을 찾고 계시는 분

✔️  신용 걱정없이 빠르게 탁송 받아볼 수 있는 차량을 원하시는 분

📞 상담문의
카톡상담 : 카카오톡에 'JETCAR' 를 검색해주세요
홈페이지 방문 : 네이버 검색창에 '제트카'를 검색해주세요
            
            5. 모든 답변은 질문한 사람이 사용한 언어로 대답해 주세요.
            6. 처음 차량 추천을 요청하는 질문에는, 차량 한대당 한줄로 요약된 추천 리스트를 제공해 주세요.
            7. 장기렌트와 상관없는 질문에는 장기렌트와 관련된 답변을 하지 마세요.
            8. 추천 차량이 여러대일 경우, 각 차량의 주요 특징을 간단히 비교해 주세요.
            9. 사용자가 특정 차량(예: "카니발")을 언급한 경우, 그 차량에 대한 상세 정보를 제공해 주세요.
            10. 가격을 표시할 경우에는 가장 낮은 가격을 기준으로 안내해 주세요.
            """

            response_stream = st.session_state.chat.send_message(
                final_prompt,
                stream=True
            )
            
            def stream_text_generator(stream):
                for chunk in stream:
                    if chunk.text:
                        yield chunk.text

            with st.chat_message("assistant"):
                ai_response = st.write_stream(stream_text_generator(response_stream))
            
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
        except Exception as e:
            st.error(f"오류 발생: {e}")
