"""E2E용 서버: 임시 DB로 빌드된 화면(frontend/dist)을 FastAPI가 제공한다. 포트는 인자로."""
import os
import sys
import tempfile
from pathlib import Path

import uvicorn

tmp = tempfile.mkdtemp(prefix="swp_e2e_")
os.environ["SWP_DB_URL"] = "sqlite:///" + Path(tmp, "e2e.db").as_posix()
os.environ["SWP_UPLOAD_DIR"] = str(Path(tmp, "uploads"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
uvicorn.run("app.main:app", host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8100, log_level="warning")
