// Every hour: fetch MET Norway forecasts for all resorts, record the current hour for each
// (so the site can show recent snowfall, which a forecast alone can't), and save the result.
// This is the only writer of the "weather" store; the /api/conditions function only reads it.
import type { Config } from "@netlify/functions";
import { getStore } from "@netlify/blobs";
import { RESORTS, fetchForecast, currentHour, summarize, mergeHistory, type Hour } from "../lib/met.mts";

export default async () => {
  const store = getStore("weather");
  const now = Date.now();
  const resorts: Record<string, unknown> = {};
  const failed: string[] = [];
  await Promise.all(RESORTS.map(async r => {
    try {
      const forecast = await fetchForecast(r);
      const past = ((await store.get(`history/${r.id}`, { type: "json" })) as Hour[] | null) || [];
      const history = mergeHistory(past, currentHour(forecast), now);
      await store.setJSON(`history/${r.id}`, history);
      resorts[r.id] = summarize(r, forecast, history, now);
    } catch (err) {
      failed.push(r.id);
      console.error(`weather-update: ${r.id}:`, err);
    }
  }));
  if (Object.keys(resorts).length) {
    // Keep the last good data for any resort that failed this hour.
    const prev = (await store.get("latest", { type: "json" })) as { resorts?: Record<string, unknown> } | null;
    for (const id of failed) if (prev?.resorts?.[id]) resorts[id] = prev.resorts[id];
    await store.setJSON("latest", { updated: new Date(now).toISOString(), source: "MET Norway", resorts });
  }
  console.log(`weather-update: ${Object.keys(resorts).length} resorts saved, ${failed.length} failed`);
};

export const config: Config = {
  schedule: "7 * * * *", // minute 7 of every hour, UTC
};
