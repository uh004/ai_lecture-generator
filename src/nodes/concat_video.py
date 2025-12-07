import os
import re
import subprocess

from ..utils.utils import ffprobe_duration
from ..utils.state import State

def node_concat(state: State) -> State:
    """
    Node 9. concat (안정적인 filter_complex 방식)
    - 모든 슬라이드 영상을 하나의 최종 강의 영상으로 합친다.
    """

    video_paths = state.get("video_paths", [])
    work_dir = state.get("work_dir", "./")

    if not video_paths:
        print("합칠 영상이 없습니다.")
        return state

    print(f"총 {len(video_paths)}개의 슬라이드 영상 병합 시작")

    # 무조건 정렬 (slide 번호 기준)
    video_paths = sorted(video_paths, key=lambda x: int(re.findall(r"slide(\d+)", x)[0]))

    # 최종 파일 경로
    final_video = os.path.join(work_dir, "final_lecture.mp4")

    # filter_complex input list 구성
    input_cmd = []
    filter_inputs = ""
    for i, path in enumerate(video_paths):
        input_cmd += ["-i", path]
        filter_inputs += f"[{i}:v][{i}:a]"

    filter_cmd = f"{filter_inputs}concat=n={len(video_paths)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y",
        *input_cmd,
        "-filter_complex", filter_cmd,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", # 웹 재생 최적화
        final_video
    ]

    print("FFmpeg 병합 중 (filter_complex concat 사용)...")

    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        print("[오류] 영상 병합 실패")
        print(result.stderr.decode())
        return state

    # 병합 완료 정보 출력
    duration = ffprobe_duration(final_video)
    size_mb = os.path.getsize(final_video) / (1024 * 1024)

    print(" 최종 강의 영상 생성 완료!")
    print(f" 경로: {final_video}")
    print(f" 총 재생 시간: {duration:.1f}초")
    print(f" 파일 크기: {size_mb:.2f} MB")

    state["final_video"] = final_video
    return state