import { useState, Fragment } from 'react'

const hue = (s) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7)

/** Weekly timetable grid. entries = enriched entries; mode decides which secondary info to show.
 *  editable => classes can be dragged to another period (onMove(blockId, day, slot)). */
export default function Grid({ entries, meta, mode = 'section', editable = false, onMove, onCellClick, marked = [], highlight }) {
  const [drag, setDrag] = useState(null)
  const [over, setOver] = useState(null)
  if (!meta) return null
  const { days, slots, break_after: br } = meta
  const byStart = {}, covered = new Set()
  const blocks = {}
  entries.forEach((e) => { (blocks[e.block_id] ||= []).push(e) })
  Object.values(blocks).forEach((b) => {
    b.sort((x, y) => x.slot - y.slot)
    byStart[`${b[0].day}-${b[0].slot}`] = { ...b[0], len: b.length }
    b.slice(1).forEach((e) => covered.add(`${e.day}-${e.slot}`))
  })
  const sub = (e) => mode === 'faculty' ? `${e.section} · ${e.room}` : mode === 'room' ? `${e.section} · ${e.faculty}` : `${e.faculty} · ${e.room}`
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-1 text-xs min-w-[820px]">
        <thead><tr><th className="w-14" />{slots.map((s, i) => (
          <Fragment key={i}>
            <th className="text-mute font-semibold pb-1">P{i + 1}<div className="font-normal">{s.start}–{s.end}</div></th>
            {br.includes(i) && <th className="w-3" />}
          </Fragment>))}</tr></thead>
        <tbody>
          {days.map((dn, d) => (
            <tr key={d}>
              <td className="font-bold text-mute text-sm">{dn}</td>
              {slots.map((_, t) => {
                const k = `${d}-${t}`
                const tail = br.includes(t) ? <td className="bg-line/40 rounded" title={t === 3 ? 'Lunch' : 'Tea break'} /> : null
                if (covered.has(k)) return null
                const e = byStart[k]
                const isOver = over === k
                const isMarked = marked.some(([a, b]) => a === d && b === t)
                return (
                  <Fragment key={k}>
                    <td colSpan={e?.len || 1}
                      onClick={() => onCellClick?.(d, t)}
                      onDragOver={editable ? (ev) => { ev.preventDefault(); setOver(k) } : undefined}
                      onDragLeave={() => setOver(null)}
                      onDrop={editable ? () => { setOver(null); if (drag != null) onMove?.(drag, d, t); setDrag(null) } : undefined}
                      className={`h-14 align-top rounded-lg border ${isOver ? 'border-accent ring-2 ring-accent/40' : 'border-line'} ${isMarked ? 'bg-bad/30' : 'bg-card'}`}>
                      {e && (
                        <div draggable={editable} onDragStart={() => setDrag(e.block_id)} onDragEnd={() => setDrag(null)}
                          title={`${e.subject}\n${e.faculty}\n${e.room}${editable ? '\n(drag to move)' : ''}`}
                          className={`h-full rounded-lg p-1.5 leading-tight ${editable ? 'cursor-grab' : ''} ${highlight === e.block_id ? 'ring-2 ring-bad' : ''}`}
                          style={{ background: `hsl(${hue(e.code)} 70% 50% / 0.18)`, borderLeft: `4px solid hsl(${hue(e.code)} 70% 45%)` }}>
                          <div className="font-bold">{e.code}{e.is_lab && <span className="ml-1 text-[10px] opacity-70">LAB</span>}</div>
                          <div className="opacity-80 truncate">{sub(e)}</div>
                        </div>)}
                    </td>
                    {tail}
                  </Fragment>
                )
              })}
            </tr>))}
        </tbody>
      </table>
    </div>
  )
}
