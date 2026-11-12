export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message)
  }
}

let token = ''
try { token = sessionStorage.getItem('swp_token') || '' } catch { /* 저장소 접근 불가 시 메모리만 사용 */ }
export const getToken = () => token
export function setToken(t: string) {
  token = t
  try { t ? sessionStorage.setItem('swp_token', t) : sessionStorage.removeItem('swp_token') } catch { /* 무시 */ }
}

async function send(method: string, path: string, body?: unknown, form?: FormData): Promise<Response> {
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = 'Bearer ' + token
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  let res: Response
  try {
    res = await fetch('/api' + path, { method, headers, body: form ?? (body !== undefined ? JSON.stringify(body) : undefined) })
  } catch {
    throw new ApiError(0, 'NETWORK', '서버에 연결할 수 없습니다. 네트워크와 서버 실행 상태를 확인한 뒤 다시 시도하세요.')
  }
  if (!res.ok) {
    let j: any = {}
    try { j = await res.json() } catch { /* 본문 없음 */ }
    if (res.status === 401 && token && j.code === 'UNAUTHORIZED') window.dispatchEvent(new Event('swp:unauth'))
    throw new ApiError(res.status, j.code || 'ERROR', j.message || '요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.')
  }
  return res
}

export async function api<T = any>(method: string, path: string, body?: unknown): Promise<T> {
  return (await send(method, path, body)).json()
}
export const get = <T = any>(p: string) => api<T>('GET', p)
export const post = <T = any>(p: string, b: unknown = {}) => api<T>('POST', p, b)
export const put = <T = any>(p: string, b: unknown) => api<T>('PUT', p, b)
export const del = <T = any>(p: string) => api<T>('DELETE', p)

export async function upload<T = any>(path: string, file: File): Promise<T> {
  const f = new FormData()
  f.append('file', file)
  return (await send('POST', path, undefined, f)).json()
}

/** Bearer 헤더가 필요한 PDF는 fetch로 받아 blob URL로 보여 준다. */
export async function blobUrl(path: string): Promise<string> {
  return URL.createObjectURL(await (await send('GET', path)).blob())
}

export const qs = (o: Record<string, any>) => {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(o)) if (v !== '' && v != null) p.set(k, String(v))
  const s = p.toString()
  return s ? '?' + s : ''
}
