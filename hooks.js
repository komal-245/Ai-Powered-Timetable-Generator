import { useEffect, useState } from 'react'
import { api } from './api'
let metaCache
export function useMeta() {
  const [meta, setMeta] = useState(metaCache)
  useEffect(() => { if (!metaCache) api.get('/meta').then((m) => { metaCache = m; setMeta(m) }) }, [])
  return meta
}
export function useLoad(fn, deps = []) {
  const [data, setData] = useState(null), [err, setErr] = useState('')
  const reload = () => fn().then((d) => { setData(d); setErr('') }).catch((e) => setErr(e.message))
  useEffect(() => { reload() }, deps)
  return [data, reload, err, setData]
}
