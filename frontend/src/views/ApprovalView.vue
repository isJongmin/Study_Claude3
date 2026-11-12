<script setup lang="ts">
import { reactive, ref } from 'vue'
import Pager from '../components/Pager.vue'
import { get, post } from '../api'
import { useLoad, useWrite } from '../composables'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

defineOptions({ name: 'approvals' })
const ui = useUi(), auth = useAuth(), { run, busy } = useWrite()
const hpage = ref(1)
const { data, error } = useLoad(() => get('/approvals/inbox?hpage=' + hpage.value), () => [hpage.value])
const comments = reactive<Record<number, string>>({})
const canW = () => auth.can('M33')
async function act(a: any, result: 'APPROVE' | 'REJECT') {
  const comment = (comments[a.ApprovalId] || '').trim()
  if (result === 'REJECT' && !comment) return ui.toast('반려 시 의견을 입력하세요. 반려 사유를 적어야 작성자가 수정할 수 있습니다.', 'e')
  await run(() => post(`/approvals/${a.ApprovalId}/act`, { result, comment }), result === 'APPROVE' ? '승인했습니다.' : '반려했습니다. 도면은 작성중으로 되돌려집니다.')
}
const issue = (x: any) => run(() => post(`/drawings/${x.DrawingId}/revisions/${x.RevNo}/issue`), '도면이 배포되었습니다. 연계 공정 상태가 갱신됩니다.')
</script>

<template>
  <div class="ph"><h2>도면 결재함</h2><span class="d">{{ auth.user.display_name }} 님의 결재 대기와 배포 대기 도면입니다.</span></div>
  <div v-if="error" class="warnbox" role="alert">{{ error }}</div>
  <div v-if="data" class="stack">
    <div class="card"><h3>내 결재 대기 <span class="bdg b-warn">{{ data.mine.length }}</span></h3>
      <div class="tw"><table class="tbl cards" data-test="apv-mine">
        <thead><tr><th>도면번호</th><th>도면명</th><th class="fit">Rev</th><th class="fit">단계</th><th>변경사유</th><th>의견</th><th class="r"></th></tr></thead>
        <tbody>
          <tr v-for="a in data.mine" :key="a.ApprovalId" :data-test="'apv-' + a.DrawingNo">
            <td data-label="도면번호"><a @click="ui.openModal('dwg', a.DrawingId)">{{ a.DrawingNo }}</a></td><td data-label="도면명">{{ a.DrawingNm }}</td><td class="fit" data-label="Rev">Rev{{ a.RevNo }}</td>
            <td class="fit" data-label="단계">{{ a.StepNo === 1 ? '검토' : '승인' }}</td><td class="wrap" data-label="변경사유">{{ a.ChangeDesc }}</td>
            <td data-label="의견"><input v-model="comments[a.ApprovalId]" placeholder="의견 (반려 시 필수)" aria-label="의견" data-test="apv-comment"></td>
            <td class="r"><button class="btn sm ok" data-test="apv-approve" :disabled="busy || !canW()" @click="act(a, 'APPROVE')">승인</button><button class="btn sm dng" data-test="apv-reject" :disabled="busy || !canW()" @click="act(a, 'REJECT')">반려</button></td>
          </tr>
          <tr v-if="!data.mine.length"><td colspan="7" class="empty">처리할 결재가 없습니다.</td></tr>
        </tbody>
      </table></div></div>
    <div class="card"><h3>배포 대기 (승인 완료) <span class="bdg b-info">{{ data.ready.length }}</span></h3>
      <div class="tw"><table class="tbl cards" data-test="apv-ready">
        <thead><tr><th>도면번호</th><th>도면명</th><th class="fit">Rev</th><th>배포 시 착수 가능해질 수 있는 공정</th><th class="r"></th></tr></thead>
        <tbody>
          <tr v-for="x in data.ready" :key="x.DrawingId"><td data-label="도면번호"><a @click="ui.openModal('dwg', x.DrawingId)">{{ x.DrawingNo }}</a></td><td data-label="도면명">{{ x.DrawingNm }}</td><td class="fit" data-label="Rev">Rev{{ x.RevNo }}</td>
            <td class="wrap" data-label="영향 공정">{{ x.affects.join(', ') || '-' }}</td><td class="r"><button class="btn sm ok" data-test="apv-issue" :disabled="busy || !auth.can('M31', 'M33')" @click="issue(x)">배포</button></td></tr>
          <tr v-if="!data.ready.length"><td colspan="5" class="empty">배포 대기 도면이 없습니다.</td></tr>
        </tbody>
      </table></div></div>
    <div class="card"><h3>최근 결재 이력</h3>
      <div class="tw"><table class="tbl cards">
        <thead><tr><th class="fit">일시</th><th>도면번호</th><th class="fit">Rev</th><th class="fit">단계</th><th>결재자</th><th>결과</th><th>의견</th></tr></thead>
        <tbody>
          <tr v-for="a in data.history.items" :key="a.ApprovalId"><td class="fit" data-label="일시">{{ a.ActDt }}</td><td data-label="도면번호">{{ a.DrawingNo }}</td><td class="fit" data-label="Rev">Rev{{ a.RevNo }}</td><td class="fit" data-label="단계">{{ a.StepNo === 1 ? '검토' : '승인' }}</td>
            <td data-label="결재자">{{ a.ApproverNm }}</td><td data-label="결과"><span class="bdg" :class="a.Result === 'APPROVE' ? 'b-ok' : 'b-bad'">{{ a.Result === 'APPROVE' ? '승인' : '반려' }}</span></td><td class="wrap" data-label="의견">{{ a.Comment }}</td></tr>
          <tr v-if="!data.history.items.length"><td colspan="7" class="empty">결재 이력이 없습니다.</td></tr>
        </tbody>
      </table></div>
      <Pager v-model:page="hpage" :pages="data.history.pages" :total="data.history.total" :size="data.history.size" />
    </div>
  </div>
</template>
