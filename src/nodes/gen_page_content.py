import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from ..utils.state import State
from ..utils.utils import clean_text, split_sents, img_to_data_url
from ..utils.split_chunk import build_external_block_for_prompt

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL")
llm_page = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0.3,  # 요약/설명이라 약간 낮게, 필요하면 조정
    api_key=os.getenv("OPENAI_API_KEY")
)

def node_generate_page_content(state: State) -> State:
    """
    슬라이드 인덱스 기준으로 해당 슬라이드 내용만 사용.
    - 텍스트는 항상 문자열로 처리.
    - 외부 보완 자료(external_content) 통합 후 요약 생성.
    """
    # (1) 인덱스 및 데이터 선택
    idx = int(state.get("slide_index", 0))
    titles = state.get("titles", [])
    texts_all = state.get("texts", [])
    tables_all = state.get("tables", [])
    images_all = state.get("images", [])
    shape_texts_all = state.get("shape_texts", [])

    title = clean_text(str(titles[idx])) if idx < len(titles) else ""
    texts = clean_text(str(texts_all[idx])) if idx < len(texts_all) else ""
    tables = tables_all[idx] if idx < len(tables_all) else []
    images = images_all[idx] if idx < len(images_all) else []
    shape_texts = shape_texts_all[idx] if idx < len(shape_texts_all) else []
    prompt = clean_text(str(state.get("prompt", "")))

    # (2) 표 전처리: 첫 표 최대 6행만 문자열로
    table_text = ""
    if tables and isinstance(tables, list) and len(tables) > 0:
        first_table = tables[0][:6] if isinstance(tables[0], list) else []
        table_text = "\n".join([" | ".join(map(str, row)) for row in first_table])

    # (3) 이미지 인코딩 (최대 3장)
    image_data_urls = []
    for img_path in images[:3]:
        try:
            image_data_urls.append(img_to_data_url(img_path))
        except Exception:
            continue

    # (4) 외부 보완 데이터
    ext = state.get("external_content", {}) or {}
    ext_queries = ext.get("queries", []) or []
    ext_summaries = ext.get("summaries", []) or []
    ext_refs = ext.get("references", []) or []

    # (5) 외부 보완 블록 구성 - 길이/개수 제한

    # 5-1) 질의 블록: 상위 3개, 각 40자 정도만
    ext_query_block = ""
    if ext_queries:
        q_lines = []
        for q in ext_queries[:3]:
            ctx  = q.get("context", "")
            text = clean_text(str(q.get("text", "")))[:40]
            if text and len(str(q.get("text", ""))) > 40:
                text += "..."
            q_lines.append(f"{ctx}: {text}")
        ext_query_block = "; ".join(q_lines)

    # 5-2) 요약 블록: score 기반 상위 source + chunk + 전체 길이 제한
    ext_summary_block = build_external_block_for_prompt(
        ext,
        max_sources=3, # 상위 3개 source만 사용
        max_chunks_per_source=2, # 각 source당 2개 chunk
        max_total_chars=1500, # 전체 1500자 내
        chunk_len=220, # chunk 한 개 최대 220자
    )

    # 5-3) 참고 URL 블록: score 기준 상위 4개만
    ext_ref_block = ""
    if ext_refs:
        refs_sorted = sorted(
            ext_refs,
            key=lambda r: r.get("score", 0.0),
            reverse=True,
        )
        cites = []
        for i, r in enumerate(refs_sorted[:4]):
            title_ref = clean_text(r.get("title", ""))[:100]
            url_ref = r.get("url", "")
            cites.append(f"[{i+1}] {title_ref} — {url_ref}")
        ext_ref_block = "\n".join(cites)

    # (6) 프롬프트 구성

    content_input = (
        f"다음은 한 슬라이드의 정보와 외부 보완 자료입니다.\n"
        f"제목: {title}\n"
        f"---\n"
        f"[텍스트]\n{texts}\n\n"
        f"[표 (앞 6행)]\n{table_text}\n\n"
        f"[도형 텍스트]\n{shape_texts}\n\n"
        f"[프롬프트 지침]\n{prompt}\n"
        f"---\n"
        f"타입별 해석 포인트:\n"
        f"- 텍스트: 주요 용어 정의, 핵심 문장, 강조된 개념을 파악합니다.\n"
        f"- 표(Table): 비교 기준과 각 항목 간의 차이점, 우위·열위 포인트를 추출합니다.\n"
        f"- 그래프(Chart): 수치의 변화 추세, 증가·감소 구간, x축과 y축 간의 인과관계를 분석합니다.\n"
        f"- 이미지(Image): 그림/도형 내의 핵심 텍스트와 주요 객체, 관계를 파악합니다.\n"
        f"- 코드(Code): 입력·처리·출력 단계의 흐름과 목적, 핵심 프로세스를 요약합니다.\n"
        f"---\n"
        f"[외부 보완 자료]\n"
        f"- 생성 질의: {ext_query_block if ext_query_block else '(질의 없음)'}\n"
        f"- 핵심 보강 요약:\n{ext_summary_block if ext_summary_block else '(요약 없음)'}\n"
        f"- 참조 출처:\n{ext_ref_block if ext_ref_block else '(참고 URL 없음)'}\n"
        f"---\n"
        f"규칙:\n"
        f"1) 과장 금지, 객관적으로 요약할 것.\n"
        f"2) 4~6문장, 문단 형태(불릿 금지).\n"
        f"3) 이미지/표/도형의 의미를 자연스럽게 통합해 설명.\n"
        f"4) 외부 보완 내용은 핵심만 반영하되, 출처를 대괄호 숫자로 표시 (예: [1][2]).\n"
    )

    # (7) LangChain LLM 호출 (멀티모달: 텍스트 + 이미지)
    human_content = [{"type": "text", "text": content_input}]
    for img_url in image_data_urls:
        human_content.append({
            "type": "image_url",
            "image_url": {"url": img_url},
        })

    response_msg = llm_page.invoke(
        [
            SystemMessage(
                content="당신은 슬라이드의 텍스트와 이미지, 표, 그래프 등을 바탕으로 강의 내용을 생성하고 신뢰할 수 있는 외부 자료로 보완하는 전문 강사입니다."
            ),
            HumanMessage(content=human_content),
        ]
    )

    # (8) 결과 저장
    page_content = clean_text(response_msg.content)
    state["page_content"] = " ".join(split_sents(page_content))
    print(response_msg)

    return state

