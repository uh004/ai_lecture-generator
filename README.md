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
