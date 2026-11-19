// Every hour, refresh one sixth of the states and provinces from MET Norway (all ~745 resorts every
// 6 hours), keep a short record per resort for recent snowfall, and save one blob per region.
// This is the only writer of the "weather" store; /api/conditions/:key only reads it.
import type { Config } from "@netlify/functions";
import { getStore } from "@netlify/blobs";
import meta from "../lib/meta.json" with { type: "json" };
import { RESORTS, fetchForecast, recordWindow, summarize, mergeHistory, pool, type Hour } from "../lib/met.mts";

export default async () => {
  const store = getStore("weather");
  const now = Date.now();
  const shards = meta.shards as string[][];
  const regions = shards[new Date(now).getUTCHours() % shards.length];
  const todo = RESORTS.filter(r => regions.includes(r.region));
  const forecasts = new Map<string, unknown>();
  let failed = 0;
  await pool(todo, 6, 75, async r => {
    try { forecasts.set(r.id, await fetchForecast(r)); }
    catch (err) { failed++; console.error(`weather-update: ${r.id}:`, err); }
  });
  for (const region of regions) {
    const history = ((await store.get(`history-v2/${region}`, { type: "json" })) as Record<string, Hour[]> | null) || {};
    const prev = (await store.get(`latest-v2/${region}`, { type: "json" })) as { resorts?: Record<string, unknown> } | null;
    const resorts: Record<string, unknown> = {};
    for (const r of todo.filter(r => r.region === region)) {
      const f = forecasts.get(r.id);
      if (!f) { if (prev?.resorts?.[r.id]) resorts[r.id] = prev.resorts[r.id]; continue; }   // keep the last good data
      history[r.id] = mergeHistory(history[r.id] || [], recordWindow(f, 6), now);
      try { resorts[r.id] = summarize(r, f, history[r.id], now); }
      catch (err) { console.error(`weather-update: ${r.id}:`, err); if (prev?.resorts?.[r.id]) resorts[r.id] = prev.resorts[r.id]; }
    }
    await store.setJSON(`history-v2/${region}`, history);
    await store.setJSON(`latest-v2/${region}`, { updated: new Date(now).toISOString(), source: "MET Norway", resorts });
  }
  console.log(`weather-update: ${regions.length} regions, ${todo.length - failed}/${todo.length} resorts refreshed`);
};

export const config: Config = {
  schedule: "11 * * * *", // minute 11 of every hour, UTC; each hour handles one of six region groups
};
