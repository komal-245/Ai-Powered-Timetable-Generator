const BASE = import.meta.env.VITE_API_URL || ''
export const getToken = () => localStorage.getItem('token')
export const getUser = () => { try { return JSON.parse(localStorage.getItem('user')) } catch { return null } }
export const setSession = (t, u) => { localStorage.setItem('token', t); localStorage.setItem('user', JSON.stringify(u)) }
export const logout = () => { localStorage.removeItem('token'); localStorage.removeItem('user'); location.hash = '#/login' }

async function req(path, opts = {}) {
  const res = await fetch(BASE + '/api' + path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(getToken() ? { Authorization: 'Bearer ' + getToken() } : {}), ...opts.headers },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  })
  if (res.status === 401 && !path.startsWith('/auth/login')) { logout(); throw new Error('Session expired') }
  if (!res.ok) { let m = res.statusText; try { m = (await res.json()).detail || m } catch {} ; throw new Error(typeof m === 'string' ? m : JSON.stringify(m)) }
  return res.json()
}
export const api = {
  get: (p) => req(p), post: (p, b) => req(p, { method: 'POST', body: b ?? {} }),
  put: (p, b) => req(p, { method: 'PUT', body: b }), del: (p) => req(p, { method: 'DELETE' }),
}
export async function download(path, filename) {          // authenticated file download
  const res = await fetch(BASE + '/api' + path, { headers: { Authorization: 'Bearer ' + getToken() } })
  if (!res.ok) { alert((await res.json().catch(() => ({}))).detail || 'Download failed'); return }
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click(); URL.revokeObjectURL(url)
}
