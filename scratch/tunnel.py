import subprocess
import time

print("Starting public web tunnel...")
proc = subprocess.Popen("npx localtunnel --port 8501", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

for line in proc.stdout:
    print(line, end="", flush=True)
    if "your url is:" in line:
        break

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    proc.terminate()
