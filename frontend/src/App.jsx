import React from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Players from './pages/Players.jsx'
import PlayerDetail from './pages/PlayerDetail.jsx'
import Lineup from './pages/Lineup.jsx'
import Stats from './pages/Stats.jsx'

function Nav() {
  const cls = ({isActive}) => isActive
    ? "px-3 py-2 rounded-xl bg-slate-800 text-slate-100"
    : "px-3 py-2 rounded-xl hover:bg-slate-900 text-slate-300";

  return (
    <div className="sticky top-0 z-10 bg-slate-950/90 backdrop-blur border-b border-slate-800">
      <div className="max-w-6xl mx-auto px-4 py-3 flex flex-wrap gap-4 items-center">
        <div className="font-semibold">EPL Predictor</div>
        <div className="flex gap-2">
          <NavLink to="/" className={cls} end>Dashboard</NavLink>
          <NavLink to="/players" className={cls}>Players</NavLink>
          <NavLink to="/lineup" className={cls}>Lineup</NavLink>
          <NavLink to="/stats" className={cls}>Statistik Pemain</NavLink>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <div>
      <Nav />
      <div className="max-w-6xl mx-auto p-4">
        <Routes>
          <Route path="/" element={<Dashboard/>} />
          <Route path="/players" element={<Players/>} />
          <Route path="/players/:id" element={<PlayerDetail/>} />
          <Route path="/lineup" element={<Lineup/>} />
          <Route path="/stats" element={<Stats/>} />
        </Routes>
      </div>
    </div>
  )
}
