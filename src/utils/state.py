from typing import TypedDict, Dict, List, Any

class State(TypedDict, total=False): # total=False는 TypedDict에서 모든 키를 선택(optional)으로 취급
    # 입력/기본
    pptx_path: str
    work_dir: str
    prompt: Dict  # -> 내부 speed, + 변경 : voice 후보
    slide_index: int
    slides: List[Dict[str, Any]]
    total_slides: int

    # 추출 산출물
    titles: List[str]
    texts: List[str]
    tables: List[List[List[str]]]
    images: List[str]
    slide_image: List[str]
    external_content: Dict[str, List[Dict[str, str]]] # (외부 지식)
    slide_image: List[str]
    shape_texts: List[List[str]]
    links: List[List[str]]

    # 생성 산출물
    page_content: str
    script: str
    all_scripts: List[str] # 퀴즈 노드를 위해 스크립트 저장
    quiz_set: List[Dict[str, Any]] # 퀴즈 노드가 생성한 퀴즈 -> 수정: List[Dict[str, Any]]

    # 미디어 산출물
    audio: str
    video_path: List[str] # 변경 : str -> List[str]

    video_paths: List[str] # 생성된 영상 path 리스트
    final_video: str # 최종 합쳐진 영상 path