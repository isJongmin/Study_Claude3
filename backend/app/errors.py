from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def bad(msg, code="VALIDATION"):
    return AppError(422, code, msg)  # 입력값 오류(형식·범위·참조)는 422


def conflict(msg, code="CONFLICT"):
    return AppError(409, code, msg)


def forbidden(msg="이 작업을 수행할 권한이 없습니다. 관리자에게 권한 그룹 변경을 요청하세요."):
    return AppError(403, "FORBIDDEN", msg)


def missing(what):
    return AppError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없습니다. 삭제되었을 수 있으니 목록을 새로고침하세요.")


def _resp(status, code, message):
    return JSONResponse({"code": code, "message": message}, status_code=status)


def install(app: FastAPI):
    @app.exception_handler(AppError)
    async def _app(_: Request, e: AppError):
        return _resp(e.status, e.code, e.message)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, e: HTTPException):
        msg = {404: "요청한 주소를 찾을 수 없습니다.", 405: "허용되지 않는 요청 방식입니다."}.get(e.status_code, str(e.detail))
        return _resp(e.status_code, "NOT_FOUND" if e.status_code == 404 else "HTTP_ERROR", msg)

    @app.exception_handler(RequestValidationError)
    async def _val(_: Request, e: RequestValidationError):
        f = ", ".join(sorted({str(x["loc"][-1]) for x in e.errors() if x.get("loc")})) or "입력값"
        return _resp(422, "VALIDATION", f"입력 형식이 올바르지 않습니다 ({f}). 값의 형식과 범위를 확인한 뒤 다시 시도하세요.")

    @app.exception_handler(Exception)
    async def _any(_: Request, e: Exception):
        return _resp(500, "SERVER_ERROR", "서버 처리 중 오류가 발생했습니다. 잠시 후 다시 시도하고, 반복되면 관리자에게 문의하세요.")
