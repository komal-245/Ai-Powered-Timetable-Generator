import { useState, useRef, useEffect } from 'react'
import { api } from '../api'

export default function Chat() {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState([{ from: 'bot', text: 'Hi! Ask me things like "Who teaches AI?" or "Find an empty classroom at 2 PM".' }])
  const [text, setText] = useState('')
  const end = useRef()
  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth' }), [msgs, open])
  const send = async (t = text) => {
    if (!t.trim()) return
    setMsgs((m) => [...m, { from: 'me', text: t }]); setText('')
    try { const r = await api.post('/chat', { message: t }); setMsgs((m) => [...m, { from: 'bot', text: r.reply }]) }
    catch (e) { setMsgs((m) => [...m, { from: 'bot', text: 'Error: ' + e.message }]) }
  }
  const ideas = ['Who teaches AI?', "Show today's timetable for 5-B", 'Find an empty classroom at 2 PM', 'Which faculty has the highest workload?', 'Generate a timetable without Friday afternoon classes']
  return (
    <>
      <button onClick={() => setOpen(!open)} className="fixed bottom-5 right-5 z-40 w-14 h-14 rounded-full bg-accent text-white text-2xl shadow-lg">{open ? '×' : '🤖'}</button>
      {open && (
        <div className="fixed bottom-24 right-5 z-40 w-[22rem] max-w-[92vw] h-[30rem] card flex flex-col p-0 overflow-hidden shadow-2xl">
          <div className="px-4 py-2 bg-accent text-white font-semibold">AI Timetable Assistant</div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 text-sm">
            {msgs.map((m, i) => <div key={i} className={`max-w-[85%] px-3 py-2 rounded-xl whitespace-pre-wrap ${m.from === 'me' ? 'ml-auto bg-accent text-white' : 'bg-bg'}`}>{m.text}</div>)}
            {msgs.length === 1 && <div className="flex flex-wrap gap-1">{ideas.map((i) => <button key={i} className="btn-ghost !text-xs" onClick={() => send(i)}>{i}</button>)}</div>}
            <div ref={end} />
          </div>
          <div className="p-2 border-t border-line flex gap-2">
            <input className="inp" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="Ask anything…" />
            <button className="btn" onClick={() => send()}>Send</button>
          </div>
        </div>)}
    </>
  )
}
