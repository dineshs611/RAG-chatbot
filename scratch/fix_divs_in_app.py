import re

file_path = r"C:\Users\dines\.gemini\antigravity\scratch\EduRAG-Assistant\app.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace split div open and close tags that cause Streamlit React DOM tree mismatches
content = re.sub(r'st\.markdown\(f?[\'"]<div class="[^"]*">[\'"],\s*unsafe_allow_html=True\)\n?', '', content)
content = re.sub(r'st\.markdown\([\'"]</div>[\'"],\s*unsafe_allow_html=True\)\n?', '', content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Cleaned split div markdown calls in app.py successfully!")
