<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Badge from '../components/Badge.vue'
import Donut from '../components/Donut.vue'
import Icon from '../components/Icon.vue'
import Ship from '../components/Ship.vue'
import { get } from '../api'
import { DWG_COLORS, PLAN_COLORS } from '../colors'
import { useLoad } from '../composables'
import { useUi } from '../stores/ui'

defineOptions({ name: 'dashboard' })
const ui = useUi(), router = useRouter()
const { data: d, loading, error } = useLoad(() => get('/dashboard'))
const goPlan = (hull: string) => router.push({ name: 'plans', query: { hull } })
const ratio = (n: number, t: number) => (t ? Math.min(100, Math.max(n ? 4 : 0, Math.round((n / t) * 100))) : 0)
const tot = computed(() => ({
  hulls: d.value?.hulls.length ?? 0,
  plans: Object.values(d.value?.plan_status ?? {}).reduce((a: number, b: any) => a + b, 0) as number,
  dwgs: (d.value?.dwg_by_discipline ?? []).reduce((a: number, x: any) => a + x.total, 0) as number,
}))
const pick = ref('')
const cur = computed(() => d.value?.hulls.find((h: any) => h.HullNo === pick.value) ?? d.value?.hulls[0])
// 기준일(서버 today) 대비 인도일: 남으면 D-n, 지나면 D+n
const dleft = (dt?: string) => (dt && d.value ? Math.round((Date.parse(dt) - Date.parse(d.value.today)) / 864e5) : 9999)
const dday = (dt?: string) => {
  if (!dt || !d.value) return ''
  const n = dleft(dt)
  return n > 0 ? `D-${n}` : n < 0 ? `D+${-n}` : 'D-Day'
}
const byDelivery = computed(() => (d.value?.hulls ?? []).filter((h: any) => h.DeliveryDt).sort((a: any, b: any) => a.DeliveryDt.localeCompare(b.DeliveryDt)))
</script>

<template>
  <div class="dash">
    <div v-if="error" class="warnbox" role="alert"><Icon name="alert" :size="18" />{{ error }}</div>
    <div v-else-if="loading && !d" data-test="dashboard-loading" aria-busy="true">
      <div class="sk" style="height:40px;width:220px;margin-bottom:24px"></div>
      <div class="kpis"><div v-for="i in 4" :key="i" class="sk" style="height:150px;border-radius:20px"></div></div>
      <div class="sk" style="height:260px;margin-top:32px;border-radius:20px"></div>
    </div>
    <div v-else-if="d" data-test="dashboard">
      <div class="ph"><h2>대시보드</h2><span class="d">호선·공정·도면 현황을 한눈에 확인하고 조치가 필요한 항목으로 이동하세요.</span></div>

      <h3 class="sec"><span class="secno">1</span>요약 수치</h3>
      <div class="kpis">
        <button class="kpi t-blue" data-test="kpi-active" @click="router.push({ name: 'hulls' })">
          <div class="kh"><span class="chip" aria-hidden="true">🚢</span><span class="l">진행 호선</span><span class="pill blue">운영 중</span></div>
          <div class="v">{{ d.kpi.active_hulls }}<small>척</small></div>
          <div class="kb"><span class="meter"><i :style="{ width: ratio(d.kpi.active_hulls, tot.hulls) + '%' }"></i></span><span class="kr">전체 {{ tot.hulls }}척 중</span></div>
          <div class="h">설계·건조·진수·시운전 중</div></button>
        <button class="kpi t-red" :class="{ bad: d.kpi.delay_plans }" data-test="kpi-delay" @click="router.push({ name: 'plans' })">
          <div class="kh"><span class="chip" aria-hidden="true">🚨</span><span class="l">지연 공정</span><span class="pill" :class="d.kpi.delay_plans ? 'red' : 'green'">{{ d.kpi.delay_plans ? '조치 필요' : '정상' }}</span></div>
          <div class="v">{{ d.kpi.delay_plans }}<small>건</small></div>
          <div class="kb"><span class="meter"><i :style="{ width: ratio(d.kpi.delay_plans, tot.plans) + '%' }"></i></span><span class="kr">전체 공정 {{ tot.plans }}건 중</span></div>
          <div class="h">{{ d.kpi.delay_plans ? '계획 종료일이 지난 공정' : '지연 없음' }}</div></button>
        <button class="kpi t-orange" :class="{ warn: d.kpi.waiting_plans }" data-test="kpi-waiting" @click="router.push({ name: 'plans' })">
          <div class="kh"><span class="chip" aria-hidden="true">⏳</span><span class="l">도면 대기 공정</span><span class="pill" :class="d.kpi.waiting_plans ? 'orange' : 'green'">{{ d.kpi.waiting_plans ? '주의' : '정상' }}</span></div>
          <div class="v">{{ d.kpi.waiting_plans }}<small>건</small></div>
          <div class="kb"><span class="meter"><i :style="{ width: ratio(d.kpi.waiting_plans, tot.plans) + '%' }"></i></span><span class="kr">전체 공정 {{ tot.plans }}건 중</span></div>
          <div class="h">필수 도면 배포를 기다리는 공정</div></button>
        <button class="kpi t-purple" :class="{ warn: d.kpi.pending_drawings }" data-test="kpi-pending" @click="router.push({ name: 'approvals' })">
          <div class="kh"><span class="chip" aria-hidden="true">📐</span><span class="l">결재·배포 대기 도면</span><span class="pill" :class="d.kpi.pending_drawings ? 'purple' : 'green'">{{ d.kpi.pending_drawings ? '확인 필요' : '정상' }}</span></div>
          <div class="v">{{ d.kpi.pending_drawings }}<small>건</small></div>
          <div class="kb"><span class="meter"><i :style="{ width: ratio(d.kpi.pending_drawings, tot.dwgs) + '%' }"></i></span><span class="kr">전체 도면 {{ tot.dwgs }}건 중</span></div>
          <div class="h">검토 중이거나 승인 후 배포 전</div></button>
      </div>

      <h3 class="sec"><span class="secno">2</span>호선별 진척</h3>
      <div class="card">
        <div class="ships">
          <button v-for="h in d.hulls" :key="h.HullNo" class="ship" :data-test="'ship-' + h.HullNo" :aria-label="`${h.HullNo} ${h.HullNm} 진척률 ${h.progress}%`" :class="{ sel: cur?.HullNo === h.HullNo }" @click="pick = h.HullNo">
            <Ship :progress="h.progress" :type="h.ShipType" />
            <div class="pc">{{ h.progress }}%</div><div class="no">{{ h.HullNo }}</div><div class="nm" :title="h.HullNm">{{ h.HullNm }}</div><div class="st">{{ ui.cn('HULLSTAT', h.HullStatus) }}</div>
          </button>
        </div>
        <div v-if="cur" class="voyage" data-test="voyage">
          <div class="voyage-head" aria-live="polite">
            <div class="voyage-nm"><b>{{ cur.HullNo }}</b><span :title="cur.HullNm">{{ cur.HullNm }}</span><span class="bdg b-info">{{ ui.cn('SHIPTYPE', cur.ShipType) }}</span></div>
            <p>{{ cur.progress }}% 진행 · 인도 예정 {{ cur.DeliveryDt || '미정' }}<template v-if="dday(cur.DeliveryDt)"> · <b>{{ dday(cur.DeliveryDt) }}</b></template></p>
            <button class="btn sm" data-test="voyage-plan" @click="goPlan(cur.HullNo)">공정 계획 보기 →</button>
          </div>
          <div class="sea" :style="{ '--p': cur.progress / 100 }" aria-hidden="true">
            <span v-for="t in [0, 25, 50, 75, 100]" :key="t" class="sea-tick" :style="{ '--t': t / 100 }">{{ t === 0 ? '착공' : t === 100 ? '인도' : t + '%' }}</span>
            <span class="wake"></span>
            <span class="sailer"><Ship :progress="cur.progress" :type="cur.ShipType" /></span>
          </div>
        </div>
      </div>

      <h3 class="sec"><span class="secno">3</span>상태 분포</h3>
      <div class="dist">
        <div class="card"><h3>공정 상태 분포</h3>
          <Donut side caption="공정" :items="Object.keys(PLAN_COLORS).map((k) => ({ label: ui.cn('PLANSTAT', k), value: d.plan_status[k], color: PLAN_COLORS[k] }))" /></div>
        <div class="card"><h3>분야별 도면 상태 <span class="muted sub">가운데는 배포율</span></h3>
          <div class="chips top"><span v-for="k in ['ISSUED', 'APPROVED', 'REVIEW', 'DRAFT']" :key="k"><i :style="{ background: DWG_COLORS[k] }"></i>{{ ui.cn('DWGSTAT', k) }}</span></div>
          <div class="dwgm">
            <div v-for="x in d.dwg_by_discipline" :key="x.Discipline" class="dm" :data-test="'disc-' + x.Discipline">
              <Donut mini caption="배포" :center="Math.round((x.ISSUED / x.total) * 100) + '%'" :items="['ISSUED', 'APPROVED', 'REVIEW', 'DRAFT'].map((k) => ({ label: ui.cn('DWGSTAT', k), value: x[k], color: DWG_COLORS[k] }))" />
              <b>{{ x.name }}</b><small>총 {{ x.total }}건</small>
              <div class="cn"><span v-for="k in ['ISSUED', 'APPROVED', 'REVIEW', 'DRAFT']" :key="k" :title="ui.cn('DWGSTAT', k)"><i :style="{ background: DWG_COLORS[k] }"></i>{{ x[k] }}</span></div>
            </div>
          </div>
        </div>
        <div class="card"><h3>인도 일정</h3>
          <ol class="tl" data-test="delivery-timeline"><li v-for="h in byDelivery" :key="h.HullNo" :class="{ soon: dleft(h.DeliveryDt) <= 90 }">
            <div class="r1"><b>{{ h.HullNo }}</b><span class="nm">{{ h.HullNm }}</span><em>{{ dday(h.DeliveryDt) }}</em></div>
            <div class="r2"><span>{{ h.DeliveryDt }}</span><span class="pb"><i :style="{ width: h.progress + '%' }"></i></span><span>{{ h.progress }}%</span></div>
          </li></ol>
          <div v-if="!byDelivery.length" class="empty">인도 예정 호선이 없습니다.</div>
        </div>
      </div>
      <h3 class="sec"><span class="secno">4</span>조치가 필요한 항목</h3>
      <div class="cols-auto act3">
        <div class="card" data-test="card-delay"><h3>지연 공정 <span class="bdg b-bad">{{ d.delay.length }}건</span></h3>
          <ul v-if="d.delay.length" class="lst"><li v-for="p in d.delay.slice(0, 6)" :key="p.PlanId" @click="goPlan(p.HullNo)"><span>{{ p.HullNo }} {{ p.label }}</span><span class="m">{{ p.ProgressRate }}% · 계획종료 {{ p.PlanEndDt }}</span></li></ul>
          <div v-else class="empty">지연 공정이 없습니다.</div></div>
        <div class="card" data-test="card-waiting"><h3>도면 대기 공정 <span class="bdg b-warn">{{ d.waiting.length }}건</span></h3>
          <ul v-if="d.waiting.length" class="lst"><li v-for="p in d.waiting.slice(0, 6)" :key="p.PlanId" @click="goPlan(p.HullNo)"><span>{{ p.HullNo }} {{ p.label }}</span><span class="m">착수 {{ p.PlanStartDt }} · {{ p.blockers.join(', ') }}</span></li></ul>
          <div v-else class="empty">대기 중인 공정이 없습니다.</div></div>
        <div class="card" data-test="card-impact"><h3>도면 개정 영향 공정 <span class="bdg b-info">{{ d.impacts.length }}건</span></h3>
          <ul v-if="d.impacts.length" class="lst"><li v-for="x in d.impacts" :key="x.DrawingId + '-' + x.PlanId" @click="ui.openModal('dwg', x.DrawingId)">
            <span>{{ x.DrawingNo }} Rev{{ x.RevNo }} → {{ x.label }} <Badge kind="plan" :code="x.PlanStatus" /></span><span class="m">{{ x.ChangeDesc }} · 배포 {{ x.IssueDt }}</span></li></ul>
          <div v-else class="empty">최근 개정된 도면의 영향 공정이 없습니다.</div></div>
      </div>
    </div>
  </div>
</template>
