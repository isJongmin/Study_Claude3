<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Badge from '../components/Badge.vue'
import Pbar from '../components/Pbar.vue'
import Pager from '../components/Pager.vue'
import { del, get, post } from '../api'
import { nz, useLoad, usePage, useWrite } from '../composables'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

defineOptions({ name: 'progress' })
const ui = useUi(), auth = useAuth(), { run, busy } = useWrite()
const hull = ref(''), showDone = ref(false), sel = ref<number | null>(null)
watch(() => ui.lookups, (l) => { if (!hull.value && l?.hulls?.length) hull.value = (l.hulls.find((h: any) => h.HullStatus === 'BUILD') || l.hulls[0]).HullNo }, { immediate: true })
const { data: plans, error } = useLoad(() => (hull.value ? get('/plans?hull=' + hull.value) : Promise.resolve([])), () => [hull.value])
const list = computed(() => (plans.value || []).filter((p: any) => showDone.value || ['READY', 'WORK', 'DELAY'].includes(p.PlanStatus)))
const cur = computed(() => (plans.value || []).find((p: any) => p.PlanId === sel.value))
const pg = usePage(() => list.value, 15)
const hpage = ref(1)
const { data: hist } = useLoad(() => (sel.value ? get(`/plans/${sel.value}/progress?page=${hpage.value}`) : Promise.resolve(null)), () => [sel.value, hpage.value])
watch(sel, () => { hpage.value = 1 })
const f = reactive<any>({ WorkDt: '', ProgressRate: 0, ManHour: '', WorkerCnt: '', WorkerEmpNo: '', Remark: '' })
watch([sel, () => ui.lookups], () => {
  Object.assign(f, { WorkDt: ui.today, ProgressRate: cur.value?.ProgressRate ?? 0, ManHour: '', WorkerCnt: '', WorkerEmpNo: auth.user?.emp_no || '', Remark: '' })
}, { immediate: true })
watch(hull, () => { sel.value = null })
const canW = computed(() => auth.can('M22'))
const save = () => {
  if (f.ProgressRate === '' || f.ProgressRate < 0 || f.ProgressRate > 100) return ui.toast('진척률은 0~100 사이로 입력하세요.', 'e')
  return run(() => post(`/plans/${sel.value}/progress`, { WorkDt: f.WorkDt, ProgressRate: Number(f.ProgressRate), ManHour: f.ManHour === '' ? null : Number(f.ManHour), WorkerCnt: f.WorkerCnt === '' ? null : Number(f.WorkerCnt), WorkerEmpNo: nz(f.WorkerEmpNo), Remark: nz(f.Remark) }),
    f.ProgressRate >= 100 ? '실적 저장 — 공정이 완료 처리되었습니다.' : '실적이 저장되었습니다.')
}
const remove = async (x: any) => { if (await ui.ask('실적을 삭제합니다.')) run(() => del('/progress/' + x.ProgressId), '삭제되었습니다.') }
</script>

<template>
  <div class="ph"><h2>공정 실적</h2><span class="d">착수 가능/진행/지연 공정의 일별 진척률·공수를 입력하면 공정 진척과 상태가 갱신됩니다.</span></div>
  <div class="bar">
    <select v-model="hull" aria-label="호선" data-test="pg-hull"><option v-for="h in ui.lookups?.hulls || []" :key="h.HullNo" :value="h.HullNo">{{ h.HullNo }} {{ h.HullNm }}</option></select>
    <label class="chk"><input v-model="showDone" type="checkbox" data-test="pg-done">완료 공정 포함</label>
  </div>
  <div v-if="error" class="warnbox" role="alert">{{ error }}</div>
  <div class="card" style="padding:0"><div class="tw sc"><table class="tbl cards" data-test="pg-table">
    <thead><tr><th>공정</th><th class="fit">계획기간</th><th class="fit">실제착수</th><th>진척</th><th>상태</th><th>담당</th></tr></thead>
    <tbody>
      <tr v-for="p in pg.view.value" :key="p.PlanId" class="click" :class="{ sel: sel === p.PlanId }" :data-test="'pg-row-' + p.PlanId" @click="sel = p.PlanId">
        <td data-label="공정">{{ p.label }}</td><td class="fit" data-label="계획기간">{{ p.PlanStartDt }} ~ {{ p.PlanEndDt }}</td><td class="fit" data-label="실제착수">{{ p.ActualStartDt || '-' }}</td>
        <td data-label="진척"><Pbar :value="p.ProgressRate" /></td><td class="fit" data-label="상태"><Badge kind="plan" :code="p.PlanStatus" /></td><td data-label="담당">{{ p.ManagerNm }}</td>
      </tr>
      <tr v-if="!list.length"><td colspan="6" class="empty">입력할 공정이 없습니다. '완료 공정 포함'을 켜거나 다른 호선을 선택하세요.</td></tr>
    </tbody>
  </table></div></div>
  <Pager v-model:page="pg.page.value" :pages="pg.pages.value" :total="pg.total.value" :size="pg.size" unit="건" />

  <div v-if="cur" class="card" style="margin-top:12px" data-test="pg-panel">
    <h3>{{ cur.label }} <Badge kind="plan" :code="cur.PlanStatus" /></h3>
    <div v-if="!cur.gate.ok" class="warnbox">📐 필수 도면 <b>{{ cur.gate.blockers.map((d: any) => d.DrawingNo).join(', ') }}</b>이(가) 배포되지 않아 착수(첫 실적)할 수 없습니다.</div>
    <form class="grid g6" style="align-items:end" @submit.prevent="save">
      <div><label class="f">작업일</label><input v-model="f.WorkDt" type="date" :max="ui.today" data-test="pg-date"></div>
      <div><label class="f">누적 진척률(%)</label><input v-model="f.ProgressRate" type="number" min="0" max="100" step="1" data-test="pg-rate"></div>
      <div><label class="f">투입 공수(MH)</label><input v-model="f.ManHour" type="number" min="0" step="0.5"></div>
      <div><label class="f">투입 인원</label><input v-model="f.WorkerCnt" type="number" min="0"></div>
      <div><label class="f">작업자</label><select v-model="f.WorkerEmpNo"><option value="">미지정</option><option v-for="u in ui.lookups?.users || []" :key="u.emp_no" :value="u.emp_no">{{ u.display_name }}</option></select></div>
      <div><button class="btn pri block" data-test="pg-save" :disabled="busy || !canW">실적 저장</button></div>
      <div class="span6"><label class="f">비고</label><input v-model="f.Remark"></div>
    </form>
    <h3 style="margin-top:14px">실적 이력</h3>
    <div class="tw sc"><table class="tbl cards" data-test="pg-hist">
      <thead><tr><th class="fit">작업일</th><th class="r">누적 진척률</th><th class="r">공수</th><th class="r">인원</th><th>작업자</th><th>비고</th><th class="r"></th></tr></thead>
      <tbody>
        <tr v-for="x in hist?.items || []" :key="x.ProgressId"><td class="fit" data-label="작업일">{{ x.WorkDt }}</td><td class="r" data-label="누적 진척률">{{ x.ProgressRate }}%</td><td class="r" data-label="공수">{{ x.ManHour ?? '' }}</td><td class="r" data-label="인원">{{ x.WorkerCnt ?? '' }}</td><td data-label="작업자">{{ x.WorkerNm }}</td><td data-label="비고">{{ x.Remark }}</td>
          <td class="r"><button class="btn sm dng" :disabled="!canW" @click="remove(x)">삭제</button></td></tr>
        <tr v-if="!(hist?.items || []).length"><td colspan="7" class="empty">입력된 실적이 없습니다.</td></tr>
      </tbody>
    </table></div>
    <Pager v-model:page="hpage" :pages="hist?.pages || 1" :total="hist?.total || 0" :size="hist?.size || 8" />
  </div>
  <div v-else class="note">위 목록에서 공정을 선택하세요.</div>
</template>
