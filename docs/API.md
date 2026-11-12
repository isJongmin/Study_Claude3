# API (모두 `/api`, `Authorization: Bearer <JWT>`, 오류는 `{code,message}`)
권한: V=해당 메뉴 View, W=Write 이상. 키 이름은 목업 컬럼명 그대로. 날짜는 `YYYY-MM-DD` 문자열.

## 인증 (인증 불필요: signup·login·otp)
- POST /auth/signup {last_name,first_name,birth_date,email,phone,emp_no,password} → 201 / 409 DUP_ID·DUP_EMAIL·DUP_PHONE / 422
- POST /auth/login {emp_no,password} → {otp_required:false,access_token,user} 또는 {otp_required:true,otp_token}. 401 BAD_CREDENTIALS, 403 ACCOUNT_PENDING|REJECTED|DISABLED, 429
- POST /auth/otp {otp_token,code} → {access_token,user}. 401 BAD_OTP|OTP_EXPIRED, 429
- POST /auth/logout, GET /auth/me → {user,menus:[{MenuId,ParentId,Title,TokenUrl,Seq,level}],levels:{M11:2,...}} (level 1=View,2=Write,3=Admin; 볼 수 없는 메뉴는 빠짐)
- GET /lookups → {codes:{SHIPTYPE:[{Code,CodeName}],HULLSTAT,MILESTONE,BLOCKTYPE,PLANSTAT,DWGDISC,DWGSTAT},today,procs,hulls:[{HullNo,HullNm,HullStatus}],users:[{emp_no,display_name}],groups}
- GET /weather?region=울산|거제|목포 → {region,obsDt,tempC,condition,humidity,windMs,state:"live"|"sample"}

## 대시보드 GET /dashboard (V M00)
{today,kpi:{active_hulls,delay_plans,waiting_plans,pending_drawings},hulls:[{HullNo,HullNm,HullStatus,ShipType,DeliveryDt,progress}],plan_status:{PLAN,READY,WORK,DONE,DELAY},
dwg_by_discipline:[{Discipline,name,total,ISSUED,APPROVED,REVIEW,DRAFT}],delivery_by_month:[{month,hulls}],
delay:[{PlanId,HullNo,label,ProgressRate,PlanEndDt}],waiting:[{PlanId,HullNo,label,PlanStartDt,blockers:[DrawingNo]}],
impacts:[{DrawingId,DrawingNo,RevNo,IssueDt,ChangeDesc,PlanId,HullNo,label,PlanStatus}]}

## 호선 (V/W M11)
- GET /hulls?status&type&q → [{...Hull컬럼,has_plan,progress,delay_count}]
- POST /hulls HullIn → 201 상세 / PUT /hulls/{no} HullIn → 상세 / DELETE /hulls/{no} → {ok}
  HullIn = {HullNo,HullNm,ShipType,HullStatus,OwnerNm,ClassSociety,LengthM,BreadthM,DepthM,DeadWeight,DockNo,ContractDt,DeliveryDt,Remark,UseYN}. 409 DUP_HULL, 422(인도<계약)
- GET /hulls/{no} → {...Hull,progress,milestones:[{MilestoneCd,PlanDt,ActualDt}],blocks:[{BlockId,BlockCd,BlockNm,BlockType,WeightTon,progress,plan_count,drawing_count}],plan_stats,dwg_stats}
- PUT /hulls/{no}/milestones [{MilestoneCd,PlanDt,ActualDt}] → 상세
- POST /hulls/{no}/blocks {BlockCd,BlockNm,BlockType,WeightTon} → 201 / DELETE /blocks/{BlockId}. 409 DUP_BLOCK

## 공정 (V M21|M22, W M21 / 실적 W M22)
- GET /plans?hull=8001 → [{...Plan컬럼,label,BlockCd,ProcNm,ManagerNm,preds:[PlanId],gate:{ok,blockers:[{DrawingId,DrawingNo,DwgStatus}]},links:[{DrawingId,DrawingNo,DrawingNm,DwgStatus,RequiredYN,NeedDt,issued}]}] (블록·공정순)
- POST /hulls/{no}/plans, PUT /plans/{PlanId}: {BlockId,ProcCd,PlanStartDt,PlanEndDt,ManagerEmpNo,Remark,preds:[PlanId]} → 공정. 409 CYCLE, 422
- DELETE /plans/{PlanId}
- POST /links {drawing_id,plan_id,required} → 201 (W M21|M31), DELETE /links?drawing_id=&plan_id= . 409 DUP_LINK
- GET /plans/{id}/progress → [{ProgressId,WorkDt,ProgressRate,ManHour,WorkerCnt,WorkerEmpNo,WorkerNm,Remark}] (최근일 먼저)
- POST /plans/{id}/progress {WorkDt,ProgressRate,ManHour,WorkerCnt,WorkerEmpNo,Remark} → 갱신된 공정. 409 DRAWING_GATE(첫 실적에서만), 422(미래일)
- DELETE /progress/{ProgressId} → 갱신된 공정

## 도면 (V M31|M33, W M31)
- GET /drawings?hull&disc&status&q → [{...Drawing컬럼,BlockCd,DesignerNm,link_count,LatestRevNo}]
- POST /drawings {DrawingNo,DrawingNm,HullNo,BlockId,Discipline,DesignerEmpNo} → 201 상세(Rev0 DRAFT). PUT /drawings/{id}(HullNo·DrawingNo는 바뀌지 않음). DELETE
- GET /drawings/{id} → {...Drawing,BlockCd,DesignerNm,revisions:[{RevNo,RevStatus,ChangeDesc,FileNm,has_file,AuthorEmpNo,IssueDt}],approvals:[{ApprovalId,RevNo,StepNo,ApproverEmpNo,ApproverNm,Result,Comment,ActDt}],links:[{PlanId,HullNo,label,PlanStatus,PlanStartDt,PlanEndDt,RequiredYN}],impact:{count,RevNo,IssueDt,plans},free_plans:[{PlanId,label}]}
- POST /drawings/{id}/revisions {ChangeDesc} → 상세. 409 REV_IN_PROGRESS
- POST /drawings/{id}/request {a1,a2} → 상세 (검토자·승인자 emp_no)
- POST /drawings/{id}/revisions/{rev}/issue → 상세 (W M31|M33). 409 BAD_STATE
- POST /drawings/{id}/revisions/{rev}/file (multipart `file`) → 상세. 422 NOT_PDF, 413, 409(DRAFT 아님) / DELETE 같은 경로
- GET /drawings/{id}/revisions/{rev}/file → application/pdf (업로드본, 없으면 샘플 PDF). fetch로 받아 blob URL로 표시

## 결재함 (V/W M33)
- GET /approvals/inbox → {mine:[{ApprovalId,DrawingId,DrawingNo,DrawingNm,RevNo,StepNo,ChangeDesc}],ready:[{DrawingId,DrawingNo,DrawingNm,RevNo,affects:[label]}],history:[{...Approval,DrawingNo,ApproverNm}]}
- POST /approvals/{ApprovalId}/act {result:"APPROVE"|"REJECT",comment} → 도면 상세. 403 본인 아님, 409 STEP_ORDER|BAD_STATE, 422 반려 의견 없음

## 회원관리 (V/W M91)
- GET /users?status&q → [{id,emp_no,display_name,email,phone,birth_date,status,totp_enabled,created_at,groups:[AuthCd]}]
- POST /users, PUT /users/{emp}: {last_name,first_name,birth_date,email,phone,emp_no,password(수정 시 선택),status,group,totp_enabled} → 회원 + `totp_secret_new`(새로 켠 경우만)
- DELETE /users/{emp} (본인 409), POST /users/{emp}/approve

## 목록 페이징(공통)
GET /hulls, /drawings, /users, /plans/{id}/progress(size 기본 8), /approvals/inbox(history는 hpage·hsize) → 목록 대신 `{items,total,page,size,pages}`. 쿼리 `page`(1~, 범위 밖은 마지막 쪽)·`size`(기본 15, 최대 100)·`sort`(행 필드명)·`dir`(asc|desc). /users는 `pending`(승인대기 수) 추가.
