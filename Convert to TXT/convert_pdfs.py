"""
PDF 批量轉換腳本
================
把 INPUT_DIR 裡所有 PDF 用 docling 轉成 .txt
輸出到 OUTPUT_DIR（副檔名換成 .txt）

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

# 先建資料夾，才能寫 log
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(OUTPUT_DIR.parent / "convert.log", encoding="utf-8", mode="w"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def convert_pdf_to_txt(converter, pdf_path: Path, txt_path: Path) -> bool:
    try:
        result = converter.convert(str(pdf_path))
        txt_path.write_text(result.document.export_to_markdown(), encoding="utf-8")
        return True
    except Exception as e:
        log.warning(f"  docling 失敗 {pdf_path.name}：{e}，改用 pypdf")
        try:
            import pypdf
            reader = pypdf.PdfReader(str(pdf_path))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            txt_path.write_text(text, encoding="utf-8")
            return True
        except Exception as e2:
            log.error(f"  pypdf 也失敗：{e2}")
            return False


def main():
    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    log.info(f"共找到 {len(pdf_files)} 份 PDF")

    # 跳過已轉換的（斷點續跑）
    todo = [p for p in pdf_files if not (OUTPUT_DIR / (p.stem + ".txt")).exists()]
    log.info(f"需要轉換：{len(todo)} 份（已跳過 {len(pdf_files) - len(todo)} 份）")

    if not todo:
        print("全部已轉換完畢！")
        return

    # 只初始化一次 docling
    from docling.document_converter import DocumentConverter
    log.info("初始化 docling（首次執行會下載模型）...")
    converter = DocumentConverter()
    log.info("docling 初始化完成，開始轉換...")

    ok, fail = 0, 0
    for pdf_path in tqdm(todo, desc="轉換中", unit="份"):
        txt_path = OUTPUT_DIR / (pdf_path.stem + ".txt")
        if convert_pdf_to_txt(converter, pdf_path, txt_path):
            log.info(f"  ✅ {pdf_path.name}")
            ok += 1
        else:
            log.error(f"  ❌ {pdf_path.name}")
            fail += 1

    print(f"\n{'='*50}")
    print(f"  完成：{ok} 份成功，{fail} 份失敗")
    print(f"  輸出位置：{OUTPUT_DIR.resolve()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
