from ..utils.tts_generate import tts_generate
from ..utils.state import State
def node_tts(state: State) -> State:
    """
    교육용 강의 스크립트를 TTS로 변환하는 함수.
    - 학생/수강생 대상 친절한 톤으로 읽기 좋은 음성을 생성
    - 기본 voice = 'nova' (설명형에 가장 적합)
    - 속도 = 1.0 (교육용 자연스러운 속도)
    """

    print("\n--- Node 5: 교육용 TTS 변환 실행 ---")

    # 입력
    script = (state.get("script", "") or "").strip()
    prompt = state.get("prompt", {}) or {}
    work_dir = state.get("work_dir", "./")
    slide_idx = int(state.get("slide_index", 0))

    # Voice preset 처리
    # raw_voice = prompt.get("voice", "부드러운 설명형")
    raw_voice = prompt.get("voice") or "기본 설명형 -nova"
    voice = raw_voice.split('-')[-1].strip()
    # speed_val = prompt.get("speed", 1.0)
    speed_val = float(prompt.get("speed", 1.0))

    # LangChain Runnable 호출 (또는 tts_generate 직접 호출해도 됨)
    result_path, duration = tts_generate(
        script=script,
        work_dir=work_dir,
        slide_idx=slide_idx,
        voice_preset=voice,
        speed=speed_val,
    )

    # ------------------------------
    # state 저장
    # ------------------------------
    state["audio"] = result_path
    state.setdefault("audio_paths", []).append(result_path)

    if duration is not None:
        state.setdefault("audio_meta", {})
        state["audio_meta"][slide_idx] = {
            "path": result_path,
            "duration": float(duration),
        }

    print(f"[완료] 교육용 음성 파일 저장 → {result_path}\n")

    return state
