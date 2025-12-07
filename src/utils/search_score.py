import re
from difflib import SequenceMatcher

# 점수 계산하여 유사도가 높은 것으로 검색
# 도메인 신뢰도 테이블
DOMAIN_TRUST = {
    # 공식 문서 / 레퍼런스 계열
    "microsoft.com": 0.95,
    "learn.microsoft.com": 0.98,
    "docs.python.org": 0.98,
    "wikipedia.org": 0.9,
    "mozilla.org": 0.9,

    # 국내 포털/뉴스/기술 문서 예시 (원하는대로 추가)
    "naver.com": 0.8,
    "cloud.naver.com": 0.9,
    "daum.net": 0.75,
    "kakao.com": 0.8,
    "tech.ebay.com": 0.85,
}

def _norm_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^가-힣a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def similarity_score(query: str, snippet: str) -> float:
    """
    질의(title)와 snippet 간의 간단한 유사도 점수 [0,1]
    - 토큰 교집합 비율 + SequenceMatcher를 섞어서 사용
    """
    q = _norm_text(query)
    t = _norm_text(snippet)
    if not q or not t:
        return 0.0

    q_tokens = set(q.split())
    t_tokens = set(t.split())
    if not q_tokens or not t_tokens:
        overlap = 0.0
    else:
        overlap = len(q_tokens & t_tokens) / len(q_tokens)

    seq_sim = SequenceMatcher(None, q, t).ratio()
    # 단순 평균
    return (overlap + seq_sim) / 2.0

def domain_score(domain: str) -> float:
    """
    출처(domain) 신뢰도 점수 [0,1]
    - DOMAIN_TRUST에 있으면 높은 점수
    - 없으면 기본 0.5에서 도메인 길이에 따라 살짝 조정 (예시)
    """
    domain = (domain or "").lower()
    for key, score in DOMAIN_TRUST.items():
        if key in domain:
            return score

    if not domain:
        return 0.4

    # 서브도메인까지 포함된 전체 길이를 기준으로 적당히 0.45~0.65 사이 할당
    base = 0.5
    adj = min(len(domain) / 50.0, 0.15)  # 길면 약간 더 신뢰
    return max(0.45, min(base + adj, 0.65))

def content_score(snippet: str, max_len: int = 400) -> float:
    """
    내용 충실도 점수 [0,1]
    - snippet 길이를 기준으로 간단히 계산
    - max_len 이상이면 1.0, 그 이하면 비례해서 증가
    """
    if not snippet:
        return 0.0
    n = len(snippet)
    return max(0.1, min(n / max_len, 1.0))  # 너무 짧으면 최소 0.1
