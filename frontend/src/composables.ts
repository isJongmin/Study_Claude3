import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { ApiError, get, qs } from './api'
import { useUi } from './stores/ui'

/** 데이터 읽기: 처음, 의존 값 변경, 다른 화면의 쓰기 성공(ui.version) 때마다 다시 읽는다. */
export function useLoad<T>(fn: () => Promise<T>, deps?: () => unknown[]) {
  const ui = useUi()
  const data = ref(null) as Ref<T | null>
  const loading = ref(true)
  const error = ref('')
  let seq = 0
  async function reload() {
    const my = ++seq
    loading.value = true
    try {
      const r = await fn()
      if (my === seq) { data.value = r; error.value = '' }
    } catch (e) {
      if (my === seq) error.value = e instanceof ApiError ? e.message : '불러오지 못했습니다. 새로고침 후 다시 시도하세요.'
    } finally {
      if (my === seq) loading.value = false
    }
  }
  onMounted(reload)
  watch(() => ui.version, reload)
  if (deps) watch(deps, reload)
  return { data, loading, error, reload }
}

/** 쓰기: 성공 토스트(4초) + 전체 화면 갱신 신호, 실패는 서버 메시지를 오류 토스트(6초)로. */
export function useWrite() {
  const ui = useUi()
  const busy = ref(false)
  async function run<T>(fn: () => Promise<T>, okMsg = '저장되었습니다.', refresh = true): Promise<T | undefined> {
    if (busy.value) return
    busy.value = true
    try {
      const r = await fn()
      if (okMsg) ui.toast(okMsg, 's')
      if (refresh) ui.bump()
      return r
    } catch (e) {
      ui.toast(e instanceof ApiError ? e.message : '처리하지 못했습니다. 잠시 후 다시 시도하세요.', 'e')
    } finally {
      busy.value = false
    }
  }
  return { busy, run }
}

export const pct = (n: number, total: number) => (total ? Math.round((n / total) * 100) : 0)
export const nz = (v: any) => (v === '' || v === undefined ? null : v)

// 표 머리글 정렬: 같은 열을 다시 누르면 방향이 바뀐다. 수치·날짜·글자 모두 한국어 순서로 비교한다.
export function useSort(rows: () => any[]) {
  const key = ref(''), asc = ref(true)
  const sorted = computed(() => {
    const r = [...(rows() || [])]
    if (!key.value) return r
    const k = key.value, s = asc.value ? 1 : -1
    return r.sort((a, b) => s * String(a[k] ?? '').localeCompare(String(b[k] ?? ''), 'ko', { numeric: true }))
  })
  const by = (k: string) => { if (key.value === k) asc.value = !asc.value; else { key.value = k; asc.value = true } }
  const mark = (k: string) => (key.value === k ? (asc.value ? ' ▲' : ' ▼') : '')
  const aria = (k: string) => (key.value === k ? (asc.value ? 'ascending' : 'descending') : 'none')
  return { sorted, by, mark, aria }
}

// 클라이언트 페이징: 목록이 한 화면(size건)을 넘으면 페이지 이동. 행 수가 바뀌면(조회·필터) 1쪽으로 돌아간다.
export function usePage(rows: () => any[], size = 15) {
  const page = ref(1)
  const total = computed(() => (rows() || []).length)
  const pages = computed(() => Math.max(1, Math.ceil(total.value / size)))
  const view = computed(() => (rows() || []).slice((page.value - 1) * size, page.value * size))
  watch(total, () => { page.value = 1 })
  watch(pages, (n) => { if (page.value > n) page.value = n })
  return { page, pages, total, view, size }
}

// 서버 페이징 목록: 쪽·정렬·조건이 바뀔 때마다 서버에서 그 쪽만 읽는다. 조건이 바뀌면 1쪽으로 돌아간다.
export function useServerPage(path: string, filters: () => Record<string, any>, size = 15) {
  const page = ref(1), key = ref(''), asc = ref(true)
  const { data, loading, error, reload } = useLoad<any>(
    () => get(path + qs({ ...filters(), page: page.value, size, sort: key.value, dir: asc.value ? 'asc' : 'desc' })),
    () => [JSON.stringify(filters()), page.value, key.value, asc.value],
  )
  watch(() => JSON.stringify(filters()), () => { page.value = 1 })
  watch(data, (d) => { if (d && d.page !== page.value) page.value = d.page }) // 삭제 등으로 쪽이 줄었을 때
  const items = computed<any[]>(() => data.value?.items || [])
  const total = computed(() => data.value?.total ?? 0)
  const pages = computed(() => data.value?.pages ?? 1)
  const by = (k: string) => { if (key.value === k) asc.value = !asc.value; else { key.value = k; asc.value = true }; page.value = 1 }
  const mark = (k: string) => (key.value === k ? (asc.value ? ' ▲' : ' ▼') : '')
  const aria = (k: string) => (key.value === k ? (asc.value ? 'ascending' : 'descending') : 'none')
  return { data, items, total, pages, page, size, loading, error, reload, by, mark, aria }
}
