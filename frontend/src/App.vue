<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get } from './api'
import Icon from './components/Icon.vue'
import Modal from './components/Modal.vue'
import { MENU_ROUTE, useAuth } from './stores/auth'
import { useUi } from './stores/ui'
import DrawingModal from './views/DrawingModal.vue'
import HullModal from './views/HullModal.vue'

const auth = useAuth(), ui = useUi(), route = useRoute(), router = useRouter()
const showAcct = ref(false), q = ref('')
const region = ref('울산'), wx = ref<any>(null)
try { region.value = localStorage.getItem('swp_region') || '울산' } catch { /* 저장소 접근 불가 */ }

const menuTree = computed(() => {
  const top = auth.menus.filter((m: any) => !m.ParentId)
  return top.map((t: any) => ({ ...t, kids: auth.menus.filter((m: any) => m.ParentId === t.MenuId && m.TokenUrl) }))
})
const flat = computed(() => auth.menus.filter((m: any) => m.TokenUrl && MENU_ROUTE[m.TokenUrl]))
const hits = computed(() => (q.value ? flat.value.filter((m: any) => m.Title.includes(q.value)) : []))
const go = (token: string) => { router.push({ name: MENU_ROUTE[token] }); ui.drawer = false; q.value = '' }
const isAct = (token: string) => route.name === MENU_ROUTE[token]
const locked = computed(() => !!ui.modal || ui.drawer || !!ui.confirmState)

async function loadWx() {
  if (!auth.loggedIn) return
  try { wx.value = await get('/weather?region=' + encodeURIComponent(region.value)) } catch { wx.value = null }
}
watch(region, (v) => { try { localStorage.setItem('swp_region', v) } catch { /* 무시 */ } loadWx() })
watch(() => auth.loggedIn, (v) => { if (v) loadWx() })
onMounted(() => { loadWx(); setInterval(loadWx, 600000) })
const groupNm = computed(() => (auth.user.groups || []).map((g: string) => ui.lookups?.groups?.find((x: any) => x.AuthCd === g)?.AuthNm || g).join(', ') || '권한그룹 없음')
const wxIcon = computed(() => { const c = wx.value?.condition || ''; return c.includes('맑') ? '☀️' : c.includes('구름') ? '⛅' : c.includes('흐') ? '☁️' : c.includes('눈') ? '❄️' : c.includes('비') || c.includes('소나기') ? '🌧️' : '🌤️' })

function closeOthers() {
  const keep = String(route.name)
  if (ui.tabs.some((t) => t.name === keep)) ui.closeOthers(keep)
}
function closeTab(name: string) {
  const next = ui.closeTab(name)
  if (route.name === name) router.push(next || '/dashboard')
}
async function logout() {
  showAcct.value = false
  await auth.logout(); ui.reset(); router.push('/login')
}
watch(locked, (v) => document.body.classList.toggle('lock', v), { immediate: true })
const openTabNames = computed(() => ui.tabs.map((t) => t.name))
const viewName = (c: any) => c
</script>

<template>
  <router-view v-if="route.name === 'login' || !auth.loggedIn" />
  <div v-else class="shell" data-test="shell">
    <header class="hd">
      <button class="btn sm menu-btn" aria-label="메뉴" data-test="menu-btn" :aria-expanded="ui.drawer" @click="ui.drawer = !ui.drawer"><Icon name="menu" :size="18" /></button>
      <div class="brand"><i class="mark"><Icon name="ship" :size="16" /></i>SWP <span>조선소 통합관리</span></div>
      <div class="search">
        <input v-model="q" placeholder="화면 검색" data-test="screen-search" aria-label="화면 검색">
        <button type="button" class="search-submit" aria-label="검색" @click="hits[0] && go(hits[0].TokenUrl)">검색</button>
        <div v-if="hits.length" class="pop"><a v-for="m in hits" :key="m.MenuId" @click="go(m.TokenUrl)">{{ m.Title }}</a></div>
      </div>
      <div class="sp"></div>
      <div class="wx" data-test="weather">
        <select v-model="region" aria-label="날씨 지역"><option>울산</option><option>거제</option><option>목포</option></select>
        <template v-if="wx"><span>{{ wxIcon }}</span><b>{{ wx.tempC }}°C</b><span class="detail muted">{{ wx.condition }} · 습도 {{ wx.humidity }}% · 풍속 {{ wx.windMs }}m/s</span>
          <span class="src" :class="{ live: wx.state !== 'sample' }">{{ wx.state === 'sample' ? '샘플' : 'LIVE' }}</span></template>
        <span v-else class="muted">날씨 없음</span>
      </div>
      <div class="acct">
        <button class="btn sm" data-test="acct-btn" @click="showAcct = !showAcct"><i class="avatar">{{ auth.user.display_name.slice(0, 1) }}</i><span class="nm"><b>{{ auth.user.display_name }} 님 ▾</b><small data-test="acct-meta">{{ ui.today }} · {{ groupNm }}</small></span></button>
        <div v-if="showAcct" class="pop">
          <div style="padding:4px 8px"><b>{{ auth.user.display_name }}</b><div class="muted">{{ auth.user.emp_no }}</div></div>
          <button class="btn block" data-test="logout" @click="logout">로그아웃</button>
        </div>
      </div>
    </header>
    <div class="body" :class="{ col: ui.collapsed }">
      <nav class="sb" :class="{ open: ui.drawer }" aria-label="메뉴">
        <template v-for="t in menuTree" :key="t.MenuId">
          <a v-if="t.TokenUrl" class="item" :class="{ act: isAct(t.TokenUrl) }" :data-test="'menu-' + t.TokenUrl" @click="go(t.TokenUrl)"><span class="ico"><Icon :name="MENU_ROUTE[t.TokenUrl]" /></span><span class="lbl">{{ t.Title }}</span></a>
          <template v-else>
            <div class="grp">{{ t.Title }}</div>
            <a v-for="k in t.kids" :key="k.MenuId" class="item" :class="{ act: isAct(k.TokenUrl) }" :data-test="'menu-' + k.TokenUrl" :title="k.Title" @click="go(k.TokenUrl)"><span class="ico"><Icon :name="MENU_ROUTE[k.TokenUrl]" /></span><span class="lbl">{{ k.Title }}</span></a>
          </template>
        </template>
      </nav>
      <button class="sb-handle" :aria-label="ui.collapsed ? '메뉴 펼치기' : '메뉴 접기'" :title="ui.collapsed ? '메뉴 펼치기' : '메뉴 접기'" :aria-expanded="!ui.collapsed" data-test="collapse" @click="ui.collapsed = !ui.collapsed"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="ui.collapsed ? 'M9 6l6 6-6 6' : 'M15 6l-6 6 6 6'" /></svg></button>
      <div class="sb-mask" :class="{ on: ui.drawer }" @click="ui.drawer = false"></div>
      <main class="main">
        <div class="tabs" role="tablist">
          <div v-for="t in ui.tabs" :key="t.name" class="tab" :class="{ act: route.name === t.name }" role="tab" :aria-selected="route.name === t.name" :data-test="'tab-' + t.name" @click="router.push(t.path)">
            {{ t.title }}<button v-if="ui.tabs.length > 1" :aria-label="t.title + ' 닫기'" @click.stop="closeTab(t.name)">×</button>
          </div>
          <button v-if="ui.tabs.length > 1" type="button" class="tabs-others" data-test="close-others" @click="closeOthers">다른 탭 닫기</button>
        </div>
        <section class="work" :class="{ locked }">
          <router-view v-slot="{ Component, route: r }">
            <keep-alive :include="openTabNames.map(viewName)"><component :is="Component" :key="String(r.name)" /></keep-alive>
          </router-view>
        </section>
      </main>
    </div>

    <HullModal v-if="ui.modal?.kind === 'hull'" :id="ui.modal.id" :key="'h' + ui.modal.id" />
    <DrawingModal v-if="ui.modal?.kind === 'dwg'" :id="ui.modal.id" :key="'d' + ui.modal.id" />
    <Modal v-if="ui.confirmState" title="확인" small @close="ui.answer(false)">
      <p data-test="confirm-msg" style="margin-top:0">{{ ui.confirmState.msg }}</p>
      <div class="bar" style="justify-content:flex-end;margin:0"><button class="btn" data-test="confirm-no" @click="ui.answer(false)">취소</button><button class="btn pri" data-test="confirm-yes" @click="ui.answer(true)">확인</button></div>
    </Modal>
  </div>
  <div class="toasts"><div v-for="t in ui.toasts" :key="t.id" :class="t.type" :role="t.type === 'e' ? 'alert' : 'status'" data-test="toast"><Icon :name="t.type === 'e' ? 'alert' : 'check'" /><span>{{ t.msg }}</span></div></div>
</template>
