<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import FileDrop from '../components/FileDrop.vue'
import PdfViewer from '../components/PdfViewer.vue'
import Badge from '../components/Badge.vue'
import Modal from '../components/Modal.vue'
import { blobUrl, del, get, post, put, upload } from '../api'
import { nz, useLoad, useWrite } from '../composables'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

const props = defineProps<{ id: string | number }>()
const ui = useUi(), auth = useAuth(), router = useRouter(), { run, busy } = useWrite()
const isNew = props.id === 'new'
const canW = computed(() => auth.can('M31'))
const canIssue = computed(() => auth.can('M31', 'M33'))
const { data: d, error } = useLoad(() => (isNew ? Promise.resolve(null) : get('/drawings/' + props.id)))

const form = reactive<any>({ DrawingNo: '', DrawingNm: '', HullNo: ui.lookups?.hulls?.[0]?.HullNo || '', BlockId: '', Discipline: 'HULL', DesignerEmpNo: auth.user?.emp_no || '' })
const blocks = ref<any[]>([])
const newFile = ref<File | null>(null)
async function loadBlocks(hull: string) {
  try { blocks.value = hull ? (await get('/hulls/' + hull)).blocks : [] } catch { blocks.value = [] }
}
watch(() => form.HullNo, (h) => { if (isNew) form.BlockId = ''; loadBlocks(h) }, { immediate: true })
watch(d, (v: any) => {
  if (!v) return
  Object.assign(form, { DrawingNo: v.DrawingNo, DrawingNm: v.DrawingNm, HullNo: v.HullNo, BlockId: v.BlockId ?? '', Discipline: v.Discipline, DesignerEmpNo: v.DesignerEmpNo ?? '' })
  if (viewRev.value === null || !v.revisions.some((r: any) => r.RevNo === viewRev.value)) viewRev.value = v.revisions[v.revisions.length - 1].RevNo
}, { immediate: true })

const body = () => ({ ...form, BlockId: form.BlockId === '' ? null : Number(form.BlockId), DesignerEmpNo: nz(form.DesignerEmpNo) })
async function save() {
  if (!form.DrawingNo || !form.DrawingNm) return ui.toast('도면번호와 도면명을 입력하세요.', 'e')
  if (isNew) {
    const r = await run(() => post('/drawings', body()), '도면이 등록되었습니다. (Rev0 작성중)')
    if (!r) return
    if (newFile.value) {
      try { await upload(`/drawings/${r.DrawingId}/revisions/0/file`, newFile.value); ui.toast('PDF가 첨부되었습니다.', 's') } catch (e: any) { ui.toast('도면은 등록됐지만 PDF 첨부에 실패했습니다: ' + e.message, 'e') }
    }
    ui.openModal('dwg', r.DrawingId)
  } else await run(() => put('/drawings/' + props.id, body()))
}
async function remove() {
  if (!(await ui.ask('도면과 리비전·결재·공정 연계를 삭제합니다.'))) return
  if (await run(() => del('/drawings/' + props.id), '삭제되었습니다.')) ui.closeModal()
}

// ----- PDF 뷰어 -----
const viewRev = ref<number | null>(null), pdfUrl = ref(''), pdfErr = ref('')
const vrow = computed(() => d.value?.revisions.find((r: any) => r.RevNo === viewRev.value))
async function loadPdf() {
  if (isNew || viewRev.value === null) return
  const my = viewRev.value
  try {
    const u = await blobUrl(`/drawings/${props.id}/revisions/${my}/file`)
    if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = u; pdfErr.value = ''
  } catch (e: any) { pdfErr.value = e.message }
}
watch([viewRev, () => vrow.value?.has_file, () => ui.version], loadPdf)
onBeforeUnmount(() => { if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value) })
const canUp = computed(() => canW.value && vrow.value?.RevStatus === 'DRAFT')
async function takeFile(f?: File, rev: number | null = viewRev.value) {
  if (!f) return
  if (isNew) { newFile.value = f; return }
  if (await run(() => upload(`/drawings/${props.id}/revisions/${rev}/file`, f), `Rev${rev}에 PDF를 업로드했습니다.`)) viewRev.value = rev
}
async function onFile(e: Event) {
  const el = e.target as HTMLInputElement
  await takeFile(el.files?.[0])
  el.value = ''
}
const over = ref(false), asc = ref(false)
const onDrop = (e: DragEvent) => { over.value = false; if (canUp.value && !busy.value) void takeFile(e.dataTransfer?.files?.[0]) }
const rmFile = async () => { if (await ui.ask('업로드한 PDF를 삭제합니다.')) run(() => del(`/drawings/${props.id}/revisions/${viewRev.value}/file`), '파일을 삭제했습니다.') }

// ----- 개정·결재·배포 -----
const last = computed(() => d.value?.revisions[d.value.revisions.length - 1])
const nrFile = ref<File | null>(null), nr = reactive({ ChangeDesc: '' }), ap = reactive({ a1: 'lee.dwg', a2: 'admin' })
const newRev = async () => {
  if (!nr.ChangeDesc.trim()) return ui.toast('개정 사유를 입력하세요.', 'e')
  const rev = last.value.RevNo + 1, f = nrFile.value
  // 개정 생성 후 선택한 PDF를 같은 Rev에 올린다. 파일만 실패해도 Rev는 만들어진 상태라 따로 알린다.
  const ok = await run(async () => {
    const r = await post(`/drawings/${props.id}/revisions`, { ChangeDesc: nr.ChangeDesc })
    if (f) { try { await upload(`/drawings/${props.id}/revisions/${rev}/file`, f) } catch (e: any) { ui.toast(`Rev${rev}은 만들어졌지만 PDF 첨부에 실패했습니다: ${e.message}`, 'e') } }
    return r
  }, f ? `새 Rev${rev}를 작성중으로 만들고 PDF를 첨부했습니다.` : '새 Rev가 작성중으로 생성되었습니다.')
  if (ok) { nr.ChangeDesc = ''; nrFile.value = null; viewRev.value = rev }
}
const request = () => {
  if (ap.a1 === ap.a2) return ui.toast('검토자와 승인자는 서로 다른 사람이어야 합니다.', 'e')
  return run(() => post(`/drawings/${props.id}/request`, ap), '결재가 요청되었습니다.')
}
const issue = () => run(() => post(`/drawings/${props.id}/revisions/${last.value.RevNo}/issue`), '도면이 배포되었습니다. 연계 공정 상태가 갱신됩니다.')

// ----- 공정 연계 -----
const linkSel = ref(''), linkReq = ref(true)
const addLink = async () => { if (!linkSel.value) return ui.toast('공정을 선택하세요.', 'e'); if (await run(() => post('/links', { drawing_id: Number(props.id), plan_id: Number(linkSel.value), required: linkReq.value }), '공정이 연계되었습니다.')) linkSel.value = '' }
const delLink = (l: any) => run(() => del(`/links?drawing_id=${props.id}&plan_id=${l.PlanId}`), '연계가 해제되었습니다.')
const goPlan = (hull: string) => { ui.closeModal(); router.push({ name: 'plans', query: { hull } }) }
const step = (n: number) => (n === 1 ? '검토' : '승인')
const resBdg = (r: string) => ({ WAIT: ['대기', 'b-warn'], APPROVE: ['승인', 'b-ok'], REJECT: ['반려', 'b-bad'] }[r] || [r, ''])
</script>

<template>
  <Modal :title="isNew ? '도면 등록' : d ? '도면 ' + d.DrawingNo : '도면 상세'" @close="ui.closeModal()">
    <div v-if="error" class="warnbox" role="alert">{{ error }}</div>
    <div v-else data-test="dwg-modal">
      <div v-if="isNew" class="card">
        <p class="muted" style="margin-top:0">신규 도면은 Rev0(작성중)으로 생성됩니다. PDF는 지금 첨부하거나 등록 후 뷰어에서 올릴 수 있습니다.</p>
      </div>

      <div :class="isNew ? '' : 'dwgx'">
        <div v-if="!isNew" class="card" data-test="pdf-card">
          <h3>도면 뷰어 (PDF) <span class="muted" style="font-weight:400;font-size:12px">작성중(DRAFT) 리비전만 업로드·교체·삭제</span></h3>
          <div class="bar">
            <select v-if="d" v-model="viewRev" aria-label="리비전" data-test="view-rev"><option v-for="r in [...d.revisions].reverse()" :key="r.RevNo" :value="r.RevNo">Rev{{ r.RevNo }} ({{ ui.cn('DWGSTAT', r.RevStatus) }})</option></select>
            <span v-if="vrow">{{ vrow.FileNm || '파일 없음' }} <span v-if="vrow.has_file" class="bdg b-ok">업로드 파일</span><span v-else class="bdg b-warn">샘플 PDF</span></span>
          </div>
          <div class="bar">
            <label class="drop" :class="{ over, off: !canUp || busy }" @dragover.prevent="over = true" @dragleave="over = false" @drop.prevent="onDrop">
              <input type="file" accept=".pdf,application/pdf" :disabled="!canUp || busy" aria-label="PDF 업로드" data-test="pdf-input" @change="onFile">
              <span>PDF를 끌어 놓거나 눌러서 선택</span>
            </label>
            <button class="btn" :disabled="!canUp || !vrow?.has_file" data-test="pdf-del" @click="rmFile">파일 삭제</button>
            <a v-if="pdfUrl" :href="pdfUrl" target="_blank" rel="noopener" class="btn">새 창으로 열기</a>
          </div>
          <div class="pdfbox"><PdfViewer v-if="pdfUrl" :url="pdfUrl" data-test="pdf-frame" /><div v-else class="empty">{{ pdfErr || 'PDF를 불러오는 중…' }}</div></div>
        </div>

        <div class="stack">
          <div class="card"><h3>도면 정보</h3>
            <form class="grid g2 dform" @submit.prevent="save">
              <div><label class="f">도면번호 *</label><input v-model="form.DrawingNo" :readonly="!isNew" data-test="d-no"></div>
              <div><label class="f">분야</label><select v-model="form.Discipline"><option v-for="c in ui.codes('DWGDISC')" :key="c.Code" :value="c.Code">{{ c.CodeName }}</option></select></div>
              <div class="span2"><label class="f">도면명 *</label><input v-model="form.DrawingNm" data-test="d-nm"></div>
              <div><label class="f">호선</label><select v-model="form.HullNo" :disabled="!isNew" data-test="d-hull"><option v-for="h in ui.lookups?.hulls || []" :key="h.HullNo" :value="h.HullNo">{{ h.HullNo }} {{ h.HullNm }}</option></select></div>
              <div><label class="f">블록</label><select v-model="form.BlockId"><option value="">블록 없음</option><option v-for="b in blocks" :key="b.BlockId" :value="b.BlockId">{{ b.BlockCd }} {{ b.BlockNm }}</option></select></div>
              <div class="span2"><label class="f">설계자</label><select v-model="form.DesignerEmpNo"><option value="">미지정</option><option v-for="u in ui.lookups?.users || []" :key="u.emp_no" :value="u.emp_no">{{ u.display_name }} ({{ u.emp_no }})</option></select></div>
              <div v-if="isNew" class="span2"><label class="f">도면 파일 (PDF, 선택)</label><FileDrop v-model="newFile" test-id="d-pdf" /></div>
              <div class="span2 bar" style="margin:0"><button class="btn pri" data-test="d-save" :disabled="busy || !canW">저장</button><button v-if="!isNew" type="button" class="btn dng" data-test="d-del" :disabled="busy || !canW" @click="remove">삭제</button></div>
            </form>
          </div>

          <template v-if="d">
            <div class="card"><h3>리비전 이력</h3>
              <div class="tw"><table class="tbl cards">
                <thead><tr><th aria-sort="none"><button class="sortb" data-test="sort-rev" @click="asc = !asc">Rev {{ asc ? '▲' : '▼' }}</button></th><th>상태</th><th>변경사유</th><th>도면 파일</th><th class="fit">배포일</th></tr></thead>
                <tbody><tr v-for="r in (asc ? d.revisions : [...d.revisions].reverse())" :key="r.RevNo"><td data-label="Rev"><b>Rev{{ r.RevNo }}</b> <span v-if="r.has_file">📎</span> <a @click="viewRev = r.RevNo">보기</a></td>
                  <td data-label="상태"><Badge kind="dwg" :code="r.RevStatus" /></td><td class="wrap" data-label="변경사유">{{ r.ChangeDesc }}</td>
                  <td class="wrap" data-label="도면 파일"><span class="fn rfn" :title="r.FileNm || ''">{{ r.has_file ? r.FileNm : '샘플 PDF' }}</span></td>
                  <td class="fit" data-label="배포일">{{ r.IssueDt || '-' }}</td></tr></tbody>
              </table></div>
              <div style="margin-top:10px" data-test="rev-actions">
                <form v-if="['ISSUED', 'OBSOLETE'].includes(last.RevStatus)" class="grid g2" style="align-items:end" @submit.prevent="newRev">
                  <div class="span2"><label class="f">신규 Rev{{ last.RevNo + 1 }} 개정 사유</label><input v-model="nr.ChangeDesc" data-test="nr-desc"></div>
                  <div class="span2"><label class="f">도면 파일 (PDF, 선택)</label><FileDrop v-model="nrFile" test-id="nr-pdf" :disabled="busy || !canW" /></div>
                  <div><button class="btn pri" data-test="nr-save" :disabled="busy || !canW">신규 Rev 작성</button></div>
                </form>
                <template v-else-if="last.RevStatus === 'DRAFT'">
                  <div class="warnbox">Rev{{ last.RevNo }} 작성중입니다. 검토자/승인자를 지정해 결재를 요청하세요.</div>
                  <form class="grid g2" style="align-items:end" @submit.prevent="request">
                    <div><label class="f">1단계 검토자</label><select v-model="ap.a1" data-test="ap-a1"><option v-for="u in ui.lookups?.users || []" :key="u.emp_no" :value="u.emp_no">{{ u.display_name }} ({{ u.emp_no }})</option></select></div>
                    <div><label class="f">2단계 승인자</label><select v-model="ap.a2" data-test="ap-a2"><option v-for="u in ui.lookups?.users || []" :key="u.emp_no" :value="u.emp_no">{{ u.display_name }} ({{ u.emp_no }})</option></select></div>
                    <div><button class="btn pri" data-test="ap-request" :disabled="busy || !canW">결재 요청</button></div>
                  </form>
                </template>
                <div v-else-if="last.RevStatus === 'REVIEW'" class="warnbox">Rev{{ last.RevNo }} 결재 진행중입니다. 결재자는 [결재함]에서 처리합니다.</div>
                <template v-else-if="last.RevStatus === 'APPROVED'">
                  <div class="okbox">Rev{{ last.RevNo }} 승인 완료 — 배포하면 연계 공정의 도면 게이트가 열립니다.</div>
                  <button class="btn ok" data-test="rev-issue" :disabled="busy || !canIssue" @click="issue">Rev{{ last.RevNo }} 배포</button>
                </template>
              </div>
            </div>
          </template>
        </div>
      </div>
      <div v-if="d && !isNew" class="dwgy">
            <div class="card"><h3>결재 이력</h3>
              <div class="tw"><table class="tbl cards">
                <thead><tr><th>Rev</th><th>단계</th><th>결재자</th><th>결과</th><th>의견</th></tr></thead>
                <tbody><tr v-for="a in d.approvals" :key="a.ApprovalId"><td data-label="Rev">Rev{{ a.RevNo }}</td><td data-label="단계">{{ step(a.StepNo) }}</td><td data-label="결재자">{{ a.ApproverNm }}</td>
                  <td data-label="결과"><span class="bdg" :class="resBdg(a.Result)[1]">{{ resBdg(a.Result)[0] }}</span></td><td class="wrap" data-label="의견">{{ a.Comment }}</td></tr>
                  <tr v-if="!d.approvals.length"><td colspan="5" class="empty">결재 이력이 없습니다.</td></tr></tbody>
              </table></div>
            </div>

            <div class="card"><h3>연계 공정</h3>
              <div v-if="d.impact.count" class="warnbox" data-test="impact-warn">⚠ 최근 개정(Rev{{ d.impact.RevNo }}, {{ d.impact.IssueDt }})으로 이미 착수·완료된 공정 <b>{{ d.impact.count }}건</b>이 영향을 받습니다: {{ d.impact.plans.join(', ') }}</div>
              <div class="tw"><table class="tbl cards">
                <thead><tr><th>공정</th><th>상태</th><th>필수</th><th class="r"></th></tr></thead>
                <tbody><tr v-for="l in d.links" :key="l.PlanId" :title="l.PlanStartDt + ' ~ ' + l.PlanEndDt"><td data-label="공정"><a @click="goPlan(l.HullNo)">{{ l.label }}</a></td><td data-label="상태"><Badge kind="plan" :code="l.PlanStatus" /></td><td data-label="필수">{{ l.RequiredYN ? '필수' : '참고' }}</td>
                  <td class="r"><button class="btn sm dng" :disabled="!auth.can('M21', 'M31')" @click="delLink(l)">해제</button></td></tr>
                  <tr v-if="!d.links.length"><td colspan="4" class="empty">연계된 공정이 없습니다.</td></tr></tbody>
              </table></div>
              <form class="bar" style="margin:8px 0 0" @submit.prevent="addLink">
                <select v-model="linkSel" aria-label="연계할 공정" data-test="dl-plan"><option value="">공정 선택</option><option v-for="p in d.free_plans" :key="p.PlanId" :value="p.PlanId">{{ p.label }}</option></select>
                <label class="chk"><input v-model="linkReq" type="checkbox">필수</label><button class="btn" data-test="dl-add" :disabled="busy || !auth.can('M21', 'M31')">+ 공정 연계</button>
              </form>
            </div>
      </div>
    </div>
  </Modal>
</template>
