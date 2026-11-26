// GET /api/nws/:id — the National Weather Service 7-day text forecast for one US resort.
// Serves what nws-update saved; if nothing recent is saved (a resort not refreshed yet), it asks
// NWS directly. 404 for resorts outside the US, which NWS doesn't cover.
import type { Config, Context } from "@netlify/functions";
import { getStore } from "@netlify/blobs";
import { RESORTS } from "../lib/met.mts";
import { fetchNws, isUS, type GridCache, type NwsForecast } from "../lib/nws.mts";

const STALE_MS = 9 * 3600_000;
type Saved = { updated: string; resorts?: Record<string, NwsForecast> };

export default async (req: Request, context: Context) => {
  const r = RESORTS.find(x => x.id === context.params.id);
  if (!r || !isUS(r)) return Response.json({ error: "No National Weather Service forecast for this resort." }, { status: 404 });

  const store = getStore("weather");
  let saved: Saved | null = null;
  try { saved = (await store.get(`nws-v1/${r.region}`, { type: "json" })) as Saved | null; }
  catch (err) { console.error(`nws: could not read ${r.region}:`, err); }
  let f = saved?.resorts?.[r.id] || null;
  if (!f || !saved || Date.now() - Date.parse(saved.updated) > STALE_MS) {
    try {
      const grids = ((await store.get("nws-grid", { type: "json" }).catch(() => null)) as GridCache | null) || {};
      f = await fetchNws(r, grids);
    } catch (err) { console.error(`nws: ${r.id}:`, err); }
  }
  if (!f) return Response.json({ error: "The National Weather Service forecast is unavailable right now." },
    { status: 503, headers: { "Cache-Control": "no-store" } });
  return Response.json(f, {
    headers: {
      "Cache-Control": "public, max-age=600",
      "Netlify-CDN-Cache-Control": "public, durable, s-maxage=1800, stale-while-revalidate=21600",
    },
  });
};

export const config: Config = { path: "/api/nws/:id" };
