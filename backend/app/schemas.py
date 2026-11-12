from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def _dt(v: str) -> str:
    date.fromisoformat(v)  # 잘못된 날짜는 ValueError -> 422
    return v


Dt = Annotated[str, AfterValidator(_dt)]
Str = Annotated[str, Field(max_length=200)]


class SignupIn(BaseModel):
    last_name: Str
    first_name: Str
    birth_date: Dt
    email: Str
    phone: Str
    emp_no: Str
    password: Annotated[str, Field(max_length=72)]


class LoginIn(BaseModel):
    emp_no: Str
    password: Annotated[str, Field(max_length=72)]


class OtpIn(BaseModel):
    otp_token: str
    code: Annotated[str, Field(max_length=10)]


class UserIn(SignupIn):
    password: Annotated[str, Field(max_length=72)] = ""
    status: str = "approved"
    group: str | None = None
    totp_enabled: bool = False


class HullIn(BaseModel):
    HullNo: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,20}$")]
    HullNm: Str | None = None
    ShipType: str | None = None
    HullStatus: str = "PLAN"
    OwnerNm: Str | None = None
    ClassSociety: Str | None = None
    LengthM: Annotated[float, Field(ge=0)] | None = None
    BreadthM: Annotated[float, Field(ge=0)] | None = None
    DepthM: Annotated[float, Field(ge=0)] | None = None
    DeadWeight: Annotated[float, Field(ge=0)] | None = None
    DockNo: Str | None = None
    ContractDt: Dt | None = None
    DeliveryDt: Dt | None = None
    Remark: Annotated[str, Field(max_length=2000)] | None = None
    UseYN: bool = True


class MilestoneItem(BaseModel):
    MilestoneCd: str
    PlanDt: Dt | None = None
    ActualDt: Dt | None = None


class BlockIn(BaseModel):
    BlockCd: Annotated[str, Field(min_length=1, max_length=20)]
    BlockNm: Str | None = None
    BlockType: str | None = None
    WeightTon: Annotated[float, Field(ge=0)] | None = None


class PlanIn(BaseModel):
    BlockId: int | None = None
    ProcCd: str
    PlanStartDt: Dt
    PlanEndDt: Dt
    ManagerEmpNo: str | None = None
    Remark: Annotated[str, Field(max_length=2000)] | None = None
    preds: list[int] = []


class ProgressIn(BaseModel):
    WorkDt: Dt
    ProgressRate: Annotated[int, Field(ge=0, le=100)]
    ManHour: Annotated[float, Field(ge=0)] | None = None
    WorkerCnt: Annotated[int, Field(ge=0)] | None = None
    WorkerEmpNo: str | None = None
    Remark: Annotated[str, Field(max_length=500)] | None = None


class DrawingIn(BaseModel):
    DrawingNo: Annotated[str, Field(min_length=1, max_length=40)]
    DrawingNm: Annotated[str, Field(min_length=1, max_length=100)]
    HullNo: str
    BlockId: int | None = None
    Discipline: str
    DesignerEmpNo: str | None = None


class RevIn(BaseModel):
    ChangeDesc: Annotated[str, Field(min_length=1, max_length=500)]


class RequestIn(BaseModel):
    a1: str
    a2: str


class ActIn(BaseModel):
    result: Annotated[str, Field(pattern="^(APPROVE|REJECT)$")]
    comment: Annotated[str, Field(max_length=500)] = ""


class LinkIn(BaseModel):
    drawing_id: int
    plan_id: int
    required: bool = True
