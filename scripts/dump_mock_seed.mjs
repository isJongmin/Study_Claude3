// 목업의 seed()를 그대로 실행해 backend/app/seed_data.json 으로 저장한다. 손으로 옮기지 않는다.
import fs from 'node:fs';
import vm from 'node:vm';
const src = fs.readFileSync(new URL('../origin/shipyard_mockup.html', import.meta.url), 'utf8').split('\n');
const a = src.findIndex(l => l.startsWith('const TODAY'));
const b = src.findIndex(l => l.includes('UI 공통 / 인증 / 셸')) - 1;
const ctx = vm.createContext({ console });
vm.runInContext(src.slice(a, b).join('\n') + '\n;this.out = seed();', ctx);
const db = ctx.out;
// 실제착수일에 0% '착수' 실적을 더해, 실적 한 건 저장으로 착수일이 밀리지 않게 한다.
let gid = Math.max(0, ...db.TB_PRC_Progress.map(r => r.ProgressId)) + 1;
for (const p of db.TB_PRC_Plan) {
  if (!p.ActualStartDt) continue;
  db.TB_PRC_Progress = db.TB_PRC_Progress.filter(r => r.PlanId !== p.PlanId || r.WorkDt >= p.ActualStartDt);
  if (!db.TB_PRC_Progress.some(r => r.PlanId === p.PlanId && r.WorkDt === p.ActualStartDt))
    db.TB_PRC_Progress.push({ ProgressId: gid++, PlanId: p.PlanId, WorkDt: p.ActualStartDt, ProgressRate: 0, ManHour: null, WorkerCnt: null, WorkerEmpNo: p.ManagerEmpNo, Remark: '착수', CreateDt: p.ActualStartDt });
}
db.users.forEach(u => delete u.password_hash); // 비밀번호는 seed.py 가 데모 값으로 bcrypt 해시
fs.writeFileSync(new URL('../backend/app/seed_data.json', import.meta.url), JSON.stringify(db));
console.log(Object.entries(db).map(([k, v]) => `${k}:${v.length}`).join(' '));
