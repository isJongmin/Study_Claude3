<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Badge from '../components/Badge.vue'
import { del, get, post, put } from '../api'
import { nz, useLoad, useWrite } from '../composables'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

defineOptions({ name: 'plans' })
const ui = useUi(), auth = useAuth(), route = useRoute(), { run, busy } = useWrite()
const hull = ref(String(route.query.hull || ''))
watch(() => route.query.hull, (v) => { if (v) { hull.value = String(v); sel.value = null } })
const canW = computed(() => auth.can('M21'))

const { data: plans, loading, error } = useLoad(() => (hull.value ? get('/plans?hull=' + hull.value) : Promise.resolve([])), () => [hull.value])
const { data: hd } = useLoad(() => (hull.value ? get('/hulls/' + hull.value) : Promise.resolve(null)), () => [hull.value])
watch(() => ui.lookups, (l) => { if (!hull.value && l?.hulls?.length) hull.value = (l.hulls.find((h: any) => h.HullStatus === 'BUILD') || l.hulls[0]).HullNo }, { immediate: true })

// ----- 간트 -----
const PPD = ref(6), ROW = 32
const D = (s: string) => Date.parse(s) / 864e5
const range = computed(() => {
  const ps = plans.value || []
  if (!ps.length) return { start: D(ui.today), days: 30 }
  const start = Math.min(...ps.map((p: any) => D(p.PlanStartDt))) - 3
  const end = Math.max(...ps.map((p: any) => D(p.PlanEndDt)), D(ui.today)) + 3
  return { start, days: Math.ceil(end - start) }
})
const x = (s: string) => (D(s) - range.value.start) * PPD.value
const width = computed(() => range.value.days * PPD.value)
const months = computed(() => {
  const out: { left: number; label: string }[] = []
  const d = new Date(range.value.start * 864e5); d.setUTCDate(1)
  for (let i = 0; i < 60; i++) {
    const left = (d.getTime() / 864e5 - range.value.start) * PPD.value
    if (left > width.value) break
    if (left >= -40) out.push({ left, label: d.toISOString().slice(0, 7) })
    d.setUTCMonth(d.getUTCMonth() + 1)
  }
  return out
})
const COLOR: Record<string, string> = { PLAN: 'var(--s-plan)', READY: 'var(--s-ready)', WORK: 'var(--s-work)', DONE: 'var(--s-done)', DELAY: 'var(--s-delay)' }
const deps = computed(() => {
  const ps = plans.value || [], idx: Record<number, number> = {}
  ps.forEach((p: any, i: number) => { idx[p.PlanId] = i })
  const out: string[] = []
  ps.forEach((p: any, i: number) => p.preds.forEach((q: number) => {
    const j = idx[q]; if (j === undefined) return
    const pp = ps[j], x1 = x(span(pp).e) + PPD.value, y1 = j * ROW + ROW / 2, x2 = x(span(p).s), y2 = i * ROW + ROW / 2
    out.push(`M${x1} ${y1} H${Math.max(x1 + 6, x2 - 6)} V${y2} H${x2}`)
  }))
  return out
})
const todayX = computed(() => x(ui.today) + PPD.value / 2)
const gl = ref<HTMLElement>(), gr = ref<HTMLElement>()
const syncScroll = () => { if (gl.value && gr.value) gl.value.scrollTop = gr.value.scrollTop }

// ----- 막대 가장자리 드래그로 계획 시작/종료일 수정 -----
const dur = computed(() => (form.PlanStartDt && form.PlanEndDt ? Math.round(D(form.PlanEndDt) - D(form.PlanStartDt)) + 1 : 0))
const iso = (n: number) => new Date(n * 864e5).toISOString().slice(0, 10)
const drag = ref<{ id: number; edge: 's' | 'e' | 'm'; x0: number; s: number; e: number; cs: number; ce: number } | null>(null)
// 저장하지 않은 일정 변경은 공정별로 모아 둔다. 여러 번 끌어도, 다른 공정을 눌러도 유지되고 [저장] 때 반영, [닫기]·[모두 되돌리기]로 버린다.
const drafts = reactive<Record<number, { s: string; e: string }>>({})
const draftCount = computed(() => Object.keys(drafts).length)
const discardDrafts = () => { for (const k of Object.keys(drafts)) delete drafts[Number(k)] }
watch(hull, discardDrafts)
const span = (p: any) => {
  const g = drag.value
  if (g && g.id === p.PlanId) return { s: iso(g.cs), e: iso(g.ce) }
  // 선택한 공정은 편집 패널의 값을 그대로 미리 보여 준다(저장 전 값, 닫으면 원래대로)
  if (sel.value === p.PlanId && form.PlanStartDt && form.PlanEndDt && form.PlanStartDt <= form.PlanEndDt) return { s: form.PlanStartDt, e: form.PlanEndDt }
  const d = drafts[p.PlanId]
  if (d) return d
  return { s: p.PlanStartDt, e: p.PlanEndDt }
}
function dragStart(ev: PointerEvent, p: any, edge: 's' | 'e' | 'm') {
  if (!canW.value || busy.value || ev.button > 0) return
  ;(ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId)
  const cur = span(p), s = D(cur.s), e = D(cur.e) // 이전에 옮긴 값에서 이어서 시작
  moved = false
  drag.value = { id: p.PlanId, edge, x0: ev.clientX, s, e, cs: s, ce: e }
}
function dragMove(ev: PointerEvent) {
  const g = drag.value; if (!g) return
  const dd = Math.round((ev.clientX - g.x0) / PPD.value)
  if (g.edge === 'm') { g.cs = g.s + dd; g.ce = g.e + dd } else if (g.edge === 's') g.cs = Math.min(g.s + dd, g.e); else g.ce = Math.max(g.e + dd, g.s)
  if (dd) moved = true
}
// 놓는 순간에는 저장하지 않는다. 아래 편집 패널의 시작/종료일만 바꾸고 차트는 그 값을 미리 보여 준다.
// 연속해서 여러 번 옮겨도 이전 변경은 유지된다. [저장]을 누르면 반영되고, [닫기]·[모두 되돌리기]로 원래 값으로 돌아간다.
function dragEnd() {
  const g = drag.value; if (!g) return
  drag.value = null
  if (g.cs === g.s && g.ce === g.e) return
  pick(g.id)
  form.PlanStartDt = iso(g.cs); form.PlanEndDt = iso(g.ce)
  drafts[g.id] = { s: form.PlanStartDt, e: form.PlanEndDt }
  ui.toast('일정을 미리 변경했습니다. 아래에서 [저장]을 누르면 반영됩니다.')
}
const dragCancel = () => { drag.value = null }
// 몸통을 끈 직후에 따라오는 click이 편집 패널을 열지 않게 한다.
let moved = false
const barClick = (id: number) => { if (moved) { moved = false; return } pick(id) }

// ----- 편집 패널 -----
const sel = ref<number | 'new' | null>(null)
const form = reactive<any>({ BlockId: '', ProcCd: 'CUT', PlanStartDt: '', PlanEndDt: '', ManagerEmpNo: '', Remark: '', preds: [] as number[] })
const cur = computed(() => (typeof sel.value === 'number' ? (plans.value || []).find((p: any) => p.PlanId === sel.value) : null))
function stash() { // 패널에서 바꾼 값(직접 입력 포함)을 떠나기 전에 보관
  const p = cur.value
  if (!p || !form.PlanStartDt || !form.PlanEndDt || form.PlanStartDt > form.PlanEndDt) return
  if (form.PlanStartDt !== p.PlanStartDt || form.PlanEndDt !== p.PlanEndDt) drafts[p.PlanId] = { s: form.PlanStartDt, e: form.PlanEndDt }
  else delete drafts[p.PlanId]
}
function pick(id: number | 'new') {
  if (id !== sel.value) stash()
  sel.value = id
  if (id === 'new') {
    const d = new Date(ui.today); d.setUTCDate(d.getUTCDate() + 13)
    Object.assign(form, { BlockId: '', ProcCd: 'CUT', PlanStartDt: ui.today, PlanEndDt: d.toISOString().slice(0, 10), ManagerEmpNo: '', Remark: '', preds: [] })
  } else {
    const p = (plans.value || []).find((q: any) => q.PlanId === id)
    if (p) Object.assign(form, { BlockId: p.BlockId ?? '', ProcCd: p.ProcCd, PlanStartDt: p.PlanStartDt, PlanEndDt: p.PlanEndDt, ManagerEmpNo: p.ManagerEmpNo ?? '', Remark: p.Remark ?? '', preds: [...p.preds] })
    const d = drafts[id]
    if (d) Object.assign(form, { PlanStartDt: d.s, PlanEndDt: d.e })
  }
}
const body = () => ({ BlockId: form.BlockId === '' ? null : Number(form.BlockId), ProcCd: form.ProcCd, PlanStartDt: form.PlanStartDt, PlanEndDt: form.PlanEndDt, ManagerEmpNo: nz(form.ManagerEmpNo), Remark: nz(form.Remark), preds: form.preds.map(Number) })
async function save() {
  if (!form.PlanStartDt || !form.PlanEndDt) return ui.toast('계획 시작/종료일을 입력하세요.', 'e')
  const late = form.preds.some((q: number) => (plans.value || []).find((p: any) => p.PlanId === q)?.PlanEndDt > form.PlanStartDt)
  if (late && !(await ui.ask('선행 공정 종료일이 이 공정의 시작일보다 늦습니다. 그대로 저장할까요?'))) return
  const r = await run(() => (sel.value === 'new' ? post(`/hulls/${hull.value}/plans`, body()) : put('/plans/' + sel.value, body())))
  if (r) { if (typeof sel.value === 'number') delete drafts[sel.value]; sel.value = r.PlanId }
}
async function remove() {
  if (!(await ui.ask('공정을 삭제합니다. (실적·선후행·도면 연계도 함께 삭제됩니다)'))) return
  if (await run(() => del('/plans/' + sel.value), '삭제되었습니다.')) { if (typeof sel.value === 'number') delete drafts[sel.value]; sel.value = null }
}
const blocks = computed(() => hd.value?.blocks || [])
const others = computed(() => (plans.value || []).filter((p: any) => p.PlanId !== sel.value))
const linkSel = ref(''), linkReq = ref(true), freeDwgs = ref<any[]>([])
watch([sel, () => ui.version], async () => {
  if (typeof sel.value !== 'number') return
  try { const all = await get(`/drawings?hull=${hull.value}`); const linked = new Set((cur.value?.links || []).map((l: any) => l.DrawingId)); freeDwgs.value = all.filter((d: any) => !linked.has(d.DrawingId)) } catch { freeDwgs.value = [] }
})
const addLink = async () => { if (!linkSel.value) return ui.toast('도면을 선택하세요.', 'e'); if (await run(() => post('/links', { drawing_id: Number(linkSel.value), plan_id: sel.value, required: linkReq.value }), '도면이 연계되었습니다.')) linkSel.value = '' }
const delLink = (l: any) => run(() => del(`/links?drawing_id=${l.DrawingId}&plan_id=${sel.value}`), '연계가 해제되었습니다.')
</script>

<template>
  <div class="ph"><h2>공정 계획</h2><span class="d">막대 또는 좌측 공정명을 클릭하면 상세/수정 패널이 열립니다. 막대 왼쪽·오른쪽 끝을 끌면 계획 시작일·종료일을, 막대 몸통을 끌면 일정 전체를 옮길 수 있습니다. 빨간 선은 기준일 {{ ui.today }}입니다.</span></div>
  <div class="bar">
    <select v-model="hull" aria-label="호선" data-test="plan-hull"><option v-for="h in ui.lookups?.hulls || []" :key="h.HullNo" :value="h.HullNo">{{ h.HullNo }} {{ h.HullNm }}</option></select>
    <select v-model.number="PPD" aria-label="확대"><option :value="3">축소</option><option :value="6">보통</option><option :value="10">확대</option></select>
    <span class="sp"></span>
    <button v-if="canW" class="btn pri" data-test="plan-new" @click="pick('new')">+ 공정 추가</button>
  </div>
  <div v-if="error" class="warnbox" role="alert">{{ error }}</div>
  <div v-if="draftCount" class="draftbar" role="status" data-test="draft-bar">저장하지 않은 일정 변경 {{ draftCount }}건 · 공정을 선택해 [저장]하세요. <button type="button" class="btn sm" data-test="draft-reset" @click="discardDrafts">모두 되돌리기</button></div>
  <div v-if="!loading && !(plans || []).length" class="card empty">이 호선에는 공정 계획이 없습니다. [+ 공정 추가]로 등록하세요.</div>
  <div v-else class="gantt" :class="{ full: sel === null }" data-test="gantt">
    <div ref="gl" class="gl"><div class="gh"></div>
      <div v-for="p in plans" :key="p.PlanId" class="row" :class="{ sel: sel === p.PlanId }" :title="p.label" :data-test="'plan-row-' + p.PlanId" @click="pick(p.PlanId)">{{ p.label }}</div></div>
    <div ref="gr" class="gr" @scroll="syncScroll">
      <div :style="{ width: width + 'px', position: 'relative' }">
        <div class="gh"><span v-for="m in months" :key="m.label" :style="{ left: m.left + 'px' }">{{ m.label }}</span>
          <div v-if="drag" class="dtip" data-test="drag-tip" :style="{ left: Math.max(0, x(iso(drag.cs)) - 4) + 'px' }">{{ iso(drag.cs) }} ~ {{ iso(drag.ce) }} · {{ drag.ce - drag.cs + 1 }}일</div></div>
        <div v-for="p in plans" :key="p.PlanId" class="lane">
          <div class="bar2" :class="{ sel: sel === p.PlanId, dragging: drag?.id === p.PlanId, edit: canW }" :style="{ left: x(span(p).s) + 'px', width: Math.max(6, x(span(p).e) - x(span(p).s) + PPD) + 'px', background: COLOR[p.PlanStatus] }"
            :title="`${p.label} ${p.PlanStartDt}~${p.PlanEndDt} ${p.ProgressRate}%`" :data-test="'bar-' + p.PlanId" @click="barClick(p.PlanId)" @pointerdown="dragStart($event, p, 'm')" @pointermove="dragMove" @pointerup="dragEnd" @pointercancel="dragCancel"><i :style="{ width: p.ProgressRate + '%' }"></i>
            <span v-if="canW" class="hnd hl" :data-test="'bar-l-' + p.PlanId" @click.stop @pointerdown.stop.prevent="dragStart($event, p, 's')" @pointermove="dragMove" @pointerup="dragEnd" @pointercancel="dragCancel"></span>
            <span v-if="canW" class="hnd hr" :data-test="'bar-r-' + p.PlanId" @click.stop @pointerdown.stop.prevent="dragStart($event, p, 'e')" @pointermove="dragMove" @pointerup="dragEnd" @pointercancel="dragCancel"></span></div>
        </div>
        <svg class="dep" :width="width" :height="(plans || []).length * ROW" :style="{ top: '32px' }"><path v-for="(d, i) in deps" :key="i" :d="d" fill="none" stroke="#b0b8c1" stroke-width="1" /></svg>
        <div v-if="drag" class="dguide" :style="{ left: (drag.edge !== 'e' ? x(iso(drag.cs)) : x(iso(drag.ce)) + PPD) + 'px' }"></div>
        <div class="today" :style="{ left: todayX + 'px' }"></div>
      </div>
    </div>
  </div>

  <div v-if="sel !== null" class="card pp" data-test="plan-panel">
    <div class="pp-h">
      <div class="pp-t"><h3>{{ sel === 'new' ? '새 공정 추가' : cur?.label }}</h3><Badge v-if="cur" kind="plan" :code="cur.PlanStatus" />
        <template v-if="cur"><span class="pp-m">계획 {{ cur.PlanStartDt }} ~ {{ cur.PlanEndDt }}</span><span class="pp-m">진척 <b>{{ cur.ProgressRate }}%</b></span><span class="pp-m">실제 {{ cur.ActualStartDt || '미착수' }}<template v-if="cur.ActualEndDt"> ~ {{ cur.ActualEndDt }}</template></span></template></div>
      <button type="button" class="pp-x" aria-label="패널 접기" @click="discardDrafts(); sel = null">×</button>
    </div>
    <div class="pp-body">
      <form class="pp-form" @submit.prevent="save">
        <section>
          <h4>기본 정보</h4>
          <div class="grid g3">
            <div><label class="f">공정</label><select v-model="form.ProcCd" data-test="p-proc"><option v-for="p in ui.lookups?.procs || []" :key="p.ProcCd" :value="p.ProcCd">{{ p.ProcNm }}</option></select></div>
            <div><label class="f">블록</label><select v-model="form.BlockId" data-test="p-block"><option value="">호선 전체</option><option v-for="b in blocks" :key="b.BlockId" :value="b.BlockId">{{ b.BlockCd }} {{ b.BlockNm }}</option></select></div>
            <div><label class="f">담당자</label><select v-model="form.ManagerEmpNo"><option value="">미지정</option><option v-for="u in ui.lookups?.users || []" :key="u.emp_no" :value="u.emp_no">{{ u.display_name }} ({{ u.emp_no }})</option></select></div>
          </div>
        </section>
        <section>
          <h4>일정 <span v-if="dur > 0" class="pp-dur">{{ dur }}일</span><span v-else-if="form.PlanStartDt && form.PlanEndDt" class="pp-dur bad">종료일이 시작일보다 빠릅니다</span></h4>
          <div class="pp-dates">
            <div><label class="f">계획 시작</label><input v-model="form.PlanStartDt" type="date" data-test="p-start"></div>
            <span class="pp-arrow" aria-hidden="true">→</span>
            <div><label class="f">계획 종료</label><input v-model="form.PlanEndDt" type="date" data-test="p-end"></div>
          </div>
          <p class="pp-hint">차트에서 막대를 끌어도 이 값이 바뀝니다. [저장]을 눌러야 반영됩니다.</p>
        </section>
        <section>
          <h4>선행 공정 <span class="pp-cnt">{{ (form.preds || []).length }}개 선택</span></h4>
          <select v-model="form.preds" multiple data-test="p-preds" class="pp-multi" aria-label="선행 공정 (Ctrl 다중선택)"><option v-for="o in others" :key="o.PlanId" :value="o.PlanId">{{ o.label }}</option></select>
          <p class="pp-hint">Ctrl(⌘) 키를 누른 채 클릭하면 여러 공정을 선택할 수 있습니다.</p>
        </section>
        <section><h4>비고</h4><textarea v-model="form.Remark" rows="2" placeholder="메모를 입력하세요"></textarea></section>
        <div class="pp-act">
          <button v-if="sel !== 'new'" type="button" class="btn dng" data-test="p-del" :disabled="busy || !canW" @click="remove">삭제</button><span class="sp"></span>
          <button type="button" class="btn" @click="discardDrafts(); sel = null">닫기</button>
          <button class="btn pri" data-test="p-save" :disabled="busy || !canW">저장</button>
        </div>
      </form>
      <aside v-if="cur" class="pp-side">
        <h4>연계 도면 <span class="pp-cnt">{{ cur.links.length }}건</span></h4>
        <p class="pp-hint" style="margin-top:0">필수 도면은 배포되어야 착수할 수 있습니다.</p>
        <div v-if="!cur.gate.ok" class="warnbox" data-test="gate-warn">📐 도면 대기: 필수 도면 <b>{{ cur.gate.blockers.map((d: any) => `${d.DrawingNo}(${ui.cn('DWGSTAT', d.DwgStatus)})`).join(', ') }}</b> 미배포 → 착수 불가</div>
        <ul class="pp-links">
          <li v-for="l in cur.links" :key="l.DrawingId">
            <a @click="ui.openModal('dwg', l.DrawingId)">{{ l.DrawingNo }}</a>
            <Badge kind="dwg" :code="l.DwgStatus" /><span v-if="!l.issued" class="bdg b-warn">미배포</span><span class="bdg" :class="l.RequiredYN ? 'b-ok' : ''">{{ l.RequiredYN ? '필수' : '참고' }}</span>
            <button type="button" class="btn sm dng" :disabled="!auth.can('M21', 'M31')" @click="delLink(l)">해제</button>
          </li>
          <li v-if="!cur.links.length" class="empty">연계된 도면이 없습니다.</li>
        </ul>
        <form class="pp-add" @submit.prevent="addLink">
          <select v-model="linkSel" aria-label="연계할 도면" data-test="link-dwg"><option value="">도면 선택</option><option v-for="d in freeDwgs" :key="d.DrawingId" :value="d.DrawingId">{{ d.DrawingNo }} {{ d.DrawingNm }}</option></select>
          <label class="chk"><input v-model="linkReq" type="checkbox">필수</label><button class="btn" data-test="link-add" :disabled="busy || !auth.can('M21', 'M31')">+ 연계</button>
        </form>
      </aside>
      <aside v-else class="pp-side muted">저장한 뒤 이 공정에 도면을 연계할 수 있습니다.</aside>
    </div>
  </div>
</template>
