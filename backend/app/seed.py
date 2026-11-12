"""빈 DB에 seed_data.json(목업 seed() 결과)을 적재한다."""
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .database import Base
from .security import hash_pw

DEMO_PW = {"admin": "admin1234", "park.pm": "pm1234", "lee.dwg": "dwg1234", "han.wk": "wk1234", "choi.qa": "qa1234", "jung.new": "new12345"}
TABLES = {
    "TB_SYS_CodeGroup": m.CodeGroup, "TB_SYS_Code": m.Code, "users": m.User, "TB_SYS_AuthGroup": m.AuthGroup,
    "TB_SYS_AuthUser": m.AuthUser, "TB_SYS_MenuInfo": m.MenuInfo, "TB_SYS_AuthMenu": m.AuthMenu, "TB_PRC_Proc": m.Proc,
    "TB_MST_Hull": m.Hull, "TB_MST_HullMilestone": m.Milestone, "TB_MST_Block": m.Block, "TB_PRC_Plan": m.Plan,
    "TB_PRC_PlanDep": m.PlanDep, "TB_PRC_Progress": m.Progress, "TB_DWG_Drawing": m.Drawing, "TB_DWG_Revision": m.Revision,
    "TB_DWG_Approval": m.Approval, "TB_DWG_PlanLink": m.PlanLink,
}


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def seed_if_empty(db: Session, engine):
    Base.metadata.create_all(engine)
    if db.scalar(select(m.Hull.HullNo).limit(1)) or db.scalar(select(m.User.id).limit(1)):
        return False
    data = json.loads((Path(__file__).with_name("seed_data.json")).read_text(encoding="utf-8"))
    for table, model in TABLES.items():
        cols = {c.name for c in model.__table__.columns}
        for row in data.get(table, []):
            row = {k: v for k, v in row.items() if k in cols}
            if model is m.User:
                row["password_hash"] = hash_pw(DEMO_PW[row["emp_no"]])
                row["phone_digits"] = digits(row["phone"])
            db.add(model(**row))
        db.flush()
    from .services import rules
    rules.refresh_all(db)
    db.commit()
    return True
