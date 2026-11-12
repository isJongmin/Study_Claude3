# 조선소 통합관리 (FastAPI + Vue3 + SQLite)
원본: `origin/shipyard_mockup.html`. 순서·구조·유의점은 `GUIDE.md`(필요한 절만), 규칙은 `docs/SPEC.md`, 계약은 `docs/API.md`, 인수인계는 `docs/HANDOFF.md`.

## 토큰 규칙
- 목업은 통으로 읽지 않는다. Grep으로 찾고 필요한 줄만 읽는다. 규칙은 SPEC에 있으니 SPEC만 본다.
- 파일은 한 번에 완성해서 쓰고 방금 쓴 파일을 다시 읽지 않는다. 같은 파일을 조금씩 여러 번 고치지 않는다.
- 명령 출력은 꼬리만. 설치는 `-q`. 중간 단계에서는 빌드·테스트를 돌리지 않는다. 서브에이전트는 쓰지 않는다.
- 단계가 끝나면 `docs/HANDOFF.md`를 덮어쓴다(끝난 단계/만든 파일/남은 일/판단한 내용/알려진 문제, 15줄).
- 보고서: `report_data.json`은 손으로 고치지 않는다. Skill·MCP 서술은 실제 있었던 일만.

## 핵심
- 기준일 `2026-10-19` 고정(`date.today()` 금지). 테이블·컬럼명은 목업과 같다(`TB_MST_Hull`, `HullNo`).
- 데모 계정: admin/admin1234(OTP), park.pm/pm1234, lee.dwg/dwg1234(OTP), han.wk/wk1234, choi.qa/qa1234. OTP 123456은 시드 계정만.
- 규칙은 서버가 판정, 화면 비활성화는 편의. 오류는 `{code,message}` 한국어, 타입 오류는 422.
- 화면: 업무 앱(상단 검색·날씨·계정 / 왼쪽 메뉴 / 탭+작업영역, 상세는 모달). 색은 `:root` 변수만(배경 #F4F6FA, 주색 #3182F6,
  상태색 계획 회청·착수가능 청록·진행 파랑·완료 초록·지연 분홍빨강·검토 주황·승인 보라). Pretendard, 숫자 tabular-nums, 4px 간격, 모서리 12/16/20.
- 표: 글자·날짜 왼쪽, 수치·버튼 오른쪽, 모바일은 카드. 토스트 성공 4초·오류 6초. reduced-motion이면 애니메이션 끔.
- 360~1440px에서 가로 넘침 없음. 팝업이 열리면 뒤 페이지 고정. Playwright용 `data-test` 속성을 미리 붙인다.
- 실행: `backend/.venv/Scripts/python.exe`, 검사는 `python scripts/verify.py --e2e`(3단계).
- 화면 검토: `docs/screens/`의 스크린샷을 본다(바꾼 뒤 재생성 명령은 그 폴더 README). 새 환경은 `python scripts/setup.py`.
