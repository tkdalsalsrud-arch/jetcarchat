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
st.title("🚗 jetcar 챗봇")
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
    context = "--- [제트카 정보] ---\n\n"
    
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

    st.info("✅ 출고 가능 차량 로딩 완료!")

except Exception as e:
    st.error(f"🚨 출고 가능 차량 로딩 중 오류 발생: {e}")
    st.stop()


# 세션 상태(session_state)에 모델과 채팅 기록 초기화
if "model" not in st.session_state:
    # 1.0 세대의 표준 모델
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

# --- 4. 사용자 입력 및 AI 응답 처리 (v4와 동일) ---
if prompt := st.chat_input("SUV차량 추천해줘! / 카니발 장기렌트 가능할까? / 패밀리카 추천해줘!"):
    
    # 1. 사용자 메시지 저장 및 UI에 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# 2. AI에게 응답 요청 (🚨 '올바른' 스트리밍 방식으로 수정)
        with st.spinner("jetcar가 생각 중... 🚙💨"):
            try:
                # 🚨 final_prompt 생성 (이전과 동일)
                # (이 부분은 사용자님이 수정한 '기초 상식 답변' 버전 프롬프트입니다)
                final_prompt = f"""
                {context}
                
                [사용자 질문]
                {prompt}
                
                [지시]
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

                # 🚨 chat.send_message를 그대로 쓰되, stream=True 추가!
                response_stream = st.session_state.chat.send_message(
                    final_prompt,
                    stream=True
                )
                
                # 3. AI 응답 저장 및 UI에 표시 (🚨 스트리밍 방식으로 변경)
                with st.chat_message("assistant"):
                    # 🚨 st.write_stream을 사용해 답변을 실시간으로 표시
                    # 이 함수는 스트리밍이 끝나면 전체 텍스트(ai_response)를 반환합니다.
                    ai_response = st.write_stream(response_stream)
                
                # 4. 🚨 UI에 표시할 메시지 목록(messages)에만 AI 응답 추가
                # (st.session_state.chat.history는 .send_message가 자동으로 관리합니다)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
            except Exception as e:
                st.error(f"AI 응답 중 오류가 발생했습니다: {e}")
