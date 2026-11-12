"""도면 개정·결재·배포 규칙. 실패는 AppError, commit은 호출자."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import config
from .. import models as m
from ..errors import bad, conflict, forbidden


def revs(db: Session, drawing_id: int) -> list[m.Revision]:
    return list(db.scalars(select(m.Revision).where(m.Revision.DrawingId == drawing_id).order_by(m.Revision.RevNo)))


def get_rev(db: Session, drawing_id: int, rev_no: int) -> m.Revision | None:
    return db.get(m.Revision, (drawing_id, rev_no))


def new_revision(db: Session, d: m.Drawing, desc: str, emp: str) -> m.Revision:
    last = revs(db, d.DrawingId)[-1]
    if last.RevStatus not in ("ISSUED", "OBSOLETE"):
        raise conflict("진행 중인 리비전이 있어 새 Rev를 만들 수 없습니다. 먼저 결재·배포를 마치거나 반려 후 수정하세요.", "REV_IN_PROGRESS")
    r = m.Revision(DrawingId=d.DrawingId, RevNo=last.RevNo + 1, RevStatus="DRAFT", ChangeDesc=desc, AuthorEmpNo=emp, CreateDt=config.TODAY)
    db.add(r)
    d.DwgStatus = "DRAFT"
    return r


def request_approval(db: Session, d: m.Drawing, a1: str, a2: str):
    last = revs(db, d.DrawingId)[-1]
    if last.RevStatus != "DRAFT":
        raise conflict("작성중(DRAFT) 리비전만 결재를 요청할 수 있습니다.", "BAD_STATE")
    if a1 == a2:
        raise bad("검토자와 승인자는 서로 다른 사람이어야 합니다. 다른 승인자를 선택하세요.")
    for e in (a1, a2):
        u = db.scalar(select(m.User).where(m.User.emp_no == e))
        if not u or u.status != "approved":
            raise bad(f"결재자 {e}을(를) 찾을 수 없거나 승인된 회원이 아닙니다. 결재자를 다시 선택하세요.")
    db.execute(delete(m.Approval).where(m.Approval.DrawingId == d.DrawingId, m.Approval.RevNo == last.RevNo))
    for i, e in enumerate((a1, a2), 1):
        db.add(m.Approval(DrawingId=d.DrawingId, RevNo=last.RevNo, StepNo=i, ApproverEmpNo=e, Result="WAIT"))
    last.RevStatus = d.DwgStatus = "REVIEW"


def act(db: Session, a: m.Approval, emp: str, result: str, comment: str, now: str):
    if a.ApproverEmpNo != emp:
        raise forbidden("본인에게 배정된 결재만 처리할 수 있습니다.")
    d, r = db.get(m.Drawing, a.DrawingId), get_rev(db, a.DrawingId, a.RevNo)
    steps = list(db.scalars(select(m.Approval).where(m.Approval.DrawingId == a.DrawingId, m.Approval.RevNo == a.RevNo)))
    if a.Result != "WAIT" or r.RevStatus != "REVIEW":
        raise conflict("이미 처리되었거나 결재 중이 아닌 건입니다. 결재함을 새로고침하세요.", "BAD_STATE")
    if any(x.StepNo < a.StepNo and x.Result != "APPROVE" for x in steps):
        raise conflict("앞 단계(검토) 결재가 끝나야 처리할 수 있습니다.", "STEP_ORDER")
    comment = comment.strip()
    if result == "REJECT" and not comment:
        raise bad("반려 시 의견을 입력하세요. 반려 사유를 적어야 작성자가 수정할 수 있습니다.")
    a.Result, a.Comment, a.ActDt = result, comment or ("승인" if result == "APPROVE" else ""), now
    if result == "REJECT":
        r.RevStatus = d.DwgStatus = "DRAFT"
        for x in steps:
            if x.Result == "WAIT":
                db.delete(x)
    elif all(x.Result == "APPROVE" for x in steps):
        r.RevStatus = d.DwgStatus = "APPROVED"


def issue(db: Session, d: m.Drawing, rev_no: int):
    r = get_rev(db, d.DrawingId, rev_no)
    if not r or r.RevStatus != "APPROVED":
        raise conflict("승인 완료된 리비전만 배포할 수 있습니다. 결재 상태를 확인하세요.", "BAD_STATE")
    for x in revs(db, d.DrawingId):
        if x.RevStatus == "ISSUED":
            x.RevStatus = "OBSOLETE"
    r.RevStatus, r.IssueDt = "ISSUED", config.TODAY
    d.CurrentRevNo, d.DwgStatus = rev_no, "ISSUED"
