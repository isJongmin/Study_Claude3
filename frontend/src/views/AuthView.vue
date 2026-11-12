<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError, post } from '../api'
import { useAuth } from '../stores/auth'
import { useUi } from '../stores/ui'

defineOptions({ name: 'login' })
const auth = useAuth(), ui = useUi(), router = useRouter()
const view = ref<'login' | 'otp' | 'signup'>('login')
const err = ref(''), busy = ref(false)
const f = reactive({ emp_no: '', password: '' })
const otp = reactive({ token: '', code: '' })
const s = reactive({ last_name: '', first_name: '', birth_date: '', phone: '', email: '', emp_no: '', password: '', pw2: '' })

async function enter() {
  await ui.loadLookups()
  router.push('/dashboard')
}
async function run(fn: () => Promise<void>) {
  err.value = ''; busy.value = true
  try { await fn() } catch (e) { err.value = e instanceof ApiError ? e.message : '처리하지 못했습니다. 다시 시도하세요.' } finally { busy.value = false }
}
const doLogin = () => run(async () => {
  const r = await auth.login(f.emp_no.trim(), f.password)
  if (r.otp_required) { otp.token = r.otp_token; otp.code = ''; view.value = 'otp' } else await enter()
})
const doOtp = () => run(async () => {
  try { await auth.otp(otp.token, otp.code.trim()) } catch (e) {
    if (e instanceof ApiError && e.code === 'OTP_EXPIRED') view.value = 'login'
    throw e
  }
  await enter()
})
const doSignup = () => run(async () => {
  if (s.password !== s.pw2) throw new ApiError(0, 'PW', '비밀번호 확인이 일치하지 않습니다. 같은 비밀번호를 다시 입력하세요.')
  const { pw2, ...body } = s
  await post('/auth/signup', body)
  view.value = 'login'; f.emp_no = s.emp_no; f.password = ''
  ui.toast('가입 신청 완료. 관리자 승인 후 로그인할 수 있습니다.', 's')
})
</script>

<template>
  <div class="auth">
    <form v-if="view === 'login'" class="acard" data-test="login-form" @submit.prevent="doLogin">
      <div class="logo">SWP SHIPYARD</div><h1>조선소 통합관리</h1><div class="sub">호선 · 공정 · 도면 관리 시스템</div>
      <label class="f" for="lid">아이디</label><input id="lid" v-model="f.emp_no" data-test="login-id" autocomplete="username" autofocus>
      <label class="f" for="lpw" style="margin-top:10px">비밀번호</label><input id="lpw" v-model="f.password" data-test="login-pw" type="password" autocomplete="current-password">
      <div class="err" data-test="auth-err" role="alert">{{ err }}</div>
      <button class="btn pri block" data-test="login-submit" :disabled="busy">로그인</button>
      <div class="links"><a data-test="go-signup" @click="view = 'signup'; err = ''">회원가입</a><span class="muted">2차 인증 계정은 다음 단계에서 OTP 입력</span></div>
      <div class="hint"><b>데모 계정</b><br>admin / admin1234 (OTP <b>123456</b>) · park.pm / pm1234 (공정)<br>lee.dwg / dwg1234 (도면, OTP 123456) · han.wk / wk1234 · choi.qa / qa1234 (조회전용)</div>
    </form>

    <form v-else-if="view === 'otp'" class="acard" data-test="otp-form" @submit.prevent="doOtp">
      <div class="logo">2-STEP VERIFICATION</div><h1>2차 인증</h1><div class="sub">인증 앱(Google Authenticator)의 6자리 코드를 입력하세요.</div>
      <input v-model="otp.code" class="otp" data-test="otp-code" maxlength="6" inputmode="numeric" placeholder="······" autofocus aria-label="인증 코드">
      <div class="err" data-test="auth-err" role="alert">{{ err }}</div>
      <button class="btn pri block" data-test="otp-submit" :disabled="busy">확인</button>
      <div class="links"><a @click="view = 'login'; err = ''">← 로그인으로</a><span class="muted">데모 OTP: 123456 (시드 계정 전용)</span></div>
    </form>

    <form v-else class="acard wide" data-test="signup-form" @submit.prevent="doSignup">
      <div class="logo">SIGN UP</div><h1>회원가입</h1><div class="sub">가입 후 관리자 승인이 완료되면 로그인할 수 있습니다.</div>
      <div class="grid g2" autocomplete="off">
        <div><label class="f">성</label><input v-model="s.last_name" data-test="su-ln"></div>
        <div><label class="f">이름</label><input v-model="s.first_name" data-test="su-fn"></div>
        <div><label class="f">생년월일</label><input v-model="s.birth_date" type="date" data-test="su-bd"></div>
        <div><label class="f">전화번호</label><input v-model="s.phone" placeholder="010-0000-0000" data-test="su-ph"></div>
        <div class="span2"><label class="f">이메일</label><input v-model="s.email" type="email" data-test="su-em"></div>
        <div class="span2"><label class="f">아이디</label><input v-model="s.emp_no" placeholder="영문/숫자 4~20자" data-test="su-id"></div>
        <div><label class="f">비밀번호</label><input v-model="s.password" type="password" placeholder="8자 이상" data-test="su-pw"></div>
        <div><label class="f">비밀번호 확인</label><input v-model="s.pw2" type="password" data-test="su-pw2"></div>
      </div>
      <div class="err" data-test="auth-err" role="alert">{{ err }}</div>
      <button class="btn pri block" data-test="su-submit" :disabled="busy">가입 신청</button>
      <div class="links"><a @click="view = 'login'; err = ''">← 로그인으로</a></div>
    </form>
  </div>
</template>
