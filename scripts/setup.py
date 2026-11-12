"""처음 한 번: 가상환경·의존성·Playwright 브라우저를 설치한다(Windows는 start.bat도 같은 일을 한다). 클라우드·macOS·Linux용."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(cmd, cwd=ROOT):
    print("$", " ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=cwd, check=True, shell=os.name == "nt" and cmd[0] == "npm")


if not PY.exists():
    run([sys.executable, "-m", "venv", str(VENV)])
run([str(PY), "-m", "pip", "install", "-q", "-r", "backend/requirements.txt"])
if not (ROOT / "frontend" / "node_modules").exists():
    run(["npm", "--prefix", "frontend", "ci"])
run(["npx", "--prefix", "frontend", "playwright", "install", "chromium"])
print("완료. 검사: python scripts/verify.py --e2e / 개발 서버: python scripts/dev.py")
