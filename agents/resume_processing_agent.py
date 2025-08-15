import os
import re
import pdfplumber
import docx
import magic  # python-magic for content type detection
from collections import Counter

# --- Helpers ---
def clean_text(text: str) -> str:
    """Basic cleanup: remove extra spaces, normalize newlines."""
    text = re.sub(r"\r\n", "\n", text)  # normalize line breaks
    text = re.sub(r"\n{2,}", "\n\n", text)  # collapse multiple blank lines
    text = re.sub(r"[ \t]+", " ", text)  # collapse spaces/tabs
    return text.strip()

def extract_pdf_text(file_path: str) -> str:
    text_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text_chunks.append(page.extract_text() or "")
    return clean_text("\n".join(text_chunks))

def extract_docx_text(file_path: str) -> str:
    doc = docx.Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs]
    return clean_text("\n".join(paragraphs))

def extract_txt_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return clean_text(f.read())

def detect_skills(text: str) -> list:
    """Simple keyword match for skills — later replace with taxonomy + NLP."""
    # Fixed list for determinism
    known_skills = [
        "python","java","javascript","c++","c#","sql","html","css",
        "machine learning","deep learning","nlp","flask","django",
        "react","excel","power bi","tableau"
    ]
    found = []
    text_lower = text.lower()
    for skill in known_skills:
        if skill in text_lower:
            # Title-case display regardless of match case in text
            found.append(skill.title())
    return sorted(set(found))

def extract_email(text: str) -> str:
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""

def estimate_experience(text: str) -> int:
    """Naive estimation from 'X years' patterns."""
    matches = re.findall(r"(\d+)\+?\s+year", text.lower())
    years = [int(m) for m in matches if m.isdigit()]
    if years:
        # Return most common mention (likely total experience)
        return Counter(years).most_common(1)[0][0]
    return 0

def extract_education(text: str) -> str:
    patterns = [
        r"(b\.?tech|bachelor|b\.?e\.?|be in [a-z\s]+)",
        r"(m\.?tech|master|m\.?e\.?)",
        r"(ph\.?d|doctorate)",
    ]
    for pat in patterns:
        match = re.search(pat, text.lower())
        if match:
            return match.group(0).title()
    return ""


# --- Main processing function ---
def process_resume(file_path: str) -> dict:
    """
    Extracts structured resume data from PDF/DOCX/TXT.
    Returns deterministic JSON for consistent scoring.
    """

    # Detect content type
    mime_type = magic.Magic(mime=True).from_file(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    if mime_type == "application/pdf" or ext == ".pdf":
        raw_text = extract_pdf_text(file_path)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ) or ext == ".docx":
        raw_text = extract_docx_text(file_path)
    elif mime_type == "text/plain" or ext == ".txt":
        raw_text = extract_txt_text(file_path)
    else:
        raise ValueError(f"Unsupported file format: {mime_type}")

    # Build structured parsed data
    parsed_data = {
        "file_name": os.path.basename(file_path),
        "email": extract_email(raw_text),
        "skills": detect_skills(raw_text),
        "experience_years": estimate_experience(raw_text),
        "education": extract_education(raw_text),
        "raw_text": raw_text
    }

    print(f"[INFO] Processed resume: {os.path.basename(file_path)} "
          f"({len(raw_text)} chars, {len(parsed_data['skills'])} skills found)")
    return parsed_data
