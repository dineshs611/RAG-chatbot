import os
from parsers.pdf import clean_text

def parse_txt(file_source):
    """
    Parse a TXT file.
    Returns:
        List of dicts: [{'text': str, 'page_number': int}]
    """
    pages_data = []
    text_content = ""
    
    try:
        if isinstance(file_source, bytes):
            # Try decoding options
            encodings = ['utf-8', 'latin-1', 'utf-16']
            decoded = False
            for enc in encodings:
                try:
                    text_content = file_source.decode(enc)
                    decoded = True
                    break
                except UnicodeDecodeError:
                    continue
            if not decoded:
                raise UnicodeDecodeError("Could not decode text file with standard encodings.")
        else:
            if not os.path.exists(file_source):
                raise FileNotFoundError(f"TXT file not found: {file_source}")
            encodings = ['utf-8', 'latin-1', 'utf-16']
            decoded = False
            for enc in encodings:
                try:
                    with open(file_source, 'r', encoding=enc) as f:
                        text_content = f.read()
                    decoded = True
                    break
                except UnicodeDecodeError:
                    continue
            if not decoded:
                raise UnicodeDecodeError("Could not decode text file with standard encodings.")
                
        cleaned_text = clean_text(text_content)
        if not cleaned_text:
            return []
            
        # Split text into simulated pages (e.g. 2500 characters per page)
        chars_per_page = 2500
        num_simulated_pages = (len(cleaned_text) + chars_per_page - 1) // chars_per_page
        
        for i in range(num_simulated_pages):
            chunk = cleaned_text[i * chars_per_page: (i + 1) * chars_per_page]
            cleaned_chunk = clean_text(chunk)
            if cleaned_chunk:
                pages_data.append({
                    "text": cleaned_chunk,
                    "page_number": i + 1
                })
                
    except Exception as e:
        print(f"Error parsing TXT: {e}")
        raise e
        
    return pages_data
