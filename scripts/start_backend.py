"""Start the FastAPI backend server."""
import os
import sys
import uvicorn

# Ensure the project root is the working directory
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ".")
uvicorn.run("main:app", host="0.0.0.0", port=8002)
