import os
import json
import textwrap

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..utils.state import State
import re

LLM_MODEL = os.getenv("LLM_MODEL")
llm_quiz = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY"),
    max_tokens=4096
)
def extract_json(text):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    return match.group(0) if match else "[]"

def node_generate_quiz(state: State) -> State:
    """
    Node 10. 퀴즈 생성(make_quiz)
    - 전체 강의 스크립트(all_scripts)를 기반으로 객관식 4지선다형 퀴즈 JSON 생성
    - 슬라이드별 최소 1문항 보장 (총 6문항 이상 가능)
    """

    print("\n--- Node 10: 퀴즈 생성(make_quiz) 실행 ---")

    # (1) 입력 로드
    all_scripts = state.get("all_scripts", [])
    if not all_scripts:
        print("[경고] 전체 스크립트가 없어 퀴즈 생성 불가")
        state["quiz_set"] = []
        return state

    # (2) 슬라이드 구분 포함 전체 스크립트 문자열 생성
    full_script = "\n\n".join(
        [f"[슬라이드 {i+1}]\n{txt}" for i, txt in enumerate(all_scripts)]
    )

    # (3) System Prompt
    system_prompt = textwrap.dedent("""
        당신은 전문 교육용 퀴즈 출제 AI입니다.
        다음 강의 전체 스크립트를 기반으로 학습자의 이해도를 평가할 수 있는
        객관식 4지선다형 퀴즈를 JSON 형식으로 생성하세요.
    """)

    # (4) User Prompt — JSON 형식 강제
    user_prompt = textwrap.dedent(f"""
      다음은 전체 강의 스크립트입니다:

      {full_script}

      규칙:
      1. 최소 10문항 이상 생성할 것.
      2. 각 문항은 JSON 객체로 구성.
      3. 모든 문항은 4지선다 객관식.
      4. 선택지는 반드시 "1. ...", "2. ...", "3. ...", "4. ..." 형식.

      5. answer에는 정답 보기의 번호(1~4)만 문자열로 작성하세요.
        예: "answer": "2"
      6. answer는 반드시 "1", "2", "3", "4" 중 하나여야 합니다.

      7. 각 문항의 정답 번호는 1~4 사이에서 다양하게 배치되도록 하세요.
      8. 정답 번호가 특정 보기에 반복적으로 쏠리지 않도록 하세요.
      9. 정답 번호가 두 문제 연속으로 동일하지 않도록 하세요.
      10. 전체적으로 1,2,3,4번 정답이 고르게 등장하도록 구성하세요.

      JSON 형식 예시는 다음과 같습니다:

      [
          {{
              "question": "질문 내용",
              "options": ["1. ...", "2. ...", "3. ...", "4. ..."],
              "answer": "2",
              "explanation": "해설 내용"
          }},
          ...
      ]
      """)
    
    
    response = llm_quiz.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
   
    )


    raw_json = response.content or ""
    json_text = extract_json(raw_json)
    

    # (6) JSON 파싱 + 예외 처리
    try:
        quiz_data = json.loads(json_text)
    except Exception as e:
        print("[오류] JSON 파싱 실패:", e)
        state["quiz_set"] = []
        return state

    # (7) state에 저장
    state["quiz_set"] = quiz_data

    print(f"[완료] 총 {len(quiz_data)}개의 퀴즈 생성")

    return state
