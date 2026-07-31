import py_compile
import re

file_path = r"C:\Users\dines\.gemini\antigravity\scratch\EduRAG-Assistant\app.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Clean up any lines that have 16 spaces instead of 8 spaces right after with statements
fixed_lines = []
for i, line in enumerate(lines):
    # If line starts with 16 spaces but next line starts with 8 spaces
    if line.startswith("                ") and not line.startswith("                    "):
        # Fix 16 spaces to 8 spaces
        fixed_lines.append("        " + line.lstrip())
    else:
        fixed_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(fixed_lines)

print("Indentation cleanup complete.")
