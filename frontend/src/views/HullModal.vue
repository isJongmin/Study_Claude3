<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Donut from '../components/Donut.vue'
import Modal from '../components/Modal.vue'
import Pbar from '../components/Pbar.vue'
import { del, get, post, put } from '../api'
import { DWG_COLORS, PLAN_COLORS } from '../colors'
import { nz, useLoad, useWrite } from '../composables'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

const props = defineProps<{ id: string | number }>()
const ui = useUi(), auth = useAuth(), router = useRouter(), { run, busy } = useWrite()
const isNew = props.id === 'new'
const tab = ref('info')
const canW = auth.can('M11')
const { data: h, error } = useLoad(() => (isNew ? Promise.resolve(null) : get('/hulls/' + props.id)))

const blank = () => ({ HullNo: '', HullNm: '', ShipType: '', HullStatus: 'PLAN', OwnerNm: '', ClassSociety: '', LengthM: '', BreadthM: '', DepthM: '', DeadWeight: '', DockNo: '', ContractDt: '', DeliveryDt: '', Remark: '', UseYN: true })
const form = reactive<any>(blank())
const ms = ref<any[]>([])
const nb = reactive({ BlockCd: '', BlockNm: '', BlockType: '', WeightTon: '' })
watch(h, (v: any) => {
  if (!v) return
  Object.keys(form).forEach((k) => { form[k] = v[k] ?? (typeof form[k] === 'boolean' ? true : '') })
  ms.value = ui.codes('MILESTONE').map((c) => ({ ...(v.milestones.find((m: any) => m.MilestoneCd === c.Code) || {}), MilestoneCd: c.Code, name: c.CodeName }))
}, { immediate: true })

const num = (v: any) => (v === '' || v === null ? null : Number(v))
const body = () => ({ ...form, ShipType: nz(form.ShipType), LengthM: num(form.LengthM), BreadthM: num(form.BreadthM), DepthM: num(form.DepthM), DeadWeight: num(form.DeadWeight), ContractDt: nz(form.ContractDt), DeliveryDt: nz(form.DeliveryDt) })

async function save() {
  const r = await run(() => (isNew ? post('/hulls', body()) : put('/hulls/' + props.id, body())), isNew ? '호선이 등록되었습니다.' : '저장되었습니다.')
  if (r && isNew) ui.openModal('hull', r.HullNo)
}
async function remove() {
  if (!(await ui.ask(`호선 ${props.id} 및 하위 데이터(블록·공정·도면)를 모두 삭제합니다. 계속할까요?`))) return
  if (await run(() => del('/hulls/' + props.id), '삭제되었습니다.')) ui.closeModal()
}
const saveMs = () => run(() => put(`/hulls/${props.id}/milestones`, ms.value.map((m) => ({ MilestoneCd: m.MilestoneCd, PlanDt: nz(m.PlanDt), ActualDt: nz(m.ActualDt) }))), '주요일정이 저장되었습니다.')
const addBlock = async () => {
  if (await run(() => post(`/hulls/${props.id}/blocks`, { ...nb, BlockType: nz(nb.BlockType), WeightTon: num(nb.WeightTon) }), '블록이 추가되었습니다.')) Object.assign(nb, { BlockCd: '', BlockNm: '', BlockType: '', WeightTon: '' })
}
const delBlock = async (b: any) => {
  if (await ui.ask('블록과 해당 블록의 공정을 삭제합니다. (도면의 블록 연결은 해제됩니다)')) run(() => del('/blocks/' + b.BlockId), '삭제되었습니다.')
}
const diffDays = (a: string, b: string) => (a && b ? Math.round((Date.parse(b) - Date.parse(a)) / 864e5) : '-')
const PC = PLAN_COLORS
const DCOL = DWG_COLORS
const jump = (name: string, query?: any) => { ui.closeModal(); router.push({ name, query }) }
const tabs = [['info', '기본정보'], ['ms', '주요일정'], ['blk', '블록 구성'], ['sum', '연계 현황']]
</script>

<template>
  <Modal :title="isNew ? '호선 등록' : `호선 ${id}${h ? ' · ' + (h.HullNm || '') : ''}`" @close="ui.closeModal()">
    <div v-if="error" class="warnbox" role="alert">{{ error }}</div>
    <div v-else data-test="hull-modal">
      <div v-if="!isNew" class="stabs"><a v-for="[k, n] in tabs" :key="k" :class="{ act: tab === k }" :data-test="'htab-' + k" @click="tab = k">{{ n }}</a></div>

      <div v-if="tab === 'info'" class="card">
        <form class="grid g4" @submit.prevent="save">
          <div><label class="f">호선번호 *</label><input v-model="form.HullNo" :readonly="!isNew" data-test="h-no"></div>
          <div class="span2"><label class="f">호선명</label><input v-model="form.HullNm" data-test="h-nm"></div>
          <div><label class="f">선종</label><select v-model="form.ShipType"><option value="">선택</option><option v-for="c in ui.codes('SHIPTYPE')" :key="c.Code" :value="c.Code">{{ c.CodeName }}</option></select></div>
          <div><label class="f">상태</label><select v-model="form.HullStatus" data-test="h-status"><option v-for="c in ui.codes('HULLSTAT')" :key="c.Code" :value="c.Code">{{ c.CodeName }}</option></select></div>
          <div class="span2"><label class="f">선주</label><input v-model="form.OwnerNm"></div>
          <div><label class="f">선급</label><input v-model="form.ClassSociety"></div>
          <div><label class="f">전장(m)</label><input v-model="form.LengthM" type="number" step="0.01" min="0"></div>
          <div><label class="f">선폭(m)</label><input v-model="form.BreadthM" type="number" step="0.01" min="0"></div>
          <div><label class="f">선심(m)</label><input v-model="form.DepthM" type="number" step="0.01" min="0"></div>
          <div><label class="f">재화중량(DWT)</label><input v-model="form.DeadWeight" type="number" min="0"></div>
          <div><label class="f">도크/건조장소</label><input v-model="form.DockNo"></div>
          <div><label class="f">계약일</label><input v-model="form.ContractDt" type="date" data-test="h-contract"></div>
          <div><label class="f">인도 예정일</label><input v-model="form.DeliveryDt" type="date" data-test="h-delivery"></div>
          <div><label class="f">사용여부</label><label class="chk"><input v-model="form.UseYN" type="checkbox">사용</label></div>
          <div class="span4"><label class="f">비고</label><input v-model="form.Remark"></div>
          <div class="span4 bar" style="margin:0">
            <button class="btn pri" data-test="h-save" :disabled="busy || !canW">저장</button>
            <button v-if="!isNew" type="button" class="btn dng" data-test="h-del" :disabled="busy || !canW" @click="remove">삭제</button>
            <span class="note" style="margin:0">삭제하면 블록·공정·도면이 함께 삭제됩니다.</span>
          </div>
        </form>
      </div>

      <div v-if="h && tab === 'ms'" class="card">
        <div class="tw"><table class="tbl cards">
          <thead><tr><th>일정</th><th>계획일</th><th>실적일</th><th class="r">차이(일)</th></tr></thead>
          <tbody><tr v-for="m in ms" :key="m.MilestoneCd"><td data-label="일정">{{ m.name }}</td>
            <td data-label="계획일"><input v-model="m.PlanDt" type="date" :disabled="!canW"></td><td data-label="실적일"><input v-model="m.ActualDt" type="date" :disabled="!canW"></td>
            <td class="r" data-label="차이(일)">{{ diffDays(m.PlanDt, m.ActualDt) }}</td></tr></tbody>
        </table></div>
        <div class="bar" style="margin:12px 0 0"><button class="btn pri" data-test="ms-save" :disabled="busy || !canW" @click="saveMs">일정 저장</button></div>
      </div>

      <div v-if="h && tab === 'blk'" class="card">
        <div class="tw"><table class="tbl cards" data-test="block-table">
          <thead><tr><th>블록코드</th><th>블록명</th><th>유형</th><th class="r">중량(ton)</th><th>진척</th><th class="r">공정</th><th class="r">도면</th><th class="r"></th></tr></thead>
          <tbody>
            <tr v-for="b in h.blocks" :key="b.BlockId"><td data-label="블록코드"><b>{{ b.BlockCd }}</b></td><td data-label="블록명">{{ b.BlockNm }}</td><td data-label="유형">{{ ui.cn('BLOCKTYPE', b.BlockType) }}</td>
              <td class="r" data-label="중량">{{ b.WeightTon ?? '' }}</td><td data-label="진척"><Pbar v-if="b.plan_count" :value="b.progress" /><span v-else>-</span></td>
              <td class="r" data-label="공정">{{ b.plan_count }}</td><td class="r" data-label="도면">{{ b.drawing_count }}</td>
              <td class="r"><button class="btn sm dng" :disabled="!canW" @click="delBlock(b)">삭제</button></td></tr>
            <tr v-if="!h.blocks.length"><td colspan="8" class="empty">블록이 없습니다. 아래에서 추가하세요.</td></tr>
          </tbody>
        </table></div>
        <form class="grid g6" style="margin-top:12px;align-items:end" @submit.prevent="addBlock">
          <div><label class="f">블록코드 *</label><input v-model="nb.BlockCd" data-test="b-cd"></div>
          <div class="span2"><label class="f">블록명</label><input v-model="nb.BlockNm"></div>
          <div><label class="f">유형</label><select v-model="nb.BlockType"><option value="">선택</option><option v-for="c in ui.codes('BLOCKTYPE')" :key="c.Code" :value="c.Code">{{ c.CodeName }}</option></select></div>
          <div><label class="f">중량(ton)</label><input v-model="nb.WeightTon" type="number" min="0"></div>
          <div><button class="btn pri" data-test="b-add" :disabled="busy || !canW">+ 블록 추가</button></div>
        </form>
      </div>

      <div v-if="h && tab === 'sum'" class="grid g2 hsum">
        <div class="card"><h3>공정 <button class="btn sm" @click="jump('plans', { hull: String(id) })">간트 보기</button></h3>
          <template v-if="Object.values(h.plan_stats).some((n: any) => n)">
            <Donut side :items="Object.keys(PC).map((k) => ({ label: ui.cn('PLANSTAT', k), value: h.plan_stats[k], color: PC[k] }))" /></template>
          <div v-else class="empty">공정 계획이 없습니다.</div></div>
        <div class="card"><h3>도면 <button class="btn sm" @click="jump('drawings')">목록 보기</button></h3>
          <Donut side v-if="Object.values(h.dwg_stats).some((n: any) => n)" :items="Object.keys(DCOL).map((k) => ({ label: ui.cn('DWGSTAT', k), value: h.dwg_stats[k], color: DCOL[k] }))" />
          <div v-else class="empty">도면이 없습니다.</div></div>
      </div>
    </div>
  </Modal>
</template>
