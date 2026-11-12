from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, database, errors
from .routers import api
from .seed import seed_if_empty

CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
       "font-src 'self' data: https://cdn.jsdelivr.net; script-src 'self'; connect-src 'self' blob:; worker-src 'self' blob:; "
       "frame-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'")
NO_CSP = ("/docs", "/redoc", "/openapi.json")  # Swagger는 CDN 스크립트를 쓰므로 CSP에서 뺀다


@asynccontextmanager
async def lifespan(_: FastAPI):
    with database.SessionLocal() as db:
        seed_if_empty(db, database.engine)
    yield


app = FastAPI(title="조선소 통합관리", lifespan=lifespan)
errors.install(app)
app.include_router(api.r)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "same-origin"
    if not request.url.path.startswith(NO_CSP):
        resp.headers["Content-Security-Policy"] = CSP
    return resp


if config.DIST_DIR.is_dir():  # 빌드된 화면 제공 + SPA 새로고침 대응
    app.mount("/assets", StaticFiles(directory=config.DIST_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (config.DIST_DIR / path).resolve()
        if path and f.is_file() and config.DIST_DIR.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(config.DIST_DIR / "index.html")
