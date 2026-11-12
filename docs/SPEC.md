# 업무 규칙 (목업에서 추출, 번호로 인용)
기준일 `2026-10-19`(config.TODAY). 규칙은 서버가 판정하고 구현은 `services/rules.py`·`services/workflow.py`·`routers/api.py`.

## 인증·권한
- R1 가입: 성·이름·생년월일·이메일 형식·전화(01x)·아이디(영숫자._- 4~20)·비밀번호(8자+). 아이디/이메일/전화(숫자만 비교) 중복 409. 가입 상태 pending.
- R2 로그인: pending/rejected/disabled는 403(`ACCOUNT_*`). 아이디·비번 불일치 401. 성공 시 JWT(8h). OTP 계정은 `otp_token`(5분) 발급 후 `/auth/otp`로 완료.
- R3 OTP: 시드 비밀키(JBSWY3DPEHPK3PXP) 계정만 123456 허용. 새로 켠 OTP 계정은 무작위 비밀키+실제 TOTP만.
- R4 로그인·OTP 실패 5회 → 5분간 429(`TOO_MANY_ATTEMPTS`). 성공하면 초기화.
- R5 권한: 그룹→메뉴별 View<Write<Admin. 읽기는 해당 메뉴 View, 쓰기는 Write 이상, 아니면 403. 호선 M11 / 공정계획 M21 / 실적 M22 / 도면 M31 / 결재 M33 / 회원 M91. 도면·공정 연계는 M21 또는 M31 Write.

## 호선
- R10 호선 등록 시 마일스톤 5종(CUT·KEEL·LAUNCH·TRIAL·DELIVER) 자동 생성, DELIVER 계획일=인도예정일.
- R11 인도예정일<계약일 422. 호선번호 중복 409. 선종·상태·블록유형 코드는 공통코드에 있어야 함.
- R12 호선 삭제 시 블록·공정·실적·선후행·도면·리비전·결재·연계가 함께 삭제(FK CASCADE, 업로드 PDF도 삭제).
- R13 블록코드는 호선 안에서 유일(409). 블록 삭제 시 공정 삭제, 도면의 블록 연결은 NULL.
- R14 호선 진척 = 공정 계획일수 가중 평균(반올림). 블록 진척도 같은 방식.

## 공정
- R20 공정 종료일<시작일 422. 블록은 같은 호선, 선행은 같은 호선 공정이어야 함. 담당자·공정코드 존재 확인.
- R21 선후행 순환 금지 → 409 `CYCLE`(자기 자신 포함).
- R22 상태(업무 쓰기 뒤 전체 재계산): 진척≥100 DONE / (진척>0 또는 착수일) 계획종료<기준일 DELAY 아니면 WORK / 착수 전 계획종료<기준일 DELAY / 선행 모두 DONE이고 R30 통과 READY, 아니면 PLAN.
- R23 호선 상태: DESIGN인데 WORK 공정이 생기면 BUILD. BUILD인데 LAUNCH 공정이 DONE이면 LAUNCH.
- R24 공정 삭제 시 실적·선후행·도면 연계 삭제.

## 실적
- R25 작업일>기준일 422. 진척 0~100. 같은 날 재입력은 덮어씀.
- R26 공정 진척 = 가장 늦은 작업일 값, 실제착수일 = 가장 이른 작업일, 100이면 실제종료일 = 그 작업일. 실적을 모두 지우면 착수 전(0, null).
- R27 첫 실적(0%도)이 착수. 필수 연계 도면에 배포본이 없으면 409 `DRAWING_GATE`.

## 도면
- R30 도면 게이트: 필수(RequiredYN) 연계 도면 중 OBSOLETE가 아니면서 ISSUED 리비전이 하나도 없는 것이 있으면 착수 불가. 개정 중이어도 이전 배포본이 있으면 통과.
- R31 도면 등록 시 Rev0 DRAFT("최초 작성"). 도면번호 중복 409. 연계는 같은 호선만, 중복 409.
- R32 새 Rev는 최신 리비전이 ISSUED/OBSOLETE일 때만(409). 도면 상태는 DRAFT가 됨(CurrentRevNo는 유지).
- R33 결재 요청: 최신 Rev가 DRAFT, 검토자≠승인자, 둘 다 승인된 회원. 기존 결재행 교체, Rev·도면 REVIEW.
- R34 결재 처리: 본인 배정만(403), WAIT만, 앞 단계 APPROVE 후에만, Rev가 REVIEW일 때만(409).
- R35 반려는 의견 필수(422). 반려 시 Rev·도면 DRAFT, 남은 WAIT 결재행 삭제. 모든 단계 APPROVE면 Rev·도면 APPROVED.
- R36 배포: APPROVED Rev만(409). 이전 ISSUED는 OBSOLETE, 배포일=기준일, CurrentRevNo 갱신, 도면 ISSUED.
- R37 PDF: DRAFT Rev만 업로드·삭제(409). `%PDF-` 시그니처·30MB 이하. 파일명은 서버 UUID, 원본명은 표시용.
- R38 개정 영향: 최근 30일 내 배포된 Rev≥1 도면의 연계 공정 중 WORK/DONE/DELAY.

## 회원관리
- R40 관리자가 등록·수정·삭제·가입승인. 본인 삭제·본인 상태 변경 409. 수정 시 비밀번호는 입력할 때만 변경.
- R41 OTP를 새로 켜면 무작위 비밀키를 응답 `totp_secret_new`로 한 번만 반환.

## 공통
- R50 오류 응답 `{code,message}` 한국어. 잘못된 타입·형식은 422(500 아님). 401 미인증, 403 권한/배정, 404 없음, 409 상태·중복·게이트, 429 잠금.
- R51 응답 헤더: CSP·X-Frame-Options·nosniff (`/docs` CSP 제외).
- R52 날씨: 백엔드가 stdio MCP(`get_weather`)를 호출, 10분 캐시, 실패 시 샘플값 `state:"sample"`.
