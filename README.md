## 📘 Project Overview

PowerPoint(PPTX) 파일 하나만 입력하면, 강의 제작에 필요한 전 과정을 자동화하여 <br>
**강의 영상·음성·요약·퀴즈까지 생성하는 End-to-End 파이프라인**입니다.

### 🔧 이 시스템은 아래 작업을 자동으로 수행합니다

- 🖼️ **슬라이드 이미지 추출** (PPT → PNG 변환)  
- 🔍 **슬라이드 콘텐츠 파싱** (텍스트 · 도형 · 표 · 이미지 분석)  
- 🧠 **LLM 기반 슬라이드 요약 생성**  
- 🗣️ **강의용 자연스러운 스크립트 생성**  
- 🎤 **OpenAI TTS 음성 생성**  
- 🎬 **슬라이드 이미지 + 음성 결합 mp4 강의 영상 생성** (FFmpeg)  
- ❓ **전체 강의 기반 객관식 퀴즈 자동 생성**  

### 📦 PPT 한 개만 입력하면 다음 결과물을 자동으로 생성합니다

- 📄 **강의 요약 문서**  
- 🎤 **강사의 음성(TTS)**  
- 📺 **슬라이드 기반 강의 영상(mp4)**  
- ❓ **학습자 평가용 객관식 퀴즈 세트**

AI 기반 자동화를 통해 **강의 제작 시간을 크게 줄이면서도**,  
누구나 손쉽게 고품질 교육 콘텐츠를 만들 수 있도록 설계된 프로젝트입니다.

## 🛠️ Tech Stack
| Category                   | Technology                                                              |
| -------------------------- | ----------------------------------------------------------------------- |
| **Language**               | Python 3                                                                |
| **AI / LLM**               | OpenAI Chat Models (gpt-4o-mini), OpenAI TTS                            |
| **Search & RAG**           | Tavily API · Custom Scoring (Similarity · Domain Trust · Content Score) |
| **PPT Processing**         | python-pptx · LibreOffice · Poppler(pdftoppm)                           |
| **Audio / Video**          | FFmpeg · ffprobe                                                        |
| **Pipeline Orchestration** | LangChain · LangGraph                                                   |
| **Utilities**              | Pillow · NumPy · python-dotenv                                          |


## 📂 폴더 구조 (Folder Structure)
```
ai_lecture-generator/
│
├── main.py                     # 전체 파이프라인 실행 엔트리
├── requirements.txt            # Python 패키지 의존성
├── sample.pptx                 # 데모용 PPT 파일
├── write.ipynb                 # 개발/테스트용 Jupyter Notebook
│
└── src/
    ├── nodes/                  # 파이프라인 각 단계를 처리하는 Node 모듈
    │   ├── parse_slides.py         # PPT → 텍스트/표/도형/이미지 파싱
    │   ├── rag_search.py           # Tavily 검색 + 점수 기반 RAG 보강
    │   ├── gen_page_content.py     # LLM 기반 슬라이드 요약 생성
    │   ├── gen_script.py           # 강의 말하기 스크립트 생성
    │   ├── tts.py                  # 슬라이드별 TTS 음성 생성
    │   ├── make_video.py           # TTS + 슬라이드 이미지 → mp4 영상 생성
    │   ├── concat_video.py         # 개별 mp4 영상 → 전체 강의 영상 병합
    │   ├── make_quiz.py            # 전체 강의 기반 객관식 퀴즈 자동 생성
    │   ├── accumulate_step.py      # 영상 경로 누적 및 슬라이드 index 증가
    │   ├── router.py               # 다음 슬라이드 진행 / 종료 판별
    │
    │
    ├── utils/                  # Node들을 지원하는 유틸리티 모듈
    │   ├── slides_as_png.py        # LibreOffice + Poppler → 슬라이드 PNG 변환
    │   ├── tavily_search.py        # Tavily API 검색 래퍼
    │   ├── search_score.py         # 검색 결과 유사도/도메인 신뢰도/내용 점수 계산
    │   ├── split_chunk.py          # 외부 검색 요약 chunk 처리
    │   ├── tts_generate.py         # OpenAI TTS + FFmpeg 속도 조절
    │   ├── utils.py                # 텍스트/이미지/ffprobe 공통 유틸리티
    │   ├── state.py                # LangGraph 상태(State) 정의 및 관리
    
```
## 🚀 How to Run (실행 방법)

### 🚀 1. 저장소 클론
```
!git clone https://github.com/uh004/ai_lecture-generator.git
%cd ai_lecture-generator
```

### 🔑 2. 환경 변수(.env) 설정
```
%%writefile .env
OPENAI_API_KEY=api_key입력
TAVILY_API_KEY=api_key입력
LLM_MODEL=gpt-4o-mini
TTS_MODEL=gpt-4o-mini-tts
```

※ 위 명령 실행 후 .env 파일이 생성되면 직접 API KEY를 입력하세요.
- tavily_api ---> https://www.tavily.com/
- openai_api ---> https://openai.com/ko-KR/index/openai-api/

### 🛠️ 3. 시스템 패키지 설치

(PPT → PNG 변환 + FFmpeg + LibreOffice + 폰트 필수)
```
!apt-get -y update
!apt-get -y install ffmpeg libreoffice poppler-utils poppler-data locales \
                   fonts-noto-cjk fonts-noto-cjk-extra fonts-nanum fonts-unfonts-core
!apt-get -y install libreoffice-impress libreoffice-common
!sed -i 's/^# *ko_KR.UTF-8 UTF-8/ko_KR.UTF-8 UTF-8/' /etc/locale.gen
!locale-gen ko_KR.UTF-8
!update-locale LANG=ko_KR.UTF-8
!fc-cache -fv
```

### 📝 4. 한국어 폰트 설정
```
%%bash
mkdir -p ~/.config/fontconfig
cat > ~/.config/fontconfig/fonts.conf <<'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <match target="pattern">
    <test name="lang" compare="eq"><string>ko</string></test>
    <edit name="family" mode="prepend" binding="strong">
      <string>Noto Sans CJK KR</string>
    </edit>
  </match>
</fontconfig>
EOF
fc-cache -fv
```

### 📦 5. Python 패키지 설치
```
!pip install -r requirements.txt
```

### ▶️ 6. 실행
```
!python main.py
```
---> sample.pptx 다운받아서 사용

### 📌 참고사항
```
이 실행 가이드는 **Google Colab 환경에서 실행하는 것을 기준**으로 작성되었습니다.  
Colab은 매번 런타임이 초기화되기 때문에,  
PPT 변환(LibreOffice), FFmpeg, 한국어 폰트 등 시스템 패키지를  매 실행마다 설치해야 합니다.

로컬 환경(Ubuntu/Mac)에서도 실행 가능하지만, 필요한 패키지는 직접 설치해야 합니다.
```


