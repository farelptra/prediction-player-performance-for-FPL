import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Link } from 'react-router-dom'

function Card({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 shadow">
      <div className="font-semibold mb-3">{title}</div>
      {children}
    </div>
  )
}

export default function Dashboard() {
  const [health, setHealth] = useState(null)
  const [gw, setGw] = useState(10)
  const [preds, setPreds] = useState([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.health().then(setHealth).catch(e => setErr(String(e)))
    api
      .meta()
      .then(m => {
        if (m?.next_gw) setGw(Number(m.next_gw))
      })
      .catch(() => {})
  }, [])

  async function loadPred() {
    setErr('')
    setLoading(true)
    try {
      const data = await api.predictionsByGw(Number(gw))
      setPreds(data)
    } catch (e) {
      setPreds([])
      setErr(String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  async function runPredict() {
    setErr('')
    setLoading(true)
    try {
      await api.runPredictGw(Number(gw))
      await loadPred()
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <Card title="Status">
        <div className="text-sm text-slate-300">
          API: {health ? 'OK' : '...'}
          <br />
          Model: {health?.model_version || '-'}
        </div>
      </Card>

      <Card title="Prediksi Gameweek">
        <div className="flex gap-2 items-center">
          <input
            className="w-24 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
            type="number"
            value={gw}
            onChange={e => setGw(Number(e.target.value))}
          />
          <button className="rounded-xl bg-sky-600 hover:bg-sky-500 px-3 py-2" onClick={runPredict}>
            Generate Predictions
          </button>
          <button className="rounded-xl bg-slate-800 hover:bg-slate-700 px-3 py-2" onClick={loadPred}>
            Refresh
          </button>
        </div>
        {err && <div className="text-red-300 mt-2 text-sm whitespace-pre-wrap">{err}</div>}
        <div className="mt-4 text-sm text-slate-300">{loading ? 'Loading...' : `Rows: ${preds.length}`}</div>
      </Card>

      <Card title="Top 10 Expected Points">
        <div className="space-y-2">
          {preds.slice(0, 10).map(p => (
            <div key={p.player_id} className="flex justify-between text-sm">
              <Link to={`/players/${p.player_id}`} className="truncate">
                {p.name}
              </Link>
              <div className="text-slate-300">
                {p.expected_points.toFixed(2)} (pStart {p.p_start.toFixed(2)})
              </div>
            </div>
          ))}
          {!preds.length && <div className="text-sm text-slate-500">Belum ada predictions untuk GW ini.</div>}
        </div>
      </Card>

      <Card title="Tips">
        <div className="text-sm text-slate-300 space-y-2">
          <div>
            1) Import data FPL (teams, players, fixtures, GW stats):{' '}
            <span className="text-slate-100">python backend/scripts/import_fpl_api.py</span>
          </div>
          <div>
            2) Train model: <span className="text-slate-100">python -m app.cli train</span>
          </div>
          <div>3) Klik "Generate Predictions" untuk GW target.</div>
        </div>
      </Card>
    </div>
  )
}
