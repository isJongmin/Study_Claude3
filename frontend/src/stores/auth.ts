import { defineStore } from 'pinia'
import { get, post, setToken, getToken } from '../api'

export const MENU_ROUTE: Record<string, string> = {
  dashboard: 'dashboard', 'hull-list': 'hulls', 'plan-gantt': 'plans', progress: 'progress', 'dwg-list': 'drawings', 'dwg-approval': 'approvals', 'user-mgmt': 'users',
}
export const ROUTE_MENU: Record<string, string> = { dashboard: 'M00', hulls: 'M11', plans: 'M21', progress: 'M22', drawings: 'M31', approvals: 'M33', users: 'M91' }

export const useAuth = defineStore('auth', {
  state: () => ({ user: null as any, menus: [] as any[], levels: {} as Record<string, number>, ready: false }),
  getters: {
    loggedIn: (s) => !!s.user,
    /** 화면 비활성화용(편의). 실제 판정은 서버가 한다. */
    can: (s) => (...menus: string[]) => menus.some((m) => (s.levels[m] || 0) >= 2),
    see: (s) => (menu: string) => (s.levels[menu] || 0) >= 1,
  },
  actions: {
    async restore() {
      if (getToken()) {
        try { await this.loadMe() } catch { setToken('') }
      }
      this.ready = true
    },
    async loadMe() {
      const r = await get('/auth/me')
      this.user = r.user; this.menus = r.menus; this.levels = r.levels
    },
    async login(emp_no: string, password: string) {
      const r = await post('/auth/login', { emp_no, password })
      if (!r.otp_required) { setToken(r.access_token); await this.loadMe() }
      return r
    },
    async otp(otp_token: string, code: string) {
      const r = await post('/auth/otp', { otp_token, code })
      setToken(r.access_token); await this.loadMe()
    },
    async logout() {
      try { await post('/auth/logout') } catch { /* 이미 만료됨 */ }
      this.clear()
    },
    clear() { setToken(''); this.user = null; this.menus = []; this.levels = {} },
  },
})
