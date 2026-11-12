<script setup lang="ts">
import { reactive } from 'vue'
import Badge from '../components/Badge.vue'
import Pbar from '../components/Pbar.vue'
import Pager from '../components/Pager.vue'
import { useLoad, useServerPage } from '../composables'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

defineOptions({ name: 'hulls' })
const ui = useUi(), auth = useAuth()
const f = reactive({ status: '', type: '', q: '' })
const applied = reactive({ status: '', type: '', q: '' })
const pg = useServerPage('/hulls', () => applied)
const { loading, error, by, mark, aria } = pg
const search = () => Object.assign(applied, f)
const reset = () => { Object.assign(f, { status: '', type: '', q: '' }); search() }
</script>

<template>
  <div class="ph"><h2>호선 목록</h2><span class="d">행을 클릭하거나 [상세]를 누르면 호선 상세 창이 열립니다.</span></div>
  <form class="bar" @submit.prevent="search">
    <select v-model="f.status" aria-label="상태" data-test="hf-status"><option value="">상태 전체</option><option v-for="c in ui.codes('HULLSTAT')" :key="c.Code" :value="c.Code">{{ c.CodeName }}</option></select>
    <select v-model="f.type" aria-label="선종" data-test="hf-type"><option value="">선종 전체</option><option v-for="c in ui.codes('SHIPTYPE')" :key="c.Code" :value="c.Code">{{ c.CodeName }}</option></select>
    <input v-model="f.q" placeholder="호선번호/호선명/선주" aria-label="검색어" data-test="hf-q">
    <button class="btn pri" data-test="hf-search">조회</button><button type="button" class="btn" @click="reset">초기화</button>
    <span class="sp"></span>
    <button v-if="auth.can('M11')" type="button" class="btn pri" data-test="hull-new" @click="ui.openModal('hull', 'new')">+ 호선 등록</button>
  </form>
  <div v-if="error" class="warnbox" role="alert">{{ error }}</div>
  <div class="tw card" style="padding:0">
    <table class="tbl cards" data-test="hull-table">
      <thead><tr><th class="fit" :aria-sort="aria('HullNo')"><button type="button" class="sortb" @click="by('HullNo')">호선번호{{ mark('HullNo') }}</button></th><th :aria-sort="aria('HullNm')"><button type="button" class="sortb" @click="by('HullNm')">호선명{{ mark('HullNm') }}</button></th><th :aria-sort="aria('ShipType')"><button type="button" class="sortb" @click="by('ShipType')">선종{{ mark('ShipType') }}</button></th><th :aria-sort="aria('HullStatus')"><button type="button" class="sortb" @click="by('HullStatus')">상태{{ mark('HullStatus') }}</button></th><th :aria-sort="aria('OwnerNm')"><button type="button" class="sortb" @click="by('OwnerNm')">선주{{ mark('OwnerNm') }}</button></th><th>선급</th><th>도크</th><th class="fit" :aria-sort="aria('ContractDt')"><button type="button" class="sortb" @click="by('ContractDt')">계약일{{ mark('ContractDt') }}</button></th><th class="fit" :aria-sort="aria('DeliveryDt')"><button type="button" class="sortb" @click="by('DeliveryDt')">인도예정{{ mark('DeliveryDt') }}</button></th><th>진척률</th><th class="r">지연</th><th class="r"></th></tr></thead>
      <tbody>
        <tr v-for="h in pg.items.value" :key="h.HullNo" class="click" :data-test="'hull-row-' + h.HullNo" @click="ui.openModal('hull', h.HullNo)">
          <td class="fit" data-label="호선번호"><b>{{ h.HullNo }}</b></td><td data-label="호선명">{{ h.HullNm }}</td><td class="fit" data-label="선종">{{ ui.cn('SHIPTYPE', h.ShipType) }}</td>
          <td class="fit" data-label="상태"><Badge kind="hull" :code="h.HullStatus" /></td><td data-label="선주">{{ h.OwnerNm }}</td><td class="fit" data-label="선급">{{ h.ClassSociety }}</td><td class="fit" data-label="도크">{{ h.DockNo || '-' }}</td>
          <td class="fit" data-label="계약일">{{ h.ContractDt }}</td><td class="fit" data-label="인도예정">{{ h.DeliveryDt }}</td>
          <td data-label="진척률"><Pbar v-if="h.has_plan" :value="h.progress" /><span v-else class="muted">계획 없음</span></td>
          <td class="r fit" data-label="지연">{{ h.delay_count || '-' }}</td>
          <td class="r fit"><button class="btn sm" @click.stop="ui.openModal('hull', h.HullNo)">상세</button></td>
        </tr>
        <tr v-if="!loading && !pg.total.value"><td colspan="12" class="empty">조건에 맞는 호선이 없습니다. 검색 조건을 바꿔 보세요.</td></tr>
      </tbody>
    </table>
  </div>
  <Pager v-model:page="pg.page.value" :pages="pg.pages.value" :total="pg.total.value" :size="pg.size" unit="척" />
</template>
