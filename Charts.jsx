import { useEffect, useRef } from 'react'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const PALETTE = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#db2777', '#65a30d', '#ea580c', '#4f46e5']

export function ChartBox({ type = 'bar', labels, datasets, height = 240, options = {} }) {
  const ref = useRef(), chart = useRef()
  useEffect(() => {
    const pie = ['doughnut', 'pie'].includes(type)
    const ds = datasets.map((d, i) => ({ backgroundColor: pie ? labels.map((_, j) => PALETTE[j % 10]) : PALETTE[i % 10], borderColor: PALETTE[i % 10], borderWidth: type === 'line' ? 2 : 0, borderRadius: 4, ...d }))
    const fg = getComputedStyle(document.documentElement).getPropertyValue('--mute').trim().split(' ').join(',')
    const color = `rgb(${fg})`
    chart.current?.destroy()
    chart.current = new Chart(ref.current, {
      type, data: { labels, datasets: ds },
      options: { responsive: true, maintainAspectRatio: false, animation: { duration: 400 },
        plugins: { legend: { display: pie || ds.length > 1, labels: { color } } },
        scales: pie ? {} : { x: { ticks: { color }, grid: { display: false } }, y: { ticks: { color }, beginAtZero: true } }, ...options },
    })
    return () => chart.current?.destroy()
  }, [JSON.stringify(labels), JSON.stringify(datasets), type])
  return <div style={{ height }}><canvas ref={ref} /></div>
}

export function Heatmap({ data, days, slots }) {
  const max = Math.max(1, ...data.flat())
  return (
    <div className="overflow-x-auto"><table className="text-xs border-separate border-spacing-1 w-full">
      <thead><tr><th></th>{slots.map((s, i) => <th key={i} className="text-mute font-medium">P{i + 1}<div>{s}</div></th>)}</tr></thead>
      <tbody>{data.map((row, d) => <tr key={d}><td className="pr-2 font-semibold text-mute">{days[d]}</td>
        {row.map((v, t) => <td key={t} title={`${v} classes`} className="text-center rounded-md py-2 font-semibold"
          style={{ background: `rgb(var(--accent) / ${0.08 + 0.85 * v / max})`, color: v / max > 0.55 ? '#fff' : undefined }}>{v}</td>)}</tr>)}</tbody>
    </table></div>
  )
}

export function Bar({ label, value, color = 'accent' }) {
  return (<div className="mb-2"><div className="flex justify-between text-sm"><span>{label}</span><b>{value}%</b></div>
    <div className="h-2 rounded bg-line overflow-hidden"><div className="h-full" style={{ width: `${Math.min(100, value)}%`, background: `rgb(var(--${color}))` }} /></div></div>)
}

export const scoreColor = (v) => v >= 90 ? 'ok' : v >= 75 ? 'accent' : v >= 60 ? 'warn' : 'bad'
export function ScorePanel({ score }) {
  if (!score?.overall && score?.overall !== 0) return null
  const rows = [['Overall Score', score.overall], ['Teacher Balance', score.teacher_balance], ['Room Usage', score.room_usage],
    ['Student Comfort', score.student_comfort], ['Conflict Score', score.conflict], ['Preference Match', score.preference]]
  return <div>{rows.map(([l, v]) => <Bar key={l} label={l} value={v} color={scoreColor(v)} />)}</div>
}
