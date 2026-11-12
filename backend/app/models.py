"""테이블·컬럼명은 목업(shipyard_mockup.html)의 DB.<테이블> 과 같다. 날짜는 ISO 문자열로 저장(문자열 비교가 곧 날짜 비교)."""
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

S = String


class CodeGroup(Base):
    __tablename__ = "TB_SYS_CodeGroup"
    CodeGroup: Mapped[str] = mapped_column(S(20), primary_key=True)
    CodeGroupName: Mapped[str] = mapped_column(S(50))
    Seq: Mapped[int] = mapped_column(Integer, default=0)
    UseYN: Mapped[bool] = mapped_column(Boolean, default=True)


class Code(Base):
    __tablename__ = "TB_SYS_Code"
    CodeGroup: Mapped[str] = mapped_column(S(20), primary_key=True)
    Code: Mapped[str] = mapped_column(S(20), primary_key=True)
    CodeName: Mapped[str] = mapped_column(S(50))
    Seq: Mapped[int] = mapped_column(Integer, default=0)
    UseYN: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(S(40), primary_key=True)
    email: Mapped[str] = mapped_column(S(100), unique=True)
    password_hash: Mapped[str] = mapped_column(S(100))
    display_name: Mapped[str] = mapped_column(S(50))
    emp_no: Mapped[str] = mapped_column(S(20), unique=True, index=True)
    status: Mapped[str] = mapped_column(S(10))  # pending|approved|rejected|disabled
    auth_provider: Mapped[str] = mapped_column(S(10), default="local")
    last_name: Mapped[str] = mapped_column(S(30))
    first_name: Mapped[str] = mapped_column(S(30))
    birth_date: Mapped[str | None] = mapped_column(S(10), nullable=True)
    phone: Mapped[str] = mapped_column(S(20))
    phone_digits: Mapped[str] = mapped_column(S(20), unique=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret: Mapped[str | None] = mapped_column(S(40), nullable=True)
    created_at: Mapped[str] = mapped_column(S(10))


class AuthGroup(Base):
    __tablename__ = "TB_SYS_AuthGroup"
    AuthCd: Mapped[str] = mapped_column(S(10), primary_key=True)
    AuthNm: Mapped[str] = mapped_column(S(30))


class AuthUser(Base):
    __tablename__ = "TB_SYS_AuthUser"
    AuthCd: Mapped[str] = mapped_column(S(10), primary_key=True)
    EmpNo: Mapped[str] = mapped_column(S(20), primary_key=True)


class MenuInfo(Base):
    __tablename__ = "TB_SYS_MenuInfo"
    MenuId: Mapped[str] = mapped_column(S(10), primary_key=True)
    SystemId: Mapped[str] = mapped_column(S(10), default="SHIP")
    ParentId: Mapped[str | None] = mapped_column(S(10), nullable=True)
    Title: Mapped[str] = mapped_column(S(50))
    TokenUrl: Mapped[str | None] = mapped_column(S(40), nullable=True)
    Seq: Mapped[int] = mapped_column(Integer, default=0)
    UseYN: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthMenu(Base):
    __tablename__ = "TB_SYS_AuthMenu"
    MenuId: Mapped[str] = mapped_column(S(10), primary_key=True)
    AuthCd: Mapped[str] = mapped_column(S(10), primary_key=True)
    AuthGbn: Mapped[str] = mapped_column(S(10))  # View|Write|Admin


class LogAccess(Base):
    __tablename__ = "TB_SYS_LogAccess"
    LogId: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    UserId: Mapped[str] = mapped_column(S(20))
    LoginDt: Mapped[str] = mapped_column(S(16))
    LogoutDt: Mapped[str | None] = mapped_column(S(16), nullable=True)
    IpAddress: Mapped[str | None] = mapped_column(S(45), nullable=True)


class Proc(Base):
    __tablename__ = "TB_PRC_Proc"
    ProcCd: Mapped[str] = mapped_column(S(10), primary_key=True)
    ProcNm: Mapped[str] = mapped_column(S(30))
    ProcGroup: Mapped[str] = mapped_column(S(10))
    StdDays: Mapped[int] = mapped_column(Integer)
    Seq: Mapped[int] = mapped_column(Integer)
    UseYN: Mapped[bool] = mapped_column(Boolean, default=True)


class Hull(Base):
    __tablename__ = "TB_MST_Hull"
    HullNo: Mapped[str] = mapped_column(S(20), primary_key=True)
    HullNm: Mapped[str | None] = mapped_column(S(100), nullable=True)
    ShipType: Mapped[str | None] = mapped_column(S(10), nullable=True)
    HullStatus: Mapped[str] = mapped_column(S(10), default="PLAN")
    OwnerNm: Mapped[str | None] = mapped_column(S(100), nullable=True)
    ClassSociety: Mapped[str | None] = mapped_column(S(30), nullable=True)
    LengthM: Mapped[float | None] = mapped_column(Float, nullable=True)
    BreadthM: Mapped[float | None] = mapped_column(Float, nullable=True)
    DepthM: Mapped[float | None] = mapped_column(Float, nullable=True)
    DeadWeight: Mapped[float | None] = mapped_column(Float, nullable=True)
    DockNo: Mapped[str | None] = mapped_column(S(30), nullable=True)
    ContractDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    DeliveryDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    Remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    UseYN: Mapped[bool] = mapped_column(Boolean, default=True)
    CreateUserId: Mapped[str | None] = mapped_column(S(20), nullable=True)
    CreateDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    ModifyUserId: Mapped[str | None] = mapped_column(S(20), nullable=True)
    ModifyDt: Mapped[str | None] = mapped_column(S(10), nullable=True)


class Milestone(Base):
    __tablename__ = "TB_MST_HullMilestone"
    HullNo: Mapped[str] = mapped_column(ForeignKey("TB_MST_Hull.HullNo", ondelete="CASCADE"), primary_key=True)
    MilestoneCd: Mapped[str] = mapped_column(S(10), primary_key=True)
    PlanDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    ActualDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    Remark: Mapped[str | None] = mapped_column(Text, nullable=True)


class Block(Base):
    __tablename__ = "TB_MST_Block"
    BlockId: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    HullNo: Mapped[str] = mapped_column(ForeignKey("TB_MST_Hull.HullNo", ondelete="CASCADE"), index=True)
    BlockCd: Mapped[str] = mapped_column(S(20))
    BlockNm: Mapped[str | None] = mapped_column(S(100), nullable=True)
    BlockType: Mapped[str | None] = mapped_column(S(10), nullable=True)
    ParentBlockId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    WeightTon: Mapped[float | None] = mapped_column(Float, nullable=True)
    UseYN: Mapped[bool] = mapped_column(Boolean, default=True)


class Plan(Base):
    __tablename__ = "TB_PRC_Plan"
    PlanId: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    HullNo: Mapped[str] = mapped_column(ForeignKey("TB_MST_Hull.HullNo", ondelete="CASCADE"), index=True)
    BlockId: Mapped[int | None] = mapped_column(ForeignKey("TB_MST_Block.BlockId", ondelete="CASCADE"), nullable=True)
    ProcCd: Mapped[str] = mapped_column(ForeignKey("TB_PRC_Proc.ProcCd"))
    PlanStartDt: Mapped[str] = mapped_column(S(10))
    PlanEndDt: Mapped[str] = mapped_column(S(10))
    ActualStartDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    ActualEndDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    ProgressRate: Mapped[int] = mapped_column(Integer, default=0)
    PlanStatus: Mapped[str] = mapped_column(S(10), default="PLAN")
    ManagerEmpNo: Mapped[str | None] = mapped_column(S(20), nullable=True)
    Remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    CreateUserId: Mapped[str | None] = mapped_column(S(20), nullable=True)
    CreateDt: Mapped[str | None] = mapped_column(S(10), nullable=True)


class PlanDep(Base):
    __tablename__ = "TB_PRC_PlanDep"
    PlanId: Mapped[int] = mapped_column(ForeignKey("TB_PRC_Plan.PlanId", ondelete="CASCADE"), primary_key=True)
    PredPlanId: Mapped[int] = mapped_column(ForeignKey("TB_PRC_Plan.PlanId", ondelete="CASCADE"), primary_key=True)
    LagDays: Mapped[int] = mapped_column(Integer, default=0)


class Progress(Base):
    __tablename__ = "TB_PRC_Progress"
    ProgressId: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    PlanId: Mapped[int] = mapped_column(ForeignKey("TB_PRC_Plan.PlanId", ondelete="CASCADE"), index=True)
    WorkDt: Mapped[str] = mapped_column(S(10))
    ProgressRate: Mapped[int] = mapped_column(Integer)
    ManHour: Mapped[float | None] = mapped_column(Float, nullable=True)
    WorkerCnt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    WorkerEmpNo: Mapped[str | None] = mapped_column(S(20), nullable=True)
    Remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    CreateDt: Mapped[str | None] = mapped_column(S(10), nullable=True)


class Drawing(Base):
    __tablename__ = "TB_DWG_Drawing"
    DrawingId: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    DrawingNo: Mapped[str] = mapped_column(S(40), unique=True)
    DrawingNm: Mapped[str] = mapped_column(S(100))
    HullNo: Mapped[str] = mapped_column(ForeignKey("TB_MST_Hull.HullNo", ondelete="CASCADE"), index=True)
    BlockId: Mapped[int | None] = mapped_column(ForeignKey("TB_MST_Block.BlockId", ondelete="SET NULL"), nullable=True)
    Discipline: Mapped[str] = mapped_column(S(10))
    DwgStatus: Mapped[str] = mapped_column(S(10), default="DRAFT")
    CurrentRevNo: Mapped[int] = mapped_column(Integer, default=0)
    DesignerEmpNo: Mapped[str | None] = mapped_column(S(20), nullable=True)
    UseYN: Mapped[bool] = mapped_column(Boolean, default=True)
    CreateUserId: Mapped[str | None] = mapped_column(S(20), nullable=True)
    CreateDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    ModifyUserId: Mapped[str | None] = mapped_column(S(20), nullable=True)
    ModifyDt: Mapped[str | None] = mapped_column(S(10), nullable=True)


class Revision(Base):
    __tablename__ = "TB_DWG_Revision"
    DrawingId: Mapped[int] = mapped_column(ForeignKey("TB_DWG_Drawing.DrawingId", ondelete="CASCADE"), primary_key=True)
    RevNo: Mapped[int] = mapped_column(Integer, primary_key=True)
    RevStatus: Mapped[str] = mapped_column(S(10))
    ChangeDesc: Mapped[str | None] = mapped_column(Text, nullable=True)
    FileId: Mapped[str | None] = mapped_column(S(40), nullable=True)  # 서버가 만든 UUID. 원본 파일명은 FileNm(표시용)
    FileNm: Mapped[str | None] = mapped_column(S(200), nullable=True)
    AuthorEmpNo: Mapped[str | None] = mapped_column(S(20), nullable=True)
    IssueDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
    CreateDt: Mapped[str | None] = mapped_column(S(10), nullable=True)


class Approval(Base):
    __tablename__ = "TB_DWG_Approval"
    ApprovalId: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    DrawingId: Mapped[int] = mapped_column(ForeignKey("TB_DWG_Drawing.DrawingId", ondelete="CASCADE"), index=True)
    RevNo: Mapped[int] = mapped_column(Integer)
    StepNo: Mapped[int] = mapped_column(Integer)
    ApproverEmpNo: Mapped[str] = mapped_column(S(20))
    Result: Mapped[str] = mapped_column(S(10))  # WAIT|APPROVE|REJECT
    Comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    ActDt: Mapped[str | None] = mapped_column(S(16), nullable=True)


class PlanLink(Base):
    __tablename__ = "TB_DWG_PlanLink"
    DrawingId: Mapped[int] = mapped_column(ForeignKey("TB_DWG_Drawing.DrawingId", ondelete="CASCADE"), primary_key=True)
    PlanId: Mapped[int] = mapped_column(ForeignKey("TB_PRC_Plan.PlanId", ondelete="CASCADE"), primary_key=True)
    RequiredYN: Mapped[bool] = mapped_column(Boolean, default=True)
    NeedDt: Mapped[str | None] = mapped_column(S(10), nullable=True)
