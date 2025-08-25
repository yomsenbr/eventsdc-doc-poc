import io
import os
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from docx import Document as DocxDocument
from pptx import Presentation

UPLOAD_DIR = "data/uploads"
PROCESSED_DIR = "data/processed"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def _ocr_pdf(file_bytes: bytes) -> str:
    pages = convert_from_bytes(file_bytes, dpi=200)
    text = []
    for img in pages:
        text.append(pytesseract.image_to_string(img))
    return "\n".join(text)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        text_chunks = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                text_chunks.append(text)
        text = "\n".join(text_chunks).strip()
        if len(text) < 100:
            text = _ocr_pdf(file_bytes)
        return text
    except Exception:
        return _ocr_pdf(file_bytes)

def extract_text_from_docx(file_bytes: bytes) -> str:
    f = io.BytesIO(file_bytes)
    doc = DocxDocument(f)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text_from_pptx(file_bytes: bytes) -> str:
    f = io.BytesIO(file_bytes)
    prs = Presentation(f)
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                texts.append(shape.text)
    return "\n".join(texts)

def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")

def save_upload(filename: str, content: bytes) -> str:
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    return path
