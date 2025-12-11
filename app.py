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

# --- 3. Excel 데이터 로딩 (출고 가능 차량) ---
try:
    context_file = Path("cars_data.xlsx")
    if not context_file.exists():
        st.error("🚨 'cars_data.xlsx' 파일을 찾을 수 없습니다. app.py와 같은 위치에 만들어주세요.")
        st.stop()
    
    # openpyxl 엔진 사용
    df = pd.read_excel(context_file, engine="openpyxl")
    
    # 데이터프레임을 텍스트로 변환 (AI에게 제공할 컨텍스트)
    context = "--- [제트카 현재 보유 차량 목록] ---\n\n"
    column_headers = df.columns.tolist() 

    for index, row in df.iterrows():
        context += f"[{row[column_headers[0]]}]\n" 
        for col_name in column_headers[1:]:
            context += f"- {col_name}: {row[col_name]}\n"
        context += "\n"
            
    context += "--- [차량 목록 끝] ---"

except Exception as e:
    st.error(f"🚨 차량 데이터 로딩 중 오류 발생: {e}")
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
                # 최종 프롬프트 조합 (차량정보 + 사용자프로필 + 현재질문)
                final_prompt = f"""
                {context}
                
                [현재 상담 중인 고객 프로필]
                {st.session_state.user_profile}
                
                [사용자 질문]
                {user_input}
                
                [지시 사항]
                1. [현재 상담 중인 고객 프로필] 정보를 적극적으로 활용하여 맞춤형으로 답변하세요.
                   - 고객이 선호하는 '차급'과 '차종'을 최우선으로 고려하세요.
                   - 만약 프로필 정보가 '정보 없음'이라면 일반적인 기준으로 답변하세요.
                2. [제트카 현재 보유 차량 목록]에서 질문과 관련된 차량이 있다면 그 정보를 기반으로 정확히 답변하세요.
                3. 차량 데이터에 없는 내용은 일반적인 자동차 지식을 활용해 친절하게 답변하세요.
                4. 사용자가 특정 차량번호(또는 차량명)를 물어보면 아래 서식으로 요약하세요.
                   '이런 분들께 추천 !' 부분은 [고객 프로필]을 참고하여 창의적으로 작성하세요.
                   
                   [차량 요약 서식]
                   제조사 연식 차량명 신용 무관 전국 출고 
                   ... (기존 상세 서식 유지) ...
                   👍 이런 분들께 추천 ! 
                   ✔️ (고객 프로필에 맞춰 작성 1)
                   ✔️ (고객 프로필에 맞춰 작성 2)
                   ...
                   
                5. 추천 차량이 여러 대일 경우, 각 차량의 특징을 비교해 주세요.
                6. 가격은 가장 낮은 가격을 기준으로 안내하세요.
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
        
        with col2:
            income = st.selectbox("월 급여 수준 (세후)", ["200만원 미만", "200~300만원", "300~400만원", "400~500만원", "500만원 이상"])
            purpose = st.multiselect("차량 사용 용도", ["출퇴근용", "영업/업무용", "패밀리카(가족여행)", "레저/캠핑", "장보기/마실용", "기타"])
        
        # 기타 용도 입력
        custom_purpose = st.text_input("기타 용도 (위에서 '기타' 선택 시 작성)", placeholder="예: 낚시용, 대형견 탑승 등")
        
        st.markdown("---")
        
        # 2. 희망 차량 정보 섹션
        st.markdown('<div class="form-header">🚘 희망 차량 정보</div>', unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        
        with col3:
            # 🚨 [수정] default 제거 -> 빈칸으로 시작 ('상관없음'은 선택지에 존재)
            preferred_size = st.multiselect("선호 차급 (복수 선택 가능)", ["경차/준중형", "중형", "대형", "상관없음"])
        
        with col4:
            # 🚨 [수정] default 제거 -> 빈칸으로 시작
            preferred_type = st.multiselect("선호 차종 (복수 선택 가능)", ["세단", "SUV", "RV/승합", "상관없음"])

        st.markdown("---")
        st.markdown("### 💬 무엇을 도와드릴까요?")
        
        initial_query = st.text_area("궁금한 점이 있다면 적어주세요 (빈칸으로 두시면 입력한 정보에 맞춰 추천해 드립니다!)", height=80)
        
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            submit_with_info = st.form_submit_button("🚀 정보 입력하고 상담받기", use_container_width=True)
            
        with btn_col2:
            submit_skip = st.form_submit_button("⏩ 입력 없이 바로 시작하기", use_container_width=True)
        
        # [로직 처리]
        if submit_with_info:
            # 1. 정보 입력 모드
            
            final_purpose_list = purpose
            if custom_purpose.strip():
                final_purpose_list.append(f"추가용도: {custom_purpose}")
            
            # 🚨 [수정] 리스트가 비어있으면(선택 안 했으면) 자동으로 '상관없음'으로 처리
            size_str = ", ".join(preferred_size) if preferred_size else "상관없음"
            type_str = ", ".join(preferred_type) if preferred_type else "상관없음"

            profile_text = f"""
            - 나이: {age}
            - 결혼 유무: {marital_status}
            - 월 급여: {income}
            - 사용 용도: {', '.join(final_purpose_list)}
            - 선호 차급: {size_str}
            - 선호 차종: {type_str}
            """
            st.session_state.user_profile = profile_text
            st.session_state.form_submitted = True
            
            if initial_query.strip():
                st.session_state.first_query = initial_query
            else:
                st.session_state.first_query = "제 프로필(나이, 급여, 용도, 선호 차급/차종)에 딱 맞는 차량을 추천해 주세요. 왜 추천하는지도 설명해 주세요."
            
            st.rerun()

        elif submit_skip:
            # 2. 건너뛰기 모드
            st.session_state.user_profile = "정보 없음 (일반적인 고객 기준으로 답변해 주세요)"
            st.session_state.form_submitted = True
            
            if initial_query.strip():
                st.session_state.first_query = initial_query
            else:
                st.session_state.messages.append({"role": "assistant", "content": "제트카에 대해 무엇이든 물어보세요! 🚗"})
                
            st.rerun()

# (B) 정보를 제출(또는 건너뛰기)한 후 -> '채팅 창' 표시
else:
    # 1. 이전 대화 기록 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 2. (폼에서 넘어온) 첫 번째 질문이 있다면 처리
    if "first_query" in st.session_state:
        query = st.session_state.first_query
        del st.session_state.first_query 
        generate_ai_response(query)

    # 3. 채팅 입력창 활성화
    if prompt := st.chat_input("추가로 궁금한 점이 있으신가요?"):
        generate_ai_response(prompt)
