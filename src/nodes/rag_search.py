import re
import time
import os.path as p
from difflib import SequenceMatcher

from ..utils.tavily_search import tavily_search
from ..utils.state import State

# 검색 진행하고 점수 계산하여 유사도 높은 순으로 처리
def node_tool_search(state: State) -> State:
    """
    외부 검색 노드
    - slide_index 기반으로 title/text/table/image를 읽음
    - 질의 생성 후 tavily_search_test 호출
    - 결과를 state['external_content']에 저장
    """
    state["external_content"] = {"queries": [], "summaries": [], "references": []}  # 초기화

    print("---페이지 분해 state 결과---")
    print(f"{state}")

    idx = state.get("slide_index", 0)
    titles = state.get("titles", [])
    texts_all = state.get("texts", [])
    tables_all = state.get("tables", [])
    images_all = state.get("images", [])

    title = titles[idx] if idx < len(titles) else ""
    texts = texts_all[idx] if idx < len(texts_all) else ""
    tables = tables_all[idx] if idx < len(tables_all) else []
    images = images_all[idx] if idx < len(images_all) else []

    print(f"idx : {idx}")
    print(f"title : {title}")
    print(f"texts : {texts}")
    print(f"tables : {tables}")
    print(f"images : {images}")

    # ---------- 1) 질의 생성 ----------
    queries: list[dict] = []
    if title:
        queries.append({"text": title, "context": "title"})
    if title and texts:
        queries.append({"text": f"{title} {texts[:80]}", "context": "title+text"})
    if title and tables and tables[0] and tables[0][0]:
        head = " ".join(map(str, tables[0][0][:5]))
        queries.append({"text": f"{title} {head}", "context": "title+table"})
    if title and images:
        names = " ".join([p.splitext(p.basename(x))[0] for x in images[:2]])
        queries.append({"text": f"{title} {names}", "context": "title+image"})
    if not queries and texts:
        queries.append({"text": texts[:100], "context": "text_only"})

    print(f"질의 생성 : {queries}")

    # ---------- 2) 검색 수행 (tavily_search_test 사용) ----------
    all_results: list[dict] = []

    for q in queries:
        q_text = q["text"]
        print(f"질문 내용 : {q_text}")

        results = tavily_search(q_text, num=4)   # 이미 score 포함
        all_results.extend(results)
        time.sleep(0.2)

    # ---------- 3) 일관성/신뢰도 필터 ----------
    def norm(s: str) -> str:
        s = (s or "").lower().strip()
        s = re.sub(r"\s+", " ", s)
        return s

    def similar(a: str, b: str, thr: float = 0.82) -> bool:
        return bool(a and b) and SequenceMatcher(None, norm(a), norm(b)).ratio() >= thr

    groups = []  # 각 그룹: {"rep": str, "items": [dict], "domains": set}
    for r in all_results:
        snip, dom = r.get("snippet", ""), r.get("domain", "")
        if not snip:
            continue
        placed = False
        for g in groups:
            if similar(snip, g["rep"]):
                g["items"].append(r)
                if dom:
                    g["domains"].add(dom)
                placed = True
                break
        if not placed:
            groups.append({
                "rep": snip,
                "items": [r],
                "domains": set([dom] if dom else []),
            })

    picked = [g for g in groups if len(g["items"]) >= 2 and len(g["domains"]) >= 2]

    if not picked:
        # 폴백: 그냥 전체 결과를 summaries / references로 사용
        summaries = [
            {
                "text":   r["snippet"],
                "source": r["title"],
                "score":  r.get("score", 0.0),
            }
            for r in all_results if r.get("snippet")
        ]
        references = [
            {
                "title": r["title"],
                "url":   r["url"],
                "score": r.get("score", 0.0),
            }
            for r in all_results
        ]
    else:
        summaries: list[dict] = []
        references: list[dict] = []
        seen_dom: set[str] = set()

        # 그룹별 대표 score (그룹 내 max score) 기준으로 정렬
        picked.sort(
            key=lambda g: max((it.get("score", 0.0) for it in g["items"]), default=0.0),
            reverse=True,
        )

        for g in picked:
            # 그룹 내에서 score 가장 높은 아이템 선택
            top = max(g["items"], key=lambda it: it.get("score", 0.0))

            summaries.append({
                "text": top.get("snippet", ""),
                "source": top.get("title", ""),
                "score": top.get("score", 0.0),
            })

            # 그룹 내 도메인별 대표 레퍼런스 1개씩 선택
            dom_pick = {}
            for item in g["items"]:
                domain = item.get("domain")
                if domain and domain not in dom_pick:
                    dom_pick[domain] = {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "score": item.get("score", 0.0),
                    }

            for domain, ref in dom_pick.items():
                if domain not in seen_dom:
                    seen_dom.add(domain)
                    references.append(ref)

    # score 기준으로 summaries / references 전역 정렬 (안 해도 되지만 깔끔하게)
    summaries.sort(key=lambda s: s.get("score", 0.0), reverse=True)
    references.sort(key=lambda r: r.get("score", 0.0), reverse=True)

    # ---------- 4) 결과 state에 저장 ----------
    state["external_content"] = {
        "queries": queries,
        "summaries": summaries,
        "references": references,
    }
    return state
