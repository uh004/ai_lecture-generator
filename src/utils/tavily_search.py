import os
from urllib.parse import urlparse
from tavily import TavilyClient
from langchain_community.tools.tavily_search import TavilySearchResults

from ..utils.search_score import domain_score 
from ..utils.search_score import similarity_score
from ..utils.search_score import content_score

# tavily로 검색 진행
def tavily_search(title: str, num: int = 4) -> list[dict]:
    key = os.getenv("TAVILY_API_KEY")
    tavily_client = TavilyClient(api_key=key)

    # 제외할 도메인 리스트 -> 신뢰성이 떨어지는 리스트
    EXCLUDE_DOMAINS = [
        "blog.naver.com", "m.blog.naver.com", "tistory.com",
        "brunch.co.kr", "medium.com", "velog.io",
        "kin.naver.com", "reddit.com", "youtube.com"
    ]

    # Tavily에 보낼 실제 쿼리 (제외 도메인까지 포함)
    query = f"{title} " + " ".join([f"-site:{d}" for d in EXCLUDE_DOMAINS])

    # 후보 개수를 num보다 넉넉하게 받아서 그 중 Top-N만 필터링
    candidate_k = max(num * 3, num + 2)

    res_tool = TavilySearchResults(
        max_results=candidate_k,
        search_depth="basic",
        topic="general",
        exclude_domains=EXCLUDE_DOMAINS,
        include_answer=False,
        include_raw_content=False,
    )

    data = res_tool.invoke(query) or []

    results: list[dict] = []
    seen_urls: set[str] = set()

    for item in data:
        url = item.get("url", "")
        if not url:
            continue

        domain = urlparse(url).netloc

        # 제외할 도메인 필터링 (한 번 더 방어적으로)
        if any(ex in domain for ex in EXCLUDE_DOMAINS):
            continue

        # 중복 URL 제거
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title_res   = item.get("title", "") or ""
        snippet_res = item.get("content", "") or ""

        # 1) 유사도 점수
        s_sim = similarity_score(title, snippet_res)

        # 2) 도메인 신뢰도 점수
        s_dom = domain_score(domain)

        # 3) 내용 충실도 점수
        s_cont = content_score(snippet_res)

        # 4) 최종 점수 (가중 평균)
        # → 필요에 따라 가중치 조정 (기업용이면 정확도/도메인 비중↑)
        score = (
            0.5 * s_sim + # 질의와 얼마나 관련 있는지
            0.3 * s_dom + # 출처 신뢰도
            0.2 * s_cont  # 내용 충실도
        )

        results.append({
            "title": title_res,
            "url": url,
            "snippet": snippet_res,
            "domain": domain,
            "score":round(score, 4),  # 보기 좋게 반올림
            "score_detail": {
                "similarity": round(s_sim, 4),
                "domain": round(s_dom, 4),
                "content": round(s_cont, 4),
            },
        })

    # 점수 기준으로 정렬 후 Top-N만 반환
    results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)
    print(results_sorted)
    return results_sorted[:num]
