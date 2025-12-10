import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
from pathlib import Path

# --- 0. 페이지 설정 및 CSS 스타일 ---
st.set_page_config(page_title="JETCAR 챗봇", page_icon="🚗")

st.markdown("""
<style>
    /* 챗 메시지 컨테이너 스타일 */
    div[data-testid="chat-message-container"] {
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 10px;
    }
    /* 사용자(user) 메시지 배경색 */
    div[data-testid="chat-message-container"]:has(div[data-testid="stChatMessageContent-user"]) {
        background-color: #F0F2F6;
        color: #333;
    }
    /* 봇(assistant) 메시지 배경색 */
    div[data-testid="chat-message-container"]:has(div[data-testid="stChatMessageContent-assistant"]) {
        background-color: #4A90E2;
        color: white;
    }
    /* 입력 폼 컨테이너 스타일 */
    div[data-testid="stForm"] {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
    /* 채팅 입력창 여백 조정 */
    .stChatInputContainer {
        padding-top: 15px !important;
    }
    /* 폼 내부 섹션 헤더 스타일 */
    .form-header {
        font-size: 1.1em;
        font-weight: bold;
        color: #444;
        margin-top: 10px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. API 키 설정 ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error("🚨 [Gemini API 키]를 설정하는 데 실패했습니다. Secrets를 확인하세요.")
    st.stop()

# --- 2. 앱 제목 ---
st.title("🚗 JETCAR 맞춤형 상담 챗봇")
st.caption("Powered by Streamlit & Google Gemini")

# --- 3. [최적화] 데이터 로딩 캐싱 함수 ---
# 🚀 핵심 변경점: 이 함수는 데이터가 바뀌지 않는 한 재실행되지 않습니다.
@st.cache_data
def load_car_data():
    try:
        context_file = Path("cars_data.xlsx")
        if not context_file.exists():
            return None, "🚨 'cars_data.xlsx' 파일을 찾을 수 없습니다."
        
        # openpyxl 엔진 사용
        df = pd.read_excel(context_file, engine="openpyxl")
        
        # 데이터프레임을 텍스트로 변환 (AI에게 제공할 컨텍스트)
        # 팁: 데이터가 너무 많으면 AI가 느려집니다. 필요한 컬럼만 추리는 것도 방법입니다.
        text_context = "--- [제트카 현재 보유 차량 목록] ---\n\n"
        column_headers = df.columns.tolist() 

        for index, row in df.iterrows():
            text_context += f"[{row[column_headers[0]]}]\n" 
            for col_name in column_headers[1:]:
                # 값이 없는(NaN) 경우는 제외하여 토큰 수를 줄임
                if pd.notna(row[col_name]):
                    text_context += f"- {col_name}: {row[col_name]}\n"
            text_context += "\n"
                
        text_context += "--- [차량 목록 끝] ---"
        return text_context, None
        
    except Exception as e:
        return None, f"🚨 데이터 로딩 중 오류: {e}"

# 캐싱된 데이터 불러오기
context, error_msg = load_car_data()

if error_msg:
    st.error(error_msg)
    st.stop()


# --- 4. 세션 상태 초기화 ---
if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel('gemini-2.5-flash')

if "chat" not in st.session_state:
    st.session_state.chat = st.session_state.model.start_chat(history=[])

if "messages" not in st.session_state:
    st.session_state.messages = []

# 폼 제출 여부 확인 플래그
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False

# 사용자 프로필 저장 변수
if "user_profile" not in st.session_state:
    st.session_state.user_profile = ""


# --- 5. 공통 함수: AI 응답 생성 및 스트리밍 ---
def generate_ai_response(user_input):
    # 1. 사용자 메시지 UI 표시 및 저장
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. AI 응답 요청
    with st.chat_message("assistant"):
        with st.spinner("jetcar가 정보를 분석 중입니다... 🚙💨"):
            try:
                # 최종 프롬프트 조합
                final_prompt = f"""
                [현재 상담 중인 고객 프로필]
                {st.session_state.user_profile}
                
                [사용자 질문]
                {user_input}
                
                {context}
                
               [지시 사항]
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
	11. 모든 대답 뒤에는 '추천 받은 차량을 홈페이지에서 확인하세요'라는 멘트와 함께 'https://www.jetcar.co.kr/' 이 링크를 누를 수 있도록 유도해줘
            """

                # 스트리밍 요청
                response_stream = st.session_state.chat.send_message(
                    final_prompt,
                    stream=True
                )
                
                # 텍스트 추출 제너레이터
                def stream_text_generator(stream):
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text

                # 스트리밍 출력 및 저장
                ai_response = st.write_stream(stream_text_generator(response_stream))
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
            except Exception as e:
                st.error(f"AI 응답 중 오류가 발생했습니다: {e}")


# --- 6. 메인 UI 로직 ---

# (A) 아직 정보를 제출하지 않은 경우 -> '입력 폼' 표시
if not st.session_state.form_submitted:
    st.info("👋 안녕하세요! 고객님께 딱 맞는 차량을 추천해 드리기 위해 기본 정보를 입력해 주세요.")
    
    with st.form("consultation_form"):
        # 1. 고객 기본 정보 섹션
        st.markdown('<div class="form-header">👤 고객 기본 정보</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            age = st.selectbox("나이", ["만 26~35세", "만 36~45세", "만 46~55세", "만 55세 이상"])
            marital_status = st.radio("결혼 유무", ["미혼", "기혼 (자녀 없음)", "기혼 (자녀 있음)"], horizontal=True)
