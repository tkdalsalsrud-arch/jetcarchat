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

# --- 4. 사용자 입력 및 AI 응답 처리 (🚨 'Search-then-Answer' RAG로 수정) ---
if prompt := st.chat_input("SUV차량 추천해줘 / 장기렌트의 장점이 뭐에요? / 30대 직장인 여성에게 맞는 차량은?"):
    
    # 1. 사용자 메시지 저장 및 UI에 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. AI에게 응답 요청
    with st.spinner("jetcar가 생각 중... 🚙💨"):
        try:
            # 🚨 (핵심 로직 1) '검색' 단계
            # 사용자의 질문(prompt)에 엑셀 데이터(df)의 '차량명'이 포함되어 있는지 확인
            # 'df'는 코드 상단에서 엑셀을 읽어온 pandas DataFrame입니다.
            
            # 1-1. 검색 결과(일치하는 차량 정보)를 담을 변수
            search_results = ""
            
            # 1-2. DataFrame(df)을 한 줄씩 돌면서 '차량명'이 질문(prompt)에 포함되는지 확인
            # (더 정확한 검색을 위해, 차량명/차량번호 목록을 따로 관리할 수도 있습니다)
            # (여기서는 간단히 df의 첫 번째 열(차량명/번호)을 기준으로 검색)
            
            # '차량명' 열 이름 (코드 상단에서 정의한 column_headers 사용)
            vehicle_name_column = column_headers[0] 
            
            # '차량명' 또는 '차량번호'가 프롬프트에 언급되었는지 검색
            # 예: "아반떼 12가3456" 질문에 대해 "아반떼" 또는 "12가3456" 차량을 찾음
            # (간단한 예시: 프롬프트에 차량명이 포함되거나, 차량명이 프롬프트에 포함되거나)
            
            # 🚨 DataFrame에서 일치하는 데이터 검색 (pandas의 str.contains 사용)
            # 여기서는 '차량명' 열을 기준으로 검색 (필요시 다른 열도 추가)
            try:
                # 사용자의 프롬프트에 '차량명' 열의 값이 포함되어 있는지 검색
                # (예: 프롬프트 "아반떼 있나요?" -> df['차량명'] "아반떼"가 포함됨)
                # (이 검색 방식은 사용자의 질문에 따라 조정이 필요할 수 있습니다)
                
                # 더 나은 검색: 키워드를 뽑아서 검색 (간단한 예시)
                # 여기서는 'df'의 '차량명' 열(column_headers[0])에 프롬프트의 단어가 있는지 검색
                # (이 방식은 정확도가 낮을 수 있으니, 실제로는 더 정교한 검색 필요)
                
                # **가장 간단하고 효과적인 검색 (가정):**
                # 사용자가 '아반떼' 또는 '12가3456'처럼 키워드를 입력한다고 가정
                # df의 '차량명' 열(column_headers[0])에 그 키워드가 있는지 검색
                
                # 🚨 (수정된 검색 로직) '차량명' 열에서 프롬프트 키워드 찾기
                # (만약 '차량명'이 '제조사' '모델명'으로 분리되어 있다면 로직 변경 필요)
                
                # **(가장 현실적인 검색 로직)**
                # df의 모든 텍스트 셀을 검사하여 prompt의 단어가 포함되는지 확인
                # 여기서는 '차량명' 열(첫 번째 열)만 검사
                
                # 1. 차량명 열(첫번째 열)을 기준으로 검색
                # df[vehicle_name_column]이 문자열이 아닐 수 있으므로 .astype(str) 추가
                relevant_rows = df[df[vehicle_name_column].astype(str).str.contains(prompt, case=False, na=False)]

                # 2. 만약 1번에서 못찾았고, 프롬프트가 2단어 이하라면 (차량명일 가능성 높음)
                #    전체 텍스트에서 검색 시도 (현재 context 변환 로직 활용)
                
                # (우선 1번 로직만 사용)
                
                if not relevant_rows.empty:
                    # 3. 검색된 결과를 context 텍스트로 변환
                    search_results = "--- [jetcar 참고 자료 (검색 결과)] ---\n\n"
                    for index, row in relevant_rows.iterrows():
                        search_results += f"[{row[column_headers[0]]}]\n" 
                        for col_name in column_headers[1:]:
                            search_results += f"- {col_name}: {row[col_name]}\n"
                        search_results += "\n"
                    search_results += "--- [참고 자료 끝] ---"
            
            except Exception as search_e:
                st.warning(f"검색 중 오류 발생 (무시하고 진행): {search_e}")
                search_results = "" # 검색 실패 시 빈칸으로

            # 🚨 (핵심 로직 2) '선택적' 프롬프트 구성
            # 검색 결과(search_results)가 있을 때만 '참고 자료'를 AI에게 제공
            
            # 'search_results'가 비어있다면, AI는 'context' 없이 질문만 받음
            # -> AI가 '기초 상식'으로 답변하게 됨 (지시 3번)
            
            # 'search_results'가 있다면 (차량 정보가 검색됨)
            # -> AI는 '검색된 차량 정보'만 가지고 답변함 (지시 2번)

            final_prompt = f"""
            {search_results} 
            
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

            # 3. AI에게 응답 요청 (스트리밍)
            response_stream = st.session_state.chat.send_message(
                final_prompt,
                stream=True
            )
            
            # 4. 스트리밍 '번역기' 함수 (이전과 동일)
            def stream_text_generator(stream):
                for chunk in stream:
                    if chunk.text:
                        yield chunk.text

            # 5. UI에 스트리밍 표시 (이전과 동일)
            with st.chat_message("assistant"):
                ai_response = st.write_stream(stream_text_generator(response_stream))
            
            # 6. 세션에 저장 (이전과 동일)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
        except Exception as e:
            st.error(f"AI 응답 중 오류가 발생했습니다: {e}")
