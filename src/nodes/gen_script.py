import os
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from ..utils.state import State
from ..utils.utils import clean_text

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL")
llm_script = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

def node_generate_script(state: State) -> State:
    """
    page_content를 실제 사람이 ‘강의하듯 말하는 스타일’로 변환하는 단계.
    이전 스크립트 흐름 유지, 톤앤매너, 길이 조절, 금지 표현 제거 등을 모두 포함.
    """

    print("\n--- Node 4: 강의 스크립트 생성(gen_script) 실행 ---")

    # ============================
    # 1. State에서 입력 정보 추출
    # ============================

    all_titles = state.get("titles", [])
    total_slides = len(all_titles)

    idx = state.get("slide_index", 0)
    current_title = all_titles[idx] if idx < len(all_titles) else f"슬라이드 {idx+1}"

    page_content = clean_text(state.get("page_content", ""))

    # 이전 스크립트
    prev_scripts = state.get("all_scripts", [])
    previous_script = prev_scripts[-1] if prev_scripts else None

    # 사용자 프롬프트 스타일 옵션
    prompt_data = state.get("prompt", {})
    tone = prompt_data.get("tone", "친절하고 명료한 톤")
    style = prompt_data.get("style", "자연스럽고 설명적인 말투")
    target_sec = prompt_data.get("target_duration_sec", 70)  # 기본값 70초 (60~90 사이)

    # 길이 가이드 (글자 수 / 문장 수)
    chars_min = int(target_sec * 6)
    chars_max = int(target_sec * 8)
    sent_min = max(4, int(target_sec / 15))  # 15초에 1문장 정도
    sent_max = max(sent_min + 2, int(target_sec / 10))

    work_dir = state.get("work_dir", "./")

    # 예외 처리: page_content가 없으면 title 기반 생성
    if not page_content.strip():
        page_content = (
            f"{current_title}의 핵심 개념을 중심으로 설명하는 슬라이드입니다. "
            "이 슬라이드의 주요 내용을 바탕으로 기본적인 강의 스크립트를 생성해 주세요."
        )

    # ============================
    # 2. 슬라이드 위치 기반 흐름 규칙 (Flow Instruction)
    # ============================

    if idx == 0:
        flow_instruction = (
            # "이 슬라이드는 전체 강의의 첫 슬라이드입니다. "
            # "강의 전체를 부드럽게 시작하는 도입부를 작성하되, "
            # "'안녕하세요' 같은 인사 표현은 절대 사용하지 마세요. "
            # "전체 강의가 매끄럽게 한 흐름으로 시작되는 느낌을 강조하세요."
            # f"{current_title} 를 시작한다고 알리고 시작하세요."
            
            # "이 슬라이드는 전체 강의의 첫 슬라이드입니다. "
            # "첫 문장은 반드시 슬라이드 제목을 자연스럽게 언급하면서 강의를 시작하는 형식으로 작성하세요. "
            # f"예: “{current_title}에 대해 함께 살펴보겠습니다.” "
            # "단, '안녕하세요', '이번 슬라이드에서는' 같은 표현은 절대 사용하지 않습니다."
            # "강의가 시작된다는 느낌만 주고 과한 인사는 하지 마세요."

            "이 슬라이드는 전체 강의의 첫 슬라이드입니다. "
            "첫 문장은 반드시 슬라이드 제목을 자연스럽게 언급하면서 강의를 시작하는 형식으로 작성하세요. "
            f"예: “지금부터 {current_title}에 대해 함께 살펴보겠습니다.” 와 같이 제목을 그대로 넣으세요. "
            "단, '안녕하세요' 등 인사하는 표현은 어떤 형태로도 절대 사용하지 마세요. "
            "강의가 시작된다는 느낌만 주고, 과한 인사나 형식적인 멘트는 쓰지 마세요."
        )
    elif idx == total_slides - 1:
        flow_instruction = (
            "이 슬라이드는 마지막 슬라이드입니다. "
            "전체 강의를 간결하게 마무리하고 핵심 메시지를 정리한 뒤 자연스럽게 끝맺는 스크립트를 생성하세요. "
            "마지막 슬라이드에서만 인사 멘트 사용이 허용됩니다."
        )
    else:
        flow_instruction = (
            # "이 슬라이드는 중간 슬라이드입니다. "
            # "첫 문장은 이전 슬라이드의 내용을 한두 문장으로 자연스럽게 이어주는 연결 문장으로 시작하세요. "
            # "연결형 표현('그리고', '이어서', '앞서 이야기한 내용에 기반해') 등을 사용하되 글의 흐름에 따라 자연스럽게 사용하세요. "
            # "하지만 '이번 슬라이드에서는', '다음은', '지금 보시는 슬라이드는' 같은 표현은 절대 사용하지 마세요."

            "이 슬라이드는 중간 슬라이드입니다. "
            "첫 문장은 이전 슬라이드의 내용을 간단하게 한 문장으로 자연스럽게 이어주세요. "
            "하지만 '이번 슬라이드에서는', '지금 보시는 슬라이드는', '다음으로 넘어가 보면' 같은 표현은 절대 사용하지 않습니다."
        )

    # ============================
    # 3. LLM 프롬프트 구성
    # ============================

    system_prompt = (
        "당신은 전문 강사이며, page_content 내용을 기반으로 실제 강사가 말하듯 자연스러운 스크립트를 생성하는 AI입니다. "
        "텍스트 설명을 '읽는 글'이 아닌 '말하는 글'로 자연스럽게 변환해야 합니다. "
        "슬라이드 간 흐름이 끊기지 않고 이어지도록 하는 것이 핵심입니다. "
        "기술적인 내용을 쉬운 비유로 설명하고, 청중에게 말을 거는 톤을 사용하세요. "
        "이미 이전 슬라이드에서 충분히 설명된 내용은 불필요하게 반복하지 말고, "
        "핵심만 간단히 상기시키는 수준으로만 언급하세요."
    )

    user_prompt = f"""
    # 전체 강의 목차
    {all_titles}

    # 현재 슬라이드
    - index: {idx}
    - title: {current_title}

    # 이전 스크립트 흐름
    {previous_script if previous_script else "(첫 슬라이드이므로 없음)"}

    # 현재 슬라이드 요약(page_content)
    {page_content}

    # 작성 조건
    1) 톤앤매너: {tone}, 스타일: {style}
    2) 목표 길이: 약 {target_sec}초 분량
        - 글자 수 기준: 약 {chars_min} ~ {chars_max}자
        - 문장 수 기준: 약 {sent_min} ~ {sent_max}문장
    3) 슬라이드 위치 규칙: {flow_instruction}
    4) page_content의 내용을 ‘강의 말투’로 자연스럽게 변환
    5) 금지 표현:
        - '이번 슬라이드에서는'
        - '다음으로 넘어가 보면'
        - '지금 보시는 슬라이드는'
        - '안녕하세요' (첫 슬라이드 포함)
        - '정리하자면' (마지막 슬라이드 외 사용 금지)
        - '이번 강의에서는', '이번 강의에선', '이번 강의에서' 등 '이번 강의~'로 시작하는 모든 표현 (첫 슬라이드 제외)

    # 출력 형식 (반드시 이 형식을 지키세요)
    [스크립트 시작]
    자연스럽고 강의형 말투의 스크립트만 작성
    [스크립트 종료]
    """

    # ============================
    # 4. LangChain LLM 호출
    # ============================

    response_msg = llm_script.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )

    raw_script = response_msg.content or ""

    # ============================
    # 5. 태그 파싱 + 금지 표현 필터링
    # ============================

    start_tag = "[스크립트 시작]"
    end_tag = "[스크립트 종료]"

    if start_tag in raw_script and end_tag in raw_script:
        script = raw_script.split(start_tag, 1)[1].split(end_tag, 1)[0].strip()
    else:
        # 태그가 없으면 전체를 스크립트로 간주
        script = raw_script.strip()

    banned_line_phrases = [
        "이번 슬라이드에서는",
        "지금 보시는 슬라이드는",
        "다음 슬라이드에서는",
        "다음으로 넘어가",
        "이번 강의에서는",
        "이번 강의에선",
        "이번 강의에서",
    ]

    lines = script.splitlines()
    cleaned_lines = []
    for line in lines:
        if any(phrase in line for phrase in banned_line_phrases):
            # 해당 줄 전체를 버림
            continue
        cleaned_lines.append(line)
    script = "\n".join(cleaned_lines)

    # 5-2) 그래도 남아 있을 수 있는 경우, 단어 단위로 한 번 더 제거
    banned_patterns = [
        r"이번\s*슬라이드\s*에서는",
        r"지금\s*보시는\s*슬라이드는",
        r"다음\s*슬라이드\s*에서는",
        r"다음으로\s*넘어가[^\n\.]*",
        r"이번\s*강의\s*에서는",
        r"이번\s*강의\s*에선",
        r"이번\s*강의\s*에서",
    ]

    for pattern in banned_patterns:
        script = re.sub(pattern, "", script)

    # 중복 공백/줄 정리
    script = re.sub(r"[ \t]{2,}", " ", script)
    script = re.sub(r"\n{3,}", "\n\n", script).strip()

    # ============================
    # 6. State 저장
    # ============================

    state["script"] = script

    if "all_scripts" not in state:
        state["all_scripts"] = []
    state["all_scripts"].append(script)

    # 파일 저장
    os.makedirs(work_dir, exist_ok=True)
    out_path = os.path.join(work_dir, f"script_{idx}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(script)

    print(f"   → 스크립트 생성 완료: {out_path}")

    return state
