import streamlit as st
import google.generativeai as genai
import pandas as pd
from pathlib import Path

# --- 0. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="JETCAR 직원 지원 시스템", page_icon="🏎️")

st.markdown("""
<style>
    div[data-testid="chat-message-container"] { border-radius: 10px; padding: 10px 14px; margin-bottom: 10px; }
    div[data-testid="chat-message-container"]:has(div[data-testid="stChatMessageContent-user"]) { background-color: #F0F2F6; color: #333; }
    div[data-testid="chat-message-container"]:has(div[data-testid="stChatMessageContent-assistant"]) { background-color: #4A90E2; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 1. 키워드 데이터 정의 ---
KEYWORDS_CONDITION = ["1년렌트카", "1년장기렌트", "개인회생렌탈", "개인회생자장기렌트", "개인회생장기렌트", "개인회생장기렌트카", "개인회생중고차", "무심사렌트카", "무심사장기렌트", "무심사장기렌트카", "수입차장기렌트", "신불자렌트", "신불자렌트카", "신불자장기렌트", "신불자장기렌트카", "신불자중고차", "신불장기렌트", "신용불량자장기렌트", "신용불량자중고차", "신용불량장기렌트", "신용불량장기렌트카", "신용불량중고차", "신용회복장기렌트", "신용회복중장기렌트", "신용회복중중중고차", "연체자장기렌트", "연체자중고차", "외제차장기렌트", "장기렌트신용", "장기렌트신용등급", "장기렌트카신용", "저신용렌트", "저신용렌트카", "저신용자장기렌트", "저신용자장기렌트카", "저신용장기렌트", "저신용장기렌트카", "저신용중고차", "저신용중고차렌트", "중고장기렌터카", "중고장기렌트", "중고장기렌트카", "중고차장기렌트", "중고차장기렌트카", "대전스타리아렌트"]
KEYWORDS_LOCATION_BIZ = ["개인사업렌트카", "개인사업자렌트", "개인사업자장기렌트", "법인렌터카", "법인렌트", "법인렌트견적", "법인렌트카", "법인장기렌터카", "법인장기렌트", "법인장기렌트견적", "법인장기렌트카", "법인장기렌트카견적", "법인차량렌트", "사업자렌트", "사업자렌트카", "사업자장기렌트", "신규법인장기렌트", "강릉장기렌트", "거제장기렌트", "경산장기렌트", "경주장기렌트", "계룡장기렌트", "고양장기렌트", "공주장기렌트", "광명장기렌트", "광양장기렌트", "광주장기렌트", "구리장기렌트", "군산장기렌트", "군포장기렌트", "금산장기렌트", "김제장기렌트", "김포장기렌트", "김해장기렌트", "나주장기렌트", "남양주장기렌트", "남원장기렌트", "논산장기렌트", "대구장기렌트", "대전장기렌트", "동두천장기렌트", "동해장기렌트", "목포장기렌트", "무주장기렌트", "문경장기렌트", "밀양장기렌트", "보령장기렌트", "부산장기렌트", "부천장기렌트", "사천장기렌트", "삼척장기렌트", "서산장기렌트", "서울장기렌트", "속초장기렌트", "수원장기렌트", "순천장기렌트", "시흥장기렌트", "아산장기렌트", "안동장기렌트", "안산장기렌트", "안성장기렌트", "안양장기렌트", "양산장기렌트", "양주장기렌트", "여수장기렌트", "여주장기렌트", "오산장기렌트", "옥천장기렌트", "용인장기렌트", "원주장기렌트", "의왕장기렌트", "의정부장기렌트", "이천장기렌트", "익산장기렌트", "전주장기렌트", "정읍장기렌트", "제주장기렌트", "제천장기렌트", "진주장기렌트", "창원장기렌트", "천안장기렌트", "청주장기렌트", "춘천장기렌트", "충주장기렌트", "태백장기렌트", "통영장기렌트", "파주장기렌트", "평택장기렌트", "포천장기렌트", "포항장기렌트", "하남장기렌트", "홍천장기렌트", "화성장기렌트", "횡성장기렌트"]
CAR_MODELS = ["모닝", "레이", "니로", "스토닉", "셀토스", "스포티지", "쏘렌토", "모하비", "카니발", "EV3", "EV4", "EV6", "EV9", "G70", "G80", "G90", "GV60", "GV70", "GV80", "GV90", "EQ900", "SM3", "SM5", "SM6", "SM7", "XM3", "QM5", "QM6", "그랑콜레오스", "아르카나", "QM3", "티볼리", "토레스", "액티언", "렉스턴", "코란도", "스파크", "트랙스", "트레일블레이저", "A클래스", "C클래스", "E클래스", "S클래스", "GLC클래스", "GLE클래스", "CLA클래스", "CLE클래스", "CLS클래스", "EQ", "X1", "X3", "X4", "X5", "X6", "X7", "1시리즈", "3시리즈", "5시리즈", "7시리즈", "GT", "i3", "i4", "i5", "i7", "ix", "아테온", "티구안", "골프", "제타"]

# --- 2. API 설정 및 데이터 로드 ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error("🚨 API 키 오류")
    st.stop()

@st.cache_data
def load_car_data():
    try:
        context_file = Path("cars_data.xlsx")
        if not context_file.exists(): return None, "🚨 'cars_data.xlsx' 없음"
        df = pd.read_excel(context_file, engine="openpyxl")
        return df, None
    except Exception as e: return None, f"🚨 오류: {e}"

df_cars, error_msg = load_car_data()
if error_msg: st.error(error_msg); st.stop()

# --- 3. 세션 관리 ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "제트카 직원 전용 시스템입니다. 찾으시는 차량이나 상담 키워드가 있으신가요?"}]

# --- 4. 응답 생성 함수 ---
def generate_ai_response(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"): st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("데이터 분석 및 서식 구성 중..."):
            try:
                car_text_context = df_cars.to_string(index=False)
                
                system_prompt = f"""
                당신은 제트카(JETCAR) 상담 직원을 돕는 AI 비서입니다.
                제공된 [차량 현황 데이터]를 기반으로 답변하세요.

                [데이터]
                {car_text_context}

                [필수 지시 사항 - 절대 누락 금지]
                1. 차량 제목 형식:
                   형식: **[전국] 차량명 (분류1 / 분류2 / 분류3) 최저가개월수 연식 연료 2WD 5인승**
                   - 제목 끝에는 반드시 "2WD 5인승"이라는 문구를 수동으로라도 붙여야 합니다.
                   - 차량명 자체에 금액을 표시하지 마세요.

                2. 3단 키워드 조합 규칙:
                   - 분류1 (조건): {KEYWORDS_CONDITION} 중 선택. (주행거리 30 차량은 '중고차' 단어 포함 키워드 절대 금지)
                   - 분류2 (지역/사업자): {KEYWORDS_LOCATION_BIZ} 중 선택.
                   - 분류3 (모델): 차량명에서 {CAR_MODELS} 중 일치하는 모델 추출 후 '모델명장기렌트'로 표기.

                3. 렌트비용 안내 (데이터 기반 가변 출력):
                   - 엑셀 데이터에 존재하는 모든 개월수 컬럼을 찾아 각각 한 줄씩 표시하세요.
                   - 형식:
                   💸 렌트비용
                   보증금 80만원
                   정비 포함 여부 : 정비 미포함
                   탁송료 : 별도 

                   📆 (데이터 개월수) (해당 금액)만원

                4. 상세 서식 예시:
                   📌 차량정보
                   차량명: 
                   주행거리 : 
                   연식: 
                   연료 : 

                   ✨ 적용옵션: 기본형

                   (위 렌트비용 섹션)

                   👍 이런 분들께 추천 ! 
                   ✔️ (데이터 기반 추천 사유 3가지)

                   📞 상담문의
                   카톡상담 : 카카오톡에 'JETCAR' 를 검색해주세요
                   홈페이지 방문 : https://www.jetcar.co.kr/
                """
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(f"{system_prompt}\n\n직원 질문: {user_input}")
                
                ai_response = response.text
                st.markdown(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
            except Exception as e: st.error(f"오류: {e}")

# --- 5. UI 메인 ---
st.title("🚗 JETCAR 스마트 상담 비서")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("차량명이나 번호를 입력하세요."):
    generate_ai_response(prompt)
