import os
import re

project_dir = r"C:\Users\dines\.gemini\antigravity\scratch\EduRAG-Assistant"

for root, dirs, files in os.walk(project_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()
                for idx, line in enumerate(lines):
                    if "st.rerun" in line or "rerun()" in line or "set_page_config" in line:
                        rel_path = os.path.relpath(path, project_dir)
                        print(f"{rel_path}:{idx+1} -> {line.strip()}")
