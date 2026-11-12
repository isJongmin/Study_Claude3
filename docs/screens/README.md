# 화면 스크린샷 (검토용)
폰·클라우드에서 AI가 화면을 보고 검토하도록 저장한 캡처다. 데스크톱 1440×900(로그인 park.pm, 결재함 lee.dwg, 회원관리 admin), 모바일 390×844. 기준일 2026-10-19 시드 데이터.

| 파일 | 화면 |
|---|---|
| 01-dashboard, 01-dashboard-bottom | 대시보드(위쪽 / 아래로 스크롤) |
| 02-hull-list, 03-hull-modal-info·sum | 호선 목록, 상세 모달(기본정보·연계 현황) |
| 04-plan-gantt, 04-plan-gantt-panel-open | 공정 계획(상세 닫힘 / 열림) |
| 05-progress, 06-dwg-list, 07-dwg-modal | 공정 실적, 도면 목록, 도면 상세 |
| 08-mobile-* | 모바일 도면 목록·메뉴·대시보드 |
| 09-approval, 10-users | 결재함, 회원관리 |

다시 만들기(화면을 바꾼 뒤): `npm --prefix frontend run build` → `cd frontend && SHOTS=1 npx playwright test shots`
