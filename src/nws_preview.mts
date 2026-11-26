// Local preview only: print one resort's NWS forecast the way /api/nws/:id serves it, using the same
// code as the live function (netlify/lib/nws.mts). src/preview.py runs this when the live site
// doesn't have /api/nws yet. Usage: node --experimental-strip-types src/nws_preview.mts bogus
import { RESORTS } from "../netlify/lib/met.mts";
import { fetchNws, isUS } from "../netlify/lib/nws.mts";
const r = RESORTS.find(x => x.id === process.argv[2]);
if (!r || !isUS(r)) { console.log(JSON.stringify({ error: "No National Weather Service forecast for this resort." })); process.exit(4); }
try { console.log(JSON.stringify(await fetchNws(r))); }
catch (err) { console.error(String(err)); console.log(JSON.stringify({ error: "unavailable" })); process.exit(5); }
