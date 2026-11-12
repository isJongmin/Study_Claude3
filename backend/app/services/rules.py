"""업무 규칙 한 곳: 공정 상태·도면 게이트·개정 영향·호선 상태 전이·진척 계산."""
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import config
from .. import models as m

TODAY = config.TODAY


def day(s: str) -> int:
    return date.fromisoformat(s).toordinal()


def span(p) -> int:
    return day(p.PlanEndDt) - day(p.PlanStartDt) + 1


def wavg(plans) -> int:
    tot = sum(span(p) for p in plans)
    return round(sum(p.ProgressRate * span(p) for p in plans) / tot) if tot else 0


def issued_ids(db: Session) -> set[int]:
    return set(db.scalars(select(m.Revision.DrawingId).where(m.Revision.RevStatus == "ISSUED")))


def gate_map(db: Session) -> dict[int, list[m.Drawing]]:
    """plan_id -> 배포본이 없는 필수 연계 도면. 개정 중이어도 이전 배포본이 있으면 통과."""
    ok = issued_ids(db)
    out: dict[int, list[m.Drawing]] = {}
    q = select(m.PlanLink.PlanId, m.Drawing).join(m.Drawing, m.Drawing.DrawingId == m.PlanLink.DrawingId).where(m.PlanLink.RequiredYN)
    for pid, d in db.execute(q):
        if d.DwgStatus != "OBSOLETE" and d.DrawingId not in ok:
            out.setdefault(pid, []).append(d)
    return out


def gate_of(db: Session, plan_id: int) -> list[m.Drawing]:
    return gate_map(db).get(plan_id, [])


def impacts(db: Session) -> list[tuple[m.Drawing, m.Revision, m.Plan]]:
    """최근 30일 내 Rev>=1 배포 도면 -> 연계 공정 중 착수/완료된 것."""
    out = []
    for d in db.scalars(select(m.Drawing)):
        revs = [r for r in db.scalars(select(m.Revision).where(m.Revision.DrawingId == d.DrawingId, m.Revision.RevStatus == "ISSUED", m.Revision.RevNo >= 1))
                if r.IssueDt and 0 <= day(TODAY) - day(r.IssueDt) <= 30]
        if not revs:
            continue
        r = max(revs, key=lambda x: x.RevNo)
        for p in db.scalars(select(m.Plan).join(m.PlanLink, m.PlanLink.PlanId == m.Plan.PlanId).where(m.PlanLink.DrawingId == d.DrawingId)):
            if p.PlanStatus in ("WORK", "DONE", "DELAY"):
                out.append((d, r, p))
    return out


def refresh_all(db: Session):
    """모든 업무 쓰기 뒤에 호출: 공정 상태 재계산 + 호선 상태 자동 전이. commit은 호출자가 한다."""
    db.flush()
    plans = list(db.scalars(select(m.Plan)))
    preds: dict[int, list[int]] = {}
    for d in db.scalars(select(m.PlanDep)):
        preds.setdefault(d.PlanId, []).append(d.PredPlanId)
    gates = gate_map(db)
    done = {p.PlanId for p in plans if p.ProgressRate >= 100}
    for p in plans:
        if p.ProgressRate >= 100:
            p.PlanStatus = "DONE"
        elif p.ProgressRate > 0 or p.ActualStartDt:
            p.PlanStatus = "DELAY" if p.PlanEndDt < TODAY else "WORK"
        elif p.PlanEndDt < TODAY:
            p.PlanStatus = "DELAY"
        else:
            p.PlanStatus = "READY" if all(x in done for x in preds.get(p.PlanId, [])) and p.PlanId not in gates else "PLAN"
    by_hull: dict[str, list[m.Plan]] = {}
    for p in plans:
        by_hull.setdefault(p.HullNo, []).append(p)
    for h in db.scalars(select(m.Hull)):
        ps = by_hull.get(h.HullNo)
        if not ps:
            continue
        if h.HullStatus == "DESIGN" and any(p.PlanStatus == "WORK" for p in ps):
            h.HullStatus = "BUILD"
        if h.HullStatus == "BUILD" and any(p.ProcCd == "LAUNCH" and p.PlanStatus == "DONE" for p in ps):
            h.HullStatus = "LAUNCH"
    db.flush()


def recompute_plan(db: Session, plan: m.Plan):
    """누적 진척 = 가장 늦은 작업일 값, 착수일 = 가장 이른 작업일. 실적이 없으면 착수 전."""
    rows = list(db.scalars(select(m.Progress).where(m.Progress.PlanId == plan.PlanId).order_by(m.Progress.WorkDt)))
    if not rows:
        plan.ProgressRate, plan.ActualStartDt, plan.ActualEndDt = 0, None, None
        return
    last = rows[-1]
    plan.ProgressRate, plan.ActualStartDt = last.ProgressRate, rows[0].WorkDt
    plan.ActualEndDt = last.WorkDt if last.ProgressRate >= 100 else None


def reaches(db: Session, start: int, target: int) -> bool:
    """start 의 선행 사슬을 거슬러 target 에 닿는가 (순환 검사)."""
    seen, stack = set(), [start]
    while stack:
        x = stack.pop()
        if x == target:
            return True
        if x in seen:
            continue
        seen.add(x)
        stack += list(db.scalars(select(m.PlanDep.PredPlanId).where(m.PlanDep.PlanId == x)))
    return False


def delete_plans(db: Session, ids: list[int]):
    if ids:
        db.execute(delete(m.Plan).where(m.Plan.PlanId.in_(ids)))  # 실적·선후행·도면 연계는 FK CASCADE
