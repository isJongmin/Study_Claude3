"""GUIDE 6절 시나리오 1~3. 서버가 규칙을 판정하는지 API로 검사한다."""
import io

from conftest import totp_now

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
NEW = {"last_name": "홍", "first_name": "길동", "birth_date": "1991-02-03", "email": "hong@swp.co.kr", "phone": "010-7777-8888", "emp_no": "hong.gd", "password": "hong12345"}


# ---------- 시나리오 1: 가입·승인·로그인·OTP·권한 ----------
def test_signup_approve_login_otp_and_permissions(client, H):
    c = client
    assert c.post("/api/auth/signup", json=NEW).status_code == 201
    r = c.post("/api/auth/login", json={"emp_no": "hong.gd", "password": "hong12345"})
    assert r.status_code == 403 and r.json()["code"] == "ACCOUNT_PENDING"
    for k, v in (("emp_no", "hong.gd"), ("email", "hong@swp.co.kr"), ("phone", "01077778888")):  # 아이디·이메일·전화 중복
        body = {**NEW, "emp_no": "other.id", "email": "o@swp.co.kr", "phone": "010-1212-3434", k: v}
        r = c.post("/api/auth/signup", json=body)
        assert r.status_code == 409, (k, r.text)
        assert set(r.json()) == {"code", "message"}
    assert c.post("/api/auth/signup", json={**NEW, "birth_date": 5}).status_code == 422  # 타입 오류는 500이 아니라 422
    assert c.post("/api/users/hong.gd/approve", headers=H["choi.qa"]).status_code == 403
    assert c.post("/api/users/hong.gd/approve", headers=H["admin"]).status_code == 200
    assert c.post("/api/auth/login", json={"emp_no": "hong.gd", "password": "hong12345"}).json()["otp_required"] is False

    # OTP 오류 후 재입력
    j = c.post("/api/auth/login", json={"emp_no": "lee.dwg", "password": "dwg1234"}).json()
    assert j["otp_required"]
    assert c.post("/api/auth/otp", json={"otp_token": j["otp_token"], "code": "000000"}).status_code == 401
    assert c.post("/api/auth/otp", json={"otp_token": j["otp_token"], "code": "123456"}).status_code == 200

    # 조회 전용 계정의 쓰기는 403
    qa = H["choi.qa"]
    assert c.post("/api/hulls", json={"HullNo": "Q1"}, headers=qa).status_code == 403
    assert c.post("/api/plans/1/progress", json={"WorkDt": "2026-10-19", "ProgressRate": 1}, headers=qa).status_code == 403
    assert c.get("/api/users", headers=qa).status_code == 403
    assert c.get("/api/dashboard").status_code == 401

    # 새 OTP 계정에는 데모 OTP 123456이 통하지 않는다 (실제 TOTP만)
    body = {**NEW, "emp_no": "otp.user", "email": "otp@swp.co.kr", "phone": "010-5151-6161", "totp_enabled": True, "group": "VIEW"}
    u = c.post("/api/users", json=body, headers=H["admin"]).json()
    secret = u["totp_secret_new"]
    assert secret and secret != "JBSWY3DPEHPK3PXP"
    j = c.post("/api/auth/login", json={"emp_no": "otp.user", "password": "hong12345"}).json()
    assert c.post("/api/auth/otp", json={"otp_token": j["otp_token"], "code": "123456"}).status_code == 401
    assert c.post("/api/auth/otp", json={"otp_token": j["otp_token"], "code": totp_now(secret)}).status_code == 200


def test_login_lock_after_5_failures(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"emp_no": "han.wk", "password": "bad-pw"}).status_code == 401
    r = client.post("/api/auth/login", json={"emp_no": "han.wk", "password": "wk1234"})
    assert r.status_code == 429 and r.json()["code"] == "TOO_MANY_ATTEMPTS"


def test_security_headers(client):
    r = client.get("/api/lookups")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"]
    assert "frame-src 'self' blob:" in r.headers["content-security-policy"] and "worker-src 'self' blob:" in r.headers["content-security-policy"]
    assert "content-security-policy" not in client.get("/docs").headers


# ---------- 시나리오 2: 호선→공정→도면→결재→실적→삭제 ----------
def test_hull_to_delivery_flow(client, H):
    c, pm, dwg, ad = client, H["park.pm"], H["lee.dwg"], H["admin"]
    hull = {"HullNo": "9100", "HullNm": "Test Ship", "ShipType": "LNG", "HullStatus": "PLAN", "ContractDt": "2026-01-01", "DeliveryDt": "2027-01-01"}
    assert c.post("/api/hulls", json={**hull, "DeliveryDt": "2025-12-31"}, headers=pm).status_code == 422  # 인도<계약
    r = c.post("/api/hulls", json=hull, headers=pm)
    assert r.status_code == 201 and len(r.json()["milestones"]) == 5
    assert c.post("/api/hulls", json=hull, headers=pm).status_code == 409
    b = c.post("/api/hulls/9100/blocks", json={"BlockCd": "101", "BlockNm": "선수", "BlockType": "FLAT", "WeightTon": 100}, headers=pm).json()

    def plan(proc, s, e, preds=()):
        r = c.post("/api/hulls/9100/plans", json={"BlockId": b["BlockId"], "ProcCd": proc, "PlanStartDt": s, "PlanEndDt": e, "preds": list(preds)}, headers=pm)
        assert r.status_code == 201, r.text
        return r.json()
    p1 = plan("CUT", "2026-11-01", "2026-11-14")
    p2 = plan("SUBASM", "2026-11-15", "2026-12-03", [p1["PlanId"]])
    r = c.put(f"/api/plans/{p1['PlanId']}", json={"BlockId": b["BlockId"], "ProcCd": "CUT", "PlanStartDt": "2026-11-01", "PlanEndDt": "2026-11-14", "preds": [p2["PlanId"]]}, headers=pm)
    assert r.status_code == 409 and r.json()["code"] == "CYCLE"

    d = c.post("/api/drawings", json={"DrawingNo": "9100-HULL-101", "DrawingNm": "테스트 도면", "HullNo": "9100", "BlockId": b["BlockId"], "Discipline": "HULL", "DesignerEmpNo": "lee.dwg"}, headers=dwg)
    assert d.status_code == 201, d.text
    did = d.json()["DrawingId"]
    assert c.post("/api/links", json={"drawing_id": did, "plan_id": p1["PlanId"], "required": True}, headers=pm).status_code == 201

    prog = f"/api/plans/{p1['PlanId']}/progress"
    r = c.post(prog, json={"WorkDt": "2026-10-19", "ProgressRate": 0}, headers=pm)
    assert r.status_code == 409 and r.json()["code"] == "DRAWING_GATE"  # 필수 도면 미배포 -> 착수 불가

    up = f"/api/drawings/{did}/revisions/0/file"
    assert c.post(up, files={"file": ("a.pdf", io.BytesIO(b"not a pdf"), "application/pdf")}, headers=dwg).status_code == 422
    r = c.post(up, files={"file": ("../../evil.pdf", io.BytesIO(PDF), "application/pdf")}, headers=dwg)
    assert r.status_code == 200 and r.json()["revisions"][0]["has_file"]
    got = c.get(up, headers=dwg)
    assert got.status_code == 200 and got.content.startswith(b"%PDF-") and got.headers["content-type"] == "application/pdf"

    assert c.post(f"/api/drawings/{did}/request", json={"a1": "lee.dwg", "a2": "lee.dwg"}, headers=dwg).status_code == 422  # 검토자=승인자
    assert c.post(f"/api/drawings/{did}/request", json={"a1": "lee.dwg", "a2": "admin"}, headers=dwg).status_code == 200
    inbox = c.get("/api/approvals/inbox", headers=ad).json()
    assert not [a for a in inbox["mine"] if a["DrawingId"] == did]  # 2단계는 1단계 완료 전 노출 안 됨
    a1 = [a for a in c.get("/api/approvals/inbox", headers=dwg).json()["mine"] if a["DrawingId"] == did][0]
    step2 = [x for x in c.get(f"/api/drawings/{did}", headers=dwg).json()["approvals"] if x["StepNo"] == 2][0]
    assert c.post(f"/api/approvals/{step2['ApprovalId']}/act", json={"result": "APPROVE"}, headers=ad).status_code == 409  # 앞 단계 미완료
    assert c.post(f"/api/approvals/{a1['ApprovalId']}/act", json={"result": "REJECT", "comment": " "}, headers=dwg).status_code == 422  # 반려 사유 필수
    assert c.post(f"/api/approvals/{a1['ApprovalId']}/act", json={"result": "APPROVE"}, headers=ad).status_code == 403  # 본인 배정 아님
    r = c.post(f"/api/approvals/{a1['ApprovalId']}/act", json={"result": "REJECT", "comment": "치수 오류"}, headers=dwg)
    assert r.status_code == 200 and r.json()["DwgStatus"] == "DRAFT"
    c.post(f"/api/drawings/{did}/request", json={"a1": "lee.dwg", "a2": "admin"}, headers=dwg)
    a1 = [a for a in c.get("/api/approvals/inbox", headers=dwg).json()["mine"] if a["DrawingId"] == did][0]
    assert c.post(f"/api/approvals/{a1['ApprovalId']}/act", json={"result": "APPROVE"}, headers=dwg).status_code == 200
    a2 = [a for a in c.get("/api/approvals/inbox", headers=ad).json()["mine"] if a["DrawingId"] == did][0]
    r = c.post(f"/api/approvals/{a2['ApprovalId']}/act", json={"result": "APPROVE"}, headers=ad)
    assert r.json()["DwgStatus"] == "APPROVED"
    assert c.post(up, files={"file": ("b.pdf", io.BytesIO(PDF), "application/pdf")}, headers=dwg).status_code == 409  # DRAFT 아님
    r = c.post(f"/api/drawings/{did}/revisions/0/issue", headers=dwg)
    assert r.status_code == 200 and r.json()["DwgStatus"] == "ISSUED"

    plans = {p["PlanId"]: p for p in c.get("/api/plans?hull=9100", headers=pm).json()}
    assert plans[p1["PlanId"]]["PlanStatus"] == "READY" and plans[p2["PlanId"]]["PlanStatus"] == "PLAN"
    r = c.post(prog, json={"WorkDt": "2026-10-19", "ProgressRate": 40}, headers=pm)
    assert r.status_code == 200 and r.json()["ProgressRate"] == 40 and r.json()["PlanStatus"] == "WORK"
    assert c.post(prog, json={"WorkDt": "2026-10-20", "ProgressRate": 50}, headers=pm).status_code == 422  # 미래 실적
    assert c.post(prog, json={"WorkDt": "2026-10-19", "ProgressRate": 101}, headers=pm).status_code == 422
    assert c.post(prog, json={"WorkDt": "2026-10-19", "ProgressRate": "x"}, headers=pm).status_code == 422
    r = c.post(prog, json={"WorkDt": "2026-10-19", "ProgressRate": 100}, headers=pm)  # 같은 날은 덮어쓴다
    assert r.json()["PlanStatus"] == "DONE" and r.json()["ActualEndDt"] == "2026-10-19"
    assert c.get(prog, headers=pm).json()["total"] == 1
    assert [p for p in c.get("/api/plans?hull=9100", headers=pm).json() if p["PlanId"] == p2["PlanId"]][0]["PlanStatus"] == "READY"

    assert c.delete("/api/hulls/9100", headers=pm).status_code == 200
    assert c.get("/api/hulls/9100", headers=pm).status_code == 404
    assert c.get(f"/api/drawings/{did}", headers=pm).status_code == 404
    assert c.get("/api/plans?hull=9100", headers=pm).json() == []


# ---------- 시나리오 3: 개정 영향 +1, 호선 상태 자동 전이 ----------
def test_revision_impact_and_hull_transition(client, H):
    c, dwg, ad, pm = client, H["lee.dwg"], H["admin"], H["park.pm"]
    before = len(c.get("/api/dashboard", headers=pm).json()["impacts"])
    d = [x for x in c.get("/api/drawings?q=8001-HULL-101", headers=dwg).json()["items"]][0]
    assert d["DwgStatus"] == "ISSUED"
    c.post(f"/api/drawings/{d['DrawingId']}/revisions", json={"ChangeDesc": "하중 조건 변경"}, headers=dwg)
    assert c.post(f"/api/drawings/{d['DrawingId']}/revisions", json={"ChangeDesc": "중복"}, headers=dwg).status_code == 409  # 진행 중 Rev
    c.post(f"/api/drawings/{d['DrawingId']}/request", json={"a1": "lee.dwg", "a2": "admin"}, headers=dwg)
    for h in (dwg, ad):
        a = [x for x in c.get("/api/approvals/inbox", headers=h).json()["mine"] if x["DrawingId"] == d["DrawingId"]][0]
        c.post(f"/api/approvals/{a['ApprovalId']}/act", json={"result": "APPROVE"}, headers=h)
    rev = c.get(f"/api/drawings/{d['DrawingId']}", headers=dwg).json()["revisions"][-1]["RevNo"]
    r = c.post(f"/api/drawings/{d['DrawingId']}/revisions/{rev}/issue", headers=dwg)
    assert r.status_code == 200 and r.json()["impact"]["count"] >= 1
    assert len(c.get("/api/dashboard", headers=pm).json()["impacts"]) >= before + 1
    statuses = [x["RevStatus"] for x in r.json()["revisions"]]
    assert statuses.count("ISSUED") == 1 and statuses[-1] == "ISSUED"  # 이전 배포본은 OBSOLETE

    # 설계 호선에 실적을 넣으면 건조로 전이
    c.post("/api/hulls", json={"HullNo": "9200", "HullStatus": "DESIGN"}, headers=pm)
    p = c.post("/api/hulls/9200/plans", json={"ProcCd": "CUT", "PlanStartDt": "2026-10-19", "PlanEndDt": "2026-11-10"}, headers=pm).json()
    assert c.post(f"/api/plans/{p['PlanId']}/progress", json={"WorkDt": "2026-10-19", "ProgressRate": 0}, headers=pm).json()["PlanStatus"] == "WORK"
    assert c.get("/api/hulls/9200", headers=pm).json()["HullStatus"] == "BUILD"
    c.delete("/api/hulls/9200", headers=pm)


def test_seed_matches_mockup(client, H):
    d = client.get("/api/dashboard", headers=H["choi.qa"]).json()
    assert d["today"] == "2026-10-19" and len(d["hulls"]) == 5
    assert d["plan_status"]["DELAY"] >= 1
    assert client.get("/api/weather?region=울산", headers=H["choi.qa"]).json()["state"] in ("live", "sample")
    assert client.get("/api/weather?region=서울", headers=H["choi.qa"]).status_code == 422


# ---------- 서버 페이징 ----------
def test_server_paging_and_sort(client, H):
    pm = H["park.pm"]
    a = client.get("/api/drawings?size=5&page=1&sort=DrawingNo&dir=asc", headers=pm).json()
    assert len(a["items"]) == 5 and a["total"] > 5 and a["pages"] == -(-a["total"] // 5)
    b = client.get("/api/drawings?size=5&page=2&sort=DrawingNo&dir=asc", headers=pm).json()
    assert b["page"] == 2 and not {x["DrawingId"] for x in a["items"]} & {x["DrawingId"] for x in b["items"]}
    d = client.get("/api/drawings?size=5&sort=DrawingNo&dir=desc", headers=pm).json()["items"]
    assert [x["DrawingNo"] for x in d] == sorted((x["DrawingNo"] for x in d), reverse=True)
    assert client.get("/api/drawings?size=5&page=999", headers=pm).json()["page"] == a["pages"]  # 범위 밖은 마지막 쪽
    assert client.get("/api/hulls?size=2", headers=pm).json()["total"] >= 5
    assert "pending" in client.get("/api/users", headers=H["admin"]).json()
    h = client.get("/api/hulls?sort=progress&dir=desc", headers=pm).json()["items"]
    assert [x["progress"] for x in h] == sorted((x["progress"] for x in h), reverse=True)  # 계산 열도 SQL 정렬
    assert client.get("/api/drawings?sort=DesignerNm&size=3", headers=pm).status_code == 200
    assert client.get("/api/drawings?q=%25", headers=pm).json()["total"] == 0  # LIKE 와일드카드는 글자로 취급
    assert client.get("/api/users?q=park&status=approved", headers=H["admin"]).json()["total"] >= 1
