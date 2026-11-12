import { createRouter, createWebHistory } from 'vue-router'
import { ROUTE_MENU, useAuth } from './stores/auth'
import { useUi } from './stores/ui'

const R = (path: string, name: string, view: () => Promise<any>) => ({ path, name, component: view, meta: { tab: true } })

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('./views/AuthView.vue') },
    R('/dashboard', 'dashboard', () => import('./views/DashboardView.vue')),
    R('/hulls', 'hulls', () => import('./views/HullListView.vue')),
    R('/plans', 'plans', () => import('./views/PlanView.vue')),
    R('/progress', 'progress', () => import('./views/ProgressView.vue')),
    R('/drawings', 'drawings', () => import('./views/DrawingListView.vue')),
    R('/approvals', 'approvals', () => import('./views/ApprovalView.vue')),
    R('/users', 'users', () => import('./views/UserView.vue')),
    { path: '/:rest(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuth()
  if (to.name === 'login') return auth.loggedIn ? '/dashboard' : true
  if (!auth.loggedIn) return '/login'
  const menu = ROUTE_MENU[String(to.name)]
  if (menu && !auth.see(menu)) return '/dashboard' // 메뉴 권한이 없으면 대시보드로
  return true
})

router.afterEach((to) => {
  if (to.meta.tab) useUi().openTab(String(to.name), to.fullPath)
})
