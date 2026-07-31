import py_compile
import sys

try:
    py_compile.compile("app.py", doraise=True)
    print("SUCCESS: app.py syntax is 100% valid!")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
