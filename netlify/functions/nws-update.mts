// Every hour, refresh the National Weather Service text forecast for the US resorts in the same
// sixth of the states that weather-update handles that hour (every US resort every 6 hours).
// Runs separately from weather-update so an NWS outage can never hold up the wax picks.
// This is the only writer of the "nws-v1/..." and "nws-grid" keys in the "weather" store.
import type { Config } from "@netlify/functions";
import { getStore } from "@netlify/blobs";
import meta from "../lib/meta.json" with { type: "json" };
import { RESORTS, pool } from "../lib/met.mts";
import { fetchNws, isUS, type GridCache, type NwsForecast } from "../lib/nws.mts";

type Saved = { updated: string; resorts: Record<string, NwsForecast> };
const BUDGET_MS = 20_000;   // scheduled functions get 30 seconds; stop starting new resorts after 20

export default async () => {
  const store = getStore("weather");
  const started = Date.now();
  const shards = meta.shards as string[][];
  const regions = shards[new Date(started).getUTCHours() % shards.length].filter(g => g.startsWith("US-"));
  const todo = RESORTS.filter(r => isUS(r) && regions.includes(r.region));
  const grids = ((await store.get("nws-grid", { type: "json" })) as GridCache | null) || {};
  const gridCount = Object.keys(grids).length;
  const got = new Map<string, NwsForecast>();
  let failed = 0, skipped = 0;
  await pool(todo, 4, 120, async r => {
    if (Date.now() - started > BUDGET_MS) { skipped++; return; }
    try { got.set(r.id, await fetchNws(r, grids)); }
    catch (err) { failed++; console.error(`nws-update: ${r.id}:`, err); }
  });
  if (Object.keys(grids).length !== gridCount) await store.setJSON("nws-grid", grids);
  for (const region of regions) {
    const prev = (await store.get(`nws-v1/${region}`, { type: "json" })) as Saved | null;
    const resorts: Record<string, NwsForecast> = {};
    for (const r of todo.filter(r => r.region === region)) {
      const f = got.get(r.id) || prev?.resorts?.[r.id];   // keep the last good forecast
      if (f) resorts[r.id] = f;
    }
    await store.setJSON(`nws-v1/${region}`, { updated: new Date(started).toISOString(), resorts });
  }
  console.log(`nws-update: ${regions.length} regions, ${got.size}/${todo.length} resorts refreshed, ${failed} failed, ${skipped} skipped`);
};

export const config: Config = {
  schedule: "41 * * * *", // minute 41 of every hour, UTC, half an hour after weather-update
};
