// Weather for the resort pages, from MET Norway's Locationforecast 2.0.
// Data: MET Norway, CC BY 4.0 (https://api.met.no/doc/License). We adapt it: mid-mountain
// altitude, snow estimated from precipitation and temperature, daily summaries in resort time.
import resorts from "./resorts.json" with { type: "json" };

export type Resort = { id: string; lat: number; lon: number; mid: number; tz: string; region: string };
export type Hour = { t: number; temp: number; snow: number };          // one recorded window: start (epoch ms), max °C, snow cm
export type Day = { date: string; min: number; max: number; snow: number };
export type Conditions = {
  air: number; rh: number; cloud: number; sky: string;
  snow48: number; pastMax: number; historyHours: number;
  tmrMin: number; tmrMax: number; tmrSnow: number; days: Day[];
};

export const RESORTS = resorts as Resort[];
// MET asks every client to identify itself; requests without this are refused.
const USER_AGENT = "TheSkiAdvisor/1.0 (+https://theskiadvisor.com)";
const HOUR = 3600_000;

// How much of the precipitation settles as snow. Both have to agree: MET's label for the hour
// (snow, sleet or rain) and the mid-mountain temperature. Rain never counts; sleet counts half at most.
export function snowShare(symbol: string | undefined, tempC: number): number {
  const s = (symbol || "").replace(/_(day|night|polartwilight)$/, "");
  const byLabel = s.includes("sleet") ? 0.5 : s.includes("snow") ? 1 : s.includes("rain") ? 0 : 1;
  const byTemp = tempC <= 0 ? 1 : tempC <= 1.5 ? 0.5 : 0;
  return Math.min(byLabel, byTemp);
}

// Centimeters of new snow per millimeter of water: dense and wet near freezing, light when it's cold.
export function snowRatio(tempC: number): number {
  return tempC <= -10 ? 1.5 : tempC <= -4 ? 1.2 : tempC <= -1 ? 1 : 0.8;
}

// Fresh snow (cm) from liquid-equivalent precipitation (mm).
export function snowFrom(mm: number, tempC: number, symbol?: string): number {
  if (!(mm > 0)) return 0;
  return mm * snowShare(symbol, tempC) * snowRatio(tempC);
}

export function skyFrom(symbol: string | undefined): string {
  const s = (symbol || "").replace(/_(day|night|polartwilight)$/, "");
  if (!s) return "—";
  if (s.includes("thunder")) return "Storms";
  if (s.includes("snow")) return "Snowing";
  if (s.includes("sleet")) return "Sleet";
  if (s.includes("rain")) return "Rain";
  if (s === "fog") return "Fog";
  if (s === "cloudy") return "Overcast";
  if (s === "partlycloudy") return "Partly cloudy";
  if (s === "fair") return "Mostly clear";
  if (s === "clearsky") return "Clear";
  return "—";
}

export async function fetchForecast(r: Resort): Promise<any> {
  const url = `https://api.met.no/weatherapi/locationforecast/2.0/complete?lat=${r.lat.toFixed(4)}&lon=${r.lon.toFixed(4)}&altitude=${Math.round(r.mid)}`;
  const res = await fetch(url, { headers: { "User-Agent": USER_AGENT, Accept: "application/json" } });
  if (!res.ok) throw new Error(`MET Norway ${res.status} for ${r.id}`);
  return res.json();
}

const localDate = (t: number, tz: string) =>
  new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(t));

// What we record each time a resort is refreshed: the warmest temperature and the snow expected
// over the next `hours` (the gap until its next refresh), so recent snowfall adds up without gaps.
export function recordWindow(forecast: any, hours = 6): Hour | null {
  const ts: any[] = forecast?.properties?.timeseries || [];
  if (!ts.length) return null;
  const t0 = Date.parse(ts[0].time);
  let temp = -Infinity, snow = 0;
  for (const e of ts) {
    if (Date.parse(e.time) >= t0 + hours * HOUR) break;
    const det = e.data?.instant?.details || {};
    if (typeof det.air_temperature === "number") temp = Math.max(temp, det.air_temperature);
    const mm = e.data?.next_1_hours?.details?.precipitation_amount;
    if (typeof mm === "number") snow += snowFrom(mm, det.air_temperature ?? 0, e.data?.next_1_hours?.summary?.symbol_code);
  }
  return Number.isFinite(temp) ? { t: Math.floor(t0 / HOUR) * HOUR, temp, snow } : null;
}

// Run fn over items with limited concurrency and at most one start every gapMs (MET allows 20 requests/second).
export async function pool<T>(items: T[], concurrency: number, gapMs: number, fn: (item: T) => Promise<void>) {
  let i = 0, last = 0;
  const worker = async () => {
    while (i < items.length) {
      const item = items[i++];
      const now = Date.now(), slot = Math.max(now, last + gapMs);
      last = slot;
      if (slot > now) await new Promise(r => setTimeout(r, slot - now));
      await fn(item);
    }
  };
  await Promise.all(Array.from({ length: concurrency }, worker));
}

// Turn one forecast plus our recorded hours into what the resort page needs.
export function summarize(r: Resort, forecast: any, history: Hour[], now = Date.now()): Conditions {
  const ts: any[] = forecast?.properties?.timeseries || [];
  if (!ts.length) throw new Error(`empty forecast for ${r.id}`);
  const first = ts[0].data, d0 = first.instant.details;

  // Daily low/high/snow in the resort's own time zone. Hourly steps first, 6-hour steps later on.
  const byDay = new Map<string, Day>();
  ts.forEach((e, i) => {
    const t = Date.parse(e.time), det = e.data?.instant?.details || {};
    const key = localDate(t, r.tz);
    let day = byDay.get(key);
    if (!day) { day = { date: key, min: Infinity, max: -Infinity, snow: 0 }; byDay.set(key, day); }
    if (typeof det.air_temperature === "number") {
      day.min = Math.min(day.min, det.air_temperature);
      day.max = Math.max(day.max, det.air_temperature);
    }
    const next = ts[i + 1] ? Date.parse(ts[i + 1].time) - t : HOUR;
    const block = next <= HOUR ? e.data?.next_1_hours : e.data?.next_6_hours;
    const mm = block?.details?.precipitation_amount ?? 0;
    day.snow += snowFrom(mm, det.air_temperature ?? 0, block?.summary?.symbol_code);
  });
  const days = [...byDay.values()]
    .filter(d => Number.isFinite(d.min))
    .map(d => ({ date: d.date, min: round1(d.min), max: round1(d.max), snow: round1(d.snow) }));

  // Recent snow and recent high come from the hours we have recorded (MET only forecasts forward).
  // windows that started in the last 48 hours and are already over (the newest one is still in the future)
  const recent = history.filter(h => h.t > now - 49 * HOUR && h.t <= now - HOUR);
  const snow48 = recent.reduce((a, h) => a + h.snow, 0);
  const today = days[0];
  const pastMax = recent.length ? Math.max(...recent.map(h => h.temp)) : (today ? today.max : d0.air_temperature);

  return {
    air: round1(d0.air_temperature),
    rh: Math.round(d0.relative_humidity ?? 70),
    cloud: Math.round(d0.cloud_area_fraction ?? 50),
    sky: skyFrom(first.next_1_hours?.summary?.symbol_code),
    snow48: round1(snow48), pastMax: round1(pastMax), historyHours: recent.length,
    tmrMin: days[1]?.min ?? d0.air_temperature, tmrMax: days[1]?.max ?? d0.air_temperature, tmrSnow: days[1]?.snow ?? 0,
    days
  };
}

// Keep the last 72 recorded hours, one entry per hour.
export function mergeHistory(history: Hour[], hour: Hour | null, now = Date.now()): Hour[] {
  const keep = history.filter(h => h.t > now - 72 * HOUR && (!hour || h.t !== hour.t));
  if (hour) keep.push(hour);
  return keep.sort((a, b) => a.t - b.t);
}

const round1 = (v: number) => Math.round(v * 10) / 10;
