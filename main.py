
import os

from langgraph.graph import StateGraph, END
from src.utils.state import State
import gradio as gr

from src.nodes.parse_slides import node_parse_all
from src.nodes.rag_search import node_tool_search
from src.nodes.gen_page_content import node_generate_page_content
from src.nodes.gen_script import node_generate_script
from src.nodes.tts import node_tts
from src.nodes.make_video import node_make_video
from src.nodes.accumulate_step import node_accumulate_and_step
from src.nodes.concat_video import node_concat
from src.nodes.make_quiz import node_generate_quiz
from src.nodes.router  import router_continue_or_done

# 출력 dir 만들기
WORK_DIR = "./gradio_output/"
MEDIA_DIR = os.path.join(WORK_DIR, "media")
SLIDES_DIR = os.path.join(WORK_DIR, "slides")

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(SLIDES_DIR, exist_ok=True)

builder = StateGraph(State)

# ---- 노드 등록 ----
builder.add_node("parse_ppt", node_parse_all)
builder.add_node("tool_search", node_tool_search)
builder.add_node("gen_page_content", node_generate_page_content)
builder.add_node("gen_script", node_generate_script)
builder.add_node("tts", node_tts)
builder.add_node("make_video", node_make_video)
builder.add_node("accumulate", node_accumulate_and_step)
builder.add_node("concat", node_concat)
builder.add_node("make_quiz", node_generate_quiz)

# ---- 기본 흐름 연결 ----
builder.set_entry_point("parse_ppt")

builder.add_edge("parse_ppt", "tool_search")
builder.add_edge("tool_search", "gen_page_content")
builder.add_edge("gen_page_content", "gen_script")
builder.add_edge("gen_script", "tts")
builder.add_edge("tts", "make_video")
builder.add_edge("make_video", "accumulate")

# 조건 분기 라우터 등록
builder.add_conditional_edges(
    "accumulate",                    # 분기 기준 노드
    router_continue_or_done,         # 실행될 조건 함수
    {                                # 반환값에 따라 이동할 노드 지정
        "continue": "tool_search",   # 남은 슬라이드가 있을 때
        "done": "concat"             # 모든 슬라이드 완료 시
    }
)

builder.add_edge("concat", "make_quiz")
builder.add_edge("make_quiz", END)
# builder.add_edge("concat", "make_quiz")
# builder.add_edge("make_quiz", END)

# ---- 그래프 컴파일 ----
app = builder.compile()

def generate_state_and_run(pptx_file, tone, voice, style, target_duration_sec, speed):

    pptx_path = pptx_file
    USER_PROMPT = {
        "tone": tone,
        "voice": voice,
        "style": style,
        "target_duration_sec": int(target_duration_sec),
        "speed": float(speed)
    }

    state = {
        "pptx_path": pptx_path,
        "work_dir": WORK_DIR,
        # "work_dir": work_dir,
        "prompt": USER_PROMPT
    }

    # 실제 Agent 그래프(app) 실행
    state = app.invoke(state, config={"recursion_limit": 200})

    final_video = state.get("final_video", "")
    quiz_set = state.get("quiz_set", {})

    return final_video, final_video, quiz_set


# ===============================
# 🔹 복습 퀴즈 표시 함수
# ===============================
def display_quizzes(quiz_set):
    quizzes = get_quiz_list(quiz_set)

    if not quizzes:
        return "❌ 생성된 퀴즈가 없습니다."

    md = "## 🧠 복습 퀴즈\n\n"
    for i, q in enumerate(quizzes, 1):
        md += f"**Q{i}. {q['question']}**\n"
        for opt in q["options"]:
            md += f"- {opt}\n"
        md += "\n"
    return md


# ===============================
# 🔹 정답 표시 함수
# ===============================
def display_answers(quiz_set):
    """정답 보기 버튼 클릭 시 표시"""
    quizzes = get_quiz_list(quiz_set)

    if not quizzes:
        return "❌ 퀴즈 데이터가 없습니다."

    md = "## ✅ 정답 보기\n\n"
    for i, q in enumerate(quizzes, 1):
        md += f"**Q{i}.** {q['answer']}\n"
    return md


# ===============================
# 🔹 퀴즈 내용 전처리 함수
# ===============================
def get_quiz_list(quiz_set):
    if not quiz_set:
        return []
    if isinstance(quiz_set, dict) and "quiz" in quiz_set:
        qs = quiz_set["quiz"]
    else:
        qs = quiz_set
    if isinstance(qs, list):
        return [q for q in qs if isinstance(q, dict)]
    return []


# ===============================
# 🔹 개별 문제 불러오기 함수
# ===============================
def load_quiz_question(quiz_set, index):
    quizzes = get_quiz_list(quiz_set)

    if not quizzes:
        # 보기 리스트도 같이 초기화
        return (
            "❌ 퀴즈가 없습니다. 먼저 실행 버튼으로 퀴즈를 생성해 주세요.",
            gr.update(choices=["(문제를 먼저 불러오세요)"], value=None),
        )

    # index → 0-based 변환
    try:
        idx = int(index) - 1
    except:
        idx = 0

    if idx < 0:
        idx = 0
    if idx >= len(quizzes):
        idx = len(quizzes) - 1

    q = quizzes[idx]

    question_text = f"Q{idx + 1}. {q['question']}"
    options = q["options"]  # ['1. ...', '2. ...', '3. ...', '4. ...']

    return question_text, gr.update(choices=options, value=None)

def load_quiz_question_with_reset(quiz_set, index):
    question, options = load_quiz_question(quiz_set, index)
    return question, options, ""

# ===============================
# 🔹 정답 체크 함수
# ===============================
def check_quiz_answer(quiz_set, index, user_answer):
    quizzes = get_quiz_list(quiz_set)

    if not quizzes:
        return "❌ 퀴즈가 없습니다. 먼저 실행 버튼으로 퀴즈를 생성해 주세요."

    # index → 0-based
    try:
        idx = int(index) - 1
    except:
        idx = 0

    idx = max(0, min(idx, len(quizzes) - 1))

    q = quizzes[idx]
    correct = q["answer"]   # 예: "2"

    if not user_answer:
        return "❗ 먼저 보기를 하나 선택해 주세요."

    # 🔥 사용자가 선택한 보기에서 번호만 추출
    selected_number = user_answer.split(".")[0].strip()  # "2. 텍스트" → "2"

    # 🔥 번호만 비교
    if selected_number == correct:
        return (
            f"✅ 정답입니다!\n\n"
            f"정답: {correct}번\n\n"
            f"해설: {q.get('explanation', '해설이 제공되지 않았습니다.')}"
        )
    else:
        return (
            f"❌ 오답입니다.\n\n"
            f"선택한 답: {selected_number}번\n"
            f"정답: {correct}번"
        )


# ===============================
# 🔹 Gradio 인터페이스
# ===============================
tone_choices = [
    "친절하고 명료한 강의 톤",
    "열정적이고 에너지 넘치는 발표 톤",
    "차분하고 신뢰감 있는 설명 톤",
    "격식 있고 전문적인 톤"
]

voice_choices = [
    "기본 설명형 -nova",
    "교육·온라인 수업용 -alloy",
    "감정 전달 중심 -fable",
    "기술 세미나용 -onyx",
    "홍보·SNS용 -verse",
    "명상·상담용 -coral"
]

style_choices = [
    "예시와 핵심 요점 중심",
    "스토리텔링 중심",
    "데이터 기반 설명",
    "감정과 공감 중심"
]


with gr.Blocks(theme="soft", title="🎬 AI 슬라이드 강의 생성기") as demo:
    gr.Markdown("## 🎬 AI 슬라이드 강의 생성기")
    gr.Markdown("PPTX를 업로드하고, 말투·목소리·스타일·속도를 선택한 뒤 **실행**을 누르면 AI가 자동으로 강의 영상을 생성합니다.")

    # 입력 영역
    with gr.Row():
        inp_ppt = gr.File(label="🎞️ PPTX 파일 업로드", file_types=[".pptx"], type="filepath")

    with gr.Row():
        inp_tone  = gr.Radio(label="🗣️ 말투 (tone)", choices=tone_choices, value="친절하고 명료한 강의 톤")
        inp_voice = gr.Radio(label="🎤 목소리 (voice)", choices=voice_choices, value="기본 설명형 -nova")

    with gr.Row():
        inp_style = gr.Radio(label="🧩 스타일 (style)", choices=style_choices, value="예시와 핵심 요점 중심")
        inp_duration = gr.Number(label="📄 페이지 당 몇 초 분량", value=60, precision=0)
        inp_speed = gr.Slider(
            label="🎚️ 음성 속도 (Speed)",
            minimum=0.8,
            maximum=2.0,
            step=0.1,
            value=1.0,
            info="음성 재생 속도를 조절하세요 (0.8x~2.0x)"
        )

    run_btn = gr.Button("🚀 실행", variant="primary")

    # 출력 구역
    with gr.Row():
        out_video = gr.Video(label="📽️ 최종 동영상 미리보기", interactive=False)

    out_download = gr.DownloadButton(label="💾 동영상 다운로드")

    # 🔹 인터랙티브 퀴즈 영역 (문제 1개씩 풀기)
    gr.Markdown("### 🎯 인터랙티브 퀴즈 (문제별 선택)")

    with gr.Row():
        quiz_index = gr.Number(
            label="문제 번호",
            value=1,
            precision=0,
            interactive=True,
            minimum=1,
            maximum=10
        )
        load_quiz_btn = gr.Button("📥 이 번호의 문제 불러오기")

    current_question_md = gr.Markdown(label="현재 문제", value="(문제를 불러오세요)")
    current_options_radio = gr.Radio(
        label="보기 선택",
        choices=["(문제를 먼저 불러오세요)"],  # 기본 더미 choice
        value=None,                            # 초기값은 None
        interactive=True
    )

    check_btn = gr.Button("✅ 이 문제 정답 확인")
    check_result_md = gr.Markdown(label="결과", value="(정답 여부가 여기에 표시됩니다.)")

    # 내부 상태 저장용
    quiz_state = gr.State([])

    # 버튼 연결
    run_btn.click(
        fn=generate_state_and_run,
        inputs=[inp_ppt, inp_tone, inp_voice, inp_style, inp_duration, inp_speed],
        outputs=[out_video, out_download, quiz_state]
    )

    # 🔹 "문제 불러오기" 버튼 → 선택한 번호의 문제 + 보기 표시
    load_quiz_btn.click(
    fn=load_quiz_question_with_reset,
    inputs=[quiz_state, quiz_index],
    outputs=[current_question_md, current_options_radio, check_result_md]
    )

    # 🔹 "정답 확인" 버튼 → 사용자가 선택한 보기 기준으로 정답/오답 피드백
    check_btn.click(
        fn=check_quiz_answer,
        inputs=[quiz_state, quiz_index, current_options_radio],
        outputs=[check_result_md]
    )


demo.launch(share=True)
