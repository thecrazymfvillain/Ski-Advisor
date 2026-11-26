// One-time lookup: for every US resort, the National Weather Service grid square (about 2.5 km)
// whose elevation is closest to the resort's mid-mountain. The square the resort's map pin falls in is
// often the base area or town (Aspen's is 1,660 ft below mid-mountain), so its forecast runs warm and wet.
// We start at the pin's square and step to whichever neighbor is closer in elevation, staying within
// 2 squares (about 5 km) of the pin so the forecast stays on the mountain.
//
// Writes netlify/lib/nws-grid.json, which the NWS functions use. Re-run only if resorts are added or
// NWS changes its grids (the functions fall back to the pin's square if a saved square stops working):
//   NODE_USE_ENV_PROXY=1 node --experimental-strip-types src/nws_grids.mts          (only resorts not in the file)
//   NODE_USE_ENV_PROXY=1 node --experimental-strip-types src/nws_grids.mts --all    (redo every resort)
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { RESORTS, pool } from "../netlify/lib/met.mts";
import { isUS } from "../netlify/lib/nws.mts";

const OUT = new URL("../netlify/lib/nws-grid.json", import.meta.url);
const UA = "TheSkiAdvisor/1.0 (+https://theskiadvisor.com)";
const GOOD_M = 75;        // within about 250 ft of mid-mountain: stop looking
const MAX_STEPS = 2;      // squares away from the pin's square

type Pick = { grid: string; elev: number; pinElev: number };
const saved: Record<string, Pick> = existsSync(OUT) && !process.argv.includes("--all") ? JSON.parse(readFileSync(OUT, "utf8")) : {};

async function get(url: string, tries = 3): Promise<any> {
  for (let i = 1; ; i++) {
    const res = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/geo+json" } });
    if (res.ok) return res.json();
    if (res.status === 404 || i >= tries) throw Object.assign(new Error(`${res.status} ${url}`), { status: res.status });
    await new Promise(r => setTimeout(r, 1500 * i));
  }
}
const elevCache = new Map<string, Promise<number | null>>();
const elevOf = (office: string, x: number, y: number) => {
  const k = `${office}/${x},${y}`;
  if (!elevCache.has(k)) elevCache.set(k, get(`https://api.weather.gov/gridpoints/${k}/forecast`)
    .then(d => typeof d?.properties?.elevation?.value === "number" ? d.properties.elevation.value : null)
    .catch(() => null));
  return elevCache.get(k)!;
};

const todo = RESORTS.filter(r => isUS(r) && !saved[r.id]);
console.log(`${todo.length} resorts to look up`);
let done = 0, failed = 0;
await pool(todo, 4, 150, async r => {
  try {
    const p = (await get(`https://api.weather.gov/points/${r.lat.toFixed(4)},${r.lon.toFixed(4)}`)).properties;
    const office = p.gridId, x0 = p.gridX, y0 = p.gridY;
    const pinElev = await elevOf(office, x0, y0);
    if (pinElev == null) throw new Error("no elevation for the pin's square");
    let best = { x: x0, y: y0, elev: pinElev };
    for (let step = 0; step < 4 && Math.abs(best.elev - r.mid) > GOOD_M; step++) {
      let moved = false;
      const around: [number, number][] = [];
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        const x = best.x + dx, y = best.y + dy;
        if ((dx || dy) && Math.abs(x - x0) <= MAX_STEPS && Math.abs(y - y0) <= MAX_STEPS) around.push([x, y]);
      }
      const elevs = await Promise.all(around.map(([x, y]) => elevOf(office, x, y)));
      around.forEach(([x, y], i) => {
        const e = elevs[i];
        if (e != null && Math.abs(e - r.mid) < Math.abs(best.elev - r.mid)) { best = { x, y, elev: e }; moved = true; }
      });
      if (!moved) break;
    }
    saved[r.id] = { grid: `${office}/${best.x},${best.y}`, elev: Math.round(best.elev), pinElev: Math.round(pinElev) };
  } catch (err) { failed++; console.error(`${r.id}: ${err}`); }
  if (++done % 50 === 0) console.log(`${done}/${todo.length}`);
});
const sorted = Object.fromEntries(Object.keys(saved).sort().map(k => [k, saved[k]]));
writeFileSync(OUT, JSON.stringify(sorted, null, 0).replace(/},"/g, '},\n"') + "\n");
console.log(`saved ${Object.keys(saved).length} resorts, ${failed} failed`);
