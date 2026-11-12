# HANDOFF (전체 완료, 보고서 작성됨)
**끝난 단계:** 1 백엔드 · 2 프런트 · 3 테스트·검증·README. `report_data.json` 고정(extract_usage.py 1회 실행, 다시 실행 금지).
**만든 파일(폴더):** `backend/`(app, mcp_servers, tests) · `frontend/`(src: api·composables·router·stores·components·views, e2e, playwright.config.ts) · `scripts/`(dump_mock_seed.mjs, dev.py, verify.py, e2e_server.py) · `docs/` · `.claude/skills/{verify,report}` · `.mcp.json` · `start.bat` · `README.md` · `report_data.json`
**남은 일:** 없음. 보고서는 2026-11-12에 `completion_report.html/pdf`로 작성함(report_data.json은 파일이 없어 그날 extract_usage.py를 1회 실행해 생성, 이후 고정). 보고서는 양식(1~5절)을 그대로 두고 내용만 채움: 사전 준비(하네스) 단계와 본 구현 단계의 세션 기록을 합쳐 집계(`report_data_study_claude.json` + `report_data.json` → `report_data_merged.json`, 원본은 수정 안 함). 사전 준비 단계는 새 프로젝트용으로 준비한 하네스 부분만 서술. 원래 계획: `completion_report.html`·`completion_report.pdf` 작성. 작성자·작성일·구현 범위표·바이브 코딩 서술을 채우고 Skill·MCP 표 `(작성)` 칸 기입.
**판단한 내용:**
- 검증 결과(`python scripts/verify.py --e2e`): ruff·pytest(6개)·vue-tsc·vite build·playwright(9개) 모두 PASS. verify 스킬 1회 사용.
- Playwright MCP로 빌드된 대시보드(park.pm) 1회 확인: KPI 4·호선 5척·도넛 범례·조치 카드 정상.
- 구현 범위: 필수(가입·승인·로그인·권한·호선/공정/도면 CRUD·선후행·실적·결재·배포·3대 규칙) 전부 완료. 선택(대시보드·간트·개정 영향·호선 상태 전이·OTP·PDF 업로드/보기·날씨 MCP) 전부 완료.
- 집계에 안 잡히는 도구: 백엔드가 stdio로 호출하는 날씨 MCP(`shipyard-weather`)는 표에 행으로 추가(실제 호출 확인함: Open-Meteo live, 실패 시 샘플). 서브에이전트는 쓰지 않음.
- 집계 주의: 사용자가 작업 도중 보낸 "다음단계부터 끝까지 진행" 메시지는 프롬프트 수에 따로 잡히지 않음(`report_data.json` 프롬프트 3개). 1·2단계·3단계를 한 세션에서 이어서 진행했음(가이드는 단계별 새 세션 권장).
- mcp 패키지는 2.x에서 FastMCP가 사라져 `mcp==1.30.0` 고정. 입력값 오류 422, 상태·중복·게이트·순환 409.
**디자인:** `custom_design.md`를 적용함(토큰·타이포·56px 상단바·240px 사이드·알약 탭·KPI 카드·배지 아이콘·하단 우측 토스트·모달 포커스 이동/복귀·스켈레톤). 적용 후 verify --e2e 5단계 PASS.
**UI 이식(Study_Claude 참고) 완료:** 선박 일러스트, 항로(voyage), 인도 일정 타임라인, 상단바 브랜드칩·검색 버튼·날씨 LIVE·아바타, PDF 드롭존, pdf.js 뷰어(`PdfViewer.vue`, pdfjs-dist 6.5.438, blob URL), 호선·도면 목록·리비전 표 정렬(`useSort`). 검사 5단계 PASS. 브라우저 육안 확인은 안 함.
**간트 드래그 편집:** `PlanView.vue` 막대 좌·우 가장자리 핸들(시작/종료일)과 몸통(기간 유지 이동)을 끌 수 있음(권한 M21 쓰기). 드래그 중 머리글에 "시작 ~ 종료 · n일" 칩+점선 가이드. 놓아도 저장하지 않고 편집 패널의 계획 시작/종료 값만 바뀌며 차트는 그 값을 미리 보여 줌 → [저장] 시 PUT /plans/{id}, [닫기]·다른 공정 선택 시 원래대로. 리비전 이력 표의 "도면 파일" 열은 파일명만 표시(행별 버튼 없음). 파일은 신규 Rev 작성·신규 도면 등록 때 `FileDrop.vue`(클릭 선택·드래그앤드롭)로 선택해 저장 시 함께 업로드. 연속 드래그·공정 전환 시에도 미저장 변경 유지(drafts, 상단 "저장하지 않은 일정 변경 n건" 배너, [모두 되돌리기]). e2e 14개.
**도면 상세 모달 균형:** 넓은 화면에서 뷰어(좌) | 도면 정보+리비전 이력(우) 높이를 맞추고(.dwgx stretch, 뷰어 카드 채움), 결재 이력 | 연계 공정은 아래 2열(.dwgy, ≤960px 1열). PDF 툴바 버튼은 어두운 톤. 1440px만 육안 확인.
**페이징·공정 패널:** 표 목록(도면·호선·회원·결재 이력·공정 실적 목록/이력)은 무한스크롤 대신 클라이언트 페이징(`usePage`, `Pager.vue`, 15건·결재 이력 10·실적 이력 8). 업무 표라 위치·건수 파악과 정렬 유지가 중요해서 페이징을 택함. 서버는 아직 전체 목록을 내려줌. 공정 상세 패널은 요약 타일·기본정보·일정(일수)·선행공정 칩·연계 도면 카드로 재구성.
**한 화면 밀도:** 데스크톱(≥1024px)에서 여백·제목 축소, 간트·모달·결재함·공정 실적 표는 목록 부분만 안에서 스크롤(머리글 고정). 공정 패널은 3열, 선행 공정은 다시 Ctrl 다중선택 select. 900px 높이 기준 공정 계획(패널 열림)은 한 화면, 대시보드만 약 1.9화면. 모달·좁은 화면은 일부 스크롤 남음.
**서버 페이징:** GET /hulls·/drawings·/users·/plans/{id}/progress·/approvals/inbox(history)는 `?page&size(&sort&dir)` → `{items,total,page,size,pages}`(users는 pending 포함, inbox는 hpage/hsize). SQL COUNT+ORDER BY+LIMIT/OFFSET으로 그 쪽 행만 읽음(`page_query`; 계산 열 progress·delay_count·link_count 등도 서브쿼리 정렬). inbox의 mine·ready도 SQL(EXISTS·상관 서브쿼리)로 조회. 프런트 `useServerPage`. 공정 실적의 공정 목록만 클라이언트 페이징(호선별 소량·선택 공정 조회 때문). 헤더 사용자 칸에 오늘 날짜·권한그룹 표시, 대시보드 기준일 문구 제거.
**알려진 문제:** 로그인 잠금은 서버 메모리라 재시작 시 초기화. JWT 기본 비밀키는 개발용. 일정 겹침 경고는 화면만. PDF 보기는 Bearer fetch→blob 방식이라 외부 링크로는 못 연다.
