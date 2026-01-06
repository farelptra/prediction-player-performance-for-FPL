import React, { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../lib/api'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts'

function playerPhotoUrl(photo, size = 250) {
  if (!photo) return null
  const clean = String(photo).replace('.jpg', '')
  return `https://resources.premierleague.com/premierleague/photos/players/${size}x${size}/p${clean}.png`
}

function Card({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 shadow">
      <div className="font-semibold mb-3">{title}</div>
      {children}
    </div>
  )
}

function FixtureMini({ title, fx }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/30 p-3">
      <div className="text-slate-300 font-semibold">{title}</div>
      {!fx && <div className="text-slate-500 mt-1 text-sm">Not available.</div>}
      {fx && (
        <div className="text-slate-200 mt-1 text-sm">
          GW {fx.gw} | {fx.is_home ? 'Home' : 'Away'} vs {fx.opponent_short || fx.opponent_name}
          {fx.kickoff_time ? (
            <div className="text-slate-400 text-xs mt-1">{new Date(fx.kickoff_time).toLocaleString()}</div>
          ) : null}
        </div>
      )}
    </div>
  )
}

export default function PlayerDetail() {
  const { id } = useParams()
  const [player, setPlayer] = useState(null)
  const [hist, setHist] = useState([])
  const [nextFx, setNextFx] = useState(null)
  const [lastFx, setLastFx] = useState(null)
  const [err, setErr] = useState('')
  const [fromGw, setFromGw] = useState(1)
  const [toGw, setToGw] = useState(10)
  const [metaReady, setMetaReady] = useState(false)

  const totals = useMemo(() => {
    const base = { goals: 0, assists: 0, saves: 0, clean_sheet: 0, yellow: 0, red: 0 }
    for (const r of hist) {
      base.goals += Number(r.goals || 0)
      base.assists += Number(r.assists || 0)
      base.saves += Number(r.saves || 0)
      base.clean_sheet += Number(r.clean_sheet || 0)
      base.yellow += Number(r.yellow || 0)
      base.red += Number(r.red || 0)
    }
    return base
  }, [hist])

  async function load() {
    setErr('')
    try {
      const p = await api.player(id)
      const h = await api.playerHistory(id, fromGw, toGw)
      setPlayer(p)
      setHist(h)

      if (p?.team_id) {
        api.teamNextFixture(p.team_id).then(setNextFx).catch(() => {})
        api.teamLastFixture(p.team_id).then(setLastFx).catch(() => {})
      }
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

  useEffect(() => {
    api
      .meta()
      .then(m => {
        const last = Number(
          m?.last_finished_gw ??
          m?.current_gw ??
          toGw
        )
        if (Number.isFinite(last) && last > 0) {
          setToGw(last)
        }
      })
      .catch(() => {})
      .finally(() => setMetaReady(true))
  }, [])

  useEffect(() => {
    if (!metaReady) return
    load()
  }, [id, metaReady])

  const chartData = useMemo(
    () =>
      hist.map(r => ({
        gw: r.gw,
        minutes: r.minutes,
        xg: Number(r.xg),
        xa: Number(r.xa),
        total_points: r.total_points,
      })),
    [hist]
  )

  return (
    <div className="space-y-4">
      {err && <div className="text-red-300 text-sm">{err}</div>}

      <Card title="Player">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="w-16 h-16 rounded-full overflow-hidden border border-slate-800 bg-slate-900">
            {playerPhotoUrl(player?.photo, 250) ? (
              <img
                src={playerPhotoUrl(player?.photo, 250)}
                alt={player?.name}
                className="w-full h-full object-cover"
                loading="lazy"
                onError={e => { e.currentTarget.style.display = 'none' }}
              />
            ) : null}
          </div>
          <div>
            <div className="text-xl font-bold">{player?.name || '...'}</div>
            <div className="text-sm text-slate-300">
              {player?.position} | {player?.team_short || player?.team_name || `Team ${player?.team_id}`} | GBP
              {Number(player?.price || 0).toFixed(1)} | {player?.status}
            </div>
          </div>
        </div>
        <div className="text-sm text-slate-400 mt-2">
          Team strengths: ATT {player?.team?.strength_attack ?? '-'} / DEF {player?.team?.strength_defense ?? '-'}
        </div>
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm text-slate-200">
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2">
            <div className="text-xs uppercase text-slate-400">Goals</div>
            <div className="font-semibold">{totals.goals}</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2">
            <div className="text-xs uppercase text-slate-400">Assists</div>
            <div className="font-semibold">{totals.assists}</div>
          </div>
          {player?.position === 'GK' && (
            <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2">
              <div className="text-xs uppercase text-slate-400">Saves</div>
              <div className="font-semibold">{totals.saves}</div>
            </div>
          )}
          {player?.position === 'GK' && (
            <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2">
              <div className="text-xs uppercase text-slate-400">Clean Sheets</div>
              <div className="font-semibold">{totals.clean_sheet}</div>
            </div>
          )}
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2">
            <div className="text-xs uppercase text-slate-400">Yellow</div>
            <div className="font-semibold">{totals.yellow}</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2">
            <div className="text-xs uppercase text-slate-400">Red</div>
            <div className="font-semibold">{totals.red}</div>
          </div>
        </div>

        <div className="mt-3 grid sm:grid-cols-2 gap-3">
          <FixtureMini title="Next match" fx={nextFx} />
          <FixtureMini title="Last match" fx={lastFx} />
        </div>
      </Card>

      <Card title="History Filters">
        <div className="space-y-2">
          <div className="text-sm text-slate-300">Gameweek (GW)</div>
          <div className="flex gap-2 items-center flex-wrap">
            <label className="flex items-center gap-1 text-sm text-slate-300">
              <span>From</span>
              <input
                className="w-24 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
                type="number"
                value={fromGw}
                onChange={e => setFromGw(Number(e.target.value))}
              />
            </label>
            <label className="flex items-center gap-1 text-sm text-slate-300">
              <span>To</span>
              <input
                className="w-24 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
                type="number"
                value={toGw}
                onChange={e => setToGw(Number(e.target.value))}
              />
            </label>
          </div>
          <button className="rounded-xl bg-slate-800 hover:bg-slate-700 px-3 py-2" onClick={load}>
            Reload
          </button>
        </div>
      </Card>

      <Card title="Minutes / xG / xA / Points">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="gw" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="minutes" />
              <Line type="monotone" dataKey="xg" />
              <Line type="monotone" dataKey="xa" />
              <Line type="monotone" dataKey="total_points" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}
