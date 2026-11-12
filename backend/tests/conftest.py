import os
import sys
import tempfile
from pathlib import Path

# 앱을 import 하기 전에 임시 DB·업로드 폴더로 돌린다 (개발 DB를 건드리지 않는다)
_tmp = tempfile.mkdtemp(prefix="swp_test_")
os.environ["SWP_DB_URL"] = "sqlite:///" + Path(_tmp, "test.db").as_posix()
os.environ["SWP_UPLOAD_DIR"] = str(Path(_tmp, "uploads"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyotp  # noqa: E402
import pytest  # noqa: E402
from app import security  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

PW = {"admin": "admin1234", "park.pm": "pm1234", "lee.dwg": "dwg1234", "han.wk": "wk1234", "choi.qa": "qa1234"}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_limits():
    security.clear_fails()


def login(c, emp, pw=None, code="123456"):
    """OTP 계정이면 OTP까지 마쳐 Authorization 헤더를 돌려준다."""
    r = c.post("/api/auth/login", json={"emp_no": emp, "password": pw or PW[emp]})
    assert r.status_code == 200, r.text
    j = r.json()
    if j["otp_required"]:
        r = c.post("/api/auth/otp", json={"otp_token": j["otp_token"], "code": code})
        assert r.status_code == 200, r.text
        j = r.json()
    return {"Authorization": "Bearer " + j["access_token"]}


@pytest.fixture(scope="session")
def H(client):
    return {u: login(client, u) for u in PW}


def totp_now(secret):
    return pyotp.TOTP(secret).now()
