import re
from ..utils.utils import clean_text

# 검색 결과를 chunk단위로 처리
def split_text_to_chunks(text: str, max_len: int = 220) -> list[str]:
    """
    text를 문장 단위로 자르면서 최대 max_len 글자 안쪽으로 묶어주는 간단한 chunker.
    - 토큰까지 정확히 보진 않지만, 대략적인 길이 제어용
    """
    text = (text or "").strip()
    if not text:
        return []

    # 문장 단위로 대충 나누기 (.!? 기준)
    sentences = re.split(r'(?<=[\.!?])\s+', text)
    chunks = []
    buf = ""

    for s in sentences:
        s = s.strip()
        if not s:
            continue

        # 이번 문장을 buf에 추가했을 때 max_len 넘으면 → 기존 buf를 하나의 chunk로 확정
        if len(buf) + len(s) + 1 > max_len:
            if buf:
                chunks.append(buf.strip())
            buf = s
        else:
            buf = (buf + " " + s).strip() if buf else s

    if buf:
        chunks.append(buf.strip())

    return chunks


def build_external_block_for_prompt(
    ext: dict,
    max_sources: int = 3, # 상위 몇 개 source만 쓸지
    max_chunks_per_source: int = 2, # source당 chunk 최대 개수
    max_total_chars: int = 1500, # 전체 외부 블록 최대 문자 수
    chunk_len: int = 220, # chunk 한 개 최대 길이
) -> str:
    """
    state['external_content'] 구조에서 summaries를 읽어와
    프롬프트에 들어갈 외부 요약 블록 텍스트를 만들어준다.
    - score 기준으로 상위 source만 사용
    - 각 source의 text를 chunk로 쪼개고
    - 전체 길이를 max_total_chars 안으로 자른다
    """
    summaries = ext.get("summaries", []) or []

    # score 기준 상위 정렬 (없으면 0으로)
    summaries = sorted(
        summaries,
        key=lambda s: s.get("score", 0.0),
        reverse=True,
    )

    lines = []
    total_len = 0

    for s in summaries[:max_sources]:
        source = clean_text(str(s.get("source", "")))
        text   = clean_text(str(s.get("text", "")))
        if not text:
            continue

        chunks = split_text_to_chunks(text, max_len=chunk_len)

        for ch in chunks[:max_chunks_per_source]:
            line = f"[{source}] {ch}"
            if total_len + len(line) + 1 > max_total_chars:
                return "\n".join(lines)
            lines.append(line)
            total_len += len(line) + 1

    return "\n".join(lines)
