<script setup lang="ts">
import { reactive } from 'vue'
import Badge from '../components/Badge.vue'
import Pager from '../components/Pager.vue'
import { useServerPage } from '../composables'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

defineOptions({ name: 'drawings' })
const ui = useUi(), auth = useAuth()
const f = reactive({ hull: '', disc: '', status: '', q: '' })
const applied = reactive({ hull: '', disc: '', status: '', q: '' })
const pg = useServerPage('/drawings', () => applied)
const { loading, error, by, mark, aria } = pg
const search = () => Object.assign(applied, f)
const reset = () => { Object.assign(f, { hull: '', disc: '', status: '', q: '' }); search() }
</script>

<template>
  <div class="ph"><h2>도면 목록</h2><span class="d">행을 클릭하면 도면 상세·PDF 뷰어·리비전·결재 창이 열립니다. Rev는 현재 배포(유효) 리비전입니다.</span></div>
  <form class="bar" @submit.prevent="search">
    <select v-model="f.hull" aria-label="호선" data-test="df-hull"><option value="">호선 전체</option><option v-for="h in ui.lookups?.hulls || []" :key="h.HullNo" :value="h.HullNo">{{ h.HullNo }}</option></select>
    <select v-model="f.disc" aria-label="분야" data-test="df-disc"><option value="">분야 전체</option><option v-for="c in ui.codes('DWGDISC')" :key="c.Code" :value="c.Code">{{ c.CodeName }}</option></select>
    <select v-model="f.status" aria-label="상태" data-test="df-status"><option value="">상태 전체</option><option v-for="c in ui.codes('DWGSTAT')" :key="c.Code" :value="c.Code">{{ c.CodeName }}</option></select>
    <input v-model="f.q" placeholder="도면번호/도면명" aria-label="검색어" data-test="df-q">
    <button class="btn pri" data-test="df-search">조회</button><button type="button" class="btn" @click="reset">초기화</button><span class="sp"></span>
    <button v-if="auth.can('M31')" type="button" class="btn pri" data-test="dwg-new" @click="ui.openModal('dwg', 'new')">+ 도면 등록</button>
  </form>
  <div v-if="error" class="warnbox" role="alert">{{ error }}</div>
  <div class="card" style="padding:0"><div class="tw"><table class="tbl cards" data-test="dwg-table">
    <thead><tr><th class="fit" :aria-sort="aria('DrawingNo')"><button type="button" class="sortb" @click="by('DrawingNo')">도면번호{{ mark('DrawingNo') }}</button></th><th :aria-sort="aria('DrawingNm')"><button type="button" class="sortb" @click="by('DrawingNm')">도면명{{ mark('DrawingNm') }}</button></th><th class="fit" :aria-sort="aria('HullNo')"><button type="button" class="sortb" @click="by('HullNo')">호선{{ mark('HullNo') }}</button></th><th class="fit" :aria-sort="aria('BlockCd')"><button type="button" class="sortb" @click="by('BlockCd')">블록{{ mark('BlockCd') }}</button></th><th :aria-sort="aria('Discipline')"><button type="button" class="sortb" @click="by('Discipline')">분야{{ mark('Discipline') }}</button></th><th class="fit" :aria-sort="aria('CurrentRevNo')"><button type="button" class="sortb" @click="by('CurrentRevNo')">Rev{{ mark('CurrentRevNo') }}</button></th><th :aria-sort="aria('DwgStatus')"><button type="button" class="sortb" @click="by('DwgStatus')">상태{{ mark('DwgStatus') }}</button></th><th :aria-sort="aria('DesignerNm')"><button type="button" class="sortb" @click="by('DesignerNm')">설계자{{ mark('DesignerNm') }}</button></th><th class="r">연계공정</th><th class="r"></th></tr></thead>
    <tbody>
      <tr v-for="d in pg.items.value" :key="d.DrawingId" class="click" :data-test="'dwg-row-' + d.DrawingNo" @click="ui.openModal('dwg', d.DrawingId)">
        <td class="fit" data-label="도면번호"><b>{{ d.DrawingNo }}</b></td><td data-label="도면명">{{ d.DrawingNm }}</td><td class="fit" data-label="호선">{{ d.HullNo }}</td><td class="fit" data-label="블록">{{ d.BlockCd || '-' }}</td>
        <td class="fit" data-label="분야">{{ ui.cn('DWGDISC', d.Discipline) }}</td>
        <td class="fit" data-label="Rev">Rev{{ d.CurrentRevNo }}<span v-if="d.LatestRevNo !== d.CurrentRevNo" class="muted"> (최신 Rev{{ d.LatestRevNo }})</span></td>
        <td class="fit" data-label="상태"><Badge kind="dwg" :code="d.DwgStatus" /></td><td data-label="설계자">{{ d.DesignerNm }}</td><td class="r" data-label="연계공정">{{ d.link_count || '-' }}</td>
        <td class="r fit"><button class="btn sm" @click.stop="ui.openModal('dwg', d.DrawingId)">상세</button></td>
      </tr>
      <tr v-if="!loading && !pg.total.value"><td colspan="10" class="empty">조건에 맞는 도면이 없습니다. 검색 조건을 바꿔 보세요.</td></tr>
    </tbody>
  </table></div></div>
  <Pager v-model:page="pg.page.value" :pages="pg.pages.value" :total="pg.total.value" :size="pg.size" />
</template>
