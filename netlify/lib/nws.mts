// The National Weather Service's 7-day text forecast for US resorts (api.weather.gov).
// NWS data is a US government work in the public domain; we credit it on the page anyway.
// It covers the United States only, so Canadian and Mexican resorts have none.
import type { Resort } from "./met.mts";
// For each US resort, the NWS grid square closest to its mid-mountain (made by src/nws_grids.mts).
import picked from "./nws-grid.json" with { type: "json" };
const PICKED = picked as Record<string, { grid: string; elev: number }>;

// NWS asks every client to identify itself with a User-Agent, as MET Norway does.
const USER_AGENT = "TheSkiAdvisor/1.0 (+https://theskiadvisor.com)";
const API = "https://api.weather.gov";

// One forecast period (NWS's "Today", "Tonight", "Friday", "Friday Night"...). Temperatures in °F,
// as NWS gives them; the page converts for °C. `start` keeps the resort's local offset, so its date
// part is the resort's own calendar day.
export type Period = { name: string; start: string; end: string; day: boolean; temp: number; pop: number | null;
  wind: string; short: string; detail: string; snow: [number, number] | null };
export type NwsForecast = { grid: string; elev: number | null; updated: string; periods: Period[] };

// NWS grid squares (about 2.5 km) never move for a resort, so we look each one up once and keep it.
// "BOI/138,92" means forecast office BOI, grid square 138,92. The square picked for mid-mountain
// (nws-grid.json) comes first; this cache only holds pin-square lookups for resorts missing from it.
export type GridCache = Record<string, string>;

async function getJSON(url: string): Promise<any> {
  const res = await fetch(url, { headers: { "User-Agent": USER_AGENT, Accept: "application/geo+json" } });
  if (!res.ok) { const e: any = new Error(`NWS ${res.status} for ${url}`); e.status = res.status; throw e; }
  return res.json();
}

export const isUS = (r: Pick<Resort, "region">) => r.region.startsWith("US-");

export async function gridFor(r: Resort): Promise<string> {
  const p = (await getJSON(`${API}/points/${r.lat.toFixed(4)},${r.lon.toFixed(4)}`)).properties;
  if (!p?.gridId || p.gridX == null || p.gridY == null) throw new Error(`NWS has no grid for ${r.id}`);
  return `${p.gridId}/${p.gridX},${p.gridY}`;
}

// Fetch one resort's forecast. Uses (and fills in) the grid cache; if NWS has moved the grid
// (404), it looks the resort up again once.
export async function fetchNws(r: Resort, grids: GridCache = {}): Promise<NwsForecast> {
  let grid = PICKED[r.id]?.grid || grids[r.id] || (grids[r.id] = await gridFor(r));
  let data: any;
  try { data = await getJSON(`${API}/gridpoints/${grid}/forecast`); }
  catch (err: any) {
    if (err?.status !== 404) throw err;
    grid = grids[r.id] = await gridFor(r);
    data = await getJSON(`${API}/gridpoints/${grid}/forecast`);
  }
  const p = data?.properties;
  const periods: Period[] = (p?.periods || []).map((x: any) => ({
    name: String(x.name || ""), start: String(x.startTime), end: String(x.endTime), day: !!x.isDaytime,
    temp: x.temperatureUnit === "C" ? Math.round(x.temperature * 9 / 5 + 32) : Math.round(x.temperature),
    pop: typeof x.probabilityOfPrecipitation?.value === "number" ? x.probabilityOfPrecipitation.value : null,
    wind: [x.windDirection, x.windSpeed].filter(Boolean).join(" "),
    short: String(x.shortForecast || ""), detail: String(x.detailedForecast || ""),
    snow: snowRange(String(x.detailedForecast || "")),
  }));
  if (!periods.length) throw new Error(`NWS forecast for ${r.id} is empty`);
  const elev = typeof p?.elevation?.value === "number" ? Math.round(p.elevation.value) : null;
  return { grid, elev, updated: String(p?.updateTime || p?.generatedAt || new Date().toISOString()), periods };
}

// New snow NWS expects in one period, in inches, read from its wording: "New snow accumulation of 1 to 3
// inches possible", "around one inch", "less than half an inch", "Total daytime snow accumulation of 4 to 8
// inches". [0, 0] for "little or no snow accumulation"; null when the period mentions no snow amount.
const WORDS: Record<string, number> = { half: 0.5, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
const amount = (w: string) => { const v = w === "an" ? 1 : WORDS[w] ?? Number(w); return Number.isFinite(v) ? v : null; };
export function snowRange(text: string): [number, number] | null {
  const t = text.toLowerCase();
  if (/little or no snow( and sleet)? accumulation/.test(t)) return [0, 0];
  const m = t.match(/snow(?: and sleet)? accumulation of (less than|around|up to)?\s*(?:a |an )?(half|[\w.]+)(?:\s+(?:to|and)\s+([\w.]+))?\s+(?:(?:of )?an )?inch/);
  if (!m) return null;
  const a = amount(m[2]), b = m[3] ? amount(m[3]) : null;
  if (a == null) return null;
  if (m[1] === "less than" || m[1] === "up to") return [0, a];
  return [a, b ?? a];
}
