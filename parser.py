# parser.py
import re
from io import BytesIO
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from docx import Document

def extract_text_from_pdf(fileobj) -> str:
    """Extract text from PDF"""
    output = BytesIO()
    laparams = LAParams()
    extract_text_to_fp(fileobj, output, laparams=laparams, output_type='text', codec=None)
    text = output.getvalue().decode('utf-8', errors='ignore')
    return text

def extract_text_from_docx(path: str) -> str:
    """Extract text from DOCX"""
    doc = Document(path)
    lines = [p.text for p in doc.paragraphs]
    return "\n".join(lines)

def extract_section(text: str, section_names: list):
    """
    Extract section content from resume text robustly.
    Finds all occurrences of section headers, returns the last occurrence.
    """
    lines = text.splitlines()
    last_section = []
    current_lines = []
    capture = False

    # Normalize section names for comparison
    section_names_lower = [name.lower() for name in section_names]

    for line in lines:
        l_clean = line.strip().lower().rstrip(":")
        if any(name in l_clean for name in section_names_lower):
            # start capturing new section
            if current_lines:
                last_section = current_lines  # save previous captured section
            current_lines = []
            capture = True
            continue
        # Stop capturing at next major header
        if capture and any(h in l_clean for h in ["experience","education","projects","certifications","achievements","summary","profile","contact"]):
            last_section = current_lines  # save captured section
            capture = False
            current_lines = []
            continue
        if capture:
            current_lines.append(line.strip())

    # If capture was active at EOF, save it
    if capture and current_lines:
        last_section = current_lines

    return "\n".join(last_section)


def basic_contact_extraction(text: str):
    email = None
    phone = None
    name = None
    m = re.search(r'[\w\.-]+@[\w\.-]+', text)
    if m:
        email = m.group(0)
    m2 = re.search(r'(\+?\d[\d\-\s\(\)]{6,}\d)', text)
    if m2:
        phone = m2.group(0)
    # Attempt to extract name from top lines
    for line in text.splitlines()[:5]:
        line = line.strip()
        if line and len(line.split()) <= 4:
            name = line
            break
    return {"email": email, "phone": phone, "name": name}

def parse_resume(path: str, ext: str):
    """Parse resume and extract key sections"""
    if ext.lower() == 'pdf':
        with open(path, "rb") as fh:
            text = extract_text_from_pdf(fh)
    elif ext.lower() == 'docx':
        text = extract_text_from_docx(path)
    else:
        raise ValueError("Unsupported file type. Only PDF or DOCX allowed.")

    contact = basic_contact_extraction(text)

    # Robust skills section extraction
    skills_section = extract_section(text, ["skills", "technical skills", "professional skills", "skills & tools", "technical expertise"])

    education = extract_section(text, ["education", "academic background", "qualifications"])
    experience = extract_section(text, ["experience","work experience","projects","internships"])

    return {
        "text": text,
        "name": contact.get("name"),
        "email": contact.get("email"),
        "phone": contact.get("phone"),
        "skills_section": skills_section,
        "education": education,
        "experience": experience
    }
