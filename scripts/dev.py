"""uvicorn(8000)과 vite(5173)를 함께 띄우고 Ctrl+C로 둘 다 끈다."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "backend" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main():
    procs = [subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--port", "8000", "--reload", "--reload-dir", "app"], cwd=ROOT / "backend")]
    if (ROOT / "frontend" / "package.json").exists():
        procs.append(subprocess.Popen("npm run dev -- --port 5173", cwd=ROOT / "frontend", shell=True))
    print("API http://127.0.0.1:8000  /  화면 http://127.0.0.1:5173  (Ctrl+C로 종료)")
    try:
        procs[0].wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            else:
                p.terminate()


if __name__ == "__main__":
    sys.exit(main())
