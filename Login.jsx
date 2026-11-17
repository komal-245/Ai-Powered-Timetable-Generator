import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setSession } from '../api'

const LOGO = '/giet-logo.png.jpg'
const CAMPUS = '/giet_cse.png.jpg'

export default function Login() {
  const [u, setU] = useState('')
  const [p, setP] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()

  const go = async (e) => {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      const r = await api.post('/auth/login', { username: u, password: p })
      setSession(r.access_token, r.user)
      nav(r.user.role === 'admin' ? '/' : r.user.role === 'faculty' ? '/faculty' : '/student')
    } catch (error) {
      setErr(error?.message || 'Unable to sign in. Please check your credentials and try again.')
    } finally {
      setBusy(false)
    }
  }

  const demo = (a, b) => { setU(a); setP(b) }
  const missing = (e) => { e.currentTarget.alt = 'Image not found: ' + e.currentTarget.getAttribute('src') }

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Full-page campus photo */}
      <img src={CAMPUS} alt="GIET University campus" onError={missing}
        className="absolute inset-0 w-full h-full object-cover object-center" />
      <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-black/10 to-black/40" />

      <div className="relative min-h-screen flex flex-col md:flex-row items-center justify-center md:justify-end p-4 md:p-12 gap-6">
        {/* Title (tablet / laptop / desktop) */}
        <div className="hidden md:block absolute left-12 bottom-10 text-white drop-shadow-lg">
          <h2 className="text-4xl font-extrabold leading-tight">AI-Powered<br />Timetable Generator</h2>
          <p className="mt-2 text-white/90">
            Department of Computer Science &amp; Engineering<br />GIET University, Gunupur
          </p>
        </div>

        {/* Login card (transparent glass, black text) */}
                {/* Login card (transparent glass, black text) */}
        <form onSubmit={go}
          className="w-full max-w-sm space-y-3 rounded-2xl p-6 shadow-2xl border border-white/40 bg-white/10 backdrop-blur-[2px] text-black">
          <div className="text-center space-y-1">
            <img src={LOGO} alt="GIET logo" onError={missing}
              className="h-20 w-20 mx-auto object-contain rounded-full bg-white p-1 shadow-lg" />
            <h1 className="text-xl font-extrabold text-black">GIET University, Gunupur</h1>
            <div className="text-black text-sm font-medium">AI Timetable Generator · CSE</div>
          </div>

          <input
            className="w-full px-3 py-2 rounded-lg border border-black/40 bg-white/30 text-black placeholder-black/70 text-sm outline-none focus:ring-2 focus:ring-black/50"
            placeholder="Username (admin / email-id / roll no)"
            value={u} onChange={(e) => setU(e.target.value)} autoFocus />
          <input
            className="w-full px-3 py-2 rounded-lg border border-black/40 bg-white/30 text-black placeholder-black/70 text-sm outline-none focus:ring-2 focus:ring-black/50"
            type="password" placeholder="Password"
            value={p} onChange={(e) => setP(e.target.value)} />

          {err && <div className="text-red-800 bg-white/70 rounded px-2 py-1 text-sm">{err}</div>}

          <button className="w-full py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="text-xs text-black border-t border-black/30 pt-2 space-y-1">
            <div className="font-medium">Demo accounts (click to fill):</div>
            <button type="button" className="px-3 py-1 rounded-lg border border-black/40 bg-white/30 text-black text-xs mr-1 hover:bg-white/50"
              onClick={() => demo('admin', 'admin123')}>Admin</button>
            <button type="button" className="px-3 py-1 rounded-lg border border-black/40 bg-white/30 text-black text-xs mr-1 hover:bg-white/50"
              onClick={() => demo('shibanisubhadarshini', 'Giet@123')}>Faculty</button>
            <button type="button" className="px-3 py-1 rounded-lg border border-black/40 bg-white/30 text-black text-xs hover:bg-white/50"
              onClick={() => demo('24cse002', '24UG010069')}>Student</button>
          </div>
        </form>
      </div>
    </div>
  )
}