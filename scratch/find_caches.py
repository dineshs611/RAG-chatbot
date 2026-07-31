import os

project_dir = r"C:\Users\dines\.gemini\antigravity\scratch\EduRAG-Assistant"

for root, dirs, files in os.walk(project_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()
                for idx, line in enumerate(lines):
                    if "@st.cache" in line or "global " in line or "st.session_state" in line and "=" in line and ("current_page" in line or "current_chat" in line):
                        rel_path = os.path.relpath(path, project_dir)
                        print(f"{rel_path}:{idx+1} -> {line.strip()}")
