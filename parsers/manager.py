import os
from parsers.pdf import parse_pdf
from parsers.docx import parse_docx
from parsers.tabular import parse_csv, parse_excel
from parsers.txt import parse_txt
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP

def parse_file(file_source, filename):
    """
    Route file extraction based on extension.
    Returns:
        List of dicts: [{'text': str, 'page_number': int}]
    """
    _, ext = os.path.splitext(filename.lower())
    
    if ext == ".pdf":
        return parse_pdf(file_source)
    elif ext == ".docx":
        return parse_docx(file_source)
    elif ext == ".csv":
        return parse_csv(file_source)
    elif ext in [".xlsx", ".xls"]:
        return parse_excel(file_source)
    elif ext == ".txt":
        return parse_txt(file_source)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def chunk_document(pages_data, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    """
    Splits text from pages into overlapping chunks while preserving page number.
    Returns:
        List of dicts: [{'text': str, 'page_number': int, 'chunk_index': int}]
    """
    chunks = []
    chunk_index = 0
    
    for page in pages_data:
        text = page["text"]
        page_num = page["page_number"]
        
        # Split text into words for word-based window chunking
        words = text.split(" ")
        num_words = len(words)
        
        # Estimate average word length is 5 chars, so CHUNK_SIZE/5 = approx words
        words_per_chunk = chunk_size // 6
        words_overlap = chunk_overlap // 6
        
        if num_words <= words_per_chunk:
            chunks.append({
                "text": text,
                "page_number": page_num,
                "chunk_index": chunk_index
            })
            chunk_index += 1
        else:
            # Sliding window over words
            start = 0
            while start < num_words:
                end = min(start + words_per_chunk, num_words)
                sub_words = words[start:end]
                sub_text = " ".join(sub_words).strip()
                
                if sub_text:
                    chunks.append({
                        "text": sub_text,
                        "page_number": page_num,
                        "chunk_index": chunk_index
                    })
                    chunk_index += 1
                
                # Advance window
                start += (words_per_chunk - words_overlap)
                # Avoid infinite loop if overlap is too large
                if words_per_chunk - words_overlap <= 0:
                    start += 1
                    
    return chunks
