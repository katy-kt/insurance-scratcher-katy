"""
PDF 批量轉換腳本（專題機斷網版）
=============================================
1. 嘗試使用 docling 進行結構化轉換。
2. 若專題機斷網缺乏模型或噴權限 Error，自動切換至 pypdf 提取純文字。
3. 自動跳過已轉換檔案、自動定位相對路徑。
"""

import os
from pathlib import Path
from tqdm import tqdm
import logging
import zipfile
import io

# ══════════════════════════════════════════════
# 設定區（自動抓取腳本所在目錄，本地、專題機通用）
# ══════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent
ZIP_FILE_PATH = os.path.join(BASE_DIR, "datasets", "保單條款.zip")
OUTPUT_DIR = BASE_DIR / "tii_txts" / "健康保險" / "保單條款"
# ══════════════════════════════════════════════

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,   # 只印警告和錯誤
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(OUTPUT_DIR.parent / "convert.log", encoding="utf-8", mode="w"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def build_converter():
    """建立關閉 OCR 且相容舊版 docling 的 converter"""
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False            
        pipeline_options.do_table_structure = False  

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    except Exception as e:
        log.warning(f"初始化 docling 失敗（可能環境缺件）：{e}")
        return None


def convert_pdf_bytes_to_txt(converter, pdf_bytes: bytes, filename: str, txt_path: Path) -> bool:
    # 第一優先：嘗試使用 docling
    if converter is not None:
        try:
            from docling.datamodel.base_models import DocumentStream
            buf = io.BytesIO(pdf_bytes)
            source = DocumentStream(name=filename, stream=buf)
            
            result = converter.convert(source)
            txt = result.document.export_to_markdown()
            if len(txt.strip()) > 50:
                txt_path.write_text(txt, encoding="utf-8")
                return True
        except Exception as e:
            # 這裡會精準捕獲當前的 Cannot find cached snapshot / Permission denied 錯誤
            pass 

    # 第二優先（大退路）：docling 失敗或斷網，立刻啟動 pypdf 救援
    try:
        import pypdf
        buf = io.BytesIO(pdf_bytes)
        reader = pypdf.PdfReader(buf)
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        
        if len(text.strip()) > 10:
            txt_path.write_text(text, encoding="utf-8")
            return True
        else:
            return False
    except Exception as e2:
        log.error(f"❌ pypdf 救援也失敗 {filename}：{e2}")
        return False


def main():
    if not os.path.exists(ZIP_FILE_PATH):
        log.error(f"❌ 找不到 ZIP 檔案：{os.path.abspath(ZIP_FILE_PATH)}")
        return

    with zipfile.ZipFile(ZIP_FILE_PATH, 'r') as z:
        all_files = sorted(z.namelist())
        pdf_names = [f for f in all_files if f.lower().endswith('.pdf') and not f.startswith('__MACOSX')]
        
        print(f"共找到 {len(pdf_names)} 份 PDF")

        # 斷點續跑：篩選出尚未轉換的檔案
        todo = []
        skipped_count = 0
        for f_name in pdf_names:
            pure_name = Path(f_name).name
            txt_path = OUTPUT_DIR / f"{Path(pure_name).stem}.txt"
            if not txt_path.exists():
                todo.append(f_name)
            else:
                skipped_count += 1

        print(f"需要轉換：{len(todo)} 份（已跳過 {skipped_count} 份）")

        if not todo:
            print("全部已轉換完畢！")
            return

        print("初始化配置中...")
        converter = build_converter()
        print("開始啟動混合轉換引擎（docling + pypdf 雙重保障）...\n")

        ok, fail = 0, 0
        for zip_member_name in tqdm(todo, desc="轉換中", unit="份"):
            pure_name = Path(zip_member_name).name
            txt_path = OUTPUT_DIR / f"{Path(pure_name).stem}.txt"
            
            try:
                pdf_bytes = z.read(zip_member_name)
            except Exception as e:
                fail += 1
                continue

            if convert_pdf_bytes_to_txt(converter, pdf_bytes, zip_member_name, txt_path):
                ok += 1
            else:
                log.error(f"❌ {pure_name} 轉換徹底失敗")
                fail += 1

    print(f"\n{'='*50}")
    print(f"  完成：{ok} 份成功，{fail} 份失敗")
    print(f"  輸出位置：{OUTPUT_DIR.resolve()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
