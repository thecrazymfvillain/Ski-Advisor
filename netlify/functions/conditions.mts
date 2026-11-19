// GET /api/conditions/:key — conditions for every resort in one state/province (key like "US-CO"),
// or for the home page's popular resorts (key "featured"). Serves what weather-update saved; for a
// region with nothing saved yet (a new site before its first refresh) it asks MET Norway directly.
import type { Config, Context } from "@netlify/functions";
import { getStore } from "@netlify/blobs";
import meta from "../lib/meta.json" with { type: "json" };
import { RESORTS, fetchForecast, summarize, pool } from "../lib/met.mts";

const STALE_MS = 9 * 3600_000;
const REGIONS = new Set(RESORTS.map(r => r.region));
type Saved = { updated: string; resorts?: Record<string, unknown> };

export default async (req: Request, context: Context) => {
  const key = context.params.key;
  const featured = meta.featured as { id: string; region: string }[];
  let regions: string[], only: Set<string> | null = null;
  if (key === "featured") { regions = [...new Set(featured.map(f => f.region))]; only = new Set(featured.map(f => f.id)); }
  else if (REGIONS.has(key)) regions = [key];
  else return Response.json({ error: "Unknown state or province." }, { status: 404 });

  const store = getStore("weather");
  const resorts: Record<string, unknown> = {};
  let oldest = Date.now();
  for (const region of regions) {
    const want = RESORTS.filter(r => r.region === region && (!only || only.has(r.id)));
    let saved: Saved | null = null;
    try { saved = (await store.get(`latest-v2/${region}`, { type: "json" })) as Saved | null; }
    catch (err) { console.error(`conditions: could not read ${region}:`, err); }
    if (saved && Date.now() - Date.parse(saved.updated) < STALE_MS) {
      for (const r of want) if (saved.resorts?.[r.id]) resorts[r.id] = saved.resorts[r.id];
      oldest = Math.min(oldest, Date.parse(saved.updated));
      continue;
    }
    await pool(want, 6, 75, async r => {
      try { resorts[r.id] = summarize(r, await fetchForecast(r), []); }
      catch (err) { console.error(`conditions: ${r.id}:`, err); if (saved?.resorts?.[r.id]) resorts[r.id] = saved.resorts[r.id]; }
    });
  }
  if (!Object.keys(resorts).length) {
    return Response.json({ error: "Weather is unavailable right now." }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
  return Response.json({ updated: new Date(oldest).toISOString(), source: "MET Norway", resorts }, {
    headers: {
      "Cache-Control": "public, max-age=600",
      "Netlify-CDN-Cache-Control": "public, durable, s-maxage=1800, stale-while-revalidate=21600",
    },
  });
};

export const config: Config = { path: "/api/conditions/:key" };
