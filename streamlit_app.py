import runpy
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Entrypoint wrapper for Streamlit Community Cloud deployment
app_path = os.path.join(os.path.dirname(__file__), "app.py")
with open(app_path, "r", encoding="utf-8") as f:
    code = compile(f.read(), app_path, "exec")
    exec(code, globals())
