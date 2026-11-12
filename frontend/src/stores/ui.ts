import { defineStore } from 'pinia'
import { get } from '../api'

export interface Tab { name: string; title: string; path: string }
export type ModalState = { kind: 'hull' | 'dwg'; id: string | number | 'new' } | null

const ROUTE_TITLES: Record<string, string> = {
  dashboard: '대시보드', hulls: '호선 목록', plans: '공정 계획', progress: '공정 실적', drawings: '도면 목록', approvals: '결재함', users: '회원관리',
}
export { ROUTE_TITLES }

export const useUi = defineStore('ui', {
  state: () => ({
    toasts: [] as { id: number; msg: string; type: 's' | 'e' }[],
    tabs: [] as Tab[],
    modal: null as ModalState,
    version: 0, // 쓰기 성공마다 +1: 열려 있는 모든 화면이 다시 읽는다
    lookups: null as any,
    collapsed: false,
    drawer: false,
    confirmState: null as null | { msg: string; resolve: (v: boolean) => void },
    seq: 1,
  }),
  getters: {
    today: (s) => s.lookups?.today || '2026-10-19',
  },
  actions: {
    toast(msg: string, type: 's' | 'e' = 's') {
      const id = this.seq++
      this.toasts.push({ id, msg, type })
      setTimeout(() => { this.toasts = this.toasts.filter((t) => t.id !== id) }, type === 's' ? 4000 : 6000)
    },
    bump() { this.version++ },
    async loadLookups() { this.lookups = await get('/lookups') },
    cn(group: string, code: string | null | undefined) {
      if (!code) return ''
      return this.lookups?.codes?.[group]?.find((c: any) => c.Code === code)?.CodeName || code
    },
    codes(group: string): { Code: string; CodeName: string }[] { return this.lookups?.codes?.[group] || [] },
    openTab(name: string, path: string) {
      if (!this.tabs.find((t) => t.name === name)) this.tabs.push({ name, title: ROUTE_TITLES[name] || name, path })
      else this.tabs.find((t) => t.name === name)!.path = path
    },
    closeTab(name: string) {
      const i = this.tabs.findIndex((t) => t.name === name)
      if (i >= 0) this.tabs.splice(i, 1)
      return this.tabs[Math.max(0, i - 1)]?.path
    },
    closeOthers(keep: string) { this.tabs = this.tabs.filter((t) => t.name === keep) },
    ask(msg: string) {
      return new Promise<boolean>((resolve) => { this.confirmState = { msg, resolve } })
    },
    answer(v: boolean) { this.confirmState?.resolve(v); this.confirmState = null },
    openModal(kind: 'hull' | 'dwg', id: string | number) { this.modal = { kind, id } },
    closeModal() { this.modal = null },
    reset() { this.tabs = []; this.modal = null; this.drawer = false },
  },
})
