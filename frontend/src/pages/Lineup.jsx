import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'

const TEAM_COLORS = {
  ARS: '#EF0107',
  AVL: '#670E36',
  BOU: '#DA291C',
  BRE: '#E30613',
  BHA: '#0057B8',
  CHE: '#034694',
  CRY: '#1B458F',
  EVE: '#003399',
  FUL: '#FFFFFF',
  IPS: '#0057B8',
  LEI: '#003090',
  LIV: '#C8102E',
  MCI: '#6CABDD',
  MUN: '#DA291C',
  NEW: '#241F20',
  NFO: '#DD0000',
  SOU: '#D71920',
  TOT: '#132257',
  WHU: '#7A263A',
  WOL: '#FDB913',
}

function playerPhotoUrl(photo, size = 150) {
  if (!photo) return null
  const clean = String(photo).replace('.jpg', '')
  return `https://resources.premierleague.com/premierleague/photos/players/${size}x${size}/p${clean}.png`
}

function fallbackTeamColor(teamId) {
  const hue = (Number(teamId || 0) * 47) % 360
  return `hsl(${hue} 75% 55%)`
}

function Card({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 shadow">
      <div className="font-semibold mb-3">{title}</div>
      {children}
    </div>
  )
}

function ShirtIcon({ className, style }) {
  return (
    <svg viewBox="0 0 64 64" className={className} style={style} aria-hidden="true">
      <path
        d="M20 10 32 6l12 4 10 8-8 10-4-3v33H22V25l-4 3-8-10 10-8Z"
        fill="currentColor"
        opacity="0.95"
      />
      <path
        d="M20 10 32 6l12 4 10 8-8 10-4-3v33H22V25l-4 3-8-10 10-8Z"
        fill="none"
        stroke="rgba(0,0,0,0.25)"
        strokeWidth="1.5"
      />
      <path
        d="M22 25c6 5 14 5 20 0"
        fill="none"
        stroke="rgba(0,0,0,0.25)"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  )
}

function buildPitchRows(players, formation, mode) {
  const parts = String(formation).split('-').map(n => Number(n || 0))
  const defCount = Number.isFinite(parts[0]) ? parts[0] : 4
  const midCount = Number.isFinite(parts[1]) ? parts[1] : 4
  const fwdCount = Number.isFinite(parts[2]) ? parts[2] : 2

  const byPos = {
    GK: players.filter(p => p.position === 'GK'),
    DEF: players.filter(p => p.position === 'DEF'),
    MID: players.filter(p => p.position === 'MID'),
    FWD: players.filter(p => p.position === 'FWD'),
  }

  const valueForSort = p => {
    if (mode === 'actual') return p.total_points ?? p.score ?? 0
    return p.expected_points ?? p.score ?? 0
  }

  const takeTop = (arr, n) =>
    [...arr].sort((a, b) => valueForSort(b) - valueForSort(a)).slice(0, n)

  return {
    FWD: takeTop(byPos.FWD, fwdCount),
    MID: takeTop(byPos.MID, midCount),
    DEF: takeTop(byPos.DEF, defCount),
    GK: takeTop(byPos.GK, 1),
  }
}

function Pitch({ formation, players, teamShortById, teamColorById, mode }) {
  const rows = useMemo(() => buildPitchRows(players, formation, mode), [players, formation, mode])

  const positionsForCount = n => {
    if (n <= 0) return []
    if (n === 1) return [50]
    const margin = n === 2 ? 36 : n === 3 ? 24 : n === 4 ? 14 : n === 5 ? 10 : 8
    const step = (100 - 2 * margin) / (n - 1)
    return Array.from({ length: n }, (_, i) => margin + step * i)
  }

  const Marker = ({ player, x, y }) => {
    const teamLabel = teamShortById[player.team_id] || `T${player.team_id}`
    const teamColor = teamColorById[player.team_id] || '#E5E7EB'
    const metricLabel = mode === 'actual' ? 'PTS' : 'EP'
    const metricValue = mode === 'actual'
      ? Number((player.total_points ?? player.score) ?? 0)
      : Number(player.expected_points ?? 0)
    const photoUrl = playerPhotoUrl(player.photo, 150)

    return (
      <div
        className="absolute -translate-x-1/2 -translate-y-1/2"
        style={{ left: `${x}%`, top: `${y}%` }}
        title={`${player.name} (${teamLabel})`}
      >
        <div className="w-[120px] rounded-xl shadow-xl border border-emerald-200/60 overflow-hidden bg-white/95">
          <div className="flex items-center justify-between px-2 py-1 text-[11px] font-semibold bg-emerald-800 text-emerald-100">
            <span>{player.position}</span>
            <span>{metricLabel} {metricValue.toFixed(1)}</span>
          </div>
          <div className="p-2 bg-white">
            <div className="flex items-center gap-2">
              <div
                className="relative w-12 h-12 rounded-lg border overflow-hidden"
                style={{ backgroundColor: `${teamColor}15`, borderColor: `${teamColor}88` }}
              >
                <ShirtIcon className="absolute inset-0 w-9 h-9 m-auto drop-shadow" style={{ color: teamColor, opacity: 0.8 }} />
                {photoUrl ? (
                  <img
                    src={photoUrl}
                    alt={player.name}
                    className="w-full h-full object-cover relative"
                    loading="lazy"
                    onError={e => { e.currentTarget.style.display = 'none' }}
                  />
                ) : null}
              </div>
              <div className="leading-tight flex-1 min-w-0">
                <div className="font-semibold text-[12px] text-slate-900 truncate">{player.name}</div>
                <div className="text-[11px] text-slate-500 truncate">{teamLabel} • {mode === 'actual' ? 'Actual' : 'Prediksi'}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const yByLine = {
    GK: 14,
    DEF: 32,
    MID: 54,
    FWD: 76,
  }

  const stripe = 'rgba(12,150,70,0.45)'
  const stripe2 = 'rgba(12,130,60,0.45)'

  return (
    <div
      className="relative w-full max-w-3xl mx-auto aspect-[4/5] rounded-2xl overflow-hidden border border-emerald-200/40 shadow-xl"
      style={{
        backgroundImage: `linear-gradient(180deg, ${stripe}, ${stripe}), repeating-linear-gradient(90deg, ${stripe2}, ${stripe2} 44px, ${stripe} 44px, ${stripe} 88px)`,
      }}
    >
      {/* Pitch markings */}
      <div className="absolute inset-4 border-2 border-white/70 rounded-xl" />
      <div className="absolute left-4 right-4 top-1/2 border-t border-white/70" />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-28 h-28 rounded-full border border-white/70" />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-white/80" />

      {/* Top penalty & goal */}
      <div className="absolute left-[22%] right-[22%] top-4 h-24 border-2 border-white/70 rounded-b-xl" />
      <div className="absolute left-[30%] right-[30%] top-4 h-10 border-2 border-white/70 rounded-b-lg" />
      <div className="absolute left-1/2 top-4 -translate-x-1/2 w-24 h-3 bg-white/80 rounded-b-md" />
      {/* Bottom penalty & goal */}
      <div className="absolute left-[22%] right-[22%] bottom-4 h-24 border-2 border-white/70 rounded-t-xl" />
      <div className="absolute left-[30%] right-[30%] bottom-4 h-10 border-2 border-white/70 rounded-t-lg" />
      <div className="absolute left-1/2 bottom-4 -translate-x-1/2 w-24 h-3 bg-white/80 rounded-t-md" />

      {/* Players cards */}
      {['GK', 'DEF', 'MID', 'FWD'].map(line => {
        const xs = positionsForCount(rows[line].length)
        return rows[line].map((p, idx) => (
          <Marker key={`${line}-${p.player_id}`} player={p} x={xs[idx]} y={yByLine[line]} />
        ))
      })}
    </div>
  )
}

export default function Lineup() {
  const [gw, setGw] = useState(10)
  const [formation, setFormation] = useState('4-4-2')
  const [budget, setBudget] = useState(100)
  const [maxPerTeam, setMaxPerTeam] = useState(3)
  const [result, setResult] = useState(null)
  const [resultMode, setResultMode] = useState('predicted')
  const [meta, setMeta] = useState(null)
  const [err, setErr] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)
  const [teams, setTeams] = useState([])
  const [mode, setMode] = useState('predicted')

  useEffect(() => {
    api
      .meta()
      .then(m => {
        setMeta(m)
        if (m?.next_gw) setGw(Number(m.next_gw))
      })
      .catch(() => {})
    api.teams().then(setTeams).catch(() => {})
  }, [])

  const teamShortById = useMemo(() => {
    const map = {}
    for (const t of teams) map[t.id] = (t.short_name || t.name || '').toUpperCase()
    return map
  }, [teams])

  const teamColorById = useMemo(() => {
    const map = {}
    for (const t of teams) {
      const short = (t.short_name || '').toUpperCase()
      map[t.id] = TEAM_COLORS[short] || fallbackTeamColor(t.id)
    }
    return map
  }, [teams])

  const latestImportedGw = useMemo(() => {
    if (!meta) return null
    const maxStats = Number(meta.max_stats_gw ?? meta.last_finished_gw ?? 0)
    return Number.isFinite(maxStats) && maxStats > 0 ? maxStats : null
  }, [meta])

  // Prediction: allow from GW 1 up to latest actual + 3 (cap 38)
  const predictionRange = useMemo(() => {
    const maxActual = latestImportedGw ?? 0
    const max = Math.min(38, maxActual + 3)
    return { min: 1, max }
  }, [latestImportedGw])

  const isPredictionAvailable = useMemo(() => {
    return predictionRange.max !== null && predictionRange.min <= predictionRange.max && predictionRange.min <= 38
  }, [predictionRange])

  // Clamp GW based on mode and available data
  useEffect(() => {
    if (!meta) return
    if (mode === 'actual') {
      const maxA = latestImportedGw
      const minA = 1
      if (maxA) {
        if (gw > maxA) {
          setGw(maxA)
          setInfo(`Data Actual baru tersedia sampai GW ${maxA}. GW diset ke ${maxA}.`)
        } else if (gw < minA) {
          setGw(minA)
          setInfo(`GW tidak boleh kurang dari ${minA}. GW diset ke ${minA}.`)
        }
      }
    } else {
      const { min, max } = predictionRange
      if (min && max) {
        if (gw < min) {
          setGw(min)
          setInfo(`Prediksi dimulai dari GW ${min}. GW diset ke ${min}.`)
        } else if (gw > max) {
          setGw(max)
          setInfo(`Prediksi dibatasi sampai GW ${max} (3 GW setelah data actual terakhir). GW diset ke ${max}.`)
        }
      }
    }
  }, [mode, meta, latestImportedGw, predictionRange, gw])

  const isActualResult = resultMode === 'actual'

  async function generateLineup() {
    setErr('')
    setInfo('')
    setLoading(true)
    try {
      // Guard for invalid GW ranges
      if (mode === 'actual') {
        const maxA = latestImportedGw
        if (!maxA) {
          throw new Error('Data Actual belum tersedia (player_gameweek_stats kosong).')
        }
        if (gw > maxA) {
          setGw(maxA)
          throw new Error(`Data Actual baru tersedia sampai GW ${maxA}. GW diset ke ${maxA}.`)
        }
        if (gw < 1) {
          setGw(1)
          throw new Error('GW tidak boleh kurang dari 1. GW diset ke 1.')
        }
      } else {
        if (!isPredictionAvailable) {
          throw new Error('Prediksi tidak tersedia karena musim sudah selesai atau range tidak valid.')
        }
        const { min, max } = predictionRange
        if (gw < min) {
          setGw(min)
          throw new Error(`Prediksi dimulai dari GW ${min}. GW diset ke ${min}.`)
        }
        if (gw > max) {
          setGw(max)
          throw new Error(`Prediksi maksimal sampai GW ${max} (3 GW setelah data actual terakhir). GW diset ke ${max}.`)
        }
      }

      if (mode === 'actual') {
        const r = await api.actualLineup(Number(gw), {
          formation,
          max_per_team: Number(maxPerTeam),
        })
        setResult(r)
        setResultMode('actual')
        return
      }

      const r = await api.lineup(Number(gw), { formation, budget: Number(budget), max_per_team: Number(maxPerTeam) })
      setResult(r)
      setResultMode('predicted')
    } catch (e) {
      const msg = String(e.message || e)
      if (mode === 'predicted' && msg.includes('No predictions for this GW')) {
        try {
          await api.runPredictGw(Number(gw))
          const r2 = await api.lineup(Number(gw), {
            formation,
            budget: Number(budget),
            max_per_team: Number(maxPerTeam),
          })
          setResult(r2)
          setResultMode('predicted')
        } catch (e2) {
          setResult(null)
          setErr(String(e2.message || e2))
        }
      } else {
        setResult(null)
        setErr(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <Card title="Generate Best XI">
        <div className="grid grid-cols-2 gap-2">
          <label className="text-sm text-slate-300">
            GW
            <input
              className="mt-1 w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
              type="number"
              value={gw}
              onChange={e => setGw(Number(e.target.value))}
              min={mode === 'actual' ? 1 : (predictionRange.min || undefined)}
              max={mode === 'actual' ? (latestImportedGw || undefined) : (predictionRange.max || undefined)}
              disabled={(mode === 'predicted' && !isPredictionAvailable) || (mode === 'actual' && !latestImportedGw)}
            />
            {mode === 'actual' && latestImportedGw && (
              <div className="text-xs text-slate-500 mt-1">Actual tersedia s/d GW {latestImportedGw}.</div>
            )}
            {mode === 'predicted' && isPredictionAvailable && (
              <div className="text-xs text-slate-500 mt-1">
                Prediksi untuk GW {predictionRange.min} – {predictionRange.max} (maks 38).
              </div>
            )}
            {mode === 'predicted' && !isPredictionAvailable && (
              <div className="text-xs text-slate-500 mt-1">Prediksi tidak tersedia (season selesai).</div>
            )}
          </label>
          <label className="text-sm text-slate-300">
            Formation
            <select
              className="mt-1 w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
              value={formation}
              onChange={e => setFormation(e.target.value)}
            >
              {['4-4-2', '4-3-3', '3-5-2', '3-4-3', '5-3-2'].map(f => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Mode
            <select
              className="mt-1 w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
              value={mode}
              onChange={e => setMode(e.target.value)}
            >
              <option value="predicted">Prediksi (GW next)</option>
              <option value="actual">Aktual (GW itu)</option>
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Budget
            <input
              className="mt-1 w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
              type="number"
              value={budget}
              onChange={e => setBudget(e.target.value)}
              disabled={mode === 'actual'}
            />
          </label>
          <label className="text-sm text-slate-300">
            Max / Team
            <input
              className="mt-1 w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
              type="number"
              value={maxPerTeam}
              onChange={e => setMaxPerTeam(e.target.value)}
            />
          </label>
        </div>

        <button
          className="mt-3 rounded-xl bg-sky-600 hover:bg-sky-500 px-3 py-2"
          onClick={generateLineup}
          disabled={loading}
        >
          {loading ? 'Loading...' : (mode === 'actual' ? 'Generate Actual' : 'Generate (auto-predict)')}
        </button>

          {err && <div className="text-red-300 mt-2 text-sm whitespace-pre-wrap">{err}</div>}
        {info && <div className="text-amber-200 mt-2 text-xs whitespace-pre-wrap">{info}</div>}
        {mode === 'predicted' && (
          <div className="text-xs text-slate-400 mt-2">
            Tip: tombol ini bakal auto-run POST /predict/gw/{'{gw}'} kalau predictions belum ada.
          </div>
        )}
      </Card>

      <Card title="Result">
        {!result && <div className="text-sm text-slate-500">Belum ada lineup.</div>}
        {result && (
          <div className="text-sm space-y-3">
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-slate-300">
                <div>
                  Formation: <span className="text-slate-100">{result.formation}</span>
                </div>
                {!isActualResult && result.total_expected_points !== undefined && (
                  <div>
                    Total Expected: <span className="text-slate-100">{Number(result.total_expected_points ?? 0).toFixed(2)}</span>
                  </div>
                )}
                <div>
                  {isActualResult ? 'Total Points' : 'Total Score'}:{' '}
                  <span className="text-slate-100">{Number(result.total_score ?? 0).toFixed(2)}</span>
                </div>
              </div>

              <Pitch
                formation={result.formation}
                players={result.players}
                teamShortById={teamShortById}
                teamColorById={teamColorById}
                mode={resultMode}
              />

            <div className="mt-1 space-y-2">
              {result.players
                .slice()
                .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
                .map(p => (
                  <div
                    key={p.player_id}
                    className="flex justify-between rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2"
                  >
                    <div className="truncate flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full overflow-hidden border border-slate-800 bg-slate-900 shrink-0">
                        {playerPhotoUrl(p.photo, 120) ? (
                          <img
                            src={playerPhotoUrl(p.photo, 120)}
                            alt={p.name}
                            className="w-full h-full object-cover"
                            loading="lazy"
                            onError={e => { e.currentTarget.style.display = 'none' }}
                          />
                        ) : null}
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold truncate">{p.name}</div>
                        <div className="text-xs text-slate-400">
                          <span
                            className="inline-block w-2 h-2 rounded-full mr-1 align-middle"
                            style={{ backgroundColor: teamColorById[p.team_id] || '#E5E7EB' }}
                          />
                          {p.position} | {teamShortById[p.team_id] || `TEAM ${p.team_id}`} | GBP {Number(p.price ?? 0).toFixed(1)}
                        </div>
                      </div>
                    </div>
                    <div className="text-right text-xs text-slate-300">
                      {isActualResult ? (
                        <div>PTS {Number(p.total_points ?? p.score ?? 0).toFixed(2)}</div>
                      ) : (
                        <>
                          <div>EP {Number(p.expected_points ?? 0).toFixed(2)}</div>
                          <div>pStart {Number(p.p_start ?? 0).toFixed(2)}</div>
                        </>
                      )}
                      <div>score {Number(p.score ?? 0).toFixed(2)}</div>
                    </div>
                  </div>
                ))}
              </div>
          </div>
        )}
      </Card>
    </div>
  )
}
