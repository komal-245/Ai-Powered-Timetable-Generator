import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api, getUser, logout } from '../api'
import Chat from './Chat'

const NAV = {
  admin: [['/', '📊 Dashboard'], ['/generate', '🧠 AI Generator'], ['/timetable', '🗓️ Timetable'], ['/history', '🕘 History'],
    ['/analytics', '📈 Analytics'], ['/rooms', '🏫 Classrooms'], ['/master', '🗂️ Master Data'], ['/reports', '📄 Reports'], ['/api-docs', '🔌 REST API']],
  faculty: [['/faculty', '👩‍🏫 My Portal'], ['/rooms', '🏫 Classrooms'], ['/reports', '📄 Reports']],
  student: [['/student', '🎓 My Portal'], ['/rooms', '🏫 Classrooms']],
}

function Bell() {
  const [list, setList] = useState([]), [open, setOpen] = useState(false)
  useEffect(() => { api.get('/notifications').then(setList).catch(() => {}) }, [open])
  const c = { danger: 'text-bad', warning: 'text-warn', info: 'text-accent' }
  return (
    <div className="relative">
      <button className="btn-ghost" onClick={() => setOpen(!open)}>🔔{list.length > 0 && <span className="badge bg-bad text-white">{list.length}</span>}</button>
      {open && <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto card z-30 space-y-2">
        {list.length === 0 && <div className="text-mute text-sm">No notifications</div>}
        {list.map((n, i) => <div key={i} className={`text-sm border-b border-line pb-1 ${c[n.level] || ''}`}>{n.message}</div>)}
      </div>}
    </div>)
}

function Search() {
  const [q, setQ] = useState(''), [res, setRes] = useState(null)
  useEffect(() => { if (q.length < 2) { setRes(null); return } const t = setTimeout(() => api.get('/search?q=' + encodeURIComponent(q)).then(setRes).catch(() => {}), 250); return () => clearTimeout(t) }, [q])
  return (
    <div className="relative w-full max-w-sm">
      <input className="inp" placeholder="Search faculty, subject, room, section…" value={q} onChange={(e) => setQ(e.target.value)} />
      {res && <div className="absolute mt-1 w-full card z-30 max-h-80 overflow-y-auto text-sm space-y-2" onClick={() => setQ('')}>
        {Object.entries(res).filter(([, v]) => v.length).map(([k, v]) => <div key={k}><div className="th !p-0 !border-0">{k}</div>
          {v.map((x, i) => <div key={i}>{x.name || x.label || x.code}{x.designation ? ` · ${x.designation}` : ''}{x.capacity ? ` · cap ${x.capacity}` : ''}</div>)}</div>)}
        {Object.values(res).every((v) => !v.length) && <div className="text-mute">No results</div>}
      </div>}
    </div>)
}

export default function Layout() {
  const user = getUser(), nav = useNavigate()
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light')
  const [menu, setMenu] = useState(false)
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('theme', theme) }, [theme])
  if (!user) { setTimeout(() => nav('/login'), 0); return null }
  return (
    <div className="min-h-screen md:flex">
      <aside className={`${menu ? 'block' : 'hidden'} md:block md:w-56 shrink-0 bg-card border-r border-line p-3 md:sticky md:top-0 md:h-screen`}>
        <div className="font-extrabold text-accent text-lg leading-tight mb-4">⏱️ AI Timetable<div className="text-xs font-normal text-mute">GIET University · CSE</div></div>
        <nav className="space-y-1">{NAV[user.role].map(([to, l]) => (
          <NavLink key={to} to={to} end onClick={() => setMenu(false)} className={({ isActive }) => `block px-3 py-2 rounded-lg text-sm ${isActive ? 'bg-accent text-white' : 'hover:bg-bg'}`}>{l}</NavLink>))}</nav>
      </aside>
      <div className="flex-1 min-w-0">
        <header className="sticky top-0 z-20 bg-bg/90 backdrop-blur border-b border-line px-4 py-2 flex items-center gap-3">
          <button className="btn-ghost md:hidden" onClick={() => setMenu(!menu)}>☰</button>
          <Search />
          <div className="ml-auto flex items-center gap-2">
            <select className="inp !w-auto" value={theme} onChange={(e) => setTheme(e.target.value)}><option value="light">☀️ Light</option><option value="dark">🌙 Dark</option><option value="blue">🔷 Blue</option></select>
            <Bell />
            <div className="text-sm text-right leading-tight hidden sm:block"><b>{user.full_name}</b><div className="text-mute text-xs capitalize">{user.role}</div></div>
            <button className="btn-ghost" onClick={logout}>Logout</button>
          </div>
        </header>
        <main className="p-4 md:p-6 max-w-[1400px] mx-auto"><Outlet /></main>
      </div>
      <Chat />
    </div>)
}
