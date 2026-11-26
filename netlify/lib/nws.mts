// The National Weather Service's 7-day text forecast for US resorts (api.weather.gov).
// NWS data is a US government work in the public domain; we credit it on the page anyway.
// It covers the United States only, so Canadian and Mexican resorts have none.
import type { Resort } from "./met.mts";

// NWS asks every client to identify itself with a User-Agent, as MET Norway does.
const USER_AGENT = "TheSkiAdvisor/1.0 (+https://theskiadvisor.com)";
const API = "https://api.weather.gov";

// One forecast period (NWS's "Today", "Tonight", "Friday", "Friday Night"...). Temperatures in °F,
// as NWS gives them; the page converts for °C. `start` keeps the resort's local offset, so its date
// part is the resort's own calendar day.
export type Period = { name: string; start: string; end: string; day: boolean; temp: number; pop: number | null;
  wind: string; short: string; detail: string };
export type NwsForecast = { grid: string; elev: number | null; updated: string; periods: Period[] };

// NWS grid squares (about 2.5 km) never move for a resort, so we look each one up once and keep it.
// "BOI/138,92" means forecast office BOI, grid square 138,92.
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
  let grid = grids[r.id] || (grids[r.id] = await gridFor(r));
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
  }));
  if (!periods.length) throw new Error(`NWS forecast for ${r.id} is empty`);
  const elev = typeof p?.elevation?.value === "number" ? Math.round(p.elevation.value) : null;
  return { grid, elev, updated: String(p?.updateTime || p?.generatedAt || new Date().toISOString()), periods };
}
