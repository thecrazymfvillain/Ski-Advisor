"""Make src/cities.json: towns the resort search can find the ski areas nearest to ("Denver", "Ketchum").
Every US and Canadian town of 5,000+ people, plus smaller towns (500+) within 60 km of a ski area, because
ski resorts are in small towns. Run only to refresh the list; build.py copies the result to site/assets/.

Data: GeoNames (https://www.geonames.org), CC BY 4.0. Download cities500.zip and admin1CodesASCII.txt from
https://download.geonames.org/export/dump/, unzip, then:  python3 src/make_cities.py <folder with both files>
"""
import json, math, os, sys
d = sys.argv[1]
admin = {}
for line in open(os.path.join(d, "admin1CodesASCII.txt"), encoding="utf-8"):
    code, name, ascii_name, _ = line.rstrip("\n").split("\t")
    admin[code] = name
# Province and state short codes as the site uses them (US postal codes come straight from GeoNames).
CA = {"Alberta": "AB", "British Columbia": "BC", "Manitoba": "MB", "New Brunswick": "NB", "Newfoundland and Labrador": "NL",
      "Nova Scotia": "NS", "Ontario": "ON", "Prince Edward Island": "PE", "Quebec": "QC", "Saskatchewan": "SK",
      "Yukon": "YT", "Northwest Territories": "NT", "Nunavut": "NU"}
HERE = os.path.dirname(os.path.abspath(__file__))
resorts = json.load(open(os.path.join(HERE, "resorts-data.json"), encoding="utf-8"))
def near_ski(la, lo, km=60):
    for r in resorts:
        if abs(r["lat"] - la) > 0.6: continue
        dl = math.radians(r["lat"] - la); dn = math.radians(r["lon"] - lo)
        a = math.sin(dl / 2) ** 2 + math.cos(math.radians(la)) * math.cos(math.radians(r["lat"])) * math.sin(dn / 2) ** 2
        if 12742 * math.asin(math.sqrt(a)) <= km: return True
    return False
out = []
for line in open(os.path.join(d, "cities500.txt"), encoding="utf-8"):
    f = line.rstrip("\n").split("\t")
    cc, a1, pop = f[8], f[10], int(f[14] or 0)
    if cc not in ("US", "CA") or pop < 500: continue
    if pop < 5000 and not near_ski(float(f[4]), float(f[5])): continue
    if cc == "US": st = a1
    else: st = CA.get(admin.get(f"CA.{a1}", ""), "")
    if not st or len(st) != 2: continue
    out.append([f[1], st, round(float(f[4]), 2), round(float(f[5]), 2), round(pop / 1000, 1)])
out.sort(key=lambda c: -c[4])
with open(os.path.join(HERE, "cities.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
print(len(out), "towns;", sum(1 for c in out if c[1] in CA.values()), "in Canada")
