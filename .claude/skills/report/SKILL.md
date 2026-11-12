---
name: report
description: 개발이 끝난 뒤 완료보고서(completion_report.html/pdf)를 작성한다. "보고서 만들어" 요청에 사용. 새 세션(Sonnet)에서만 실행.
---

1. `report_data.json`은 이미 고정되어 있다. `extract_usage.py`를 다시 실행하지 않고 손으로 고치지도 않는다.
2. `origin/completion_report_sample.html`을 `completion_report.html`로 복사해 고친다.
   - 작성자·작성일·개요, 구현 범위표(필수·선택 기능별 완료/일부/제외와 비고), 바이브 코딩 서술. 서술은 `docs/HANDOFF.md`와 검증 결과의 사실만 쓴다.
   - `</body>` 앞에 `<script>`를 넣어 `report_data.json` 내용을 상수로 두고 양식의 `render(데이터)`를 호출한다. 이어서 Skill·MCP 표의 `(작성)` 칸을 이름별 용도·효과로 채운다.
   - 집계에 안 잡히는 날씨 MCP(백엔드가 호출)는 행으로 추가한다. 서브에이전트를 썼다면 토큰이 빠졌다고 적는다.
3. PDF: `frontend` 폴더에서 `npx playwright pdf --paper-format=A4 <completion_report.html의 file:// 주소> ../completion_report.pdf`.
4. 호출 횟수가 0인 도구를 썼다고 쓰지 않는다.
