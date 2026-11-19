#!/usr/bin/env python3
"""Build src/resorts-data.json from the OpenSkiMap ski-area dataset.

Source: https://tiles.openskimap.org/geojson/ski_areas.geojson
Data © OpenSkiMap and OpenStreetMap contributors, Open Database License (ODbL).
The derived resort list (src/resorts-data.json, and the copies published with the site)
is therefore also offered under the ODbL.

Keeps operating downhill ski areas in the US, Canada and Mexico that have at least one lift.

Run:  curl -o data-raw/ski_areas.geojson https://tiles.openskimap.org/geojson/ski_areas.geojson
      python3 src/import-resorts.py            (needs: pip install timezonefinder)
"""
import json, os, re, sys, unicodedata
from timezonefinder import TimezoneFinder

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data-raw", "ski_areas.geojson")
OUT = os.path.join(ROOT, "src", "resorts-data.json")

# The 11 resorts with hand-written pages keep their existing addresses.
FLAGSHIPS = {
    "whistler": "Whistler Blackcomb", "vail": "Vail", "parkcity": "Park City Mountain Resort",
    "jackson": "Jackson Hole Mountain Resort", "aspen": "Aspen Snowmass", "mammoth": "Mammoth Mountain",
    "bigsky": "Big Sky Resort", "telluride": "Telluride Ski Area", "snowbird": "Snowbird",
    "killington": "Killington Resort", "bogus": "Bogus Basin Mountain Recreation Area",
}
SUFFIX = re.compile(r"\s+(ski\s+area|ski\s+resort|mountain\s+resort|ski\s+hill|ski\s+club|resort|ski\s+center|ski\s+centre)$", re.I)

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = SUFFIX.sub("", s.strip())
    s = re.sub(r"\s+(and|&)$", "", s, flags=re.I)        # "X Ski Area and Resort" -> "x"
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "ski-area"

def point(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Point": return c[0], c[1]
    if t == "Polygon": ring = c[0]
    elif t == "MultiPolygon": ring = max((p[0] for p in c), key=len)
    else: return None
    xs = [p[0] for p in ring[:-1]] or [ring[0][0]]; ys = [p[1] for p in ring[:-1]] or [ring[0][1]]
    return sum(xs) / len(xs), sum(ys) / len(ys)

def lift_count(st):
    return sum(v.get("count", 0) for v in ((st.get("lifts") or {}).get("byType") or {}).values())

def runs(st):
    dh = (((st.get("runs") or {}).get("byActivity") or {}).get("downhill") or {}).get("byDifficulty") or {}
    out = {"easy": 0, "intermediate": 0, "advanced": 0, "expert": 0, "other": 0}
    km = snow = 0.0
    for k, v in dh.items():
        bucket = {"novice": "easy", "easy": "easy", "intermediate": "intermediate", "advanced": "advanced",
                  "expert": "expert", "extreme": "expert", "freeride": "expert"}.get(k, "other")
        out[bucket] += v.get("count", 0)
        km += v.get("lengthInKm", 0) or 0
        snow += v.get("snowmakingLengthInKm", 0) or 0
    return out, round(km, 1), round(snow, 1)

def main():
    data = json.load(open(SRC))
    tf = TimezoneFinder()
    resorts, used = [], set()
    for f in data["features"]:
        p = f["properties"]
        if p.get("status") != "operating" or "downhill" not in (p.get("activities") or []) or not p.get("name"):
            continue
        places = [pl for pl in (p.get("places") or []) if pl.get("iso3166_1Alpha2") in ("US", "CA", "MX")]
        if not places: continue
        st = p.get("statistics") or {}
        lifts = lift_count(st)
        if lifts < 1 or st.get("maxElevation") is None: continue
        pt = point(f["geometry"])
        if not pt: continue
        place = next((pl for pl in places if pl.get("iso3166_2")), places[0])
        en = (place.get("localized") or {}).get("en") or {}
        cc = place["iso3166_1Alpha2"]
        region = place.get("iso3166_2") or cc
        lo, hi = float(st.get("minElevation") or st["maxElevation"]), float(st["maxElevation"])
        r_counts, km, snowkm = runs(st)
        resorts.append({
            "osm": p["id"], "name": p["name"].strip(), "country": cc, "region": region,
            "regionName": en.get("region") or en.get("country") or cc, "locality": en.get("locality"),
            "lat": round(pt[1], 4), "lon": round(pt[0], 4),
            "base": round(lo), "summit": round(hi), "mid": round((lo + hi) / 2), "vertical": round(hi - lo),
            "lifts": lifts, "runs": r_counts, "runKm": km, "snowmakingKm": snowkm,
            "website": (p.get("websites") or [None])[0], "tz": tf.timezone_at(lng=pt[0], lat=pt[1]) or "America/Denver",
        })
    # the same name twice in one state/province is a duplicate outline in OpenStreetMap: keep the bigger one
    best = {}
    for r in resorts:
        k = (r["name"].lower(), r["region"])
        if k not in best or (r["lifts"], r["vertical"]) > (best[k]["lifts"], best[k]["vertical"]): best[k] = r
    resorts = list(best.values())
    # stable ids: flagships first, then by name; collisions get the region code
    for slug, name in FLAGSHIPS.items():
        m = [r for r in resorts if r["name"] == name]
        if not m: sys.exit(f"flagship not found: {name}")
        m[0]["id"] = slug; used.add(slug)
    for r in sorted(resorts, key=lambda r: (r["name"].lower(), r["region"])):
        if "id" in r: continue
        s = slugify(r["name"])
        if s in used: s = f"{s}-{r['region'].lower()}"
        n = 2
        while s in used: s = f"{slugify(r['name'])}-{r['region'].lower()}-{n}"; n += 1
        r["id"] = s; used.add(s)
    resorts.sort(key=lambda r: (r["country"], r["region"], r["name"].lower()))
    json.dump(resorts, open(OUT, "w"), indent=0, ensure_ascii=False)
    by = {}
    for r in resorts: by[r["country"]] = by.get(r["country"], 0) + 1
    print(f"{len(resorts)} resorts -> {os.path.relpath(OUT, ROOT)}", by)

if __name__ == "__main__":
    main()
