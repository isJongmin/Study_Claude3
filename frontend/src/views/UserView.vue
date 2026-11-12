<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import Pager from '../components/Pager.vue'
import { del, get, post, put, qs } from '../api'
import { nz, useServerPage, useWrite } from '../composables'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

defineOptions({ name: 'users' })
const ui = useUi(), auth = useAuth(), { run, busy } = useWrite()
const ST: Record<string, [string, string]> = { pending: ['승인대기', 'b-warn'], approved: ['승인', 'b-ok'], rejected: ['반려', 'b-bad'], disabled: ['중지', 'b-off'] }
const f = reactive({ status: '', q: '' }), applied = reactive({ status: '', q: '' })
const pg = useServerPage('/users', () => applied)
const { data, error } = pg
const sel = ref<string | 'new' | null>(null), secret = ref('')
const form = reactive<any>({ last_name: '', first_name: '', birth_date: '', phone: '', email: '', emp_no: '', password: '', status: 'approved', group: '', totp_enabled: false })
const cur = computed(() => pg.items.value.find((u: any) => u.emp_no === sel.value))
const canW = computed(() => auth.can('M91'))
const gname = (u: any) => u.groups.map((g: string) => ui.lookups?.groups?.find((x: any) => x.AuthCd === g)?.AuthNm).join(', ') || '-'
function pick(u: any) {
  sel.value = u.emp_no; secret.value = ''
  Object.assign(form, { last_name: u.last_name ?? '', first_name: u.first_name ?? '', birth_date: u.birth_date ?? '', phone: u.phone, email: u.email, emp_no: u.emp_no, password: '', status: u.status, group: u.groups[0] || '', totp_enabled: u.totp_enabled })
}
function newUser() {
  sel.value = 'new'; secret.value = ''
  Object.assign(form, { last_name: '', first_name: '', birth_date: '', phone: '', email: '', emp_no: '', password: '', status: 'approved', group: '', totp_enabled: false })
}
async function save() {
  const body = { ...form, group: nz(form.group) }
  const r = await run(() => (sel.value === 'new' ? post('/users', body) : put('/users/' + sel.value, body)))
  if (r) { sel.value = r.emp_no; secret.value = r.totp_secret_new || ''; form.password = '' }
}
async function remove() {
  if (!(await ui.ask(`회원 ${sel.value} 을(를) 삭제합니다.`))) return
  if (await run(() => del('/users/' + sel.value), '삭제되었습니다.')) sel.value = null
}
const approve = () => run(() => post(`/users/${sel.value}/approve`), `${cur.value?.display_name} 님의 가입을 승인했습니다.`)
// 목록 아래 폼은 선택한 회원의 최신 값을 반영한다
</script>

<template>
  <div class="ph"><h2>회원관리</h2><span class="d">상단 목록 / 하단 입력·수정</span></div>
  <div v-if="error" class="warnbox" role="alert">{{ error }}</div>
  <form class="bar" @submit.prevent="Object.assign(applied, f)">
    <select v-model="f.status" aria-label="상태" data-test="uf-status"><option value="">상태 전체</option><option v-for="(v, k) in ST" :key="k" :value="k">{{ v[0] }}</option></select>
    <input v-model="f.q" placeholder="아이디/이름/이메일/전화" aria-label="검색어" data-test="uf-q">
    <button class="btn pri" data-test="uf-search">조회</button><button type="button" class="btn" @click="f.status = ''; f.q = ''; Object.assign(applied, f)">초기화</button>
    <span class="sp"></span><span class="note" style="margin:0">{{ pg.total.value }}명 · 승인대기 {{ data?.pending ?? 0 }}명</span>
  </form>
  <div class="card" style="padding:0"><div class="tw"><table class="tbl cards" data-test="user-table">
    <thead><tr><th>아이디</th><th>이름</th><th>이메일</th><th class="fit">전화번호</th><th class="fit">생년월일</th><th>상태</th><th>2차인증</th><th>권한그룹</th><th class="fit">가입일</th></tr></thead>
    <tbody>
      <tr v-for="u in pg.items.value" :key="u.emp_no" class="click" :class="{ sel: sel === u.emp_no }" :data-test="'user-row-' + u.emp_no" @click="pick(u)">
        <td data-label="아이디"><b>{{ u.emp_no }}</b></td><td data-label="이름">{{ u.display_name }}</td><td data-label="이메일">{{ u.email }}</td><td class="fit" data-label="전화번호">{{ u.phone }}</td><td class="fit" data-label="생년월일">{{ u.birth_date }}</td>
        <td class="fit" data-label="상태"><span class="bdg" :class="ST[u.status][1]">{{ ST[u.status][0] }}</span></td><td class="fit" data-label="2차인증">{{ u.totp_enabled ? '사용' : '-' }}</td><td data-label="권한그룹">{{ gname(u) }}</td><td class="fit" data-label="가입일">{{ u.created_at }}</td>
      </tr>
    </tbody>
  </table></div></div>
  <Pager v-model:page="pg.page.value" :pages="pg.pages.value" :total="pg.total.value" :size="pg.size" unit="명" />

  <div class="card" style="margin-top:12px" data-test="user-form">
    <h3>{{ sel === 'new' ? '회원 등록' : cur ? `회원 수정 — ${cur.display_name}` : '입력 / 수정' }}</h3>
    <form v-if="sel" class="grid g4" autocomplete="off" @submit.prevent="save">
      <div><label class="f">성 *</label><input v-model="form.last_name" data-test="u-ln"></div>
      <div><label class="f">이름 *</label><input v-model="form.first_name" data-test="u-fn"></div>
      <div><label class="f">생년월일 *</label><input v-model="form.birth_date" type="date" data-test="u-bd"></div>
      <div><label class="f">전화번호 *</label><input v-model="form.phone" placeholder="010-0000-0000" data-test="u-ph"></div>
      <div class="span2"><label class="f">이메일 *</label><input v-model="form.email" type="email" data-test="u-em"></div>
      <div><label class="f">아이디 *</label><input v-model="form.emp_no" :readonly="sel !== 'new'" data-test="u-id"></div>
      <div><label class="f">{{ sel === 'new' ? '비밀번호 *' : '비밀번호 (변경 시만 입력)' }}</label><input v-model="form.password" type="password" autocomplete="new-password" placeholder="8자 이상" data-test="u-pw"></div>
      <div><label class="f">상태</label><select v-model="form.status" data-test="u-status"><option v-for="(v, k) in ST" :key="k" :value="k">{{ v[0] }}</option></select></div>
      <div><label class="f">권한 그룹</label><select v-model="form.group" data-test="u-group"><option value="">없음</option><option v-for="g in ui.lookups?.groups || []" :key="g.AuthCd" :value="g.AuthCd">{{ g.AuthNm }}</option></select></div>
      <div class="span2"><label class="f">구글 2차인증</label><label class="chk"><input v-model="form.totp_enabled" type="checkbox">사용 (새로 켜면 인증 앱 등록용 비밀키가 한 번 표시됩니다)</label></div>
      <div v-if="secret" class="span4 okbox" data-test="totp-secret">인증 앱에 등록할 비밀키: <b>{{ secret }}</b> — 이 창을 벗어나면 다시 볼 수 없습니다.</div>
      <div class="span4 bar" style="margin:0">
        <button type="button" class="btn" :disabled="!canW" @click="newUser">신규</button>
        <button class="btn pri" data-test="u-save" :disabled="busy || !canW">저장</button>
        <button v-if="sel !== 'new'" type="button" class="btn dng" data-test="u-del" :disabled="busy || !canW" @click="remove">삭제</button>
        <button v-if="cur && cur.status === 'pending'" type="button" class="btn ok" data-test="u-approve" :disabled="busy || !canW" @click="approve">가입 승인</button>
      </div>
    </form>
    <div v-else class="empty">목록에서 회원을 선택하거나 <button class="btn sm" :disabled="!canW" data-test="u-new" @click="newUser">신규</button>를 누르세요.</div>
  </div>
</template>
