"""가상환경의 파이썬으로 인자를 실행한다(Windows·macOS·Linux 공통). .mcp.json이 OS별 경로 없이 쓴다."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "backend" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
sys.exit(__import__("subprocess").call([str(PY), *sys.argv[1:]], cwd=ROOT))
