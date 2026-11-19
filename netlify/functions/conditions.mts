// GET /api/conditions — current conditions for every resort, read by the resort pages.
// Serves what the hourly weather-update function saved. If nothing is saved yet (a brand-new
// site before its first scheduled run), it fetches MET Norway directly without saving.
import type { Config } from "@netlify/functions";
import { getStore } from "@netlify/blobs";
import { RESORTS, fetchForecast, summarize } from "../lib/met.mts";

const STALE_MS = 3 * 3600_000;

export default async () => {
  let data: { updated: string } | null = null;
  try { data = (await getStore("weather").get("latest", { type: "json" })) as { updated: string } | null; }
  catch (err) { console.error("conditions: could not read saved weather:", err); }
  if (!data || Date.now() - Date.parse(data.updated) > STALE_MS) {
    const resorts: Record<string, unknown> = {};
    await Promise.all(RESORTS.map(async r => {
      try { resorts[r.id] = summarize(r, await fetchForecast(r), []); }
      catch (err) { console.error(`conditions: ${r.id}:`, err); }
    }));
    if (!Object.keys(resorts).length && !data) {
      return Response.json({ error: "Weather is unavailable right now." }, { status: 503, headers: { "Cache-Control": "no-store" } });
    }
    if (Object.keys(resorts).length) data = { updated: new Date().toISOString(), source: "MET Norway", resorts } as any;
  }
  return Response.json(data, {
    headers: {
      "Cache-Control": "public, max-age=300",
      "Netlify-CDN-Cache-Control": "public, durable, s-maxage=900, stale-while-revalidate=3600",
    },
  });
};

export const config: Config = { path: "/api/conditions" };
