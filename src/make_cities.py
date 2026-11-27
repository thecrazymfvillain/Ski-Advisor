"""Make src/cities.json: US and Canadian towns of 5,000+ people, so the resort search can find the resorts
nearest a town ("Denver", "Boise"). Run only to refresh the list; build.py copies the result to site/assets/.

Data: GeoNames (https://www.geonames.org), CC BY 4.0. Download cities5000.zip and admin1CodesASCII.txt from
https://download.geonames.org/export/dump/, unzip, then:  python3 src/make_cities.py <folder with both files>
"""
import json, os, sys
d = sys.argv[1]
admin = {}
for line in open(os.path.join(d, "admin1CodesASCII.txt"), encoding="utf-8"):
    code, name, ascii_name, _ = line.rstrip("\n").split("\t")
    admin[code] = name
# Province and state short codes as the site uses them (US postal codes come straight from GeoNames).
CA = {"Alberta": "AB", "British Columbia": "BC", "Manitoba": "MB", "New Brunswick": "NB", "Newfoundland and Labrador": "NL",
      "Nova Scotia": "NS", "Ontario": "ON", "Prince Edward Island": "PE", "Quebec": "QC", "Saskatchewan": "SK",
      "Yukon": "YT", "Northwest Territories": "NT", "Nunavut": "NU"}
out = []
for line in open(os.path.join(d, "cities5000.txt"), encoding="utf-8"):
    f = line.rstrip("\n").split("\t")
    cc, a1, pop = f[8], f[10], int(f[14] or 0)
    if cc not in ("US", "CA") or pop < 5000: continue
    if cc == "US": st = a1
    else: st = CA.get(admin.get(f"CA.{a1}", ""), "")
    if not st or len(st) != 2: continue
    out.append([f[1], st, round(float(f[4]), 3), round(float(f[5]), 3), round(pop / 1000)])
out.sort(key=lambda c: -c[4])
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cities.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
print(len(out), "towns;", sum(1 for c in out if c[1] in CA.values()), "in Canada")
