"""
PDF 批量轉換腳本（快速版）
===========================
使用 docling 但關閉 OCR，直接抽文字型 PDF 的文字層。
速度：每份約 2-10 秒（而非 OCR 的 5-30 分鐘）。

安裝：
    pip install docling pypdf tqdm
"""

from pathlib import Path
from tqdm import tqdm
import logging

# ══════════════════════════════════════════════
# 設定區
# ══════════════════════════════════════════════
INPUT_DIR  = Path(r"C:\Users\Katy\Desktop\畢業專題\tii_pdfs\健康保險\保單條款")
OUTPUT_DIR = Path(r"C:\Users\Katy\Desktop\畢業專題\tii_txts\健康保險\保單條款")
# ══════════════════════════════════════════════

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,   # 只印警告和錯誤，不印 docling 的 INFO 噪音
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(OUTPUT_DIR.parent / "convert.log", encoding="utf-8", mode="w"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def build_converter():
    """建立關閉 OCR 的 docling converter（速度快 100 倍）"""
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False          # 關閉 OCR
    pipeline_options.do_table_structure = False  # 關閉表格辨識（再快一點）

    return DocumentConverter(
        format_options={
            "pdf": PdfFormatOption(pipeline_options=pipeline_options)
        }
    )


def convert_one(converter, pdf_path: Path, txt_path: Path) -> bool:
    # 先用 docling（保留結構）
    try:
        result = converter.convert(str(pdf_path))
        txt = result.document.export_to_markdown()
        if len(txt.strip()) > 50:   # 有實質內容才用 docling 結果
            txt_path.write_text(txt, encoding="utf-8")
            return True
    except Exception as e:
        log.warning(f"docling 失敗 {pdf_path.name}：{e}")

    # fallback：直接用 pypdf 抽文字
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        txt_path.write_text(text, encoding="utf-8")
        return True
    except Exception as e2:
        log.error(f"pypdf 也失敗 {pdf_path.name}：{e2}")
        return False


def main():
    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    print(f"共找到 {len(pdf_files)} 份 PDF")

    todo = [p for p in pdf_files if not (OUTPUT_DIR / (p.stem + ".txt")).exists()]
    print(f"需要轉換：{len(todo)} 份（已跳過 {len(pdf_files) - len(todo)} 份）")

    if not todo:
        print("全部已轉換完畢！")
        return

    print("初始化 docling（不使用 OCR）...")
    converter = build_converter()
    print("初始化完成，開始轉換...\n")

    ok, fail = 0, 0
    for pdf_path in tqdm(todo, desc="轉換中", unit="份"):
        txt_path = OUTPUT_DIR / (pdf_path.stem + ".txt")
        if convert_one(converter, pdf_path, txt_path):
            ok += 1
        else:
            log.error(f"❌ {pdf_path.name}")
            fail += 1

    print(f"\n{'='*50}")
    print(f"  完成：{ok} 份成功，{fail} 份失敗")
    print(f"  輸出位置：{OUTPUT_DIR.resolve()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
