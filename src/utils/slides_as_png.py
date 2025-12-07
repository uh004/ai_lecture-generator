import os
import shutil
import subprocess
from pathlib import Path
import src.utils.state as State

def export_slide_as_png(state: State, dpi: int = 220) -> dict:
    work_dir = Path(state["work_dir"]).expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    pptx = Path(state["pptx_path"]).expanduser().resolve()
    if not pptx.exists():
        raise FileNotFoundError(f"PPTX 없음: {pptx}")

    idx = int(state.get("slide_index", 0))  # 0-based
    page_no = idx + 1
    out_prefix = work_dir / "slide_img"

    env = os.environ.copy()
    env.update({
        "LANG": "ko_KR.UTF-8",
        "LC_ALL": "ko_KR.UTF-8",
    })

    # --- PPT → PDF (한 번만 변환) ---
    pdf_path = work_dir / f"{pptx.stem}.pdf"
    if not pdf_path.exists():
        soffice_bin = shutil.which("soffice") or shutil.which("libreoffice")
        print("[DEBUG] soffice_bin:", soffice_bin)

        if not soffice_bin:
            raise RuntimeError(
                "LibreOffice 'soffice' 실행 파일을 찾을 수 없습니다.\n"
                "런타임이 초기화되었거나 LibreOffice가 설치되지 않았습니다.\n"
                "예) apt-get install -y libreoffice-impress poppler-utils"
            )

        lo_cmd = [
            soffice_bin,
            "--headless",
            "-env:UserInstallation=file:///tmp/lo_profile",
            "--convert-to","pdf:impress_pdf_Export",
            "--outdir", str(work_dir),
            str(pptx),
        ]
        print("[DEBUG] lo_cmd:", lo_cmd)

        res_pdf = subprocess.run(lo_cmd, capture_output=True, text=True, env=env)
        if res_pdf.returncode != 0:
            print("LibreOffice 변환 실패")
            print("stdout:", res_pdf.stdout)
            print("stderr:", res_pdf.stderr)
            raise RuntimeError("PPTX → PDF 변환 실패")

    # --- PDF → PNG (슬라이드별 추출) ---
    png_path = work_dir / f"{out_prefix.stem}-{page_no}.png"
    ppm_cmd = [
        "pdftoppm",
        "-f", str(page_no),
        "-l", str(page_no),
        "-png", "-r", str(dpi),
        str(pdf_path),
        str(out_prefix)
    ]
    res2 = subprocess.run(ppm_cmd, capture_output=True, text=True, env=env)
    if res2.returncode != 0:
        print("pdftoppm 변환 실패:", res2.stderr)

    if not png_path.exists():
        raise FileNotFoundError(f"슬라이드 {page_no} PNG 변환 실패")

    # --- 변환 후 PDF 삭제 ---
    try:
        if pdf_path.exists():
            os.remove(pdf_path)
            # print(f"PDF 삭제 완료: {pdf_path.name}")
    except Exception as e:
        print(f"[경고] PDF 삭제 실패: {e}")

    # --- 최종 PNG 경로 반환 ---
    state["slide_image"] = str(png_path)
    return state