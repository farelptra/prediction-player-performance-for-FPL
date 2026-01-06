import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

const CATEGORIES = [
  { key: 'top_scorers', label: 'Top Skorer', metric: 'Goals', metricKey: 'goals' },
  { key: 'top_assists', label: 'Top Assist', metric: 'Assist', metricKey: 'assists' },
  { key: 'most_yellow', label: 'Yellow Card', metric: 'Yellow', metricKey: 'yellow' },
  { key: 'most_red', label: 'Red Card', metric: 'Red', metricKey: 'red' },
  { key: 'most_pom', label: 'Player Rating (Avg BPS)', metric: 'Avg BPS', metricKey: 'avg_bps' },
  { key: 'best_gk', label: 'Best Goalkeeper', metric: 'Avg BPS', metricKey: 'avg_bps' },
]

export default function Stats() {
  const [data, setData] = useState(null)
  const [pick, setPick] = useState('most_red')
  const [err, setErr] = useState('')

  useEffect(() => {
    api
      .leaders(10)
      .then(setData)
      .catch(e => setErr(String(e.message || e)))
  }, [])

  const activeList = useMemo(() => {
    if (!data) return []
    return data[pick] || []
  }, [data, pick])

  return (
    <div className="grid md:grid-cols-[240px,1fr] gap-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 space-y-2 sticky top-20 h-fit">
        <div className="font-semibold text-slate-100">Statistik Pemain</div>
        <div className="text-xs text-slate-400">Pilih kategori untuk lihat top 10.</div>
        <div className="space-y-2">
          {CATEGORIES.map(c => (
            <button
              key={c.key}
              onClick={() => setPick(c.key)}
              className={`w-full text-left px-3 py-2 rounded-xl border ${
                pick === c.key
                  ? 'border-sky-500 bg-sky-500/10 text-sky-100'
                  : 'border-slate-800 text-slate-200 hover:border-slate-700'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
        {err && <div className="text-xs text-red-300">{err}</div>}
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <div className="text-lg font-semibold text-slate-100">
            {CATEGORIES.find(c => c.key === pick)?.label || 'Pemain'}
          </div>
          <div className="text-xs text-slate-400">Urut terbanyak ke paling sedikit (top 10)</div>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {activeList && activeList.length
            ? activeList.map((p, idx) => {
                const cat = CATEGORIES.find(c => c.key === pick)
                const metricLabel = cat ? cat.metric : ''
                const metricKey = cat ? cat.metricKey : ''
                const raw = metricKey ? p[metricKey] : ''
                const val = metricKey === 'avg_bps' && typeof raw === 'number' ? raw.toFixed(1) : raw
                return (
                  <div
                    key={`${pick}-${p.player_id}`}
                    className="rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-slate-100"
                  >
                    <div className="flex justify-between text-sm">
                      <Link
                        to={`/players/${p.player_id}`}
                        className="font-semibold truncate hover:text-sky-400"
                      >
                        {idx + 1}. {p.name}
                      </Link>
                      <div className="text-slate-300">{p.team_short || p.team_id}</div>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">{p.position}{p.minutes ? ` · ${p.minutes} min` : ''}</div>
                    <div className="text-sm mt-2">
                      <span className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2 py-1">
                        {metricLabel} {val}
                      </span>
                    </div>
                  </div>
                )
              })
            : (
              <div className="text-slate-500 text-sm">Loading...</div>
            )}
        </div>
      </div>
    </div>
  )
}
