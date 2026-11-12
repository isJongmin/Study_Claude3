# 조선소 통합관리 (FastAPI + Vue3 + SQLite)

`origin/shipyard_mockup.html`을 3-tier 웹 시스템으로 옮긴 프로젝트입니다. 호선·공정·도면을 관리하고, 업무 규칙(도면 게이트·결재·상태 계산)은 서버가 판정합니다. 기준일은 `2026-10-19`로 고정입니다.

## 실행 (Windows)
`start.bat`을 더블클릭하면 가상환경·패키지 설치 → 서버 시작 → 브라우저(http://127.0.0.1:5173)가 열립니다. Ctrl+C로 종료합니다.
필요: Python 3.11+, Node 20+.

수동 실행:
```
python -m venv backend\.venv && backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm --prefix frontend ci
python scripts\dev.py            # API 8000 + 화면 5173
```
화면을 빌드해 FastAPI 하나로 띄우려면 `npm --prefix frontend run build` 후 `uvicorn app.main:app --app-dir backend` (http://127.0.0.1:8000). macOS·Linux는 `.venv/bin/python`을 사용합니다.

## 데모 계정
| 아이디 | 비밀번호 | 권한 | 비고 |
|---|---|---|---|
| admin | admin1234 | 시스템관리자 | OTP 123456 |
| park.pm | pm1234 | 공정관리자 | |
| lee.dwg | dwg1234 | 도면관리자 | OTP 123456 |
| han.wk | wk1234 | 공정관리자 | |
| choi.qa | qa1234 | 조회전용 | |

데모 OTP `123456`은 시드 계정에만 통합니다. 관리자가 새로 켠 OTP 계정은 무작위 비밀키(저장 직후 한 번 표시)와 실제 TOTP 앱을 써야 합니다.
DB는 처음 실행할 때 `backend/app/seed_data.json`(목업의 `seed()` 결과)으로 채워집니다. 초기화하려면 `backend/shipyard.db`와 `backend/uploads/`를 지웁니다.

## 구조
```
backend/app/        main.py(보안 헤더·화면 제공) models.py security.py deps.py errors.py seed.py
                    routers/api.py(권한·입출력)  services/(rules·workflow·files·weather: 업무 규칙)
backend/mcp_servers/weather_server.py   MCP 도구 get_weather (백엔드가 stdio로 호출)
backend/tests/      pytest 시나리오      frontend/  Vue3+Pinia+Vite, e2e/ Playwright
scripts/            dump_mock_seed.mjs  dev.py  verify.py  e2e_server.py
docs/               SPEC.md(규칙 번호) API.md(경로·권한·키) HANDOFF.md
.claude/skills/     verify, report       .mcp.json  shipyard-weather, playwright
```
규칙 목록은 `docs/SPEC.md`, API 계약은 `docs/API.md`, Swagger는 `/docs`입니다.

## 검사
```
python scripts/verify.py --e2e     # ruff → pytest → vue-tsc → vite build → playwright
python scripts/verify.py --only pytest
```
처음 한 번 `npx playwright install chromium`이 필요합니다. 시나리오 테스트는 가입·승인·OTP·권한, 호선→공정→도면→결재→배포→실적→삭제, 개정 영향·호선 상태 전이, 360~1440px 반응형을 다룹니다.

## 날씨 (MCP)
화면 상단 날씨는 `GET /api/weather`가 `weather_server.py`(MCP `get_weather`, Open-Meteo)를 호출해 10분 캐시합니다. 네트워크·MCP 실패 시 샘플값과 "샘플" 배지로 대체합니다.

## 알려진 한계
- JWT 비밀키 기본값은 개발용입니다. 운영에서는 `SWP_JWT_SECRET` 환경변수를 설정하세요.
- 로그인 잠금(5회/5분)은 서버 프로세스 메모리에 저장되어 재시작하면 초기화됩니다.
- 공정 선·후행의 일정 겹침 경고는 화면에서만 확인합니다(서버는 저장 허용).
