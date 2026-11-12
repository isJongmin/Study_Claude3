from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .database import get_db
from .errors import AppError, forbidden
from .security import read_token

LV = {"View": 1, "Write": 2, "Admin": 3}
VIEW, WRITE = 1, 2


def current(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> m.User:
    tok = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    emp = read_token(tok) if tok else None
    u = db.scalar(select(m.User).where(m.User.emp_no == emp)) if emp else None
    if not u or u.status != "approved":
        raise AppError(401, "UNAUTHORIZED", "로그인이 필요하거나 세션이 만료되었습니다. 다시 로그인하세요.")
    return u


def my_levels(db: Session, emp_no: str) -> dict[str, int]:
    groups = list(db.scalars(select(m.AuthUser.AuthCd).where(m.AuthUser.EmpNo == emp_no)))
    out: dict[str, int] = {}
    for a in db.scalars(select(m.AuthMenu).where(m.AuthMenu.AuthCd.in_(groups))):
        out[a.MenuId] = max(out.get(a.MenuId, 0), LV.get(a.AuthGbn, 0))
    return out


def require(level: int, *menus: str):
    """menus 중 하나라도 level 이상이면 통과. 아니면 403 (화면 비활성화와 무관하게 서버가 판정)."""
    def dep(user: m.User = Depends(current), db: Session = Depends(get_db)) -> m.User:
        lv = my_levels(db, user.emp_no)
        if max((lv.get(x, 0) for x in menus), default=0) < level:
            raise forbidden()
        return user
    return dep
