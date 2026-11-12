import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TODAY = "2026-10-19"  # 업무 기준일 고정 (date.today() 사용 금지)
DB_URL = os.environ.get("SWP_DB_URL", f"sqlite:///{ROOT / 'backend' / 'shipyard.db'}")
UPLOAD_DIR = Path(os.environ.get("SWP_UPLOAD_DIR", ROOT / "backend" / "uploads"))
DIST_DIR = ROOT / "frontend" / "dist"
JWT_SECRET = os.environ.get("SWP_JWT_SECRET", "dev-only-secret-change-me-0123456789abcdef")  # shortcut: 데모용 기본값, 운영은 환경변수로 교체
JWT_HOURS = 8
DEMO_TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # 시드 계정 전용. 이 비밀키 계정에만 데모 OTP 123456 허용
DEMO_OTP = "123456"
MAX_PDF = 30 * 1024 * 1024
FAIL_LIMIT, FAIL_WINDOW = 5, 300  # 로그인·OTP 실패 5회 -> 5분 429
