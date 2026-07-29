import runpy
import os
import sys

# Entrypoint wrapper for Streamlit Community Cloud deployment
app_path = os.path.join(os.path.dirname(__file__), "app.py")
runpy.run_path(app_path, run_name="__main__")
