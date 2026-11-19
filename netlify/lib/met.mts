// Weather for the resort pages, from MET Norway's Locationforecast 2.0.
// Data: MET Norway, CC BY 4.0 (https://api.met.no/doc/License). We adapt it: mid-mountain
// altitude, snow estimated from precipitation and temperature, daily summaries in resort time.
import resorts from "./resorts.json" with { type: "json" };

export type Resort = { id: string; lat: number; lon: number; mid: number; tz: string };
export type Hour = { t: number; temp: number; snow: number };          // one recorded hour: epoch ms, °C, cm
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

// Fresh snow from liquid-equivalent precipitation: about 1 cm per mm when it's cold, less near freezing.
export function snowFrom(mm: number, tempC: number): number {
  if (!(mm > 0)) return 0;
  if (tempC <= 0) return mm;
  if (tempC <= 1.5) return mm * 0.5;
  return 0;
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

// The hour we record for history: current temperature and the snow expected over the next hour.
export function currentHour(forecast: any): Hour | null {
  const first = forecast?.properties?.timeseries?.[0];
  if (!first) return null;
  const temp = first.data?.instant?.details?.air_temperature;
  const mm = first.data?.next_1_hours?.details?.precipitation_amount ?? 0;
  if (typeof temp !== "number") return null;
  const t = Math.floor(Date.parse(first.time) / HOUR) * HOUR;
  return { t, temp, snow: snowFrom(mm, temp) };
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
    day.snow += snowFrom(mm, det.air_temperature ?? 0);
  });
  const days = [...byDay.values()]
    .filter(d => Number.isFinite(d.min))
    .map(d => ({ date: d.date, min: round1(d.min), max: round1(d.max), snow: round1(d.snow) }));

  // Recent snow and recent high come from the hours we have recorded (MET only forecasts forward).
  const recent = history.filter(h => h.t > now - 48 * HOUR && h.t <= now);
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
