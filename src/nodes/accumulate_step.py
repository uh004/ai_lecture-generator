import os
from ..utils.state import State

def node_accumulate_and_step(state: State) -> State:
    """
    Node 7. accumulate_and_step
    - 현재 슬라이드의 영상(mp4)을 video_paths에 누적
    - 다음 슬라이드 index로 이동
    - 실패한 슬라이드 기록
    """

    current_idx = state.get("slide_index", 0)
    total = state.get("total_slides", 1)
    current_video = state.get("video_path", None) # 이번 슬라이드 결과는 단일 파일로 받는다

    # 누적 리스트 초기화
    if "video_paths" not in state or not isinstance(state["video_paths"], list):
        state["video_paths"] = []

    # 1) 영상 존재 확인 후 누적
    if current_video and os.path.exists(current_video):
        if current_video not in state["video_paths"]:
            state["video_paths"].append(current_video)
        print(f"슬라이드 {current_idx+1} 완료 → {current_video}")

    else:
        print(f"슬라이드 {current_idx+1} 영상 생성 실패")
        state.setdefault("failed_slides", []).append(current_idx)

    # 2) 다음 슬라이드로 이동
    state["slide_index"] = current_idx + 1

    # 진행률 계산
    progress = (state["slide_index"] / total) * 100
    success = len(state["video_paths"])
    failed = len(state.get("failed_slides", []))

    print(f" 진행률: {state['slide_index']}/{total} ({progress:.1f}%)")
    print(f"   성공: {success} | 실패: {failed}")

    return state