# 조선소 통합관리 구현 가이드

`origin/shipyard_mockup.html`(목업)을 FastAPI + Vue3 + SQLite 3-tier로 옮긴다. 과제는 `origin/problem_sheet.html`, 보고서 양식은 `origin/completion_report_sample.html`.
목업이 기능·문구·시드의 원본이다. 이 문서는 **무엇을, 어떤 순서로, 무엇을 조심해서** 만들지만 정한다.

**실행 방법:** 새 폴더에 `origin/`, 이 파일, 과제에서 받은 `extract_usage.py`를 넣는다. Claude Code를 열고 단계마다 새 세션에서 입력한다. 읽은 내용은 그 세션의 매 호출에 다시 실리므로, 단계마다 필요한 절만 읽는다.
1. "GUIDE.md 0~3, 5, 7, 8절을 읽고 1단계를 진행해"
2. "GUIDE.md 0, 2, 4, 7절과 docs/HANDOFF.md, docs/API.md를 읽고 2단계를 진행해"
3. "GUIDE.md 5~8절과 docs/HANDOFF.md를 읽고 3단계를 진행해"
4. "GUIDE.md 8절 보고서 부분만 읽고 보고서를 만들어"

1단계는 7절(토큰 규칙)과 4절 핵심을 `CLAUDE.md`(30줄 이내)에 옮긴다. CLAUDE.md는 세션마다 자동으로 읽히므로 길게 쓰지 않는다.
각 단계는 끝에 `docs/HANDOFF.md`를 고정 형식으로 덮어쓴다: 끝난 단계 / 만든 파일(폴더 단위) / 남은 일 / 판단한 내용 / 알려진 문제. 다음 세션은 코드를 훑지 말고 이 파일과 필요한 파일만 연다.

권한 확인 없이 진행하려면 전용 폴더에서 `claude --dangerously-skip-permissions`로 연다.

## 0. 고정 조건
- 기준일 `2026-10-19` 고정. 업무 판정에 `date.today()`를 쓰지 않는다.
- 시드와 데모 계정은 목업 그대로: `admin/admin1234`, `park.pm/pm1234`, `lee.dwg/dwg1234`, `han.wk/wk1234`, `choi.qa/qa1234`(OTP 계정은 123456).
- 테이블·컬럼명은 목업과 같게(`TB_MST_Hull`, `HullNo` …).
- 제출물: 소스, README, 완료보고서 HTML·PDF, `report_data.json`(과제 제공 `extract_usage.py`로 추출). Skill과 MCP를 실제로 써야 한다.

## 1. 진행 순서 (세션 3개 + 보고서)
세션이 길수록 매 호출 비용이 커지므로 단계마다 새 세션을 연다. 세션 사이에는 `docs/HANDOFF.md`(15줄)로만 넘긴다.

| 순서 | 할 일 | 모델 |
|---|---|---|
| 1 백엔드 | 목업에서 규칙을 뽑아 `docs/SPEC.md`(규칙 번호 목록) 작성 → 모델·시드·서비스·API·날씨 MCP. 끝에 `docs/API.md`(경로·권한·요청/응답 키, 80줄) | Opus |
| 2 프런트 | 공통 부품 → 대시보드 → 나머지 화면. `docs/API.md`와 4절만 보고 만든다 | Opus |
| 3 테스트·검증 | 6절 시나리오로 pytest·Playwright 작성 → 전체 검사 **한 번** → 실패만 고쳐 그 부분만 재실행 → Playwright MCP로 화면 1회 확인 → README | Opus |
| 보고서 | 3단계 끝에 `python extract_usage.py`로 집계를 고정한 뒤, 새 세션에서 보고서만 작성(이 세션은 집계에 넣지 않는다) | Sonnet |

중간 단계에서는 빌드·테스트를 돌리지 않는다. 서브에이전트는 쓰지 않는다(맥락을 새로 읽느라 토큰이 더 든다).

## 2. 구조
```
backend/app/        main.py(앱, 보안 헤더, frontend/dist 제공) config.py database.py models.py schemas.py
                    security.py(bcrypt·JWT·TOTP) deps.py(current, require(VIEW|WRITE, 메뉴)) errors.py({code,message})
                    seed.py(빈 DB에 seed_data.json 적재) routers/api.py(권한과 입출력만)
                    services/(규칙. 공정 상태·게이트·영향은 rules.py 한 곳) 
backend/mcp_servers/weather_server.py   MCP 도구 get_weather. 백엔드가 stdio로 호출
backend/tests/      conftest.py(임시 DB 복사) + 규칙별 테스트
frontend/src/       api.ts composables.ts(useLoad·useWrite) router.ts stores/ components/ views/
frontend/e2e/       Playwright. 빌드 화면을 FastAPI로 띄워 검사
scripts/            dump_mock_seed.mjs  dev.py  verify.py      start.bat(설치+실행+브라우저 열기)
.claude/skills/verify/SKILL.md   "verify.py --e2e를 돌리고 실패 단계만 고친다" (과제의 Skill 사용)
.mcp.json           shipyard-weather(위 서버), playwright
```
- **시드:** `scripts/dump_mock_seed.mjs`가 목업의 `seed()`를 Node `vm`으로 실행해 `backend/app/seed_data.json`을 만든다. 손으로 옮기지 않는다.
- **verify.py:** ruff → pytest → vue-tsc → vite build → playwright를 차례로 실행하고, 단계별 PASS/FAIL과 실패 꼬리 40줄만 출력한다.

## 3. 구현할 기능
**필수**
- 회원가입(성·이름·생년월일·이메일·전화·아이디·비밀번호) → 관리자 승인 → 로그인(JWT). 권한그룹별 메뉴(View<Write<Admin), 쓰기 API는 Write 이상, 아니면 403.
- 호선 CRUD(마일스톤 5종 자동 생성, 블록, 삭제 시 하위 전부 함께 삭제).
- 공정 계획 CRUD, 선후행(순환 금지), 일별 실적 → 진척률·상태 자동 계산.
- 도면 CRUD, Rev 이력, 2단계 결재(검토→승인), 반려, 배포.
- 필수 규칙: ① 필수 연계 도면이 배포 전이면 착수 불가 ② 권한 없는 요청 403 ③ 아이디·이메일·전화 중복 불가.

**선택(모두 구현)**: 대시보드(KPI·차트), 간트, 최근 30일 개정 영향, 호선 상태 자동 전이, OTP 2차 인증, 도면 PDF 업로드·보기, 날씨(MCP).

## 4. 디자인
- 업무 앱. 상단(화면 검색·날씨·계정 메뉴), 왼쪽 메뉴(접기, 1024px 미만은 서랍), 가운데 열린 탭 + 작업 영역. 상세는 모달과 하위 탭.
- 색은 `:root` 변수로만 쓴다.
  - 배경 `#F4F6FA`, 카드 흰색, 주색 `#3182F6`
  - 상태색: 계획 회청, 착수가능 청록, 진행 파랑, 완료 초록, 지연 분홍빨강, 검토 주황, 승인 보라
  - 글꼴 Pretendard, 숫자는 `tabular-nums`
- 간격 4px 단위, 모서리 12/16/20px, 그림자는 약하게. 주 버튼은 채운 파란색 하나, 위험 행동은 빨강 + 확인 대화상자.
- 대시보드 순서: KPI 4개 → 호선 진척 → 공정·도면 분포 → 조치 필요(지연·도면 대기·개정 영향).
  - 호선 진척: 흰 선체 SVG 5척을 한 줄로, 물 높이 = 진척률, 숫자를 함께 표시. 처음 한 번만 차오른다(반복 물결 없음).
  - 도넛: 범례에 건수와 비율.
- 표: 글자·날짜는 왼쪽, 수치·행동 버튼은 오른쪽. 짧은 열은 내용 폭, 긴 글 열만 남는 폭을 가진다. 모바일은 행을 카드로 바꾼다.
- 토스트: 성공 4초, 오류 6초. 모달·서랍은 200ms 안팎. `prefers-reduced-motion`이면 끈다.
- 점검 기준: 360~1440px에서 가로 넘침·화면 밖 버튼·세로 스크롤 2개가 없다. 팝업이 열리면 뒤 페이지는 고정된다.

## 5. 유의할 점
- **규칙은 서버가 판정한다.** 화면의 비활성화는 편의일 뿐이다. 모든 업무 쓰기 뒤에 공정·호선 상태를 재계산한다.
- **공정 상태:** 진척 ≥100 완료 / 착수(실적 또는 착수일 있음) 후 계획종료<기준일이면 지연, 아니면 진행 / 착수 전 계획종료<기준일이면 지연 / 선행이 모두 완료이고 게이트 통과면 착수가능, 아니면 계획.
- **실적:** 같은 날은 덮어쓴다. 누적 진척 = 가장 늦은 작업일 값, 착수일 = 가장 이른 작업일. 모두 지우면 착수 전으로 돌아간다.
  - 목업 시드는 최근 3일 실적만 있다. 시드 스크립트에서 실제착수일에 0% "착수" 실적을 더해야 실적 한 건 저장으로 착수일이 밀리지 않는다.
- **도면 게이트:** 첫 실적이 착수다(0%도). 필수 연계 도면에 배포본이 없으면 409. 개정 중이어도 이전 배포본이 있으면 통과한다.
- **결재:** 검토자≠승인자, 본인 배정·앞 단계 완료만 처리. 반려는 의견 필수, 도면을 DRAFT로 되돌린다. 배포하면 이전 배포본은 OBSOLETE.
- **보안:**
  - 데모 OTP 123456은 시드 비밀키 계정에만 통하게 한다(모든 계정에 열면 2차 인증 우회).
  - 응답에 CSP·`X-Frame-Options`·`nosniff`를 붙인다. PDF 보기에 `connect-src`·`worker-src blob:`가 필요하고, Swagger `/docs`는 CSP에서 뺀다.
  - 업로드 파일명은 서버가 만든 UUID만 쓴다. PDF는 `%PDF-` 시그니처와 30MB 이하를 확인한다.
  - 로그인·OTP 실패 5회면 5분간 429.
- **오류:** 오류 응답은 `{code, message}`, 문구는 한국어로 해결 방법까지 적는다. 잘못된 타입 입력은 500이 아니라 422로 막는다.
- **테스트:** Playwright 실패는 대개 셀렉터·로딩 대기 문제다. 앱을 고치기 전에 셀렉터부터 본다. 화면 요소에 `data-test` 속성을 미리 붙여 둔다.

## 6. 테스트 시나리오 (3단계에서 한 번에)
1. 가입 → 승인 전 로그인 거부 → 중복 409 → 승인 → 로그인. OTP 오류 후 재입력. 조회 전용 계정의 쓰기 403. 새 OTP 계정에 123456이 안 통한다.
2. 호선 등록(인도일<계약일 거부) → 블록 → 공정 2개·선후행 → 순환 거부 → 도면 연계 → 게이트로 실적 409 → PDF 업로드 → 결재 → 반려 사유 필수 → 2단계 승인 → 배포 → 실적 40%·100% → 호선 삭제 시 하위 데이터 삭제.
3. 배포 도면 개정·재배포 → 대시보드 개정 영향 +1. 설계 호선에 실적을 넣으면 건조로 전이.
4. 1440·768·390px에서 주요 화면의 가로 넘침·콘솔 오류 없음.

## 7. 토큰 규칙 (CLAUDE.md에도 옮겨 둔다)
- 목업은 전체를 읽지 않는다. Grep으로 찾고 필요한 줄만 읽는다. 규칙은 한 번 뽑아 SPEC에 적은 뒤 SPEC만 본다.
- 파일은 한 번에 완성해서 쓰고, 방금 쓴 파일을 다시 읽지 않는다. 같은 파일을 여러 번 조금씩 고치지 않는다.
- 명령 출력은 꼬리만 본다. 설치는 `-q`. 수정 요청은 번호를 붙여 한 번에 보낸다.
- 보고서: `report_data.json`은 손으로 고치지 않는다. 보고서 HTML의 Skill·MCP 용도·효과와 서술은 실제 있었던 일만 적는다.

## 8. 스킬·MCP·실행 파일·보고서

과제는 Skill과 MCP를 **실제로 쓰고** 보고서에 용도·효과를 적어야 한다. 아래는 1단계 시작 때 만든다(각 몇 줄).

**스킬** (`.claude/skills/<이름>/SKILL.md`, 머리에 `name`, `description`)
- `verify`: "`python scripts/verify.py --e2e`를 실행하고, 실패한 단계만 고쳐 그 단계만 다시 돌린다. 결과는 단계별 PASS/FAIL로 보고한다." → 3단계에서 사용.
- `report`: 아래 보고서 절차 그대로 → 보고서 세션에서 사용.

**MCP** (`.mcp.json`)
```json
{"mcpServers": {
  "shipyard-weather": {"command": "backend/.venv/Scripts/python.exe", "args": ["backend/mcp_servers/weather_server.py"]},
  "playwright": {"command": "npx", "args": ["-y", "@playwright/mcp@0.0.84", "--headless"]}}}
```
- `weather_server.py`: `mcp` 패키지의 FastMCP로 도구 `get_weather(region)` 하나를 만든다. 지역은 울산(35.54, 129.31), 거제(34.88, 128.62), 목포(34.81, 126.39). Open-Meteo 현재값(기온·습도·풍속·날씨코드)을 반환한다.
- 백엔드는 이 서버를 stdio MCP 클라이언트로 호출한다. 결과는 10분 캐시하고, 실패하면 목업 샘플값을 `state: "sample"`로 돌려준다.
- Playwright MCP는 3단계 끝에 빌드 화면의 대시보드를 한 번 열어 확인하는 데 쓴다(반복 검사는 E2E로 한다).
- macOS·Linux는 `.venv/bin/python`.

**쉽게 실행하기**
- `start.bat`(Windows)가 하는 일:
  1. `backend\.venv`가 없으면 만들고 `pip install -q -r backend\requirements.txt`를 실행한다.
  2. `frontend\node_modules`가 없으면 `npm --prefix frontend ci`를 실행한다.
  3. API(8000)와 화면(5173)이 응답하면 브라우저를 여는 PowerShell 대기 루프를 백그라운드로 띄운다.
  4. `python scripts/dev.py`를 실행한다. 이 스크립트가 uvicorn과 vite를 함께 띄우고, Ctrl+C로 둘 다 끈다.
- 첫 줄에 `chcp 65001`. 파일은 CRLF로 저장한다.

**보고서** (개발이 끝난 뒤 새 세션, Sonnet)
1. 3단계 마지막에 `python extract_usage.py`로 `report_data.json`을 만들어 고정한다. 보고서 세션에서는 다시 실행하지 않는다. 그래야 보고서 작성 토큰이 집계에 들어가지 않는다.
2. `origin/completion_report_sample.html`을 `completion_report.html`로 복사해 고친다.
   - 작성자·작성일·개요, 구현 범위표(필수·선택 기능별 완료/일부/제외와 비고), 바이브 코딩 서술을 쓴다. 서술은 `docs/HANDOFF.md`와 검증 결과의 사실만 담는다.
   - `</body>` 앞에 `<script>`를 넣는다. `report_data.json` 내용을 상수로 넣고 양식의 `render(데이터)`를 호출한다. 이어서 Skill·MCP 표의 `(작성)` 칸을 이름별 용도·효과로 채운다.
   - 집계에 안 잡히는 것(백엔드가 부르는 날씨 MCP)은 표에 행으로 추가한다. 서브에이전트를 썼다면 그 토큰이 빠졌다고 적는다.
3. PDF: `frontend` 폴더에서 `npx playwright pdf --paper-format=A4 <completion_report.html의 file:// 주소> ../completion_report.pdf`.
4. 호출 횟수가 0인 도구를 썼다고 쓰지 않는다. `report_data.json`은 손으로 고치지 않는다.
