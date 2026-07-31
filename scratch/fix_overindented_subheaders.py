import os

file_path = r"C:\Users\dines\.gemini\antigravity\scratch\EduRAG-Assistant\app.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if i > 0 and lines[i-1].strip().startswith("with ") and line.startswith("                "):
        # Fix 16 spaces to 8 spaces
        new_lines.append("        " + line.lstrip())
    else:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Overindented subheaders fixed.")
