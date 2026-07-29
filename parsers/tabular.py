import pandas as pd
import io
import os
from parsers.pdf import clean_text

def parse_csv(file_source):
    """
    Parse a CSV file.
    Returns:
        List of dicts: [{'text': str, 'page_number': int}]
    """
    pages_data = []
    try:
        if isinstance(file_source, bytes):
            # Try parsing with utf-8, fallback to latin-1
            try:
                df = pd.read_csv(io.BytesIO(file_source), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_source), encoding='latin-1')
        else:
            if not os.path.exists(file_source):
                raise FileNotFoundError(f"CSV file not found: {file_source}")
            try:
                df = pd.read_csv(file_source, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_source, encoding='latin-1')
                
        # Drop completely empty rows
        df.dropna(how='all', inplace=True)
        
        # Convert df to markdown string representation
        markdown_str = df.to_markdown(index=False)
        cleaned = clean_text(markdown_str)
        
        # Split tabular data by chunks of 30 rows to keep contextual segments
        rows_per_page = 30
        num_chunks = (len(df) + rows_per_page - 1) // rows_per_page
        
        for i in range(num_chunks):
            sub_df = df.iloc[i * rows_per_page: (i + 1) * rows_per_page]
            sub_markdown = sub_df.to_markdown(index=False)
            cleaned_sub = clean_text(sub_markdown)
            if cleaned_sub:
                pages_data.append({
                    "text": cleaned_sub,
                    "page_number": i + 1
                })
                
        if not pages_data:
            pages_data.append({"text": cleaned, "page_number": 1})
            
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        raise e
        
    return pages_data

def parse_excel(file_source):
    """
    Parse an Excel sheet (.xlsx, .xls) using openpyxl.
    Returns:
        List of dicts: [{'text': str, 'page_number': int}]
    """
    pages_data = []
    try:
        if isinstance(file_source, bytes):
            xls = pd.ExcelFile(io.BytesIO(file_source))
        else:
            if not os.path.exists(file_source):
                raise FileNotFoundError(f"Excel file not found: {file_source}")
            xls = pd.ExcelFile(file_source)
            
        sheet_idx = 1
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            df.dropna(how='all', inplace=True)
            
            if len(df) == 0:
                continue
                
            markdown_str = df.to_markdown(index=False)
            cleaned = clean_text(f"### Sheet: {sheet_name}\n\n" + markdown_str)
            
            # Divide each sheet into pages
            rows_per_page = 30
            num_chunks = (len(df) + rows_per_page - 1) // rows_per_page
            
            for i in range(num_chunks):
                sub_df = df.iloc[i * rows_per_page: (i + 1) * rows_per_page]
                sub_markdown = sub_df.to_markdown(index=False)
                cleaned_sub = clean_text(f"### Sheet: {sheet_name} (Part {i+1})\n\n" + sub_markdown)
                if cleaned_sub:
                    pages_data.append({
                        "text": cleaned_sub,
                        "page_number": sheet_idx
                    })
                    
            sheet_idx += 1
            
    except Exception as e:
        print(f"Error parsing Excel: {e}")
        raise e
        
    return pages_data
