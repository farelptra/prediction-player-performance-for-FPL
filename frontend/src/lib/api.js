export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function http(method, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => http("GET", "/health"),
  meta: () => http("GET", "/meta"),
  teams: () => http("GET", "/teams"),
  fixturesByGw: (gw) => http("GET", `/fixtures/gw/${gw}`),
  teamNextFixture: (teamId) => http("GET", `/teams/${teamId}/next-fixture`),
  teamLastFixture: (teamId) => http("GET", `/teams/${teamId}/last-fixture`),
  players: (params={}) => {
    const cleaned = Object.fromEntries(Object.entries(params).filter(([_,v]) => v !== undefined && v !== null && v !== "" && v !== "undefined"));
    const q = new URLSearchParams(cleaned).toString();
    return http("GET", `/players${q ? `?${q}` : ""}`);
  },
  player: (id) => http("GET", `/players/${id}`),
  playerHistory: (id, from_gw=1, to_gw=99) => http("GET", `/players/${id}/history?from_gw=${from_gw}&to_gw=${to_gw}`),
  predictionsByGw: (gw) => http("GET", `/predictions/gw/${gw}`),
  runPredictGw: (gw) => http("POST", `/predict/gw/${gw}`),
  lineup: (gw, body) => http("POST", `/lineup/gw/${gw}`, body),
  actualLineup: (gw, body) => http("POST", `/lineup/actual/gw/${gw}`, body),
  leaders: (limit=5) => http("GET", `/leaders?limit=${limit}`),
};
