from ..utils.state import State
def router_continue_or_done(state: State) -> str:
    """
    Node 8. router_continue_or_done
    - 현재 슬라이드가 마지막 슬라이드인지 확인
    - continue 이면 tool_search로 이동, done 이면 concat으로 이동
    """
    current = state.get("slide_index", 0)
    total = state.get("total_slides", 1)

    if current >= total:
        print("\n🎉 모든 슬라이드 처리 완료!")
        print(f"   성공: {len(state.get('video_paths', []))}")
        print(f"   실패: {len(state.get('failed_slides', []))}\n")
        return "done"

    print(f"\n➡️ 다음 슬라이드 처리 계속: {current}/{total}")
    return "continue"