import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import { useAuth } from './stores/auth'
import { useUi } from './stores/ui'
import './styles.css'

const app = createApp(App)
app.use(createPinia())
const auth = useAuth()
const ui = useUi()

window.addEventListener('swp:unauth', () => {
  if (!auth.loggedIn) return
  auth.clear(); ui.reset()
  ui.toast('세션이 만료되었습니다. 다시 로그인하세요.', 'e')
  router.push('/login')
})

auth.restore().then(async () => {
  if (auth.loggedIn) await ui.loadLookups().catch(() => {})
  app.use(router)
  app.mount('#app')
})
