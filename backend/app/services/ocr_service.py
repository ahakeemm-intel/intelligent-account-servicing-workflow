"""
OCR Service — provider abstraction.

Selects Tesseract (local) or AWS Textract (cloud) based on OCR_PROVIDER setting.
Both paths return a normalised dict: {"raw_text": str, "blocks": list[dict]}
"""
import os
from loguru import logger
from app.core.config import settings


def extract_text(file_path: str) -> dict:
    """
    Run OCR on a document file.

    Returns:
        {"raw_text": str, "blocks": list[dict], "provider": str}
    """
    if settings.OCR_PROVIDER == "textract":
        return _textract_extract(file_path)
    return _tesseract_extract(file_path)


# ── Tesseract (local) ──────────────────────────────────────────────────────────

def _tesseract_extract(file_path: str) -> dict:
    """
    Extract text from a document.
    First attempts PyMuPDF direct text extraction (fast, no tesseract needed).
    Falls back to tesseract OCR for scanned/image-only documents.
    """
    ext = os.path.splitext(file_path)[1].lower()

    # ── Try PyMuPDF direct text extraction first (works for digital PDFs) ──
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            pages_text = [page.get_text() for page in doc]
            doc.close()
            raw_text = "\n".join(pages_text).strip()
            if raw_text:  # Non-empty → it's a digital PDF, no tesseract needed
                logger.info("PyMuPDF direct extract | file={} | chars={}", file_path, len(raw_text))
                return {"raw_text": raw_text, "blocks": [], "provider": "pymupdf"}
        except Exception as e:
            logger.warning("PyMuPDF direct extract failed | {} — will try tesseract", e)

    # ── Fall back to Tesseract OCR (for scanned images or image-based PDFs) ──
    try:
        import pytesseract
        from PIL import Image
        import fitz
    except ImportError as e:
        raise RuntimeError(
            f"OCR dependencies missing: {e}. "
            "Run: pip install pytesseract pillow pymupdf"
        ) from e

    pages_text: list[str] = []

    if ext == ".pdf":
        doc = fitz.open(file_path)
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_path = file_path + f"_page{page.number}.png"
            pix.save(img_path)
            try:
                text = pytesseract.image_to_string(Image.open(img_path))
                pages_text.append(text)
            finally:
                if os.path.exists(img_path):
                    os.remove(img_path)
        doc.close()
    else:
        img = Image.open(file_path)
        pages_text.append(pytesseract.image_to_string(img))

    raw_text = "\n".join(pages_text)
    logger.info("Tesseract OCR | file={} | chars={}", file_path, len(raw_text))
    return {"raw_text": raw_text, "blocks": [], "provider": "tesseract"}


# ── AWS Textract (cloud) ───────────────────────────────────────────────────────

def _textract_extract(file_path: str) -> dict:
    try:
        import boto3
    except ImportError as e:
        raise RuntimeError("boto3 missing. Run: pip install boto3") from e

    client = boto3.client(
        "textract",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION,
    )

    with open(file_path, "rb") as f:
        doc_bytes = f.read()

    response = client.analyze_document(
        Document={"Bytes": doc_bytes},
        FeatureTypes=["FORMS", "TABLES"],
    )

    blocks = response.get("Blocks", [])
    raw_text = " ".join(
        b["Text"] for b in blocks if b.get("BlockType") == "LINE" and "Text" in b
    )

    logger.info("Textract OCR | file={} | blocks={} | chars={}", file_path, len(blocks), len(raw_text))
    return {"raw_text": raw_text, "blocks": blocks, "provider": "textract"}
