import fitz  # PyMuPDF
import os
import re

def clean_text(text: str) -> str:
    """Clean text by removing excessive whitespace and unreadable characters."""
    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace multiple newlines with a single newline or double newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Remove control characters except tab and newline
    text = "".join(ch for ch in text if ord(ch) >= 32 or ch in ('\n', '\t'))
    return text.strip()

def parse_pdf(file_source):
    """
    Parse a PDF file from a file path or raw bytes.
    Returns:
        List of dicts: [{'text': str, 'page_number': int}]
    """
    pages_data = []
    doc = None
    try:
        if isinstance(file_source, bytes):
            doc = fitz.open(stream=file_source, filetype="pdf")
        else:
            if not os.path.exists(file_source):
                raise FileNotFoundError(f"PDF file not found: {file_source}")
            doc = fitz.open(file_source)
            
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            raw_text = page.get_text()
            cleaned_text = clean_text(raw_text)
            
            if cleaned_text:
                pages_data.append({
                    "text": cleaned_text,
                    "page_number": page_idx + 1
                })
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        raise e
    finally:
        if doc:
            doc.close()
            
    return pages_data
