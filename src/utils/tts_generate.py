import os
import subprocess
import shutil
from openai import OpenAI
from langchain_core.runnables import RunnableLambda
from dotenv import load_dotenv

from ..utils.utils import ffprobe_duration

load_dotenv()

TTS_MODEL = os.getenv("TTS_MODEL")
# TTS_MODEL = "gpt-4o-mini-tts"
client = OpenAI()
# tts 1
def tts_generate(
    script: str,
    work_dir: str,
    slide_idx: int,
    voice_preset: str = "부드러운 설명형",
    speed: float = 0.9,
) -> tuple[str, float | None]:
    """
    실제 OpenAI TTS를 호출하고 mp3 파일을 생성하는 순수 함수.
    - 반환: (최종 파일 경로, duration초 or None)
    """

    # "-" 뒤의 음성 이름 추출 (있으면) 또는 기본값 "nova"
    voice = voice_preset.split("-")[-1].strip()
    
    # OpenAI TTS에서 지원하는 유효한 음성인지 검증
    valid_voices = {"nova", "alloy", "shimmer", "onyx", "fable", "verse", "coral"}
    if voice not in valid_voices:
        print(f"[경고] '{voice}'는 지원하지 않는 음성입니다. 'nova'로 대체합니다.")
        voice = "nova"

    # ------------------------------
    # 속도 검증 (OpenAI + ffmpeg atempo 권장 범위)
    # ------------------------------
    try:
        speed = float(speed)
    except Exception:
        speed = 0.9

    # ffmpeg atempo는 0.5~2.0 권장
    if speed < 0.5:
        speed = 0.5
    elif speed > 2.0:
        speed = 2.0

    # ------------------------------
    # script 비었을 때 기본 문구
    # ------------------------------
    script = (script or "").strip()
    if not script:
        script = (
            "현재 슬라이드에는 설명할 내용이 준비되어 있지 않습니다. "
            "다음 슬라이드를 함께 살펴보겠습니다."
        )

    # 너무 긴 스크립트 방어용 (TTS 입력 길이 제한 대비)
    MAX_SCRIPT_CHARS = 4000
    if len(script) > MAX_SCRIPT_CHARS:
        script = script[:MAX_SCRIPT_CHARS] + " ..."

    # ------------------------------
    # 저장 경로
    # ------------------------------
    os.makedirs(work_dir, exist_ok=True)
    raw_path = os.path.join(work_dir, f"tts_raw_slide{slide_idx}.mp3")
    final_path = os.path.join(work_dir, f"tts_slide{slide_idx}_{speed}x.mp3")

    # ------------------------------
    # TTS 호출
    # ------------------------------
    try:
        print(f"[TTS] 교육용 보이스('{voice}')로 음성 생성 중...")
        response = client.audio.speech.create(
            model=TTS_MODEL,
            voice=voice,
            input=script,
            response_format="mp3",
        )
    except Exception as e:
        print("[오류] TTS 생성 실패:", e)
        print("[재시도] 기본 보이스 'nova'로 재생성 시도합니다.")
        response = client.audio.speech.create(
            model=TTS_MODEL,
            voice="nova",
            input=script,
            response_format="mp3",
        )

    with open(raw_path, "wb") as f:
        # 최신 openai SDK 기준: .to_bytes() / .read() 둘 다 케이스 있음
        data = getattr(response, "to_bytes", None)
        if callable(data):
            f.write(response.to_bytes())
        else:
            f.write(response.read())

    # ------------------------------
    # FFmpeg 속도 조절
    # ------------------------------
    if speed != 0.9 and shutil.which("ffmpeg"):
        print(f"[FFmpeg] {speed}배속 변환 중...")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            raw_path,
            "-filter:a",
            f"atempo={speed}",
            final_path,
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        final_path = raw_path

    # ------------------------------
    # duration 측정
    # ------------------------------
    try:
        duration = ffprobe_duration(final_path)
        print(f"[TTS] 최종 오디오 길이: {round(duration, 2)}초")
    except Exception:
        duration = None
        print("[경고] 오디오 길이를 계산할 수 없습니다.")

    return final_path, duration


# LangChain Runnable로 감싼 버전 (원하면 LangGraph에서 바로 쓸 수 있음)
tts_runnable = RunnableLambda(
    lambda args: tts_generate(
        script=args["script"],
        work_dir=args["work_dir"],
        slide_idx=args["slide_idx"],
        voice_preset=args.get("voice_preset", "부드러운 설명형"),
        speed=args.get("speed", 1.0),
    )
)
