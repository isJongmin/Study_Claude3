"""라우터: 권한 확인과 입출력만. 규칙은 services/ 에 있다."""
import re

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session, aliased

from .. import config
from .. import models as m
from .. import schemas as s
from ..database import get_db
from ..deps import VIEW, WRITE, current, my_levels, require
from ..errors import AppError, bad, conflict, missing
from ..security import check_locked, check_pw, clear_fails, hash_pw, make_token, new_totp_secret, read_token, record_fail, verify_otp
from ..seed import digits
from ..services import files, rules, weather, workflow

r = APIRouter(prefix="/api")
TODAY = config.TODAY
DUMMY_HASH = hash_pw("dummy-password")


# ---------- 공통 ----------
def row(o, *drop):
    return {c.name: getattr(o, c.name) for c in o.__table__.columns if c.name not in drop}


def page_query(db: Session, stmt, page: int, size: int, sort: str = "", dir: str = "asc", cols: dict | None = None, tie: tuple = ()):
    """목록 서버 페이징(SQL COUNT + ORDER BY + LIMIT/OFFSET). 그 쪽의 행만 읽는다.
    cols: 정렬 가능한 필드명 -> SQL 식. 모르는 sort는 무시. 범위 밖 쪽은 마지막 쪽."""
    size = min(max(size, 1), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    pages = max(1, -(-total // size))
    page = min(max(page, 1), pages)
    c = (cols or {}).get(sort)
    order = ([c.desc() if dir == "desc" else c.asc()] if c is not None else []) + list(tie)
    rows = db.scalars(stmt.order_by(*order).limit(size).offset((page - 1) * size)).all()
    return rows, {"total": total, "page": page, "size": size, "pages": pages}


def like(expr, q: str):
    return func.lower(expr).contains(q.lower(), autoescape=True)


def done(db: Session):
    """모든 업무 쓰기의 끝: 공정·호선 상태 재계산 후 저장."""
    rules.refresh_all(db)
    db.commit()


def now_str():
    from datetime import datetime
    return f"{TODAY} {datetime.now().strftime('%H:%M')}"


def chk_code(db: Session, group: str, code: str | None):
    if code and not db.get(m.Code, (group, code)):
        raise bad(f"허용되지 않는 {group} 코드입니다: {code}. 목록에서 선택하세요.")


def user_names(db: Session) -> dict[str, str]:
    return {u.emp_no: u.display_name for u in db.scalars(select(m.User))}


def need(db: Session, model, key, what):
    o = db.get(model, key)
    if not o:
        raise missing(what)
    return o


def pub_user(u: m.User, db: Session | None = None):
    out = row(u, "password_hash", "totp_secret", "phone_digits")
    if db is not None:
        out["groups"] = list(db.scalars(select(m.AuthUser.AuthCd).where(m.AuthUser.EmpNo == u.emp_no)))
    return out


def plan_label(p: m.Plan, blocks: dict, procs: dict) -> str:
    b = blocks.get(p.BlockId)
    return (f"[{b.BlockCd}] " if b else "[호선] ") + procs[p.ProcCd].ProcNm


def maps(db: Session):
    return {b.BlockId: b for b in db.scalars(select(m.Block))}, {x.ProcCd: x for x in db.scalars(select(m.Proc))}


@r.get("/health")
def health():
    """서버 준비 확인용(인증 불필요). start.bat·E2E가 사용한다."""
    return {"ok": True}


# ---------- 인증 ----------
def validate_user(db: Session, o: s.SignupIn, editing: str | None = None, need_pw: bool = True):
    if not o.last_name.strip() or not o.first_name.strip():
        raise bad("성과 이름을 입력하세요.")
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", o.email):
        raise bad("이메일 형식이 올바르지 않습니다. 예: name@company.co.kr")
    if not re.match(r"^01\d-?\d{3,4}-?\d{4}$", o.phone):
        raise bad("전화번호 형식(010-0000-0000)이 올바르지 않습니다.")
    if not re.match(r"^[a-zA-Z0-9._-]{4,20}$", o.emp_no):
        raise bad("아이디는 영문/숫자/._- 조합 4~20자입니다.")
    if (need_pw or o.password) and len(o.password) < 8:
        raise bad("비밀번호는 8자 이상 입력하세요.")
    q = select(m.User)
    if editing:
        q = q.where(m.User.emp_no != editing)
    if db.scalar(q.where(m.User.emp_no == o.emp_no)):
        raise conflict("이미 사용 중인 아이디입니다. 다른 아이디를 입력하세요.", "DUP_ID")
    if db.scalar(q.where(m.User.email == o.email)):
        raise conflict("이미 등록된 이메일입니다. 로그인하거나 다른 이메일을 입력하세요.", "DUP_EMAIL")
    if db.scalar(q.where(m.User.phone_digits == digits(o.phone))):
        raise conflict("이미 등록된 전화번호입니다. 다른 번호를 입력하세요.", "DUP_PHONE")


def fmt_phone(p: str) -> str:
    d = digits(p)
    return f"{d[:3]}-{d[3:7]}-{d[7:]}" if len(d) == 11 else f"{d[:3]}-{d[3:6]}-{d[6:]}"


def new_user(o: s.SignupIn, status: str, totp: bool = False) -> m.User:
    return m.User(id="u-" + o.emp_no, email=o.email, password_hash=hash_pw(o.password), display_name=o.last_name + o.first_name,
                  emp_no=o.emp_no, status=status, last_name=o.last_name, first_name=o.first_name, birth_date=o.birth_date,
                  phone=fmt_phone(o.phone), phone_digits=digits(o.phone), totp_enabled=totp,
                  totp_secret=new_totp_secret() if totp else None, created_at=TODAY)


@r.post("/auth/signup", status_code=201)
def signup(o: s.SignupIn, db: Session = Depends(get_db)):
    validate_user(db, o)
    db.add(new_user(o, "pending"))
    db.commit()
    return {"message": "가입 신청이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다."}


def enter(db: Session, u: m.User, request: Request):
    db.add(m.LogAccess(UserId=u.emp_no, LoginDt=now_str(), IpAddress=request.client.host if request.client else None))
    db.commit()
    return {"access_token": make_token(u.emp_no), "user": pub_user(u, db)}


@r.post("/auth/login")
def login(o: s.LoginIn, request: Request, db: Session = Depends(get_db)):
    key = f"login:{o.emp_no}"
    check_locked(key)
    u = db.scalar(select(m.User).where(m.User.emp_no == o.emp_no))
    if not check_pw(o.password, u.password_hash if u else DUMMY_HASH) or not u:
        record_fail(key)
        raise AppError(401, "BAD_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다. 입력을 확인하세요.")
    if u.status != "approved":
        msg = {"pending": "관리자 승인 대기 중인 계정입니다. 승인 후 다시 로그인하세요.", "rejected": "가입이 반려된 계정입니다. 관리자에게 문의하세요.",
               "disabled": "사용이 중지된 계정입니다. 관리자에게 문의하세요."}[u.status]
        raise AppError(403, "ACCOUNT_" + u.status.upper(), msg)
    clear_fails(key)
    if u.totp_enabled:
        return {"otp_required": True, "otp_token": make_token(u.emp_no, "otp", 5)}
    return {"otp_required": False, **enter(db, u, request)}


@r.post("/auth/otp")
def otp(o: s.OtpIn, request: Request, db: Session = Depends(get_db)):
    emp = read_token(o.otp_token, "otp")
    if not emp:
        raise AppError(401, "OTP_EXPIRED", "인증 시간이 지났습니다. 로그인부터 다시 진행하세요.")
    key = f"otp:{emp}"
    check_locked(key)
    u = db.scalar(select(m.User).where(m.User.emp_no == emp))
    if not u or u.status != "approved" or not verify_otp(u.totp_secret, o.code.strip()):
        record_fail(key)
        raise AppError(401, "BAD_OTP", "인증 코드가 올바르지 않습니다. 인증 앱의 6자리 코드를 다시 입력하세요.")
    clear_fails(key)
    return enter(db, u, request)


@r.post("/auth/logout")
def logout(user: m.User = Depends(current), db: Session = Depends(get_db)):
    lg = db.scalar(select(m.LogAccess).where(m.LogAccess.UserId == user.emp_no, m.LogAccess.LogoutDt.is_(None)).order_by(m.LogAccess.LogId.desc()))
    if lg:
        lg.LogoutDt = now_str()
        db.commit()
    return {"ok": True}


@r.get("/auth/me")
def me(user: m.User = Depends(current), db: Session = Depends(get_db)):
    lv = my_levels(db, user.emp_no)
    menus = list(db.scalars(select(m.MenuInfo).where(m.MenuInfo.UseYN).order_by(m.MenuInfo.Seq)))
    kids = {x.ParentId for x in menus if x.ParentId and lv.get(x.MenuId, 0) > 0}
    shown = [{**row(x), "level": lv.get(x.MenuId, 0)} for x in menus if lv.get(x.MenuId, 0) > 0 or x.MenuId in kids]
    return {"user": pub_user(user, db), "menus": shown, "levels": lv}


@r.get("/lookups")
def lookups(user: m.User = Depends(current), db: Session = Depends(get_db)):
    codes: dict[str, list] = {}
    for c in db.scalars(select(m.Code).where(m.Code.UseYN).order_by(m.Code.CodeGroup, m.Code.Seq)):
        codes.setdefault(c.CodeGroup, []).append({"Code": c.Code, "CodeName": c.CodeName})
    return {"codes": codes, "today": TODAY,
            "procs": [row(p) for p in db.scalars(select(m.Proc).order_by(m.Proc.Seq))],
            "hulls": [{"HullNo": h.HullNo, "HullNm": h.HullNm, "HullStatus": h.HullStatus} for h in db.scalars(select(m.Hull).order_by(m.Hull.HullNo))],
            "users": [{"emp_no": u.emp_no, "display_name": u.display_name} for u in db.scalars(select(m.User).where(m.User.status == "approved"))],
            "groups": [row(g) for g in db.scalars(select(m.AuthGroup))]}


# ---------- 날씨 ----------
@r.get("/weather")
async def get_weather(region: str = "울산", user: m.User = Depends(current)):
    if region not in weather.REGIONS:
        raise bad("지역은 울산·거제·목포 중에서 선택하세요.")
    return await weather.get_weather(region)


# ---------- 대시보드 ----------
@r.get("/dashboard")
def dashboard(user: m.User = Depends(require(VIEW, "M00")), db: Session = Depends(get_db)):
    blocks, procs = maps(db)
    hulls = list(db.scalars(select(m.Hull).where(m.Hull.UseYN).order_by(m.Hull.HullNo)))
    plans = list(db.scalars(select(m.Plan)))
    dwgs = list(db.scalars(select(m.Drawing)))
    gates = rules.gate_map(db)
    codes = {(c.CodeGroup, c.Code): c.CodeName for c in db.scalars(select(m.Code))}
    lab = lambda p: plan_label(p, blocks, procs)  # noqa: E731
    delay = [p for p in plans if p.PlanStatus == "DELAY"]
    waiting = sorted((p for p in plans if p.PlanStatus == "PLAN" and p.PlanId in gates), key=lambda p: p.PlanStartDt)
    pend = [d for d in dwgs if d.DwgStatus in ("REVIEW", "APPROVED")]
    imp = rules.impacts(db)
    months: dict[str, list[str]] = {}
    for h in hulls:
        if h.DeliveryDt:
            months.setdefault(h.DeliveryDt[:7], []).append(h.HullNo)
    return {
        "today": TODAY,
        "kpi": {"active_hulls": sum(h.HullStatus in ("DESIGN", "BUILD", "LAUNCH", "TRIAL") for h in hulls), "delay_plans": len(delay),
                "waiting_plans": len(waiting), "pending_drawings": len(pend)},
        "hulls": [{"HullNo": h.HullNo, "HullNm": h.HullNm, "HullStatus": h.HullStatus, "ShipType": h.ShipType, "DeliveryDt": h.DeliveryDt,
                   "progress": rules.wavg([p for p in plans if p.HullNo == h.HullNo])} for h in hulls],
        "plan_status": {k: sum(p.PlanStatus == k for p in plans) for k in ("PLAN", "READY", "WORK", "DONE", "DELAY")},
        "dwg_by_discipline": [{"Discipline": c, "name": codes.get(("DWGDISC", c), c), "total": len(ds),
                               **{k: sum(d.DwgStatus == k for d in ds) for k in ("ISSUED", "APPROVED", "REVIEW", "DRAFT")}}
                              for c in sorted({d.Discipline for d in dwgs}) for ds in [[d for d in dwgs if d.Discipline == c]]],
        "delivery_by_month": [{"month": k, "hulls": months[k]} for k in sorted(months)],
        "delay": [{"PlanId": p.PlanId, "HullNo": p.HullNo, "label": lab(p), "ProgressRate": p.ProgressRate, "PlanEndDt": p.PlanEndDt} for p in delay],
        "waiting": [{"PlanId": p.PlanId, "HullNo": p.HullNo, "label": lab(p), "PlanStartDt": p.PlanStartDt,
                     "blockers": [d.DrawingNo for d in gates[p.PlanId]]} for p in waiting],
        "impacts": [{"DrawingId": d.DrawingId, "DrawingNo": d.DrawingNo, "RevNo": rv.RevNo, "IssueDt": rv.IssueDt, "ChangeDesc": rv.ChangeDesc,
                     "PlanId": p.PlanId, "HullNo": p.HullNo, "label": lab(p), "PlanStatus": p.PlanStatus} for d, rv, p in imp],
    }


# ---------- 호선 ----------
def apply_hull(db: Session, h: m.Hull, o: s.HullIn):
    if o.ContractDt and o.DeliveryDt and o.DeliveryDt < o.ContractDt:
        raise bad("인도 예정일이 계약일보다 빠릅니다. 날짜를 확인하세요.")
    chk_code(db, "SHIPTYPE", o.ShipType)
    chk_code(db, "HULLSTAT", o.HullStatus)
    for k, v in o.model_dump(exclude={"HullNo"}).items():
        setattr(h, k, v)


@r.get("/hulls")
def hull_list(status: str = "", type: str = "", q: str = "", page: int = 1, size: int = 15, sort: str = "", dir: str = "asc",
              user: m.User = Depends(require(VIEW, "M11")), db: Session = Depends(get_db)):
    P = m.Plan
    stmt = select(m.Hull)
    if status:
        stmt = stmt.where(m.Hull.HullStatus == status)
    if type:
        stmt = stmt.where(m.Hull.ShipType == type)
    if q:
        stmt = stmt.where(like(m.Hull.HullNo + func.coalesce(m.Hull.HullNm, "") + func.coalesce(m.Hull.OwnerNm, ""), q))
    span = func.julianday(P.PlanEndDt) - func.julianday(P.PlanStartDt) + 1
    sub = lambda e: select(e).where(P.HullNo == m.Hull.HullNo).scalar_subquery()  # noqa: E731
    cols = {c.name: c for c in m.Hull.__table__.columns} | {
        "has_plan": sub(func.count()), "delay_count": sub(func.sum(case((P.PlanStatus == "DELAY", 1), else_=0))),
        "progress": sub(func.coalesce(func.sum(P.ProgressRate * span) / func.sum(span), 0))}
    hs, meta = page_query(db, stmt, page, size, sort, dir, cols, (m.Hull.HullNo,))
    plans = list(db.scalars(select(P).where(P.HullNo.in_([h.HullNo for h in hs]))))
    items = []
    for h in hs:
        ps = [x for x in plans if x.HullNo == h.HullNo]
        items.append({**row(h), "has_plan": bool(ps), "progress": rules.wavg(ps), "delay_count": sum(x.PlanStatus == "DELAY" for x in ps)})
    return {"items": items, **meta}


@r.post("/hulls", status_code=201)
def hull_create(o: s.HullIn, user: m.User = Depends(require(WRITE, "M11")), db: Session = Depends(get_db)):
    if db.get(m.Hull, o.HullNo):
        raise conflict("이미 존재하는 호선번호입니다. 다른 번호를 입력하세요.", "DUP_HULL")
    h = m.Hull(HullNo=o.HullNo, CreateUserId=user.emp_no, CreateDt=TODAY)
    apply_hull(db, h, o)
    db.add(h)
    for c in db.scalars(select(m.Code.Code).where(m.Code.CodeGroup == "MILESTONE").order_by(m.Code.Seq)):
        db.add(m.Milestone(HullNo=o.HullNo, MilestoneCd=c, PlanDt=o.DeliveryDt if c == "DELIVER" else None))
    done(db)
    return hull_get(o.HullNo, user, db)


@r.get("/hulls/{no}")
def hull_get(no: str, user: m.User = Depends(require(VIEW, "M11")), db: Session = Depends(get_db)):
    h = need(db, m.Hull, no, "호선")
    ps = list(db.scalars(select(m.Plan).where(m.Plan.HullNo == no)))
    ds = list(db.scalars(select(m.Drawing).where(m.Drawing.HullNo == no)))
    blocks = []
    for b in db.scalars(select(m.Block).where(m.Block.HullNo == no).order_by(m.Block.BlockCd)):
        bp = [p for p in ps if p.BlockId == b.BlockId]
        blocks.append({**row(b), "progress": rules.wavg(bp), "plan_count": len(bp), "drawing_count": sum(d.BlockId == b.BlockId for d in ds)})
    cd = {c.Code: c.Seq for c in db.scalars(select(m.Code).where(m.Code.CodeGroup == "MILESTONE"))}
    ms = sorted(db.scalars(select(m.Milestone).where(m.Milestone.HullNo == no)), key=lambda x: cd.get(x.MilestoneCd, 99))
    return {**row(h), "progress": rules.wavg(ps), "milestones": [row(x) for x in ms], "blocks": blocks,
            "plan_stats": {k: sum(p.PlanStatus == k for p in ps) for k in ("PLAN", "READY", "WORK", "DONE", "DELAY")},
            "dwg_stats": {k: sum(d.DwgStatus == k for d in ds) for k in ("ISSUED", "APPROVED", "REVIEW", "DRAFT")}}


@r.put("/hulls/{no}")
def hull_update(no: str, o: s.HullIn, user: m.User = Depends(require(WRITE, "M11")), db: Session = Depends(get_db)):
    h = need(db, m.Hull, no, "호선")
    apply_hull(db, h, o)
    h.ModifyUserId, h.ModifyDt = user.emp_no, TODAY
    done(db)
    return hull_get(no, user, db)


@r.delete("/hulls/{no}")
def hull_delete(no: str, user: m.User = Depends(require(WRITE, "M11")), db: Session = Depends(get_db)):
    need(db, m.Hull, no, "호선")
    fids = list(db.scalars(select(m.Revision.FileId).join(m.Drawing, m.Drawing.DrawingId == m.Revision.DrawingId).where(m.Drawing.HullNo == no, m.Revision.FileId.is_not(None))))
    db.execute(delete(m.Hull).where(m.Hull.HullNo == no))  # 블록·공정·실적·도면·결재·연계는 FK CASCADE
    done(db)
    for f in fids:
        files.drop(f)
    return {"ok": True}


@r.put("/hulls/{no}/milestones")
def milestones_save(no: str, items: list[s.MilestoneItem], user: m.User = Depends(require(WRITE, "M11")), db: Session = Depends(get_db)):
    need(db, m.Hull, no, "호선")
    for it in items:
        chk_code(db, "MILESTONE", it.MilestoneCd)
        ms = db.get(m.Milestone, (no, it.MilestoneCd))
        if ms is None:
            ms = m.Milestone(HullNo=no, MilestoneCd=it.MilestoneCd)
            db.add(ms)
        ms.PlanDt, ms.ActualDt = it.PlanDt, it.ActualDt
    db.commit()
    return hull_get(no, user, db)


@r.post("/hulls/{no}/blocks", status_code=201)
def block_add(no: str, o: s.BlockIn, user: m.User = Depends(require(WRITE, "M11")), db: Session = Depends(get_db)):
    need(db, m.Hull, no, "호선")
    chk_code(db, "BLOCKTYPE", o.BlockType)
    if db.scalar(select(m.Block).where(m.Block.HullNo == no, m.Block.BlockCd == o.BlockCd)):
        raise conflict("이미 존재하는 블록코드입니다. 다른 코드를 입력하세요.", "DUP_BLOCK")
    b = m.Block(HullNo=no, **o.model_dump())
    db.add(b)
    db.commit()
    return row(b)


@r.delete("/blocks/{bid}")
def block_delete(bid: int, user: m.User = Depends(require(WRITE, "M11")), db: Session = Depends(get_db)):
    need(db, m.Block, bid, "블록")
    db.execute(delete(m.Block).where(m.Block.BlockId == bid))  # 공정은 CASCADE, 도면의 블록 연결은 해제(SET NULL)
    done(db)
    return {"ok": True}


# ---------- 공정 ----------
def plan_views(db: Session, plans: list[m.Plan]) -> list[dict]:
    blocks, procs = maps(db)
    ids = [p.PlanId for p in plans]
    deps: dict[int, list[int]] = {}
    for d in db.scalars(select(m.PlanDep).where(m.PlanDep.PlanId.in_(ids))):
        deps.setdefault(d.PlanId, []).append(d.PredPlanId)
    gates = rules.gate_map(db)
    links: dict[int, list] = {}
    issued = rules.issued_ids(db)
    q = select(m.PlanLink, m.Drawing).join(m.Drawing, m.Drawing.DrawingId == m.PlanLink.DrawingId).where(m.PlanLink.PlanId.in_(ids))
    for lk, d in db.execute(q):
        links.setdefault(lk.PlanId, []).append({"DrawingId": d.DrawingId, "DrawingNo": d.DrawingNo, "DrawingNm": d.DrawingNm, "DwgStatus": d.DwgStatus,
                                                "RequiredYN": lk.RequiredYN, "NeedDt": lk.NeedDt, "issued": d.DrawingId in issued})
    names = user_names(db)
    return [{**row(p), "label": plan_label(p, blocks, procs), "BlockCd": blocks[p.BlockId].BlockCd if p.BlockId in blocks else None,
             "ProcNm": procs[p.ProcCd].ProcNm, "ManagerNm": names.get(p.ManagerEmpNo), "preds": deps.get(p.PlanId, []),
             "gate": {"ok": p.PlanId not in gates, "blockers": [{"DrawingId": d.DrawingId, "DrawingNo": d.DrawingNo, "DwgStatus": d.DwgStatus} for d in gates.get(p.PlanId, [])]},
             "links": links.get(p.PlanId, [])} for p in plans]


@r.get("/plans")
def plan_list(hull: str, user: m.User = Depends(require(VIEW, "M21", "M22")), db: Session = Depends(get_db)):
    blocks, procs = maps(db)
    ps = list(db.scalars(select(m.Plan).where(m.Plan.HullNo == hull)))
    ps.sort(key=lambda p: (int(blocks[p.BlockId].BlockCd) if p.BlockId in blocks and blocks[p.BlockId].BlockCd.isdigit() else 9999, procs[p.ProcCd].Seq))
    return plan_views(db, ps)


def apply_plan(db: Session, p: m.Plan, o: s.PlanIn, hull: str):
    if o.PlanEndDt < o.PlanStartDt:
        raise bad("계획 종료일이 시작일보다 빠릅니다. 날짜를 확인하세요.")
    if o.BlockId is not None:
        b = db.get(m.Block, o.BlockId)
        if not b or b.HullNo != hull:
            raise bad("선택한 블록이 이 호선에 속하지 않습니다. 블록을 다시 선택하세요.")
    if not db.get(m.Proc, o.ProcCd):
        raise bad("존재하지 않는 공정 코드입니다. 목록에서 선택하세요.")
    if o.ManagerEmpNo and not db.scalar(select(m.User.id).where(m.User.emp_no == o.ManagerEmpNo)):
        raise bad("담당자를 찾을 수 없습니다. 목록에서 선택하세요.")
    for q in set(o.preds):
        pp = db.get(m.Plan, q)
        if not pp or pp.HullNo != hull:
            raise bad("선행 공정은 같은 호선의 공정이어야 합니다.")
        if p.PlanId is not None and (q == p.PlanId or rules.reaches(db, q, p.PlanId)):
            raise conflict("선행 공정이 순환 구조를 만듭니다. 선후행 연결을 다시 선택하세요.", "CYCLE")
    for k in ("BlockId", "ProcCd", "PlanStartDt", "PlanEndDt", "ManagerEmpNo", "Remark"):
        setattr(p, k, getattr(o, k))
    if p.PlanId is None:
        db.add(p)
        db.flush()
    db.execute(delete(m.PlanDep).where(m.PlanDep.PlanId == p.PlanId))
    for q in sorted(set(o.preds)):
        db.add(m.PlanDep(PlanId=p.PlanId, PredPlanId=q, LagDays=0))


@r.post("/hulls/{no}/plans", status_code=201)
def plan_create(no: str, o: s.PlanIn, user: m.User = Depends(require(WRITE, "M21")), db: Session = Depends(get_db)):
    need(db, m.Hull, no, "호선")
    p = m.Plan(HullNo=no, ProgressRate=0, PlanStatus="PLAN", CreateUserId=user.emp_no, CreateDt=TODAY)
    apply_plan(db, p, o, no)
    done(db)
    return plan_views(db, [p])[0]


@r.put("/plans/{pid}")
def plan_update(pid: int, o: s.PlanIn, user: m.User = Depends(require(WRITE, "M21")), db: Session = Depends(get_db)):
    p = need(db, m.Plan, pid, "공정")
    apply_plan(db, p, o, p.HullNo)
    done(db)
    return plan_views(db, [p])[0]


@r.delete("/plans/{pid}")
def plan_delete(pid: int, user: m.User = Depends(require(WRITE, "M21")), db: Session = Depends(get_db)):
    need(db, m.Plan, pid, "공정")
    rules.delete_plans(db, [pid])
    done(db)
    return {"ok": True}


@r.post("/links", status_code=201)
def link_add(o: s.LinkIn, user: m.User = Depends(require(WRITE, "M21", "M31")), db: Session = Depends(get_db)):
    p, d = need(db, m.Plan, o.plan_id, "공정"), need(db, m.Drawing, o.drawing_id, "도면")
    if p.HullNo != d.HullNo:
        raise bad("도면과 공정은 같은 호선이어야 연계할 수 있습니다.")
    if db.get(m.PlanLink, (o.drawing_id, o.plan_id)):
        raise conflict("이미 연계된 도면입니다.", "DUP_LINK")
    db.add(m.PlanLink(DrawingId=o.drawing_id, PlanId=o.plan_id, RequiredYN=o.required, NeedDt=p.PlanStartDt))
    done(db)
    return {"ok": True}


@r.delete("/links")
def link_delete(drawing_id: int, plan_id: int, user: m.User = Depends(require(WRITE, "M21", "M31")), db: Session = Depends(get_db)):
    lk = need(db, m.PlanLink, (drawing_id, plan_id), "연계")
    db.delete(lk)
    done(db)
    return {"ok": True}


# ---------- 공정 실적 ----------
@r.get("/plans/{pid}/progress")
def progress_list(pid: int, page: int = 1, size: int = 8, user: m.User = Depends(require(VIEW, "M21", "M22")), db: Session = Depends(get_db)):
    need(db, m.Plan, pid, "공정")
    xs, meta = page_query(db, select(m.Progress).where(m.Progress.PlanId == pid), page, size, "WorkDt", "desc",
                          {"WorkDt": m.Progress.WorkDt}, (m.Progress.ProgressId.desc(),))
    names = user_names(db)
    return {"items": [{**row(x), "WorkerNm": names.get(x.WorkerEmpNo)} for x in xs], **meta}


@r.post("/plans/{pid}/progress")
def progress_save(pid: int, o: s.ProgressIn, user: m.User = Depends(require(WRITE, "M22")), db: Session = Depends(get_db)):
    p = need(db, m.Plan, pid, "공정")
    if o.WorkDt > TODAY:
        raise bad("미래 일자의 실적은 입력할 수 없습니다. 작업일을 기준일 이전으로 입력하세요.")
    if o.WorkerEmpNo and not db.scalar(select(m.User.id).where(m.User.emp_no == o.WorkerEmpNo)):
        raise bad("작업자를 찾을 수 없습니다. 목록에서 선택하세요.")
    first = not db.scalar(select(func.count()).select_from(m.Progress).where(m.Progress.PlanId == pid))
    if first:  # 첫 실적이 착수다(0%도): 필수 연계 도면이 배포 전이면 착수 불가
        bl = rules.gate_of(db, pid)
        if bl:
            raise conflict("필수 연계 도면이 배포되지 않아 착수할 수 없습니다: " + ", ".join(f"{d.DrawingNo}({d.DwgStatus})" for d in bl) + ". 도면을 배포한 뒤 다시 입력하세요.", "DRAWING_GATE")
    x = db.scalar(select(m.Progress).where(m.Progress.PlanId == pid, m.Progress.WorkDt == o.WorkDt))  # 같은 날은 덮어쓴다
    if not x:
        x = m.Progress(PlanId=pid, WorkDt=o.WorkDt, CreateDt=TODAY)
        db.add(x)
    x.ProgressRate, x.ManHour, x.WorkerCnt, x.WorkerEmpNo, x.Remark = o.ProgressRate, o.ManHour, o.WorkerCnt, o.WorkerEmpNo, o.Remark
    db.flush()
    rules.recompute_plan(db, p)
    done(db)
    return plan_views(db, [p])[0]


@r.delete("/progress/{xid}")
def progress_delete(xid: int, user: m.User = Depends(require(WRITE, "M22")), db: Session = Depends(get_db)):
    x = need(db, m.Progress, xid, "실적")
    p = db.get(m.Plan, x.PlanId)
    db.delete(x)
    db.flush()
    rules.recompute_plan(db, p)
    done(db)
    return plan_views(db, [p])[0]


# ---------- 도면 ----------
def latest(db: Session, did: int) -> m.Revision:
    return workflow.revs(db, did)[-1]


def drawing_detail(db: Session, d: m.Drawing):
    blocks, procs = maps(db)
    names = user_names(db)
    rv = workflow.revs(db, d.DrawingId)
    ap = list(db.scalars(select(m.Approval).where(m.Approval.DrawingId == d.DrawingId).order_by(m.Approval.RevNo.desc(), m.Approval.StepNo)))
    links = []
    for lk, p in db.execute(select(m.PlanLink, m.Plan).join(m.Plan, m.Plan.PlanId == m.PlanLink.PlanId).where(m.PlanLink.DrawingId == d.DrawingId)):
        links.append({"PlanId": p.PlanId, "HullNo": p.HullNo, "label": plan_label(p, blocks, procs), "PlanStatus": p.PlanStatus,
                      "PlanStartDt": p.PlanStartDt, "PlanEndDt": p.PlanEndDt, "RequiredYN": lk.RequiredYN})
    imp = [x for x in rules.impacts(db) if x[0].DrawingId == d.DrawingId]
    free = [p for p in db.scalars(select(m.Plan).where(m.Plan.HullNo == d.HullNo)) if p.PlanId not in {x["PlanId"] for x in links}]
    return {**row(d), "BlockCd": blocks[d.BlockId].BlockCd if d.BlockId in blocks else None, "DesignerNm": names.get(d.DesignerEmpNo),
            "revisions": [{**row(x, "FileId"), "has_file": bool(x.FileId)} for x in rv],
            "approvals": [{**row(a), "ApproverNm": names.get(a.ApproverEmpNo)} for a in ap], "links": links,
            "impact": {"count": len(imp), "RevNo": imp[0][1].RevNo if imp else None, "IssueDt": imp[0][1].IssueDt if imp else None,
                       "plans": [plan_label(x[2], blocks, procs) for x in imp]},
            "free_plans": [{"PlanId": p.PlanId, "label": plan_label(p, blocks, procs)} for p in free]}


def apply_drawing(db: Session, d: m.Drawing, o: s.DrawingIn):
    chk_code(db, "DWGDISC", o.Discipline)
    if o.BlockId is not None:
        b = db.get(m.Block, o.BlockId)
        if not b or b.HullNo != d.HullNo:
            raise bad("선택한 블록이 이 호선에 속하지 않습니다. 블록을 다시 선택하세요.")
    if o.DesignerEmpNo and not db.scalar(select(m.User.id).where(m.User.emp_no == o.DesignerEmpNo)):
        raise bad("설계자를 찾을 수 없습니다. 목록에서 선택하세요.")
    d.DrawingNm, d.BlockId, d.Discipline, d.DesignerEmpNo = o.DrawingNm, o.BlockId, o.Discipline, o.DesignerEmpNo


@r.get("/drawings")
def drawing_list(hull: str = "", disc: str = "", status: str = "", q: str = "", page: int = 1, size: int = 15, sort: str = "", dir: str = "asc",
                 user: m.User = Depends(require(VIEW, "M31", "M33")), db: Session = Depends(get_db)):
    D = m.Drawing
    stmt = select(D)
    if hull:
        stmt = stmt.where(D.HullNo == hull)
    if disc:
        stmt = stmt.where(D.Discipline == disc)
    if status:
        stmt = stmt.where(D.DwgStatus == status)
    if q:
        stmt = stmt.where(like(D.DrawingNo + D.DrawingNm, q))
    cols = {c.name: c for c in D.__table__.columns} | {
        "BlockCd": select(m.Block.BlockCd).where(m.Block.BlockId == D.BlockId).scalar_subquery(),
        "DesignerNm": select(m.User.display_name).where(m.User.emp_no == D.DesignerEmpNo).scalar_subquery(),
        "link_count": select(func.count()).where(m.PlanLink.DrawingId == D.DrawingId).scalar_subquery(),
        "LatestRevNo": select(func.max(m.Revision.RevNo)).where(m.Revision.DrawingId == D.DrawingId).scalar_subquery()}
    ds, meta = page_query(db, stmt, page, size, sort, dir, cols, (D.DrawingNo,))
    ids = [d.DrawingId for d in ds]
    blocks = {b.BlockId: b for b in db.scalars(select(m.Block).where(m.Block.BlockId.in_([d.BlockId for d in ds if d.BlockId])))}
    names = {u.emp_no: u.display_name for u in db.scalars(select(m.User).where(m.User.emp_no.in_([d.DesignerEmpNo for d in ds if d.DesignerEmpNo])))}
    cnt = dict(db.execute(select(m.PlanLink.DrawingId, func.count()).where(m.PlanLink.DrawingId.in_(ids)).group_by(m.PlanLink.DrawingId)).all())
    last = dict(db.execute(select(m.Revision.DrawingId, func.max(m.Revision.RevNo)).where(m.Revision.DrawingId.in_(ids)).group_by(m.Revision.DrawingId)).all())
    return {"items": [{**row(d), "BlockCd": blocks[d.BlockId].BlockCd if d.BlockId in blocks else None, "DesignerNm": names.get(d.DesignerEmpNo),
                       "link_count": cnt.get(d.DrawingId, 0), "LatestRevNo": last.get(d.DrawingId, 0)} for d in ds], **meta}


@r.post("/drawings", status_code=201)
def drawing_create(o: s.DrawingIn, user: m.User = Depends(require(WRITE, "M31")), db: Session = Depends(get_db)):
    need(db, m.Hull, o.HullNo, "호선")
    if db.scalar(select(m.Drawing.DrawingId).where(m.Drawing.DrawingNo == o.DrawingNo)):
        raise conflict("이미 존재하는 도면번호입니다. 다른 번호를 입력하세요.", "DUP_DRAWING")
    d = m.Drawing(DrawingNo=o.DrawingNo, HullNo=o.HullNo, DwgStatus="DRAFT", CurrentRevNo=0, CreateUserId=user.emp_no, CreateDt=TODAY)
    apply_drawing(db, d, o)
    db.add(d)
    db.flush()
    db.add(m.Revision(DrawingId=d.DrawingId, RevNo=0, RevStatus="DRAFT", ChangeDesc="최초 작성", AuthorEmpNo=user.emp_no, CreateDt=TODAY))
    done(db)
    return drawing_detail(db, d)


@r.get("/drawings/{did}")
def drawing_get(did: int, user: m.User = Depends(require(VIEW, "M31", "M33")), db: Session = Depends(get_db)):
    return drawing_detail(db, need(db, m.Drawing, did, "도면"))


@r.put("/drawings/{did}")
def drawing_update(did: int, o: s.DrawingIn, user: m.User = Depends(require(WRITE, "M31")), db: Session = Depends(get_db)):
    d = need(db, m.Drawing, did, "도면")
    apply_drawing(db, d, o)
    d.ModifyUserId, d.ModifyDt = user.emp_no, TODAY
    db.commit()
    return drawing_detail(db, d)


@r.delete("/drawings/{did}")
def drawing_delete(did: int, user: m.User = Depends(require(WRITE, "M31")), db: Session = Depends(get_db)):
    need(db, m.Drawing, did, "도면")
    fids = [x.FileId for x in workflow.revs(db, did) if x.FileId]
    db.execute(delete(m.Drawing).where(m.Drawing.DrawingId == did))
    done(db)
    for f in fids:
        files.drop(f)
    return {"ok": True}


@r.post("/drawings/{did}/revisions", status_code=201)
def rev_new(did: int, o: s.RevIn, user: m.User = Depends(require(WRITE, "M31")), db: Session = Depends(get_db)):
    d = need(db, m.Drawing, did, "도면")
    workflow.new_revision(db, d, o.ChangeDesc, user.emp_no)
    done(db)
    return drawing_detail(db, d)


@r.post("/drawings/{did}/request")
def rev_request(did: int, o: s.RequestIn, user: m.User = Depends(require(WRITE, "M31")), db: Session = Depends(get_db)):
    d = need(db, m.Drawing, did, "도면")
    workflow.request_approval(db, d, o.a1, o.a2)
    done(db)
    return drawing_detail(db, d)


@r.post("/drawings/{did}/revisions/{rev}/issue")
def rev_issue(did: int, rev: int, user: m.User = Depends(require(WRITE, "M31", "M33")), db: Session = Depends(get_db)):
    d = need(db, m.Drawing, did, "도면")
    workflow.issue(db, d, rev)
    done(db)
    return drawing_detail(db, d)


def draft_rev(db: Session, did: int, rev: int) -> m.Revision:
    need(db, m.Drawing, did, "도면")
    x = workflow.get_rev(db, did, rev)
    if not x:
        raise missing("리비전")
    return x


@r.post("/drawings/{did}/revisions/{rev}/file")
async def file_upload(did: int, rev: int, file: UploadFile = File(...), user: m.User = Depends(require(WRITE, "M31")), db: Session = Depends(get_db)):
    x = draft_rev(db, did, rev)
    if x.RevStatus != "DRAFT":
        raise conflict("작성중(DRAFT) 리비전만 PDF를 올리거나 바꿀 수 있습니다.", "BAD_STATE")
    fid, name = files.save_pdf(await file.read(config.MAX_PDF + 1), file.filename or "")
    old, x.FileId, x.FileNm = x.FileId, fid, name
    db.commit()
    files.drop(old)
    return drawing_detail(db, db.get(m.Drawing, did))


@r.delete("/drawings/{did}/revisions/{rev}/file")
def file_delete(did: int, rev: int, user: m.User = Depends(require(WRITE, "M31")), db: Session = Depends(get_db)):
    x = draft_rev(db, did, rev)
    if x.RevStatus != "DRAFT":
        raise conflict("작성중(DRAFT) 리비전의 파일만 삭제할 수 있습니다.", "BAD_STATE")
    old, x.FileId, x.FileNm = x.FileId, None, None
    db.commit()
    files.drop(old)
    return drawing_detail(db, db.get(m.Drawing, did))


@r.get("/drawings/{did}/revisions/{rev}/file")
def file_get(did: int, rev: int, user: m.User = Depends(require(VIEW, "M31", "M33")), db: Session = Depends(get_db)):
    x = draft_rev(db, did, rev)
    d = db.get(m.Drawing, did)
    p = files.path_of(x.FileId) if x.FileId else None
    if p:
        return FileResponse(p, media_type="application/pdf", content_disposition_type="inline")
    return Response(files.sample_pdf(d.DrawingNo, x.RevNo, x.RevStatus, d.HullNo, d.Discipline), media_type="application/pdf", headers={"Content-Disposition": "inline"})


# ---------- 결재함 ----------
@r.get("/approvals/inbox")
def inbox(hpage: int = 1, hsize: int = 10, user: m.User = Depends(require(VIEW, "M33")), db: Session = Depends(get_db)):
    A, R, D, P, L = m.Approval, m.Revision, m.Drawing, m.Plan, m.PlanLink
    # 내 결재 대기: 내 차례(앞 단계가 모두 승인)이고 리비전이 검토중인 건
    X = aliased(A)
    open_before = select(X.ApprovalId).where(X.DrawingId == A.DrawingId, X.RevNo == A.RevNo, X.StepNo < A.StepNo, X.Result != "APPROVE").exists()
    mine = [{**row(a), "DrawingNo": no, "DrawingNm": nm, "ChangeDesc": desc}
            for a, no, nm, desc in db.execute(
                select(A, D.DrawingNo, D.DrawingNm, R.ChangeDesc).join(R, (R.DrawingId == A.DrawingId) & (R.RevNo == A.RevNo)).join(D, D.DrawingId == A.DrawingId)
                .where(A.Result == "WAIT", A.ApproverEmpNo == user.emp_no, R.RevStatus == "REVIEW", ~open_before).order_by(A.ApprovalId))]
    # 배포 대기: 최신 리비전이 승인(APPROVED)인 도면 + 그로 인해 영향받을 계획 상태 공정
    R2 = aliased(R)
    last_rev = select(func.max(R2.RevNo)).where(R2.DrawingId == D.DrawingId).scalar_subquery()
    ready_rows = db.execute(select(D.DrawingId, D.DrawingNo, D.DrawingNm, R.RevNo).join(R, R.DrawingId == D.DrawingId)
                            .where(R.RevNo == last_rev, R.RevStatus == "APPROVED").order_by(D.DrawingNo)).all()
    plans: dict[int, list] = {}
    if ready_rows:
        blocks, procs = maps(db)
        for did, p in db.execute(select(L.DrawingId, P).join(P, P.PlanId == L.PlanId).where(L.DrawingId.in_([x[0] for x in ready_rows]), P.PlanStatus == "PLAN")):
            plans.setdefault(did, []).append(plan_label(p, blocks, procs))
    ready = [{"DrawingId": did, "DrawingNo": no, "DrawingNm": nm, "RevNo": rev, "affects": plans.get(did, [])} for did, no, nm, rev in ready_rows]
    # 최근 결재 이력: 서버 페이징
    hs, meta = page_query(db, select(A).where(A.Result != "WAIT"), hpage, hsize, "ActDt", "desc", {"ActDt": A.ActDt}, (A.ApprovalId.desc(),))
    nos = dict(db.execute(select(D.DrawingId, D.DrawingNo).where(D.DrawingId.in_([a.DrawingId for a in hs]))).all())
    names = dict(db.execute(select(m.User.emp_no, m.User.display_name).where(m.User.emp_no.in_([a.ApproverEmpNo for a in hs]))).all())
    return {"mine": mine, "ready": ready,
            "history": {"items": [{**row(a), "DrawingNo": nos.get(a.DrawingId), "ApproverNm": names.get(a.ApproverEmpNo)} for a in hs], **meta}}


@r.post("/approvals/{aid}/act")
def approval_act(aid: int, o: s.ActIn, user: m.User = Depends(require(WRITE, "M33")), db: Session = Depends(get_db)):
    a = need(db, m.Approval, aid, "결재 건")
    workflow.act(db, a, user.emp_no, o.result, o.comment, now_str())
    done(db)
    return drawing_detail(db, db.get(m.Drawing, a.DrawingId))


# ---------- 회원관리 ----------
@r.get("/users")
def user_list(status: str = "", q: str = "", page: int = 1, size: int = 15, sort: str = "", dir: str = "asc",
              user: m.User = Depends(require(VIEW, "M91")), db: Session = Depends(get_db)):
    U = m.User
    base = select(U)
    if q:
        base = base.where(like(U.emp_no + U.display_name + U.email + U.phone, q))
    cols = {c.name: c for c in U.__table__.columns if c.name not in ("password_hash", "totp_secret", "phone_digits")}
    us, meta = page_query(db, base.where(U.status == status) if status else base, page, size, sort, dir, cols, (U.created_at.desc(), U.emp_no))
    pending = db.scalar(select(func.count()).select_from(base.where(U.status == "pending").subquery()))
    return {"items": [pub_user(u, db) for u in us], **meta, "pending": pending}


def set_group(db: Session, emp: str, group: str | None):
    if group and not db.get(m.AuthGroup, group):
        raise bad("존재하지 않는 권한 그룹입니다. 목록에서 선택하세요.")
    db.execute(delete(m.AuthUser).where(m.AuthUser.EmpNo == emp))
    if group:
        db.add(m.AuthUser(AuthCd=group, EmpNo=emp))


def check_status(v: str):
    if v not in ("pending", "approved", "rejected", "disabled"):
        raise bad("상태 값이 올바르지 않습니다.")


@r.post("/users", status_code=201)
def user_create(o: s.UserIn, user: m.User = Depends(require(WRITE, "M91")), db: Session = Depends(get_db)):
    check_status(o.status)
    validate_user(db, o)
    u = new_user(o, o.status, o.totp_enabled)
    db.add(u)
    db.flush()
    set_group(db, u.emp_no, o.group)
    db.commit()
    return {**pub_user(u, db), "totp_secret_new": u.totp_secret}  # OTP 비밀키는 생성 응답에서만 한 번 보여준다


@r.put("/users/{emp}")
def user_update(emp: str, o: s.UserIn, user: m.User = Depends(require(WRITE, "M91")), db: Session = Depends(get_db)):
    u = need(db, m.User, db.scalar(select(m.User.id).where(m.User.emp_no == emp)) or "", "회원")
    check_status(o.status)
    o.emp_no = emp
    validate_user(db, o, editing=emp, need_pw=False)
    if u.emp_no == user.emp_no and o.status != "approved":
        raise conflict("로그인 중인 본인 계정의 상태는 바꿀 수 없습니다.", "SELF")
    new_secret = None
    u.email, u.last_name, u.first_name, u.display_name = o.email, o.last_name, o.first_name, o.last_name + o.first_name
    u.birth_date, u.phone, u.phone_digits, u.status = o.birth_date, fmt_phone(o.phone), digits(o.phone), o.status
    if o.password:
        u.password_hash = hash_pw(o.password)
    if o.totp_enabled and not u.totp_secret:
        u.totp_secret = new_secret = new_totp_secret()
    if not o.totp_enabled:
        u.totp_secret = None
    u.totp_enabled = o.totp_enabled
    set_group(db, emp, o.group)
    db.commit()
    return {**pub_user(u, db), "totp_secret_new": new_secret}


@r.delete("/users/{emp}")
def user_delete(emp: str, user: m.User = Depends(require(WRITE, "M91")), db: Session = Depends(get_db)):
    u = db.scalar(select(m.User).where(m.User.emp_no == emp))
    if not u:
        raise missing("회원")
    if emp == user.emp_no:
        raise conflict("로그인 중인 본인 계정은 삭제할 수 없습니다.", "SELF")
    db.execute(delete(m.AuthUser).where(m.AuthUser.EmpNo == emp))
    db.delete(u)
    db.commit()
    return {"ok": True}


@r.post("/users/{emp}/approve")
def user_approve(emp: str, user: m.User = Depends(require(WRITE, "M91")), db: Session = Depends(get_db)):
    u = db.scalar(select(m.User).where(m.User.emp_no == emp))
    if not u:
        raise missing("회원")
    u.status = "approved"
    db.commit()
    return pub_user(u, db)
