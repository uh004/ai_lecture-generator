import os
import subprocess

from ..utils.utils import ffprobe_duration
from ..utils.state import State

def node_make_video(state: State) -> State:
    """
    Node 6. 슬라이드 영상 생성 (교육용 강의 버전)
    - 슬라이드 PNG 이미지 + TTS 음성을 결합하여 1장의 mp4 클립 생성
    - 음성 길이(duration)를 기반으로 정확한 영상 길이를 맞춤
    - 교육용 강의 영상 스타일(정지 이미지 + 부드러운 화면 구성)에 최적화
    - 음성 길이(duration)에 1~2초 여유를 더해 영상 길이를 맞춤
    """

    print("\n--- Node 6: 슬라이드 영상 생성(make_video) 실행 ---")

    slide_imgs = state.get("slide_image", [])
    audio_path = state.get("audio", "")
    work_dir = state.get("work_dir", "./")
    slide_index = int(state.get("slide_index", 0))

    # -------------------------------
    # 1) 입력 검증
    # -------------------------------
    if not slide_imgs or slide_index >= len(slide_imgs):
        print(f"[경고] 슬라이드 이미지 없음 → index={slide_index}")
        return state

    if not os.path.exists(audio_path):
        print(f"[경고] 오디오 파일 없음 → {audio_path}")
        return state

    image_path = slide_imgs[slide_index]

    if not os.path.exists(image_path):
        print(f"[경고] 이미지 파일 없음 → {image_path}")
        return state

    # -------------------------------
    # 2) 저장 디렉토리 준비
    # -------------------------------
    os.makedirs(work_dir, exist_ok=True)

    # 개별 영상 파일명
    out_mp4 = os.path.join(work_dir, f"slide{slide_index+1}_lecture.mp4")

    # -------------------------------
    # 3) 음성 길이(duration) 구하기
    # -------------------------------
    try:
        duration = ffprobe_duration(audio_path)
    except:
        print("[경고] ffprobe 실패 → 기본 5초로 설정")
        duration = 5

    prompt = state.get("prompt", {}) or {}
    padding_sec = float(prompt.get("tts_padding_sec", 1.5))

    total_duration = max(duration + padding_sec, 0.5)  # 최소 0.5초 방어

    # -------------------------------
    # 4) FFmpeg 렌더링 명령 구성
    # -------------------------------
    # 교육용 영상 규칙:
    # - 이미지는 loop(정지 이미지)
    # - 전체 해상도 1920×1080 (padding 포함)
    # - 음성 길이에 맞춰 영상 길이 정확히 맞춤
    # - 모든 플레이어 호환: libx264 + yuv420p

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",                # 기존 파일 덮어쓰기
        "-loop", "1",        # 이미지 loop
        "-i", image_path,    # 이미지 입력
        "-i", audio_path,    # 오디오 입력
        "-t", str(total_duration), # 영상 길이 = 오디오 길이
        "-vf",
        (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"
        ),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        out_mp4
    ]

    print(f"[FFmpeg] 슬라이드 {slide_index+1} 렌더링 중...")

    # -------------------------------
    # 5) FFmpeg 실행 + 예외 처리
    # -------------------------------
    result = subprocess.run(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        print("[오류] FFmpeg 렌더링 실패 → 1회 재시도")
        print(result.stderr.decode())

        retry = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if retry.returncode != 0:
            print("[치명] 영상 생성 실패. 해당 슬라이드를 건너뜁니다.")
            return state

    # -------------------------------
    # 6) state에 저장
    # -------------------------------
    # if "video_path" not in state:
    #     state["video_path"] = []

    # if out_mp4 not in state["video_path"]:
    #     state["video_path"].append(out_mp4)
    state["video_path"] = out_mp4

    print(f"[완료] 영상 생성 → {out_mp4}")

    return state