import subprocess, sys, os
# Kill all main.py processes
result = subprocess.run(
    ['powershell', '-Command',
     'Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq "" } | Stop-Process -Force'],
    capture_output=True, text=True, timeout=30
)
print("Killed result:", result.returncode)

# Start new backend
os.chdir(r'd:\ait-code\agent_part')
subprocess.Popen(
    [r'C:\Users\JT\.conda\envs\cbcf\python.exe', 'main.py'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
)
print("New process started")
