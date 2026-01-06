import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Link } from 'react-router-dom'

const STATE_KEY = 'playersPageState'

function playerPhotoUrl(photo, size = 150) {
  if (!photo) return null
  const clean = String(photo).replace('.jpg', '')
  return `https://resources.premierleague.com/premierleague/photos/players/${size}x${size}/p${clean}.png`
}

export default function Players() {
  const [players, setPlayers] = useState([])
  const [teams, setTeams] = useState([])
  const [search, setSearch] = useState('')
  const [position, setPosition] = useState('')
  const [team, setTeam] = useState('')
  const [err, setErr] = useState('')
  const [hydrated, setHydrated] = useState(false)
  const [restoreScroll, setRestoreScroll] = useState(null)

  async function load(opts = {}) {
    setErr('')
    try {
      const useSearch = opts.search ?? search
      const usePosition = opts.position ?? position
      const useTeam = opts.team ?? team
      const data = await api.players({
        search: useSearch,
        position: usePosition || undefined,
        team_id: useTeam || undefined,
      })
      setPlayers(data)
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

  function persistState(extra = {}) {
    const state = {
      search,
      position,
      team,
      scroll: window.scrollY,
      ...extra,
    }
    try {
      sessionStorage.setItem(STATE_KEY, JSON.stringify(state))
    } catch (_) {
      // ignore storage failures
    }
  }

  // hydrate last state (filters + scroll) from sessionStorage
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STATE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed.search !== undefined) setSearch(parsed.search)
        if (parsed.position !== undefined) setPosition(parsed.position)
        if (parsed.team !== undefined) setTeam(String(parsed.team))
        if (parsed.scroll !== undefined) setRestoreScroll(parsed.scroll)
      }
    } catch (_) {
      // ignore parse errors
    } finally {
      setHydrated(true)
    }
  }, [])

  // initial load after hydration
  useEffect(() => {
    if (!hydrated) return
    load()
  }, [hydrated])

  // fetch teams
  useEffect(() => {
    api.teams().then(setTeams).catch(() => {})
  }, [])

  // restore scroll once players loaded
  useEffect(() => {
    if (restoreScroll === null) return
    window.requestAnimationFrame(() => window.scrollTo(0, restoreScroll || 0))
    setRestoreScroll(null)
  }, [players, restoreScroll])

  function handleFilter() {
    persistState()
    load()
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2 items-center mb-4">
        <input
          className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
          placeholder="search player..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
          value={position}
          onChange={e => setPosition(e.target.value)}
        >
          <option value="">All Pos</option>
          <option value="GK">GK</option>
          <option value="DEF">DEF</option>
          <option value="MID">MID</option>
          <option value="FWD">FWD</option>
        </select>
        <select
          className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2"
          value={team}
          onChange={e => setTeam(e.target.value)}
        >
          <option value="">All Teams</option>
          {teams.map(t => (
            <option key={t.id} value={t.id}>
              {t.short_name || t.name}
            </option>
          ))}
        </select>
        <button className="rounded-xl bg-slate-800 hover:bg-slate-700 px-3 py-2" onClick={handleFilter}>
          Filter
        </button>
      </div>
      {err && <div className="text-red-300 mb-3 text-sm">{err}</div>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {players.map(p => (
          <Link
            key={p.id}
            to={`/players/${p.id}`}
            onClick={() => persistState()}
            className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 hover:bg-slate-900/70"
          >
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full overflow-hidden border border-slate-800 bg-slate-900 shrink-0">
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
                <div className="text-sm text-slate-300 mt-1">
                  Pos: {p.position} • Team: {p.team_short || p.team_name || p.team_id} • £
                  {Number(p.price).toFixed(1)} • {p.status}
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
