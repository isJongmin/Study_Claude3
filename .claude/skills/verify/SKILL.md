---
name: verify
description: 프로젝트 전체 검사(ruff, pytest, vue-tsc, vite build, playwright)를 한 번에 돌리고 실패한 단계만 고친다. "검사", "verify", "테스트 돌려" 요청이나 3단계 검증에 사용.
---

1. `python scripts/verify.py --e2e`를 실행한다. 출력은 단계별 PASS/FAIL과 실패 단계의 꼬리 40줄뿐이다.
2. 실패한 단계만 원인을 찾아 고친다. Playwright 실패는 앱보다 셀렉터·로딩 대기를 먼저 의심한다.
3. 고친 단계만 `python scripts/verify.py --only <ruff|pytest|tsc|build|e2e>`로 다시 돌린다. 전체를 반복하지 않는다.
4. 결과는 단계별 PASS/FAIL 한 줄씩으로 보고한다. 실패가 남았으면 그대로 적는다.
