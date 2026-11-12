import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pyotp

from . import config
from .errors import AppError


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt(rounds=10)).decode()


def check_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def make_token(sub: str, purpose: str = "access", minutes: int | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes if minutes else config.JWT_HOURS * 60)
    return jwt.encode({"sub": sub, "purpose": purpose, "exp": exp}, config.JWT_SECRET, algorithm="HS256")


def read_token(token: str, purpose: str = "access") -> str | None:
    try:
        p = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return p["sub"] if p.get("purpose") == purpose else None


def new_totp_secret() -> str:
    return pyotp.random_base32()


def verify_otp(secret: str | None, code: str) -> bool:
    if not secret or not code:
        return False
    if secret == config.DEMO_TOTP_SECRET and code == config.DEMO_OTP:  # 데모 OTP는 시드 비밀키 계정에만 통한다
        return True
    return pyotp.TOTP(secret).verify(code, valid_window=1)


_fails: dict[str, list[float]] = {}


def check_locked(key: str):
    now = time.time()
    hits = [t for t in _fails.get(key, []) if now - t < config.FAIL_WINDOW]
    _fails[key] = hits
    if len(hits) >= config.FAIL_LIMIT:
        raise AppError(429, "TOO_MANY_ATTEMPTS", "로그인 시도가 5회 실패해 5분간 잠겼습니다. 잠시 후 다시 시도하세요.")


def record_fail(key: str):
    _fails.setdefault(key, []).append(time.time())


def clear_fails(key: str | None = None):
    _fails.pop(key, None) if key else _fails.clear()
