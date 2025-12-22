import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
from pathlib import Path

# --- 0. 페이지 설정 및 CSS 스타일 ---
st.set_page_config(page_title="JETCAR 직원용 지원 챗봇", page_icon="🏎️")

st.markdown("""
<style>
    /* 챗 메시지 컨테이너 스타일 */
    div[data-testid="chat-message-container"] {
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 10px;
    }
    /* 사용자(직원) 메시지 배경색 */
    div[data-testid="chat-message-container"]:has(div[data-testid="stChatMessageContent-user"]) {
        background-color: #F0F2F6;
        color: #333;
    }
    /* 봇(assistant) 메시지 배경색 */
    div[data-testid="chat-message-container"]:has(div[data-testid="stChatMessageContent-assistant"]) {
        background-color: #4A90E2;
        color: white;
    }
    .stChatInputContainer {
        padding-top: 15px !important;
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
st.title("🏎️ JETCAR 직원 지원 시스템")
st.caption("차량 데이터 분석 및 상담 가이드 지원 도구")

# --- 3. Excel 데이터 로딩 (출고 가능 차량) ---
@st.cache_data # 데이터 로딩 성능 최적화
def load_car_data():
    try:
        context_file = Path("cars_data.xlsx")
        if not context_file.exists():
            return None, "🚨 'cars_data.xlsx' 파일을 찾을 수 없습니다."
        
        df = pd.read_excel(context_file, engine="openpyxl")
        
        context_str = "--- [제트카 현재 보유 차량 목록] ---\n\n"
        column_headers = df.columns.tolist() 

        for index, row in df.iterrows():
            context_str += f"[{row[column_headers[0]]}]\n" 
            for col_name in column_headers[1:]:
                context_str += f"- {col_name}: {row[col_name]}\n"
            context_str += "\n"
        context_str += "--- [차량 목록 끝] ---"
        return context_str, None
    except Exception as e:
        return None, f"🚨 데이터 로딩 중 오류: {e}"

context, error_msg = load_car_data()
if error_msg:
    st.error(error_msg)
    st.stop()

# --- 4. 세션 상태 초기화 ---
# 모델 설정 (Gemini 1.5 Flash 권장)
if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel('gemini-2.5-flash')

if "chat" not in st.session_state:
    st.session_state.chat = st.session_state.model.start_chat(history=[])

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 제트카 직원용 지원 챗봇입니다. 차량 조회나 상담 답변 생성을 도와드릴까요?"}]

# --- 5. AI 응답 생성 함수 ---
def generate_ai_response(user_input):
    # 1. 사용자 메시지 UI 표시 및 저장
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. AI 응답 요청
    with st.chat_message("assistant"):
        with st.spinner("데이터 분석 중..."):
            try:
                # 직원용 특화 프롬프트
                system_instruction = f"""
                당신은 제트카(JETCAR) 상담 직원들의 업무를 돕는 AI 비서입니다.
                아래 제공된 차량 목록을 바탕으로 직원의 질문에 정확하고 효율적으로 답하세요.

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
            11. 차량명의 제일처음에는 "[전국]"을 포함시켜주시고 가장 뒤에는 가장 낮은 가격의 개월수와 연식, 연료, "2WD 5인승"을 표시해주세요.
            """

                # 스트리밍 응답
                response = st.session_state.chat.send_message(
                    f"{system_instruction}\n\n직원 질문: {user_input}",
                    stream=True
                )
                
                def stream_text_generator(stream):
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text

                ai_response = st.write_stream(stream_text_generator(response))
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
            except Exception as e:
                st.error(f"오류 발생: {e}")

# --- 6. 메인 UI 로직 ---

# 이전 대화 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 채팅 입력창
if prompt := st.chat_input("차량 번호, 차종 또는 상담 관련 질문을 입력하세요."):
    generate_ai_response(prompt)
