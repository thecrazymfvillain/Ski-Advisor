#!/usr/bin/env python3
"""Build The Ski Advisor static site (theskiadvisor.com).

Outputs:
  site/          deployable site (Netlify, Cloudflare Pages, GitHub Pages...)
  preview/       claude.ai preview entry (home page without the document wrapper; not committed)

Run:  python3 src/build.py
"""
import json, math, os, re, html, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "site")

# ---- Set this to the real domain before launch (used for canonical links and the sitemap). ----
DOMAIN = "https://theskiadvisor.com"
BRAND = "The Ski Advisor"
TODAY = datetime.date.today().isoformat()
THREE = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
# Cloudflare Web Analytics site token (cookie-free). Empty = analytics off.
CF_ANALYTICS_TOKEN = "7effe80b68fa4bdd9944534b8a820936"
# Geist and Playfair Display italic (both SIL OFL), served from the site. Preloaded so text draws in them
# quickly; font-display: swap means nothing waits on them.
FONTS = '<link rel="preload" href="/assets/fonts/geist-latin.woff2" as="font" type="font/woff2" crossorigin>'
FONT_SERIF = '<link rel="preload" href="/assets/fonts/playfair-italic-latin.woff2" as="font" type="font/woff2" crossorigin>'   # only pages that use the italic accents
LATIN = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
LATIN_EXT = "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF"
FONT_FACES = (
    '@font-face{font-family:"Geist";font-style:normal;font-weight:400 800;font-display:swap;src:url(/assets/fonts/geist-latin.woff2) format("woff2");unicode-range:' + LATIN + '}\n'
    '@font-face{font-family:"Geist";font-style:normal;font-weight:400 800;font-display:swap;src:url(/assets/fonts/geist-latin-ext.woff2) format("woff2");unicode-range:' + LATIN_EXT + '}\n'
    '@font-face{font-family:"Playfair Display";font-style:italic;font-weight:500;font-display:swap;src:url(/assets/fonts/playfair-italic-latin.woff2) format("woff2");unicode-range:' + LATIN + '}\n')
# The whole stylesheet (about 8 KB compressed) goes inline in every page, so the first paint waits on no request.
SITE_CSS = FONT_FACES + open(os.path.join(SRC, "base.css")).read() + open(os.path.join(SRC, "extra.css")).read() + open(os.path.join(SRC, "theme.css")).read()
esc = lambda s: html.escape(s, quote=True)

# =====================================================================
# Resorts
# =====================================================================
RESORTS = [
 dict(id="whistler", name="Whistler Blackcomb", region="BC", lat=50.1150, lon=-122.9486, mid=1500,
  ex=dict(air=-2,rh=88,snow48=12,pastMax=1,cloud=90,code=73,tmrMin=-5,tmrMax=-1,tmrSnow=6),
  tag="Coastal snow, huge vertical and big temperature swings",
  about=["Whistler Blackcomb sits close enough to the Pacific that its snow is often heavier and wetter than snow in the Rockies. The lifts climb from the village, around 2,200 feet, into alpine terrain above 7,000 feet, so it can be raining in the village while it snows hard up top.",
         "The wax pick on this page uses mid-mountain conditions, around 4,900 feet. If you'll spend the day in the alpine, set a colder temperature under Adjust conditions."],
  tips=["Humidity is usually high here. When you're between two waxes, take the warmer one for the lower mountain.",
        "Wet coastal snow causes suction. Brushing the structure back into the base matters as much as the wax color.",
        "Lower runs can turn to slush late in the day. A rub-on warm wax in your pocket helps on top-to-bottom days."]),
 dict(id="vail", name="Vail", region="CO", lat=39.6061, lon=-106.3550, mid=3000,
  ex=dict(air=-8,rh=55,snow48=3,pastMax=-2,cloud=20,code=1,tmrMin=-13,tmrMax=-4,tmrSnow=0),
  tag="High, dry Colorado snow and long groomers",
  about=["Vail is one of the largest ski areas in North America, with lifts from about 8,100 feet to about 11,500 feet. At that elevation the snow is usually cold and dry, and mornings stay cold even when the afternoon sun feels warm.",
         "The Back Bowls hold soft snow after storms. The front side's groomers are often firm until the sun reaches them."],
  tips=["Cold, dry snow is abrasive. A harder, colder wax lasts longer here than a soft one.",
        "Morning groomers are firm. Keep the side edge sharp. A 2° (88°) side edge suits most skiers.",
        "Strong sun warms south-facing runs quickly. If you ski mostly in the afternoon, wax for the forecast high."]),
 dict(id="parkcity", name="Park City", region="UT", lat=40.6514, lon=-111.5080, mid=2560,
  ex=dict(air=-5,rh=60,snow48=0,pastMax=2,cloud=10,code=0,tmrMin=-9,tmrMax=-1,tmrSnow=0),
  tag="Utah's dry snow across one of the biggest lift networks in the US",
  about=["Park City is one of the largest ski areas in the United States, with lifts from about 6,800 to 10,000 feet. Utah snow is known for being light and dry, and there's a lot of grooming.",
         "The base is lower than most Colorado resorts, so the bottom of the mountain warms up and refreezes more often. Expect firm snow on lower runs the morning after a warm day."],
  tips=["Lower runs go through freeze-thaw cycles. Sharpen before a morning after a warm day.",
        "After a storm, dry Utah powder calls for a colder wax than the temperature alone suggests.",
        "Long groomed cruisers reward a fresh wax job. Re-wax every few ski days."]),
 dict(id="jackson", name="Jackson Hole", region="WY", lat=43.5875, lon=-110.8279, mid=2550,
  ex=dict(air=-11,rh=72,snow48=18,pastMax=-6,cloud=95,code=75,tmrMin=-15,tmrMax=-8,tmrSnow=9),
  tag="Steep terrain, cold days and more than 4,000 feet of vertical",
  about=["Jackson Hole drops more than 4,000 vertical feet from the top of the tram to the base, and much of it is steep. Wyoming winters are cold, and the summit can be far colder than the base on the same morning.",
         "Wind often packs the upper mountain hard, while storms bring deep, dry snow."],
  tips=["Steep, firm terrain is where sharp edges matter most. Many strong skiers here run a 2° or 3° side edge.",
        "Cold days call for blue or turquoise wax. Soft, warm wax wears off fast on cold, abrasive snow.",
        "This page uses mid-mountain. For days spent off the tram, set a colder temperature under Adjust conditions."]),
 dict(id="aspen", name="Aspen Snowmass", region="CO", lat=39.2084, lon=-106.9490, mid=3100,
  ex=dict(air=-7,rh=50,snow48=2,pastMax=-1,cloud=30,code=2,tmrMin=-12,tmrMax=-3,tmrSnow=0),
  tag="Four mountains, high elevation and dry snow",
  about=["Aspen Snowmass is four ski areas on one pass: Aspen Mountain, Aspen Highlands, Buttermilk and Snowmass. The forecast here uses Snowmass, the largest, whose lifts top out above 12,000 feet.",
         "Expect cold, dry snow and intense sun at altitude, with big swings between morning and afternoon."],
  tips=["Morning and afternoon can need different waxes. Pick wax for the hours you'll actually ski.",
        "Snowmass has long, wide groomers that stay firm in the morning. Sharpen before a groomer day; if you mostly carve, a carver setup (0.7° base, 3° side) suits them.",
        "Dry snow rewards a clean, well-brushed base. Brush until it shines."]),
 dict(id="mammoth", name="Mammoth Mountain", region="CA", lat=37.6308, lon=-119.0326, mid=2900,
  ex=dict(air=-1,rh=45,snow48=0,pastMax=4,cloud=5,code=0,tmrMin=-4,tmrMax=3,tmrSnow=0),
  tag="Sierra snow, lots of sunshine and a long spring season",
  about=["Mammoth Mountain rises to about 11,000 feet in California's eastern Sierra. Storms here often bring denser snow than in the Rockies, and the weather between storms is usually sunny.",
         "The season often runs well into spring, when the snow freezes overnight and softens into corn by late morning."],
  tips=["Spring days start firm and end slushy. Keep edges sharp for the morning and wax for the afternoon.",
        "Warm, wet snow needs warm wax and extra brushing to break the suction.",
        "Dirty spring snow slows skis down. A graphite wax helps resist dirt."]),
 dict(id="bigsky", name="Big Sky", region="MT", lat=45.2833, lon=-111.4014, mid=2700,
  ex=dict(air=-14,rh=75,snow48=8,pastMax=-9,cloud=70,code=71,tmrMin=-19,tmrMax=-10,tmrSnow=3),
  tag="Cold Montana snow below Lone Peak",
  about=["Big Sky's lifts climb to the summit of Lone Peak at 11,166 feet. Montana sits farther north and farther inland than most western resorts, so temperatures run cold and the snow stays dry.",
         "Wind is common up high and can leave hard, wind-packed snow near the summit."],
  tips=["Expect blue or turquoise wax on most winter days.",
        "Very cold snow is abrasive. Iron in a harder wax and let it cool fully before scraping.",
        "Wind-packed snow up top is firm. Sharpen before a summit day."]),
 dict(id="telluride", name="Telluride", region="CO", lat=37.9375, lon=-107.8123, mid=3300,
  ex=dict(air=-9,rh=50,snow48=5,pastMax=-3,cloud=40,code=2,tmrMin=-14,tmrMax=-4,tmrSnow=2),
  tag="High, sunny and dry in southwest Colorado",
  about=["Telluride's lifts reach above 12,000 feet in the San Juan Mountains. The snow is usually dry, the sun is strong, and clear nights get very cold.",
         "Groomers are often firm at first chair and soft by early afternoon, especially on sunny aspects."],
  tips=["Clear nights mean cold snow at first chair. The snow can be several degrees colder than the air.",
        "South-facing runs soften first. Plan for the warmer end of the wax range on sunny afternoons.",
        "Cold, dry snow wears wax quickly. Re-wax every few ski days."]),
 dict(id="snowbird", name="Snowbird", region="UT", lat=40.5830, lon=-111.6556, mid=2850,
  ex=dict(air=-6,rh=82,snow48=22,pastMax=-4,cloud=100,code=75,tmrMin=-9,tmrMax=-5,tmrSnow=15),
  tag="Deep, frequent storms in Little Cottonwood Canyon",
  about=["Snowbird sits high in Little Cottonwood Canyon outside Salt Lake City and is known for some of the deepest average snowfall in North America. Its tram climbs to about 11,000 feet.",
         "Fresh snow is the normal condition here, and the season often runs into late spring."],
  tips=["New snow has sharp crystals. Go one wax color colder than the temperature alone suggests.",
        "Deep days need float more than bite. A 1° side edge is plenty for powder skis.",
        "Late-season days turn to corn snow, which calls for warm wax and extra brushing."]),
 dict(id="killington", name="Killington", region="VT", lat=43.6045, lon=-72.8201, mid=800,
  ex=dict(air=-3,rh=82,snow48=1,pastMax=3,cloud=80,code=3,tmrMin=-6,tmrMax=0,tmrSnow=1),
  tag="The East's biggest mountain, with snowmaking and ice",
  about=["Killington is the largest ski area in the eastern US, with a long season built on extensive snowmaking. Eastern snow goes through frequent freeze-thaw cycles, and machine-made snow is dense and abrasive.",
         "Firm, icy groomers are common, especially in the morning."],
  tips=["Edges matter more than wax here. Many skiers run a 2° or 3° side edge and sharpen often.",
        "Man-made snow is abrasive. Use a harder, colder wax than the temperature alone suggests.",
        "Freeze-thaw cycles make mornings icy. Sharpen the night before, not the week before."]),
 dict(id="bogus", name="Bogus Basin", region="ID", lat=43.7640, lon=-116.0975, mid=2040,
  ex=dict(air=-2,rh=84,snow48=4,pastMax=2,cloud=75,code=3,tmrMin=-5,tmrMax=0,tmrSnow=3),
  tag="Boise's nonprofit hill, with night skiing and fast-changing snow",
  about=["Bogus Basin is a nonprofit ski area a short drive from Boise, with lifts from about 5,800 to 7,600 feet and night skiing. Its lower elevation means many days hover near freezing.",
         "Winter inversions can trap cold air in the valley while the mountain sits in warmer sun above it. After dark, snow that softened in the afternoon refreezes quickly."],
  tips=["Near-freezing days are common. Red and violet waxes cover much of the season.",
        "Night sessions ski firmer than afternoons. Sharpen for night skiing, and wax for the colder evening temperature.",
        "Damp snow near 32°F causes suction. Brush the structure back into the base after waxing."]),
]
R_BY = {r["id"]: r for r in RESORTS}
MET_CREDIT = ('Weather data from <a href="https://api.met.no/">MET Norway</a> '
              '(<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>), adapted by us: forecasts at '
              'mid-mountain altitude, snow estimated from precipitation and temperature. MET Norway is not responsible for our recommendations.')

OSM_CREDIT = ('Resort data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> and '
              '<a href="https://openskimap.org">OpenSkiMap</a>, available under the '
              '<a href="https://opendatacommons.org/licenses/odbl/">Open Database License</a>.')
def ft(m): return f"{round(m*3.28084/10)*10:,} ft"
COUNTRY = {"US": "United States", "CA": "Canada", "MX": "Mexico"}

def ftm(m): return f"{ft(m)} ({m:,} m)"

COASTAL = {"US-WA", "US-OR", "US-CA", "US-AK"}
INTERIOR = {"US-ID", "US-UT", "US-NV", "US-MT", "US-WY", "CA-YT"}
ROCKIES = {"US-CO", "US-NM", "US-AZ", "CA-AB"}
EAST = {"US-VT", "US-NH", "US-ME", "US-NY", "US-MA", "US-CT", "US-RI", "US-PA", "US-NJ", "US-MD", "US-VA", "US-WV",
        "US-NC", "US-TN", "US-GA", "US-AL", "CA-QC", "CA-ON", "CA-NB", "CA-NS", "CA-NL", "CA-PE"}
def climate(x):
    r = x["region"]
    if r == "CA-BC": return "coastal" if x["lon"] < -121.2 else "interior"
    if r in COASTAL: return "coastal"
    if r in INTERIOR: return "interior"
    if r in ROCKIES: return "rockies"
    if r in EAST: return "east"
    if x["country"] == "MX": return "south"
    return "midwest"

CLIMATE = {
 "coastal": ("coastal snow", "Storms off the Pacific bring heavy, wet snow, and temperatures often hover near freezing, especially low on the mountain.",
   ["Humidity is usually high here. When you're between two waxes, take the warmer one for the lower mountain.",
    "Wet snow causes suction. Brushing the structure back into the base matters as much as the wax color."]),
 "interior": ("dry inland snow", "It sits far enough inland that storms drop lighter, drier snow, with cold nights and milder, sunny afternoons between storms.",
   ["After a storm, dry new snow calls for a colder wax than the temperature alone suggests.",
    "Clear nights make first-chair snow colder than the air. Plan for the colder end of the wax range in the morning."]),
 "rockies": ("high, dry Rockies snow", "High elevation and dry air mean cold, abrasive snow, strong sun, and big swings between morning and afternoon.",
   ["Cold, dry snow is abrasive. A harder, colder wax lasts longer here than a soft one.",
    "Morning groomers are firm. Keep the side edge sharp; a 2° (88°) side edge suits most skiers."]),
 "east": ("eastern snow and ice", "Frequent freeze-thaw cycles and a lot of machine-made snow make firm, icy conditions common, especially in the morning.",
   ["Edges matter more than wax on firm snow. Sharpen often; many skiers here run a 2° or 3° side edge.",
    "Machine-made snow is abrasive. Use a harder, colder wax than the temperature alone suggests."]),
 "midwest": ("cold, mostly machine-made snow", "Cold winters, modest natural snowfall and a lot of snowmaking mean firm, dry, abrasive snow on most days.",
   ["Machine-made snow wears wax quickly. Re-wax every few ski days, and pick the colder wax when you're unsure.",
    "Short runs on firm snow reward sharp edges. A quick polish with a fine stone before each day keeps them biting."]),
 "south": ("thin, sunny snow", "It's high but far south, so the snowpack is thin, the sun is strong and the snow softens quickly by afternoon.",
   ["Warm afternoons call for warm wax and extra brushing.", "Keep edges sharp for firm mornings."]),
}

def describe(x):
    """Resort-specific page text built from the resort's own numbers and its snow climate."""
    c = climate(x); label, ctext, ctips = CLIMATE[c]
    where = ", ".join(v for v in [x.get("locality"), x["regionName"]] if v)
    if x["country"] != "US": where += f", {COUNTRY[x['country']]}"
    rn = x["runs"]; n = sum(rn.values())
    lifts = f"{x['lifts']} lift" + ("s" if x["lifts"] != 1 else "")
    p1 = (f"{esc(x['name'])} is a ski area in {esc(where)} with {lifts}" + (f" and {n} mapped runs" if n else "") +
          f". Its lifts reach from about {ftm(x['base'])} to {ftm(x['summit'])}, {ft(x['vertical'])} of vertical.")
    mix = ""
    if n >= 5:
        easy, mid_, hard = rn["easy"] / n, rn["intermediate"] / n, (rn["advanced"] + rn["expert"]) / n
        if hard >= 0.4: mix = " A large share of the mapped runs are advanced or expert terrain, where sharp edges pay off."
        elif easy + mid_ >= 0.8: mix = " Most of the mapped runs are beginner and intermediate terrain."
        else: mix = " The mapped runs mix beginner, intermediate and advanced terrain."
    p2 = ctext + mix
    p3 = f"The forecast on this page is for {ftm(x['mid'])}, halfway up the mountain."
    tips = list(ctips)
    v = x["vertical"]
    if v >= 900: tips.append(f"With {ft(v)} of vertical, the top and bottom can need different waxes. Set a colder temperature under Adjust conditions for days spent up high.")
    elif v < 250: tips.append(f"With {ft(v)} of vertical, conditions are similar top to bottom, so this forecast covers the whole hill.")
    else: tips.append(f"The mid-mountain forecast here, at {ft(x['mid'])}, covers most of the terrain.")
    if x["runKm"] and x["snowmakingKm"] / x["runKm"] > 0.4:
        tips[1] = "Snowmaking covers much of the mapped terrain, so expect firm, abrasive machine-made snow, especially early season. Go one wax color colder."
    tag = f"{ft(v)} of vertical, {lifts}, {label}"
    return tag[0].upper() + tag[1:], [p1, p2, p3], tips

def example(x):
    """Plausible stand-in conditions, shown only when live weather can't load (e.g. in previews)."""
    c = climate(x)
    t0 = {"coastal": 1, "interior": -3, "rockies": -5, "east": -3, "midwest": -6, "south": 2}[c]
    air = round(t0 - 0.0055 * (x["mid"] - 1000) - max(0, x["lat"] - 45) * 0.3, 1)
    rh = {"coastal": 86, "east": 80, "midwest": 75}.get(c, 60)
    return dict(air=air, rh=rh, snow48=3, pastMax=round(air + 3, 1), cloud=50, code=2, tmrMin=round(air - 4, 1), tmrMax=round(air + 2, 1), tmrSnow=1)

RAW = json.load(open(os.path.join(SRC, "resorts-data.json"), encoding="utf-8"))
FLAG = {r["id"]: r for r in RESORTS}            # hand-written text for the 11 original resorts
ALL = []
for d in RAW:
    x = dict(d); x["short"] = d["region"].split("-", 1)[-1]
    if d["id"] in FLAG:
        f = FLAG[d["id"]]; x.update(tag=f["tag"], about=f["about"], tips=f["tips"], ex=f["ex"], flagship=True)
    else:
        x["tag"], x["about"], x["tips"] = describe(x); x["ex"] = example(x); x["flagship"] = False
    ALL.append(x)
A_BY = {x["id"]: x for x in ALL}
from passes import EPIC, IKON, PASS_INFO, SEASON as PASS_SEASON, pass_of   # Epic / Ikon membership, updated each season
for _id in list(EPIC) + list(IKON): assert _id in A_BY, "pass list names an unknown resort: " + _id
for x in ALL: x["pass"], x["passAccess"] = pass_of(x["id"])
def pass_code(x): return (x["pass"][0] + ("" if x["passAccess"] == "full" else "l")) if x["pass"] else ""
FEATURED = [A_BY[r["id"]] for r in RESORTS]
REGIONS = {}
for x in ALL:
    REGIONS.setdefault(x["region"], {"code": x["region"], "name": x["regionName"], "country": x["country"], "resorts": []})["resorts"].append(x)
def region_href(code, depth): return "../" * depth + f"regions/{code.lower()}.html"

def km_between(a, b):
    la1, la2 = math.radians(a["lat"]), math.radians(b["lat"]); dl = math.radians(b["lon"] - a["lon"])
    return 6371 * math.acos(min(1, math.sin(la1) * math.sin(la2) + math.cos(la1) * math.cos(la2) * math.cos(dl)))
def nearby(x, k=8):
    return sorted((y for y in ALL if y["id"] != x["id"]), key=lambda y: km_between(x, y))[:k]

def rd_script(data):
    return '<script type="application/json" id="resortData">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + '</script>'
def rd_resort(x):
    return {"id": x["id"], "name": x["name"], "region": x["short"], "api": x["region"], "lat": x["lat"], "lon": x["lon"], "mid": x["mid"], "ex": x["ex"], "pass": x["pass"] or ""}

def ft(m): return f"{round(m*3.28084/10)*10:,} ft"

# Wax bands for the chart (must match BANDS in tool.js)
BANDS = [
 ("Polar","#2A955C",-30,-15,150,"Swix PS Polar"),
 ("Turquoise","#119C99",-18,-10,145,"Swix PS5 Turquoise"),
 ("Blue","#2B69D4",-12,-6,140,"Swix PS6 Blue"),
 ("Violet","#7547C0",-8,-2,135,"Swix PS7 Violet"),
 ("Red","#CF3434",-4,4,130,"Swix PS8 Red"),
 ("Yellow","#E6B41E",0,10,120,"Swix PS10 Yellow"),
]
c2f = lambda c: round(c*9/5+32)
iron_f = lambda c: int(round((c*9/5+32)/5)*5)
def sgn(n): return ("−" if n < 0 else "+" if n > 0 else "") + str(abs(n))

def wax_chart():
    rows = "".join(
        f'<tr><td><span class="swatch" style="background:{col}"></span>{n}</td>'
        f'<td class="num">{c2f(lo)}° to {c2f(hi)}°F</td><td class="num">{sgn(lo)}° to {sgn(hi)}°C</td>'
        f'<td class="num">{iron_f(iron)}°F / {iron}°C</td><td>{ex}</td></tr>'
        for n,col,lo,hi,iron,ex in BANDS)
    return ('<div class="table-wrap"><table><thead><tr><th>Wax</th><th>Snow temp °F</th><th>Snow temp °C</th>'
            '<th>Iron (about)</th><th>Example</th></tr></thead><tbody>' + rows + '</tbody></table></div>')

def style_table():
    rows = [("Cruiser / learning","1°","1°","89°","Forgiving, releases easily"),
            ("All-mountain","1°","2°","89°","Sharp but forgiving; the most common setup"),
            ("Carver, hard snow","0.7°","3°","87.7°","Quick, strong grip on firm groomers"),
            ("Racer (GS / slalom)","0.5°","3°","87.5°","Instant bite; some slalom skiers use 4°"),
            ("Park","1°","1°","89°","Detuned tips and tails for rails and boxes"),
            ("Powder","1°","1°","89°","Soft snow needs float more than bite")]
    body = "".join(f'<tr><td>{a}</td><td class="num">{b}</td><td class="num">{c} ({90-float(c[:-1]):g}°)</td><td class="num">{d}</td><td>{e}</td></tr>' for a,b,c,d,e in rows)
    return ('<div class="table-wrap"><table><thead><tr><th>How you ski</th><th>Base bevel</th><th>Side bevel</th>'
            '<th>Included angle</th><th>Feel</th></tr></thead><tbody>' + body + '</tbody></table></div>')

def edge_figs():
    figs = [(1,1,"1° base, 1° side: forgiving"),(1,2,"1° base, 2° side: all-mountain"),(0.5,3,"0.5° base, 3° side: race")]
    return '<div class="figs">' + "".join(
        f'<figure><div data-edge-diagram data-base="{b}" data-side="{s}"></div><figcaption>{c}</figcaption></figure>' for b,s,c in figs) + '</div>'

AMAZON_TAG = "theskiadvisor-20"   # Amazon Associates (amazon.com)
def shop(q):
    from urllib.parse import quote_plus
    return f'<a class="shop" href="https://www.amazon.com/s?k={quote_plus(q)}&amp;tag={AMAZON_TAG}" target="_blank" rel="noopener sponsored">Shop on Amazon</a>'

def resort_links(depth):
    r = "../"*depth
    return ('<div class="related">' + "".join(f'<a href="{r}resorts/{x["id"]}.html">{x["name"]}</a>' for x in RESORTS) +
            f'<a href="{r}resorts/index.html">All {len(ALL)} resorts</a></div>')

# =====================================================================
# Guides
# =====================================================================
GUIDES = [
 dict(slug="how-to-wax-skis", title="How to Wax Skis at Home",
  desc="A step-by-step guide to hot waxing skis at home: tools, iron temperature, scraping, brushing and the mistakes that ruin a wax job.",
  card="The full hot-wax process, start to finish, with the mistakes to avoid.",
  dek="A full hot wax takes about an hour of work plus cooling time. Here's the whole process, and the mistakes that undo it.",
  related=["ski-wax-temperature-chart","how-often-to-wax-skis","ski-tuning-kit"],
  body="""
<h2>What you need</h2>
<ul>
<li><b>A waxing iron.</b> A dedicated ski iron holds a steady temperature. Clothes irons run hot and uneven, and their steam holes leave stripes.</li>
<li><b>Wax for the temperature you'll ski.</b> See the <a href="ski-wax-temperature-chart.html">wax temperature chart</a>, or use a universal wax if you only wax a few times a season.</li>
<li><b>A plastic (plexi) scraper</b> and <b>a nylon brush.</b> Brass and horsehair brushes are worth adding later.</li>
<li><b>Something to hold the ski:</b> a vise, or straps on a sturdy table. A thick rubber band holds the brakes up.</li>
</ul>
<h2>Step by step</h2>
<ol>
<li><b>Secure the ski base-up.</b> Loop a rubber band over the brake arms so they stay out of the way.</li>
<li><b>Clean the base.</b> Brush tip to tail. If the base is dirty, hot-scrape it: iron on a soft, warm wax and scrape it off while it's still warm. It pulls dirt out of the base.</li>
<li><b>Set the iron.</b> Use the temperature on the wax label. Most waxes melt between about 250°F and 300°F (120–150°C). Colder, harder waxes need more heat.</li>
<li><b>Drip the wax.</b> Hold the bar against the iron and let it drip in a line down each side of the base.</li>
<li><b>Iron it in.</b> Spread the wax in slow, steady passes from tip to tail. Keep the iron moving. The topsheet should feel warm to the touch, never hot.</li>
<li><b>Let it cool.</b> At least 30 minutes at room temperature, overnight if you can. Wax keeps soaking in and hardening as it cools.</li>
<li><b>Scrape.</b> Pull the plexi scraper tip to tail until only fine dust comes off. Clear the edges and sidewalls with the scraper's notch.</li>
<li><b>Brush.</b> Brush tip to tail until the base shines. For cold, hard wax, start with brass, then nylon. For warm wax, nylon then horsehair.</li>
</ol>
<h2>Mistakes that ruin a wax job</h2>
<ul>
<li><b>An iron that smokes the wax.</b> If you see smoke, the iron is too hot and can damage the base.</li>
<li><b>Stopping the iron in one spot.</b> It can burn or blister the base. Keep moving.</li>
<li><b>Scraping while the wax is warm.</b> You pull the wax back out of the base.</li>
<li><b>Leaving too much on.</b> Unscraped wax makes skis slow and grabby. Scrape until you're sure you're done, then scrape again.</li>
</ul>
<p>Not sure how often to do this? See <a href="how-often-to-wax-skis.html">how often to wax your skis</a>.</p>
"""),
 dict(slug="ski-wax-temperature-chart", title="Ski Wax Temperature Chart",
  desc="Ski wax temperature chart in °F and °C: which wax color to use for which snow temperature, the iron setting, and when to go warmer or colder.",
  card="Which wax color for which temperature, in °F and °C, with iron settings.",
  dek="Which wax to use for which snow temperature, in °F and °C, and the three conditions that should change your pick.",
  related=["how-to-wax-skis","race-wax-vs-training-wax","waxing-for-spring-snow"],
  body="""
<h2>The chart</h2>
[[CHART]]
<p>These ranges are typical of most brands' color systems. Ranges vary between products, so the temperature printed on your wax wins.</p>
<h2>Use snow temperature, not air temperature</h2>
<p>Snow can't be warmer than 32°F (0°C). On clear nights and mornings, the snow surface is often a few degrees colder than the air, because it radiates heat away to the sky. A snow thermometer is the best way to know. Our resort pages estimate snow temperature from the forecast at mid-mountain.</p>
<h2>Three things that change the pick</h2>
<ul>
<li><b>New snow:</b> fresh crystals are sharp and cut into soft wax. Go one color colder than the temperature alone suggests.</li>
<li><b>Man-made snow:</b> dense and abrasive. Also go one color colder, for durability.</li>
<li><b>Wet snow near freezing:</b> use warm wax and brush extra structure into the base. See <a href="waxing-for-spring-snow.html">waxing for spring snow</a>.</li>
</ul>
<h2>When two waxes overlap</h2>
<p>Pick the colder one unless the snow is wet. Harder wax lasts longer, and if the forecast is off, a slightly cold wax costs less speed than a slightly warm one.</p>
<h2>Universal wax</h2>
<p>If you wax a few times a season, an all-temperature universal wax is a sensible choice. It won't be the fastest on any given day, but it's never badly wrong.</p>
<h2>Fluoro-free</h2>
<p>Fluorinated waxes are banned in FIS racing, and major brands have moved their lines to fluoro-free formulas. Everything we recommend is fluoro-free.</p>
"""),
 dict(slug="ski-edge-angles", title="Ski Edge Angles Explained: 88° or 90°, and Why Some Tools Say 92°",
  desc="Ski edge angles explained: 88° vs 90°, why an 88° and a 92° file guide cut the same 2° edge, what base and side bevel do, and which angles to choose for how you ski.",
  card="88° or 90°? Base and side bevel, and why 88° and 92° guides cut the same edge.",
  dek="What base and side bevel do, why the same edge is called 88° on one tool and 92° on another, and which angles to pick for how you ski.",
  related=["how-to-sharpen-ski-edges","icy-and-man-made-snow","race-wax-vs-training-wax"],
  body="""
<h2>Base bevel and side bevel</h2>
<p><b>Base bevel</b> is how far the edge is lifted off the flat of the base, usually 0.5° to 1°. More base bevel means the ski rolls onto its edge more gradually.</p>
<p><b>Side bevel</b> is how far the side of the edge is filed past vertical, usually 1° to 3°. More side bevel makes a sharper, more aggressive edge that bites harder snow.</p>
[[EDGEFIGS]]
<p class="disclose">Material removed by each bevel is shaded. Angles are drawn five times their real size so you can see them.</p>
<h2>Base bevel vs side bevel: who sets which</h2>
<p class="callout"><b>The short version:</b> a shop sets your base bevel once a season, usually in the fall, with a stone grind. You keep the side bevel sharp yourself, all winter.</p>
<ul>
<li><b>Base bevel: set in the fall, by a shop.</b> A <a href="stone-grind-and-base-structure.html">stone grind</a> flattens the base, cuts fresh base structure and sets the base bevel, usually 0.5° to 1°. That angle then stays put for the season. At home, only take burrs off it with one or two light passes of a fine stone in a base guide. Never file the base edge yourself.</li>
<li><b>Side bevel: yours to maintain all winter.</b> This is the edge that wears and gets rock hits, and it's where the grip comes from. Every few ski days, and before firm or icy days, sharpen and polish it at home at the same angle the shop set. See <a href="how-to-sharpen-ski-edges.html">how to sharpen ski edges</a>.</li>
</ul>
<p>Tell the shop the angles you want when you drop the skis off in the fall, for example "1° base, 2° side". Then buy a side edge guide at that same side angle, so your sharpening at home matches their work.</p>
<h2>88° or 90°?</h2>
<p><b>A 90° edge is square: no side bevel at all.</b> The side of the edge stands straight up from the base. Very few skis are set up this way, because a square edge grips less on firm snow. <b>An 88° edge has a 2° side bevel</b>: the side is filed 2° past square, which makes the corner sharper so it bites better on hard snow. 88° is the most common setting for all-mountain skiing.</p>
<h2>88° or 92°: the same edge, labeled two ways</h2>
<p>Tool makers don't agree on how to write the angle, so the same 2° side bevel can be sold as an <b>88°</b> guide or a <b>92°</b> guide.</p>
<ul>
<li><b>Counting down from 90:</b> most European brands, such as Swix, Toko and Holmenkol, label the angle of the steel at the edge's corner. A 2° bevel makes that corner 88°.</li>
<li><b>Counting up from 90:</b> some American tool makers, such as SVST (SkiVisions), label the angle the file sits at, measured from the base on the other side. The same 2° bevel reads 92°.</li>
<li><b>Just the bevel:</b> other tools skip both and print the bevel itself: 1°, 2° or 3°.</li>
</ul>
<div class="table-wrap fit"><table><thead><tr><th>Side bevel</th><th>Counting down<br><small>most European tools</small></th><th>Counting up<br><small>some American tools</small></th></tr></thead><tbody>
<tr><td>0° (square)</td><td>90°</td><td>90°</td></tr>
<tr><td>1°</td><td>89°</td><td>91°</td></tr>
<tr><td>2°</td><td>88°</td><td>92°</td></tr>
<tr><td>3°</td><td>87°</td><td>93°</td></tr>
<tr><td>4°</td><td>86°</td><td>94°</td></tr>
</tbody></table></div>
<p>So a 92° guide is not "less sharp than square". It cuts the same edge as an 88° guide. Before you buy a guide or tell a shop what you want, check which way the tool counts, or just say the bevel: "a 2° side edge" means the same thing everywhere.</p>
<h2>What "88°" means</h2>
<p>Shops usually describe the side bevel by its angle: a 2° side bevel is called an 88° edge. The actual angle at the corner of the edge also includes the base bevel:</p>
<p><b>included angle = 90° − side bevel + base bevel</b></p>
<p>So a ski with 1° base and 2° side has an 89° included angle, even though everyone calls it an 88° edge.</p>
<h2>Which angles to choose</h2>
[[STYLETABLE]]
<h2>Changing the side bevel</h2>
<p>Going from 2° to 3° means filing away more steel, and you can't put it back. Choose an angle and stick with it, and only change it when your skiing changes.</p>
<h2>Detuning</h2>
<p>Many skiers dull the edge slightly at the tip and tail, past the contact points, so the ski doesn't hook. Racers don't detune. Park skiers detune more.</p>
"""),
 dict(slug="how-to-sharpen-ski-edges", title="How to Sharpen Ski Edges at Home",
  desc="How to sharpen ski edges at home with a side edge guide and diamond stones: tools, steps, how often, and mistakes that ruin the bevel.",
  card="Guides, diamond stones and a steady hand. Sharp edges without wrecking the bevel.",
  dek="Sharp edges grip ice and hard groomers. Here's how to sharpen them with a guide and diamond stones without wrecking the bevel.",
  related=["ski-edge-angles","icy-and-man-made-snow","ski-tuning-kit"],
  body="""
<h2>What you need</h2>
<ul>
<li><b>A side edge guide</b> at your angle (most skiers use 2°, an 88° edge). See <a href="ski-edge-angles.html">edge angles explained</a>.</li>
<li><b>Diamond stones</b> in 200, 400 and 600 grit. A coarser stone helps with rock damage.</li>
<li><b>A gummy stone</b> for deburring and detuning.</li>
<li><b>A file</b>, only if you're setting a new angle or repairing serious damage.</li>
<li><b>A vise or straps</b> and a permanent marker.</li>
</ul>
<h2>Step by step</h2>
<ol>
<li><b>Check the edges.</b> Run a fingernail along them. Burrs catch your nail. Rock hits leave hardened spots that a file skates over. Knock those down with a coarse stone first.</li>
<li><b>Mark the edge.</b> Run a marker along the side edge. After a few passes, the ink shows exactly where you're removing steel and confirms the guide is sitting flat.</li>
<li><b>Deburr the base edge.</b> One or two light passes with a fine stone in a base guide. Don't sharpen the base edge.</li>
<li><b>Sharpen the side edge.</b> Wet the stone, set it in the guide and work tip to tail in long, overlapping strokes. Go coarse to fine: 200, then 400, then 600 grit. Give each edge the same number of passes.</li>
<li><b>Deburr.</b> One light pass with a gummy stone along the base and side edge.</li>
<li><b>Detune if you need to.</b> Dull the tip and tail past the contact points if your skis hook. Racers skip this.</li>
</ol>
<h2>How often</h2>
<p>A quick polish with a fine stone every few ski days keeps edges consistent. Do a full sharpen after rock hits, or when your skis start sliding out on firm snow. On icy, eastern or man-made snow, sharpen more often.</p>
<h2>Mistakes to avoid</h2>
<ul>
<li><b>Pressing hard.</b> Let the stone do the work. Pressure rocks the guide and rounds the edge.</li>
<li><b>Uneven passes.</b> One edge sharper than the other makes the ski behave differently turning left and right.</li>
<li><b>Filing the base edge.</b> It changes the base bevel and the ski feels vague. Leave that to the shop.</li>
</ul>
"""),
 dict(slug="race-wax-vs-training-wax", title="Race Wax vs Training Wax",
  desc="Race wax vs training wax for ski racers: what each is for, the three-layer race-day wax system, fluoro-free rules, and how often to wax.",
  card="Two jobs, two waxes. How racers layer race wax and save money in training.",
  dek="Race wax is built for speed on one day. Training wax is built to survive a week of hard laps. Here's how racers use both.",
  related=["ski-wax-temperature-chart","ski-edge-angles","icy-and-man-made-snow"],
  body="""
<h2>Two different jobs</h2>
<p>Training days are about durability. Race courses are usually hard, injected or man-made snow that strips wax quickly, and you're doing many laps. Race day is about speed for a few runs. That's why racers use cheaper, tougher wax for training and save the expensive wax for races.</p>
<h2>Training wax</h2>
<ul>
<li>A fluoro-free performance wax matched to the temperature. One layer is enough.</li>
<li>Re-wax every few training days. Hard training snow wears it off fast.</li>
<li>When you're between two waxes, pick the colder, harder one.</li>
</ul>
<h2>Race-day wax, in three layers</h2>
<ol>
<li><b>Base layer:</b> a hard, cold wax ironed in, cooled and scraped. It helps the race wax last on abrasive snow. Skip it on soft, warm days.</li>
<li><b>Race wax:</b> a fluoro-free race wax matched to the snow temperature, ironed in, cooled fully, scraped and brushed. Many racers build two or three layers over the week before a race.</li>
<li><b>Top coat, race morning:</b> a fluoro-free race top coat (block, powder or liquid) in the same temperature range, applied per its instructions and corked or brushed in.</li>
</ol>
<h2>The fluoro ban</h2>
<p>Fluorinated waxes are banned in FIS racing, and races test skis for them. If your skis ever had fluoro wax, clean the base thoroughly with several hot-scrapes before racing, and check your club or league's rules.</p>
<h2>Edges on race day</h2>
<p>Give the side edge a final polish with a fine stone the night before. Most racers run a 3° side edge with 0.5° to 0.7° base. See <a href="ski-edge-angles.html">edge angles explained</a>.</p>
<p>Our resort pages have a Training day / Race day switch for racers that changes the wax plan and the tuning steps.</p>
"""),
 dict(slug="waxing-for-spring-snow", title="Waxing for Wet Spring Snow",
  desc="How to wax skis for wet spring snow and corn: warm wax, base structure, graphite for dirty snow, and timing your day.",
  card="Warm wax, extra structure and timing for wet, sticky spring days.",
  dek="Warm, wet snow grabs the base with suction. The fix is warm wax, more structure and timing your day.",
  related=["ski-wax-temperature-chart","how-to-wax-skis","how-often-to-wax-skis"],
  body="""
<h2>Why wet snow is slow</h2>
<p>When snow is at 32°F (0°C) and wet, a film of water builds between the base and the snow. The base sticks to that film like a wet glass sticks to a table. Spring snow also carries dirt and pollen that cling to the base.</p>
<h2>Wax</h2>
<ul>
<li>Use a warm (usually yellow) wax rated above freezing.</li>
<li>Two thin coats work better than one thick one.</li>
<li>For dirty late-season snow, a graphite wax helps resist dirt.</li>
</ul>
<h2>Structure</h2>
<p>Base structure is the fine pattern a shop grinds into the base. It channels water away and breaks the suction. Brush hard after waxing to open it back up. Skiers who ski a lot of spring snow sometimes ask the shop for a coarser, warm-snow structure.</p>
<h2>Time your day</h2>
<p>Spring snow freezes overnight and softens as the sun hits it. Mornings are firm and need sharp edges. Mid-morning corn is the best skiing of the day. Afternoons get slushy. Wax for the afternoon, and keep edges sharp for the morning.</p>
<h2>Touch-ups</h2>
<p>A rub-on or paste wax in your pocket helps when your skis start to grab in the afternoon.</p>
"""),
 dict(slug="icy-and-man-made-snow", title="Tuning for Ice and Man-Made Snow",
  desc="How to tune skis for icy and man-made snow: sharper side edges, how often to sharpen, and why you need a harder wax on machine-made snow.",
  card="Sharper edges, harder wax and more frequent tunes for hard snow.",
  dek="On hard, icy and machine-made snow, sharp edges do most of the work, and your wax needs to get harder too.",
  related=["how-to-sharpen-ski-edges","ski-edge-angles","ski-wax-temperature-chart"],
  body="""
<h2>What makes it different</h2>
<p>Man-made snow has small, dense, rounded grains. Packed down, it turns hard and icy, and it's abrasive on bases and edges. Freeze-thaw cycles make natural snow icy too, which is why eastern skiing is so hard on skis.</p>
<h2>Edges</h2>
<ul>
<li>A 2° side edge (88°) is the minimum for regular ice. Strong skiers often run 3° (87°).</li>
<li>Sharpen often. A quick polish with a fine stone before each ski day makes a real difference.</li>
<li>Deburr after every sharpen, and fix rock hits quickly.</li>
</ul>
<h2>Wax</h2>
<ul>
<li>Go one color colder (harder) than the temperature alone suggests. Soft wax wears off quickly on abrasive snow.</li>
<li>Re-wax more often. On man-made snow, the base dries out in a few days.</li>
<li>A hard base-layer wax under your regular wax improves durability.</li>
</ul>
<p>Our resort pages automatically suggest sharper edges and harder wax when the forecast points to firm, refrozen or man-made snow.</p>
"""),
 dict(slug="how-often-to-wax-skis", title="How Often Should You Wax Your Skis?",
  desc="How often to wax skis: a rule of thumb by ski days, signs your base is dry, how snow type changes it, and how to store skis for summer.",
  card="A rule of thumb by ski days, and the signs your base is dry.",
  dek="Most recreational skiers should wax every few ski days. Here's how to tell when your base is dry.",
  related=["how-to-wax-skis","ski-tuning-kit","ski-wax-temperature-chart"],
  body="""
<h2>The rule of thumb</h2>
<p>Most recreational skiers should wax every three to five ski days. Wax more often on man-made or icy snow, which is abrasive, and on very cold snow. Racers wax for every race and every few training days.</p>
<h2>Signs your base is dry</h2>
<ul>
<li>White, chalky or fuzzy-looking patches, usually near the edges and underfoot.</li>
<li>The skis feel slow on flat traverses or stick in wet snow.</li>
<li>The base looks dull even after brushing.</li>
</ul>
<h2>Edges on a different schedule</h2>
<p>Edges don't need a full sharpen every time you wax. A quick polish with a fine stone keeps them consistent between full tunes. See <a href="how-to-sharpen-ski-edges.html">how to sharpen ski edges</a>.</p>
<h2>New skis</h2>
<p>New skis usually come with a factory wax that wears off quickly. A hot wax before the first day is a good habit.</p>
<h2>Summer storage</h2>
<p>At the end of the season, iron on a thick coat of soft wax and don't scrape it. It protects the base and edges from drying and rust. Store skis somewhere cool and dry, then scrape and brush before your first day.</p>
"""),
 dict(slug="ski-tuning-kit", title="Home Ski Tuning Kit: What to Buy First",
  desc="What to buy for a home ski tuning kit, in the order you'll need it: waxing tools first, then edge tools, then the extras.",
  card="Start with five tools and add the rest as you go. Here's the order.",
  dek="You can start with five tools and add the rest as you go. Here's the order to buy them in.",
  related=["how-to-wax-skis","how-to-sharpen-ski-edges","ski-edge-angles"],
  body="""
<p class="disclose">As an Amazon Associate, The Ski Advisor earns from qualifying purchases. Commissions don't change what we recommend.</p>
<h2>Start here: waxing</h2>
<ul>
<li><b>Waxing iron:</b> a dedicated ski iron with a steady temperature. [[SHOP:ski waxing iron]]</li>
<li><b>Universal wax:</b> works across temperatures while you learn. [[SHOP:Swix universal ski wax]]</li>
<li><b>Plexi scraper:</b> removes excess wax without hurting the base. [[SHOP:ski wax scraper]]</li>
<li><b>Nylon brush:</b> opens the base structure after scraping. [[SHOP:ski wax brush]]</li>
<li><b>Ski straps or a vise:</b> hold the ski steady, base-up. [[SHOP:ski tuning vise]]</li>
</ul>
<h2>Next: edges</h2>
<ul>
<li><b>Side edge guide:</b> at your angle, usually 2° (88°). [[SHOP:side edge guide ski]]</li>
<li><b>Diamond stones:</b> 200, 400 and 600 grit. [[SHOP:diamond stone ski edge]]</li>
<li><b>Gummy stone:</b> for deburring and detuning. [[SHOP:gummy stone ski]]</li>
</ul>
<h2>Later: the extras</h2>
<ul>
<li><b>Temperature-specific waxes</b> once you know your conditions. See the <a href="ski-wax-temperature-chart.html">wax chart</a>. [[SHOP:Swix ski wax]]</li>
<li><b>Brass and horsehair brushes</b> for cold and warm wax. [[SHOP:horsehair ski brush]]</li>
<li><b>Base edge guide</b> for deburring the base edge. [[SHOP:base bevel guide]]</li>
<li><b>P-tex candles</b> for small base repairs. [[SHOP:p-tex candle]]</li>
<li><b>A polishing pad</b> for the final buff. [[SHOP:fibertex ski]]</li>
</ul>
"""),
]
from guides_extra import EXTRA, SNOWBOARD_GUIDE, XC_GUIDE, GRIND_GUIDE   # longer guide sections + the snowboard, cross-country and stone grind guides
for _g in GUIDES: _g["body"] += EXTRA.get(_g["slug"], "")
GUIDES.insert(1, SNOWBOARD_GUIDE)
GUIDES.insert(2, XC_GUIDE)
GUIDES.insert(GUIDES.index(next(g for g in GUIDES if g["slug"] == "how-to-sharpen-ski-edges")) + 1, GRIND_GUIDE)
from guides_buy import BUY_GUIDES   # buying guides (iron, $100 kit, race wax)
GUIDES.extend(BUY_GUIDES)
G_BY = {g["slug"]: g for g in GUIDES}

def guide_body(g):
    b = g["body"].replace("[[CHART]]", wax_chart()).replace("[[STYLETABLE]]", style_table()).replace("[[EDGEFIGS]]", edge_figs())
    return re.sub(r"\[\[SHOP:(.*?)\]\]", lambda m: shop(m.group(1)), b)

def read_minutes(h):
    words = len(re.sub(r"<[^>]+>", " ", h).split())
    return max(2, math.ceil(words/220))

# =====================================================================
# Page chrome
# =====================================================================
DIAMOND = '<svg width="24" height="24" viewBox="0 0 26 26" aria-hidden="true"><rect x="13" y="1.5" width="16" height="16" rx="1.5" transform="rotate(45 13 1.5)" fill="currentColor"/></svg>'

def head(title, desc, path, depth, jsonld=None, noindex=False):
    r = "../"*depth
    url = DOMAIN + "/" + path
    out = [f"<title>{esc(title)}</title>",
           '<meta name="claude:viewport-fit-sides" content="cover">',
           f'<meta name="description" content="{esc(desc)}">',
           f'<link rel="canonical" href="{url}">',
           '<meta property="og:type" content="website">',
           f'<meta property="og:site_name" content="The Ski Advisor">',
           f'<meta property="og:title" content="{esc(title)}">',
           f'<meta property="og:description" content="{esc(desc)}">',
           f'<meta property="og:url" content="{url}">',
           f'<meta property="og:image" content="{DOMAIN}/assets/og-image.jpg">',
           '<meta property="og:image:width" content="1200">',
           '<meta property="og:image:height" content="630">',
           '<meta name="twitter:card" content="summary_large_image">',
           '<meta name="theme-color" content="#00174B">',
           '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
           '<link rel="icon" href="/favicon-48.png" sizes="48x48" type="image/png">',
           '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
           FONTS + (FONT_SERIF if path == "" or (path.startswith("resorts/") and path != "resorts/index.html") else ""),
           '<style>' + SITE_CSS + '</style>']
    if noindex:
        out.append('<meta name="robots" content="noindex">')
    if CF_ANALYTICS_TOKEN:
        out.append('<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" '
                   'data-cf-beacon=\'{"token": "' + CF_ANALYTICS_TOKEN + '"}\'></script>')
    if jsonld:
        out.append('<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False) + '</script>')
    return "\n".join(out)

ICON_SNOW = '''<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><g stroke="#286FEC" stroke-width="2" stroke-linecap="round" fill="none"><path d="M12 2v20M3.3 7l17.4 10M20.7 7 3.3 17"/><path d="M9 4l3 2 3-2M9 20l3-2 3 2M4.2 10.5l3.4-.3-1.3-3.2M19.8 13.5l-3.4.3 1.3 3.2M4.2 13.5l3.4.3-1.3 3.2M19.8 10.5l-3.4-.3 1.3-3.2"/></g></svg>'''
ICON_PIN = '''<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="10" r="2.6" fill="currentColor"/></svg>'''
ICON_THERMO = '''<svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true"><path d="M10 13.5V5a2 2 0 1 1 4 0v8.5a4 4 0 1 1-4 0z" fill="none" stroke="#FFFFFF" stroke-width="2"/><circle cx="12" cy="17" r="1.8" fill="#FFFFFF"/></svg>'''
ICON_WAX = '''<svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true"><defs>
<linearGradient id="twxa" x1="10" y1="20" x2="70" y2="90" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#93C5FD"/><stop offset=".5" stop-color="#3B82F6"/><stop offset="1" stop-color="#1E3A8A"/></linearGradient>
<linearGradient id="twxb" x1="20" y1="14" x2="60" y2="40" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".75"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient></defs>
<path d="M18 38 L58 24 L80 34 L40 48 Z" fill="#1D4ED8" opacity=".2" transform="translate(4,6)"/>
<path d="M14 34 L54 20 L78 30 L38 44 Z" fill="#BFDBFE"/><path d="M14 34 L38 44 L38 76 L14 66 Z" fill="url(#twxa)"/><path d="M38 44 L78 30 L78 62 L38 76 Z" fill="#2563EB"/>
<path d="M18 36 L52 24 L70 31 L38 42 Z" fill="url(#twxb)"/></svg>'''

def header(depth, current="", chips=""):
    """Floating white pill navigation (Buildify theme)."""
    r = "../"*depth
    cur = lambda k: ' aria-current="page"' if current == k else ""
    links = (f'<a href="{r}resorts/index.html"{cur("resorts")}>Resorts</a><a href="{r}guides/index.html"{cur("guides")}>Guides</a>'
             f'<a href="{r}about.html">About</a><a href="{r}contact.html">Contact</a>')
    cta = f'<a class="btn" href="{r}resorts/index.html">Find your mountain</a>'
    burger = '<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
    chiprow = f'<div class="wrap t-chiprow">{chips}</div>' if chips else ""
    return f"""<header class="t-nav">
  <div class="t-pill">
    <a class="brand t-logo" href="{r}index.html" aria-label="The Ski Advisor home"><img src="{r}assets/logo-navy.webp" alt="The Ski Advisor" width="82" height="44"></a>
    <nav class="t-links" aria-label="Site">{links}</nav>
    <div class="t-right">{cta}<button type="button" class="t-burger" aria-label="Open menu" aria-expanded="false" aria-controls="tMenu">{burger}</button></div>
  </div>
  <nav class="t-menu" id="tMenu" aria-label="Menu" hidden>{links}<hr>{cta}</nav>
</header>{chiprow}"""

def footer(depth):
    """White footer (Buildify theme)."""
    r = "../"*depth
    res = "".join(f'<li><a href="{r}resorts/{x["id"]}.html">{x["name"]}</a></li>' for x in RESORTS[:8])
    res += f'<li><a href="{r}resorts/index.html">All {len(ALL)} resorts</a></li>'
    gds = "".join(f'<li><a href="{r}guides/{g["slug"]}.html">{g["title"]}</a></li>' for g in GUIDES[:8])
    gds += f'<li><a href="{r}guides/index.html">All guides</a></li>'
    site = (f'<li><a href="{r}about.html">About</a></li><li><a href="{r}contact.html">Contact</a></li><li><a href="{r}privacy.html">Privacy</a></li>'
            f'<li><a href="{r}passes/epic.html">Epic Pass mountains</a></li><li><a href="{r}passes/ikon.html">Ikon Pass mountains</a></li>')
    return f"""<footer class="site-foot t-foot">
  <div class="wrap" style="padding-block:56px 24px">
    <div class="t-foot-grid">
      <div class="t-foot-brand"><img src="{r}assets/logo-navy.webp" alt="The Ski Advisor" width="104" height="56"><p>Wax and edge recommendations for {len(ALL)} ski areas in the US, Canada and Mexico, from the forecast at each one's mid-mountain elevation.</p></div>
      <div><h3>Popular resorts</h3><ul>{res}</ul></div>
      <div><h3>Guides</h3><ul>{gds}</ul></div>
      <div><h3>The Ski Advisor</h3><ul>{site}</ul></div>
    </div>
    <div class="t-credits"><p>{MET_CREDIT}</p><p>{OSM_CREDIT}</p><p>As an Amazon Associate, The Ski Advisor earns from qualifying purchases. Commissions don't change what we recommend. The temperature on your wax label wins, and a snow thermometer beats any forecast.</p></div>
    <p class="t-copy">© 2026 The Ski Advisor</p>
  </div>
</footer>"""

def search_box(depth, prefix, sid):
    return f"""<form class="search" data-search data-index="{"../"*depth}assets/resort-index.json" data-prefix="{prefix}" role="search">
      <label class="sr" for="{sid}">Find a ski resort</label>
      <div class="search-row">
        <input id="{sid}" type="search" autocomplete="off" placeholder="Search {len(ALL)} ski resorts by name, town or state">
        <button type="button" class="near-btn" data-near>Near me</button>
      </div>
      <div class="pass-row" role="group" aria-label="Filter by season pass"><span>Pass</span><button type="button" class="chip" data-passpick="" aria-pressed="true">Any</button><button type="button" class="chip" data-passpick="epic" aria-pressed="false">Epic</button><button type="button" class="chip" data-passpick="ikon" aria-pressed="false">Ikon</button></div>
      <ul hidden></ul>
      <p class="near-msg muted" hidden></p>
    </form>"""

def pass_tag(x, long=False):
    if not x["pass"]: return ""
    name = PASS_INFO[x["pass"]]["name"] if long else x["pass"].capitalize()
    return f'<span class="pass-tag {x["pass"]}">{name}{"" if x["passAccess"] == "full" else " · limited"}</span>'

def report_box(depth, x=None):
    """Weekend Wax Report signup (Netlify Forms). Every copy has the same fields so Netlify sees one form."""
    r = "../"*depth
    who = f"{esc(x['name'])} and the mountains you save" if x else "the mountains you save"
    return f"""<section class="report" aria-labelledby="reportH">
    <div class="report-copy">
      <h2 id="reportH">The Weekend Wax Report</h2>
      <p>A free email, launching this season. Every Thursday in ski season: this weekend's wax and iron temperature for {who}, in time to wax before you leave. Sign up now and you'll get the first one.</p>
    </div>
    <form class="report-form" name="wax-report" method="POST" action="/report-thanks.html" data-netlify="true" netlify-honeypot="company" data-report>
      <input type="hidden" name="form-name" value="wax-report">
      <input type="hidden" name="resort" value="{x['id'] if x else ''}">
      <input type="hidden" name="mountains" value="">
      <p class="hp" hidden><label>Leave this empty <input name="company" tabindex="-1" autocomplete="off"></label></p>
      <label class="sr" for="reportEmail">Email address</label>
      <div class="report-row"><input id="reportEmail" name="email" type="email" autocomplete="email" placeholder="you@example.com" required><button class="btn" type="submit">Sign me up</button></div>
      <p class="muted small">From The Ski Advisor. Free; unsubscribe from any email in one click. We use your address only to send this report. See our <a href="{r}privacy.html">privacy policy</a>.</p>
      <p class="report-msg" role="status" hidden></p>
    </form>
  </section>"""

def region_grid(depth):
    out = []
    for cc in ("US", "CA", "MX"):
        regs = sorted((g for g in REGIONS.values() if g["country"] == cc), key=lambda g: g["name"])
        if not regs: continue
        items = "".join(f'<a href="{region_href(g["code"], depth)}">{esc(g["name"])}<small>{len(g["resorts"])}</small></a>' for g in regs)
        out.append(f'<h3>{COUNTRY[cc]}</h3><div class="region-list">{items}</div>')
    return "\n".join(out)

def page_info(page, resort=""):
    return f'<div id="pageInfo" data-page="{page}" data-resort="{resort}" hidden></div>'

def doc(full, headhtml, body):
    if not full:
        return headhtml + "\n" + body + "\n"
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            + headhtml + "\n</head>\n<body>\n" + body + "\n</body>\n</html>\n")

def crumbs(depth, items):
    r = "../"*depth
    parts = [f'<a href="{r}index.html">Home</a>']
    for label, href in items:
        parts.append('<span aria-hidden="true">›</span>')
        parts.append(f'<a href="{href}">{label}</a>' if href else f'<span>{label}</span>')
    return '<nav class="crumbs" aria-label="Breadcrumb">' + "".join(parts) + '</nav>'

def bc_ld(items):
    return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":i+1,"name":n,"item":DOMAIN+"/"+u} for i,(n,u) in enumerate(items)]}

# =====================================================================
# Pages
# =====================================================================
SIL = """<svg class="sil" viewBox="0 0 1200 600" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
  <polygon points="0,420 140,330 260,370 400,250 520,320 640,170 760,290 880,230 1010,320 1200,260 1200,600 0,600" fill="var(--hero-m1)"/>
  <polygon points="560,250 640,170 720,250 690,240 660,262 630,238 600,258" fill="#F2F6FA"/>
  <polygon points="0,500 180,420 330,470 470,380 620,450 780,360 940,440 1080,390 1200,430 1200,600 0,600" fill="var(--hero-m2)"/>
  <polygon points="0,560 220,510 420,550 640,490 860,545 1040,500 1200,530 1200,600 0,600" fill="var(--hero-m3)"/>
</svg>"""

def mtn_art(seed):
    """Seeded mountain ridges for a resort card (no photos needed)."""
    import random, hashlib
    rnd = random.Random(int(hashlib.md5(seed.encode()).hexdigest()[:8], 16))
    W, H = 400, 200
    def ridge(base, amp, n):
        pts = [(0, base - rnd.uniform(0, amp * .3))]
        for i in range(1, n):
            x = W * i / n + rnd.uniform(-W / n * .22, W / n * .22)
            pts.append((x, base - amp * (rnd.uniform(.6, 1) if i % 2 else rnd.uniform(.08, .35))))
        pts.append((W, base - rnd.uniform(0, amp * .3)))
        return " ".join(f"{x:.0f},{y:.0f}" for x, y in pts) + f" {W},{H} 0,{H}"
    return (f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" aria-hidden="true">'
            f'<polygon points="{ridge(118, 64, rnd.choice([6, 7, 8]))}" fill="#C9DAF6"/>'
            f'<polygon points="{ridge(150, 70, rnd.choice([4, 5, 6]))}" fill="#E8F0FC"/>'
            f'<polygon points="{ridge(196, 44, rnd.choice([3, 4]))}" fill="#FFFFFF"/></svg>')

# Home hero: layered mountain ridges in front of the navy-to-blue sky (brand colors from the logo).
HERO_MTNS = """<svg class="hero-mtns" viewBox="0 0 1440 360" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
  <path fill="#B9CCEE" d="M0 360V212L120 150L230 192L360 95L470 162L590 122L720 40L850 140L960 100L1080 172L1210 80L1330 150L1440 112V360Z"/>
  <path fill="#FFFFFF" d="M684 83L720 40L756 86L739 79L722 94L705 77ZM330 130L360 95L392 133L374 126L360 139L346 125ZM1180 115L1210 80L1242 118L1225 111L1210 124L1196 111Z"/>
  <path fill="#4F78C8" d="M0 360V262L150 200L280 252L420 168L560 240L700 150L830 232L980 180L1120 252L1260 188L1440 244V360Z"/>
  <path fill="#18377A" d="M0 360V300L180 252L330 292L520 238L690 296L860 250L1030 298L1220 246L1440 290V360Z"/>
  <path fill="#FFFFFF" d="M0 360V330C200 312 380 324 560 318C740 312 900 330 1080 322C1240 315 1340 326 1440 320V360Z"/>
</svg>"""

def hero_search():
    chips = ''.join(f'<button type="button" class="chip" data-passpick="{k}" aria-pressed="{"true" if not k else "false"}">{n}</button>' for k, n in (("", "Any"), ("epic", "Epic"), ("ikon", "Ikon")))
    return f"""<form class="search t-ask" data-search data-index="assets/resort-index.json" data-prefix="resorts/" role="search">
      <div class="t-ask-in">{ICON_SNOW}<label class="sr" for="homeSearch">Find a ski resort</label><input id="homeSearch" type="search" autocomplete="off" placeholder="Search by resort, town or state"></div>
      <div class="t-ask-bar">
        <div class="pass-row" role="group" aria-label="Filter by season pass"><span>Pass</span>{chips}</div>
        <div class="t-ask-act"><button type="button" class="near-btn t-near" data-near>{ICON_PIN}<span>Near me</span></button><button type="submit" class="btn">Find my wax</button></div>
      </div>
      <ul hidden></ul>
      <p class="near-msg muted" hidden></p>
    </form>"""

FAQ = [
 ("Is The Ski Advisor free?", "Yes. There's no account and no app. Your saved mountains, your style and your wax log stay in your own browser. The site earns a small commission when you buy through its Amazon links."),
 ("How do you pick the wax?", "We take the forecast at your resort's mid-mountain elevation, estimate the snow temperature and surface, and match it to the standard wax color bands. New and man-made snow get one step colder; wet snow gets a warm wax and extra brushing."),
 ("Does it work for snowboards?", "Yes. Choose Snowboard and the tune steps, edge settings and kit switch to board wording. The wax is the same."),
 ("Should I change my edge angles for the conditions?", "No. Most people set their angles once, usually at a shop, and keep them. The snow changes how much edge work is worth doing, not the angles."),
 ("Where does the weather come from?", "MET Norway's forecast, refreshed for every resort every six hours. US resort pages also show the National Weather Service's 7-day forecast. Resort locations and elevations come from OpenStreetMap."),
 ("Are the waxes fluoro-free?", "Yes. Every wax we suggest is fluoro-free, including race waxes and top coats."),
]

def home(full):
    """Home page in the Buildify theme's landing layout, with the site's real content."""
    cards = "".join(f"""<a class="resort-card t-card" href="resorts/{x['id']}.html">
  <div class="t-art">{mtn_art(x['id'])}</div>
  <div class="t-card-b"><h3>{x['name']}</h3><p>{x['regionName']}, mid-mountain {ft(x['mid'])}</p></div>
  <span class="wax-chip" data-home-wax="{x['id']}"><i></i><span>Loading today's wax…</span></span>
</a>""" for x in FEATURED)
    gcards = "".join(f'<a class="guide-card" href="guides/{g["slug"]}.html"><small>{guide_kind(g)}{read_minutes(guide_body(g))} min read</small><b>{g["title"]}</b><span>{g["card"]}</span></a>' for g in GUIDES)
    steps = [("Forecast at mid-mountain", "We pull temperature, humidity and new snow at the elevation you'll actually ski, not at the base."),
             ("Snow, not air", "We estimate the snow temperature and surface: new, packed, refrozen, man-made or wet."),
             ("Wax, edges, steps", "You get the wax color and iron setting for the snow, edge settings for how you ski or ride, and a tune walkthrough set to match.")]
    steps_html = "".join(f'<div class="t-step"><span class="t-step-l">Step - {i+1:02d}</span><div><h3>{t}</h3><p>{d}</p></div><span class="t-step-n" aria-hidden="true">{i+1}</span></div>' for i, (t, d) in enumerate(steps))
    faq_html = "".join(f'<details class="t-q"{" open" if i == 0 else ""}><summary>{q}<span class="t-plus" aria-hidden="true"></span></summary><p>{a}</p></details>' for i, (q, a) in enumerate(FAQ))
    ld = {"@context":"https://schema.org","@type":"WebSite","name":"The Ski Advisor","url":DOMAIN+"/"}
    h = head("The Ski Advisor: Ski and Snowboard Wax for Today's Snow",
             f"Ski and snowboard wax color and iron temperature for today's snow at {len(ALL)} resorts across the US, Canada and Mexico, edge settings for how you ski or ride, and step-by-step home tuning guides.",
             "", 0, ld)
    body = f"""{page_info("home")}
{rd_script({"api": "featured", "resorts": [rd_resort(x) for x in FEATURED]})}
{header(0)}
<section class="t-hero t-hero-mtn" aria-labelledby="heroH">
  {HERO_MTNS}
  <div class="t-hero-in">
    <p class="t-tag">{ICON_SNOW}<span class="t-serif">Free wax &amp; tune advice for <span class="t-blue">{len(ALL)} ski areas</span></span></p>
    <h1 id="heroH">Today's ski wax<br>for your mountain</h1>
    <p class="t-motto t-serif">Your mountain. Your snow. Your skis.</p>
    <p class="t-hero-p">Pick your mountain and get the wax color and iron temperature for today, tomorrow or this weekend, plus edge settings and a step-by-step home tune. Free, no sign-up.</p>
    {hero_search()}
    <div class="hero-live"><span class="hero-live-l">Right now:</span>{"".join(f'<a href="resorts/{i}.html"><b>{A_BY[i]["name"].split(" ")[0]}</b><span class="wax-chip" data-home-wax="{i}"><i></i><span>Loading…</span></span></a>' for i in ("vail", "whistler", "killington"))}</div>
  </div>
</section>
<main>
  <section class="t-sec wrap" aria-labelledby="featH">
    <h2 class="t-h2" id="featH">Built for the snow <span class="t-serif">you'll ski</span></h2>
    <div class="t-bento">
      <div class="t-b t-b1"><p class="t-stat">{len(ALL)}</p><div><p class="t-bt">Ski areas covered</p><p class="t-bd">Every operating ski area with a lift in the US, Canada and Mexico, each forecast at its own mid-mountain elevation.</p></div></div>
      <div class="t-b t-b2">{ICON_THERMO}<div><p class="t-bt">Snow, not air</p><p class="t-bd">We estimate the snow temperature and surface, then pick the wax for that snow.</p></div></div>
      <div class="t-b t-b3"><p class="t-stat t-white">Every 6 hours</p><div><p class="t-bt">Today, tomorrow or the weekend</p><div class="t-b3-row"><p class="t-bd">Each resort's forecast refreshes every six hours, with Saturday and Sunday side by side for weekend trips.</p><a class="btn" href="#resorts">Find your mountain</a></div></div></div>
      <div class="t-b t-b4">{ICON_WAX}<div><p class="t-big">Free</p><p class="t-bd">No account and no app. Your mountains, style and wax log stay on your device.</p></div></div>
    </div>
  </section>
  <section class="t-sec wrap" id="resorts" aria-labelledby="resortsH">
    <h2 class="t-h2" id="resortsH">Popular <span class="t-serif">mountains</span></h2>
    <p class="t-sub" id="homeDataNote">Today's wax pick for each resort, from the forecast at mid-mountain.</p>
    <div id="myMtns" hidden>
      <h3 class="t-h3">My mountains</h3>
      <p class="muted">Saved on this device. Save or remove a resort from its page.</p>
      <div class="resort-grid" id="myMtnsGrid"></div>
    </div>
    <div class="t-grid">{cards}</div>
    <p class="t-center"><a class="btn" href="resorts/index.html">See all {len(ALL)} resorts</a></p>
  </section>
  <section class="t-sec wrap" aria-labelledby="howH">
    <h2 class="t-h2" id="howH">How it works</h2>
    <div class="t-steps">{steps_html}</div>
  </section>
  <section class="t-sec wrap" aria-labelledby="browseH">
    <h2 class="t-h2" id="browseH">Browse by <span class="t-serif">state or province</span></h2>
    {region_grid(0)}
  </section>
  <section class="t-sec wrap" aria-labelledby="guidesH">
    <h2 class="t-h2" id="guidesH">Tuning <span class="t-serif">guides</span></h2>
    <p class="t-sub">Everything you need to tune skis or a snowboard at home, from your first wax job to race day.</p>
    <div class="guide-grid">{gcards}</div>
  </section>
  <section class="t-sec wrap" aria-labelledby="faqH">
    <h2 class="t-h2" id="faqH">Got questions? <span class="t-serif">We've got answers</span></h2>
    <div class="t-faq">{faq_html}</div>
  </section>
</main>
<div class="t-cta-wrap">{report_box(0)}</div>
{footer(0)}
<script src="assets/tool.js"></script>"""
    return doc(full, h, body)

TOOL_FRAG = open(os.path.join(SRC, "tool-fragment.html")).read()

def resort_page(x):
    firm = climate(x) in ("east", "midwest", "rockies")
    others = ["ski-wax-temperature-chart", "ski-edge-angles", "how-to-wax-skis", "icy-and-man-made-snow" if firm else "waxing-for-spring-snow", "race-wax-vs-training-wax"]
    near = nearby(x, 8)
    chips = ('\n    <nav class="chips" aria-label="Nearby resorts">' +
             f'<a class="chip" href="{x["id"]}.html" aria-current="page">{esc(x["name"])}<small>{x["short"]}</small></a>' +
             "".join(f'<a class="chip" href="{n["id"]}.html">{esc(n["name"])}<small>{n["short"]}</small></a>' for n in near) +
             f'<a class="chip" href="{region_href(x["region"], 1)}">All of {esc(x["regionName"])}</a></nav>')
    rel = "".join(f'<a href="../guides/{s}.html">{G_BY[s]["title"]}</a>' for s in others)
    about = "".join(f"<p>{p}</p>" for p in x["about"])
    tips = "".join(f"<li>{t}</li>" for t in x["tips"])
    name = esc(x["name"])
    pass_line = ""
    if x["pass"]:
        pi = PASS_INFO[x["pass"]]
        pass_line = (f'\n    <p class="pass-line"><span class="pass-tag {x["pass"]}">{pi["name"]}</span> On the {PASS_SEASON} pass' +
                     ("" if x["passAccess"] == "full" else f' as a {pi["limited"]}') +
                     f'. <a href="../passes/{x["pass"]}.html">See all {pi["name"]} mountains</a></p>')
    if x["country"] == "US":   # US pages also carry the National Weather Service 7-day forecast
        title = f"{x['name']} Ski & Snowboard Wax and 7-Day Snow Forecast"
        desc = f"Which ski or snowboard wax to use at {x['name']}, {x['regionName']}, today, tomorrow or this weekend, from the forecast at mid-mountain ({ft(x['mid'])}), plus the 7-day snow forecast. Edge settings and a step-by-step home tune too."
    else:
        title = f"{x['name']} Ski & Snowboard Wax: Today's Pick and Home Tune"
        desc = f"Which ski or snowboard wax to use at {x['name']}, {x['regionName']}, today, tomorrow or this weekend, from the forecast at mid-mountain ({ft(x['mid'])}). Plus edge settings and a step-by-step home tune."
    place = {"@context": "https://schema.org", "@type": "SkiResort", "name": x["name"],
             "mainEntityOfPage": f"{DOMAIN}/resorts/{x['id']}.html",
             "geo": {"@type": "GeoCoordinates", "latitude": x["lat"], "longitude": x["lon"], "elevation": x["summit"]},
             "address": {"@type": "PostalAddress", "addressRegion": x["regionName"], "addressCountry": x["country"],
                         **({"addressLocality": x["locality"]} if x.get("locality") else {})}}
    if x.get("website"): place["sameAs"] = [x["website"]]
    ld = [bc_ld([("Home",""),("Resorts","resorts/index.html"),(x["regionName"], f"regions/{x['region'].lower()}.html"),(x["name"],f"resorts/{x['id']}.html")]), place]
    body = f"""{page_info("resort", x["id"])}
{rd_script({"api": x["region"], "resorts": [rd_resort(x)]})}
{header(1, "resorts", chips)}
<main class="wrap">
  {crumbs(1, [("Resorts","index.html"),(esc(x["regionName"]), region_href(x["region"], 1)),(name,None)])}
  <div class="hero">
    <h1><span class="h1-pre">Wax and tune for</span> {name}</h1>
    <p class="lede">{x['tag']}. Wax color and iron temperature from the forecast at mid-mountain, edge settings for how you ski or ride, and a step-by-step home tune.</p>{pass_line}
    <div class="hero-sub">
      <div class="fc-pick">
        <span class="fc-lead" aria-hidden="true">Forecast<svg width="22" height="14" viewBox="0 0 22 14"><path d="M1 7h17M13 1.5L19.5 7 13 12.5" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
        <div class="seg" role="group" aria-label="Forecast: when are you skiing?">
          <button type="button" id="dayToday" aria-pressed="true">Today</button>
          <button type="button" id="dayTomorrow" aria-pressed="false">Tomorrow</button>
          <button type="button" id="dayWeekend" aria-pressed="false">This weekend</button>
        </div>
      </div>
      <div class="seg" role="group" aria-label="Units">
        <button type="button" id="unitF" aria-pressed="true">°F / in</button>
        <button type="button" id="unitC" aria-pressed="false">°C / cm</button>
      </div>
      <span class="badge" id="sourceBadge"><i></i><span id="sourceText">Loading conditions…</span></span>
      <button type="button" class="fav-btn" id="favBtn" aria-pressed="false" hidden><svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.2l-5.7 3.1 1.2-6.4L2.8 9.5l6.4-.8z" fill="currentColor"/></svg><span>Save to My mountains</span></button>
      <button type="button" class="fav-btn" id="shareBtn" hidden><svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Share this wax</span></button>
    </div>
  </div>
{TOOL_FRAG}
  {report_box(1, x)}
  <section class="block" aria-labelledby="aboutH">
    <div class="about">
      <div class="prose"><h2 id="aboutH">Skiing {name}'s snow</h2>{about}</div>
      <div class="card"><h3>Tuning tips for {name}</h3><ul class="tips">{tips}</ul></div>
    </div>
  </section>
  <section class="block" aria-labelledby="relH">
    <div class="section-head"><h2 id="relH">Related guides</h2></div>
    <div class="related">{rel}</div>
  </section>
  <div class="notes">
    <p id="dataNote">Weather from MET Norway's forecast at {name}'s mid-mountain elevation.</p>
    <p>Snow temperature is estimated from air temperature and sky cover. A snow thermometer reading is better. Wax ranges vary by brand, so the temperature on the wax label wins. All waxes suggested here are fluoro-free.</p>
    <p>Base bevels are usually set by a shop's stone grind. If your skis are new or freshly ground, ask the shop what they set before you change anything.</p>
  </div>
</main>
{footer(1)}
<script src="../assets/tool.js"></script>"""
    return doc(True, head(title, desc, f"resorts/{x['id']}.html", 1, ld), body)

def pass_filter(rs):
    ne = sum(1 for x in rs if x["pass"] == "epic"); ni = sum(1 for x in rs if x["pass"] == "ikon")
    if not ne and not ni: return ""
    b = lambda k, label, n: f'<button type="button" class="chip" data-passpick="{k}" aria-pressed="{str(k == "").lower()}">{label}<small>{n}</small></button>'
    return ('<div class="pass-row pass-filter" role="group" aria-label="Filter by season pass" data-pass-filter><span>Pass</span>' +
            b("", "All", len(rs)) + (b("epic", "Epic", ne) if ne else "") + (b("ikon", "Ikon", ni) if ni else "") + '</div>')

def region_page(g):
    rs = sorted(g["resorts"], key=lambda x: -x["vertical"])
    cards = "".join(f"""<a class="resort-card" href="../resorts/{x['id']}.html" data-pass="{x['pass'] or ''}">
  <span class="meta">{esc(x.get('locality') or g['name'])}, {x['lifts']} lift{'s' if x['lifts'] != 1 else ''}{pass_tag(x)}</span>
  <h3>{esc(x['name'])}</h3>
  <p>{ft(x['vertical'])} of vertical, {ft(x['base'])} to {ft(x['summit'])}.</p>
  <span class="wax-chip" data-home-wax="{x['id']}"><i></i><span>Loading today's wax…</span></span>
</a>""" for x in rs)
    n = len(rs); name = esc(g["name"]); country = COUNTRY[g["country"]]
    title = f"{g['name']} Ski Resorts: Today's Ski Wax Picks | The Ski Advisor"
    desc = f"Today's ski wax pick for all {n} ski areas in {g['name']}, {country}, from the forecast at each one's mid-mountain elevation."
    ld = bc_ld([("Home",""),("Resorts","resorts/index.html"),(g["name"], f"regions/{g['code'].lower()}.html")])
    body = f"""{page_info("region")}
{rd_script({"api": g["code"], "resorts": [rd_resort(x) for x in rs]})}
{header(1, "resorts")}
<main class="wrap">
  {crumbs(1, [("Resorts","../resorts/index.html"),(name,None)])}
  <div class="hero">
    <h1>{name} ski resorts</h1>
    <p class="lede">Today's wax pick for all {n} ski area{'s' if n != 1 else ''} in {name}, {country}. Pick a resort for the weekend forecast, edge settings and a full tune.</p>
  </div>
  <p class="muted" id="homeDataNote"></p>
  {pass_filter(rs)}
  <div class="resort-grid" id="regionGrid">{cards}</div>
  <div class="notes"><p>Biggest vertical first. {OSM_CREDIT}</p></div>
</main>
{footer(1)}
<script src="../assets/tool.js"></script>"""
    return doc(True, head(title, desc, f"regions/{g['code'].lower()}.html", 1, ld), body)

def resorts_index():
    body = f"""{page_info("resorts")}
{header(1, "resorts")}
<main class="wrap">
  {crumbs(1, [("Resorts",None)])}
  <div class="hero">
    <h1>Ski resorts in North America</h1>
    <p class="lede">{len(ALL)} operating ski areas with lifts. Search for yours, or browse by state or province.</p>
  </div>
  {search_box(1, "", "allSearch")}
  <p class="pass-links">Browse by season pass: <a href="../passes/epic.html">Epic Pass mountains</a> · <a href="../passes/ikon.html">Ikon Pass mountains</a></p>
  <section class="home-sec" aria-label="Browse by state or province">{region_grid(1)}</section>
  <div class="notes"><p>{OSM_CREDIT} Missing a ski area, or see a mistake? It comes from OpenStreetMap, which anyone can correct.</p></div>
</main>
{footer(1)}
<script src="../assets/tool.js"></script>"""
    return doc(True, head("Ski Resorts in North America | The Ski Advisor",
                          f"Find today's ski or snowboard wax pick and a home tune for any of {len(ALL)} ski resorts in the US, Canada and Mexico.",
                          "resorts/index.html", 1, bc_ld([("Home",""),("Resorts","resorts/index.html")])), body)


EFFECTIVE = "November 20, 2026"
AMZ_NOTE = "As an Amazon Associate, The Ski Advisor earns from qualifying purchases."

def content_page(path, title, desc, h1, dek, body, current="", noindex=False, crumb=None):
    ld = None if noindex else bc_ld([("Home",""),(crumb or h1, path)])
    page = f"""{page_info("content")}
{header(0, current)}
<main class="wrap">
  {crumbs(0, [(crumb or h1, None)])}
  <article class="article">
    <h1>{h1}</h1>
    <p class="dek">{dek}</p>
    {body}
  </article>
</main>
{footer(0)}
<script src="assets/tool.js"></script>"""
    return doc(True, head(title, desc, path, 0, ld, noindex), page)

def about_page():
    body = f"""
<h2>What the site does</h2>
<p>Pick any of {len(ALL)} ski areas in the US, Canada and Mexico and you get the wax color and iron temperature for today, tomorrow or this weekend, edge settings for how you ski, and a step-by-step home tune. The <a href="guides/index.html">guides</a> cover the rest, from a first wax job to race day.</p>
<h2>How the recommendations work</h2>
<ul>
<li><b>Forecast where you ski.</b> Every resort's forecast is for its mid-mountain elevation, not the base, refreshed every few hours.</li>
<li><b>Snow, not air.</b> We estimate the snow temperature from the air temperature and sky cover, and the surface type: new, packed, refrozen, man-made or wet.</li>
<li><b>Wax from the snow.</b> The wax color comes from the snow temperature, one step colder for sharp new snow or abrasive man-made snow, and warm with extra brushing on wet days.</li>
<li><b>Edges from how you ski.</b> Edge angles are a one-time setup for your style of skiing. The snow only changes how much edge work is worth doing.</li>
</ul>
<h2>Where the data comes from</h2>
<p>Weather comes from <a href="https://api.met.no/">MET Norway</a> under the <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> license. The 7-day forecast text on US resort pages comes from the <a href="https://www.weather.gov/">National Weather Service</a>. Resort locations, elevations, lifts and runs come from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> and <a href="https://openskimap.org">OpenSkiMap</a> under the <a href="https://opendatacommons.org/licenses/odbl/">Open Database License</a>. Volunteers maintain that map, so some details will be wrong. If you spot one, <a href="contact.html">tell us</a> or fix it in OpenStreetMap; the fix reaches this site at the next data refresh.</p>
<h2>Starting points, not rules</h2>
<p>The temperature on your wax label beats our chart, and a snow thermometer beats any forecast. Use the recommendations as a starting point and adjust from what you see on the hill.</p>
<h2>How the site makes money</h2>
<p>{AMZ_NOTE} When you buy through a Shop link, Amazon pays us a small commission at no extra cost to you. Commissions don't change what we recommend. We're independent and not affiliated with any resort or wax brand.</p>
<p><a href="contact.html">Questions, corrections or ideas? Get in touch.</a></p>"""
    return content_page("about.html", "About The Ski Advisor", f"How The Ski Advisor picks ski wax and edge settings for {len(ALL)} North American resorts, where its data comes from, and how it makes money.",
                        "About The Ski Advisor", "Wax and tuning advice for the snow you'll actually ski.", body, crumb="About")

def contact_page():
    body = """
<form class="contact-form" name="contact" method="POST" action="/contact-sent.html" data-netlify="true" netlify-honeypot="company">
  <input type="hidden" name="form-name" value="contact">
  <p class="hp" hidden><label>Leave this empty <input name="company" tabindex="-1" autocomplete="off"></label></p>
  <div class="field"><label for="cName">Name <span class="muted">(optional)</span></label><input id="cName" name="name" autocomplete="name"></div>
  <div class="field"><label for="cEmail">Email</label><input id="cEmail" name="email" type="email" autocomplete="email" required></div>
  <div class="field"><label for="cTopic">Topic</label>
    <select id="cTopic" name="topic">
      <option>Question about wax or tuning</option>
      <option>Correction to a resort's details</option>
      <option>Partnership or advertising</option>
      <option>Something else</option>
    </select></div>
  <div class="field"><label for="cMsg">Message</label><textarea id="cMsg" name="message" rows="6" required></textarea></div>
  <button class="btn" type="submit">Send message</button>
  <p class="muted small">We use your email only to reply. See our <a href="privacy.html">privacy policy</a>.</p>
</form>
<h2>Fixing a resort's details</h2>
<p>Elevations, lifts, runs and locations come from OpenStreetMap. Tell us what's wrong and which resort, or fix it directly in OpenStreetMap; either way, the fix reaches this site at the next data refresh.</p>"""
    return content_page("contact.html", "Contact The Ski Advisor", "Send The Ski Advisor a question, a correction to a resort's details, or a partnership idea.",
                        "Contact", "Questions, corrections to a resort's details, or partnership ideas. We read every message.", body, crumb="Contact")

def contact_sent_page():
    body = """<p>We'll reply to the email you gave us. In the meantime, <a href="resorts/index.html">find today's wax for your mountain</a> or browse the <a href="guides/index.html">tuning guides</a>.</p>"""
    return content_page("contact-sent.html", "Message sent | The Ski Advisor", "Your message to The Ski Advisor was sent.",
                        "Message sent", "Thanks for getting in touch.", body, noindex=True, crumb="Contact")

def pass_page(key):
    pi = PASS_INFO[key]
    rs = [x for x in ALL if x["pass"] == key]
    groups = {}
    for x in rs: groups.setdefault(x["region"], []).append(x)
    order = sorted(groups, key=lambda c: ({"US": 0, "CA": 1, "MX": 2}[REGIONS[c]["country"]], REGIONS[c]["name"]))
    secs = []
    for c in order:
        cards = "".join(f"""<a class="resort-card" href="../resorts/{x['id']}.html">
  <span class="meta">{esc(x.get('locality') or x['regionName'])}{pass_tag(x) if x['passAccess'] != 'full' else ''}</span>
  <h3>{esc(x['name'])}</h3>
  <p>{ft(x['vertical'])} of vertical, {x['lifts']} lift{'s' if x['lifts'] != 1 else ''}. Today's wax, edges and a home tune.</p>
</a>""" for x in sorted(groups[c], key=lambda x: -x["vertical"]))
        secs.append(f'<section class="pass-sec"><h3 class="sub-h"><a href="{region_href(c, 1)}">{esc(REGIONS[c]["name"])}</a></h3><div class="resort-grid">{cards}</div></section>')
    other = "ikon" if key == "epic" else "epic"
    n = len(rs); limited = sum(1 for x in rs if x["passAccess"] != "full")
    limited_txt = (f", and {limited} of these are limited-day " + ("partner resorts" if key == "epic" else "bonus mountains")) if limited else ""
    title = f"{pi['name']} Resorts {PASS_SEASON}: Ski Wax for All {n} North American Mountains"
    desc = f"All {n} North American ski areas on the {PASS_SEASON} {pi['name']}, by state and province, each with today's ski and snowboard wax, edge settings and a home tune."
    body = f"""{page_info("pass")}
{header(1, "resorts")}
<main class="wrap">
  {crumbs(1, [("Resorts","../resorts/index.html"),(pi["name"],None)])}
  <div class="hero">
    <h1>{pi['name']} mountains</h1>
    <p class="lede">All {n} North American ski areas on the {PASS_SEASON} {pi['name']}. Pick one for today's wax and iron temperature, edge settings and a home tune.</p>
  </div>
  <p class="muted">Days and blackout dates depend on which version of the pass you hold{limited_txt}. Check <a href="{pi['site']}" rel="noopener">the {pi['name']} site</a> before you go. The Ski Advisor isn't affiliated with {pi['owner']}.</p>
  {"".join(secs)}
  <div class="notes"><p>Pass lists change every season; this one is for {PASS_SEASON}. Spot a mistake? <a href="../contact.html">Tell us</a>. See also the <a href="{other}.html">{PASS_INFO[other]['name']} mountains</a>.</p></div>
</main>
{footer(1)}
<script src="../assets/tool.js"></script>"""
    return doc(True, head(title, desc, f"passes/{key}.html", 1,
                          bc_ld([("Home",""),("Resorts","resorts/index.html"),(pi["name"], f"passes/{key}.html")])), body)

def report_thanks_page():
    body = """<p>When the first Weekend Wax Report goes out, it'll come to the address you gave us. Every email has a one-click unsubscribe link.</p>
<p>Meanwhile, <a href="resorts/index.html">find today's wax for your mountain</a>, save it to My mountains, or read the <a href="guides/index.html">tuning guides</a>.</p>"""
    return content_page("report-thanks.html", "You're signed up | The Ski Advisor", "You're signed up for the Weekend Wax Report.",
                        "You're signed up", "Thanks for signing up for the Weekend Wax Report.", body, noindex=True, crumb="Weekend Wax Report")

def privacy_page():
    analytics_text = ('<p>We use <a href="https://www.cloudflare.com/web-analytics/">Cloudflare Web Analytics</a> to count visits and see which pages are useful. '
                      "It doesn't use cookies or track you across sites. See <a href=\"https://www.cloudflare.com/privacypolicy/\">Cloudflare's privacy policy</a>. "
                      "We don't use advertising or tracking cookies; if that changes, we'll update this page first.</p>") if CF_ANALYTICS_TOKEN else \
                     "<p>We don't currently use analytics, advertising or tracking cookies. If that changes, we'll update this page first.</p>"
    body = f"""
<p class="byline">Effective {EFFECTIVE}</p>
<p>The Ski Advisor (theskiadvisor.com) is a free website. You don't need an account, and we don't sell personal information. This policy explains what information is involved when you use the site.</p>
<h2>Information you give us</h2>
<p>If you use the <a href="contact.html">contact form</a>, we receive your email address, your message, the topic you chose and, if you give it, your name. We use it only to reply to you. The form is handled by our host, Netlify, which stores submissions for us. We delete messages when we no longer need them, or sooner if you ask.</p>
<p>If you sign up for the <b>Weekend Wax Report</b>, we receive your email address, the resort page you signed up on, and the mountains saved in your browser's My mountains list, so the report can cover them. We use them only to send you the report. Netlify stores signups for us; when the report launches, we'll use an email service to send it and will name it here first. Every email has a one-click unsubscribe link, and you can ask us to delete your address at any time.</p>
<h2>Information stored in your browser</h2>
<p>The site remembers a few choices in your own browser's local storage: your temperature units, how you ski or ride, training or race-day mode, the mountains you save to My mountains, your season-pass filter, your wax log (when you last waxed and how many ski days since), and which tuning steps you've checked off. This stays on your device; it isn't sent to us. Clear your browser's site data to remove it.</p>
<p>When you use Share this wax, the image is drawn in your own browser. Nothing is uploaded to us; you choose where to send it.</p>
<h2>Your location</h2>
<p>If you press Near me, your browser asks for permission to share your location. If you allow it, the site uses it only inside your browser to sort resorts by distance. Your location isn't sent to us or stored.</p>
<h2>Services that see your visit</h2>
<ul>
<li><b>Netlify</b> hosts the site. Like any web host, it processes technical information such as your IP address and browser type to deliver and protect the site. See <a href="https://www.netlify.com/privacy/">Netlify's privacy policy</a>.</li>
<li><b>cdnjs (Cloudflare)</b> provides the 3D graphics library for the home page flyover. See <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare's privacy policy</a>.</li>
<li><b>Weather</b> comes from MET Norway and, for US resorts, the National Weather Service, but our server requests it; your browser doesn't contact either of them and we don't send them anything about you.</li>
</ul>
<h2>Amazon links</h2>
<p>{AMZ_NOTE} When you click a Shop link, you go to Amazon, and Amazon may use cookies to record that you came from this site so it can pay us a commission. What Amazon collects is covered by <a href="https://www.amazon.com/gp/help/customer/display.html?nodeId=GX7NJQ4ZB8MHFRNJ">Amazon's privacy notice</a>.</p>
<h2>Analytics and advertising</h2>
{analytics_text}
<h2>Children</h2>
<p>The site isn't directed at children under 13, and we don't knowingly collect their information.</p>
<h2>Your choices</h2>
<p>You can ask us what information we have about you from the contact form, and ask us to correct or delete it, by <a href="contact.html">contacting us</a>.</p>
<h2>Changes</h2>
<p>If we change this policy, we'll update this page and its effective date.</p>"""
    return content_page("privacy.html", "Privacy Policy | The Ski Advisor", "What information The Ski Advisor collects, how it's used, and the services involved in delivering the site.",
                        "Privacy policy", "What happens to information when you use The Ski Advisor.", body, current="", crumb="Privacy")

def not_found_page():
    body = f"""<p>That page doesn't exist, or it has moved. Search for your resort instead:</p>
{search_box(0, "resorts/", "nfSearch")}
<p>Or <a href="resorts/index.html">browse all {len(ALL)} resorts</a>, read the <a href="guides/index.html">tuning guides</a>, or go to the <a href="index.html">home page</a>.</p>"""
    html_text = content_page("404.html", "Page not found | The Ski Advisor", "Page not found.", "Page not found", "We couldn't find that page.", body, noindex=True, crumb="Not found")
    # served at any missing path, so every link must start from the site root
    return re.sub(r'((?:href|src|data-index|data-prefix)=")(?!https?:|/|#|mailto:)', r'\1/', html_text)

def guide_kind(g): return {"buy": "Buying guide · ", "xc": "Cross-country · "}.get(g.get("kind"), "")

def guide_page(g):
    gb = guide_body(g)
    mins = read_minutes(gb)
    rel = "".join(f'<a class="guide-card" href="{s}.html"><small>{read_minutes(guide_body(G_BY[s]))} min read</small><b>{G_BY[s]["title"]}</b><span>{G_BY[s]["card"]}</span></a>' for s in g["related"])
    ld = [{"@context":"https://schema.org","@type":"Article","headline":g["title"],"description":g["desc"],
           "datePublished":"__DATE_PUBLISHED__","dateModified":"__DATE_MODIFIED__","author":{"@type":"Organization","name":"The Ski Advisor"},
           "mainEntityOfPage":DOMAIN+f"/guides/{g['slug']}.html"},
          bc_ld([("Home",""),("Guides","guides/index.html"),(g["title"],f"guides/{g['slug']}.html")])]
    body = f"""{page_info("guide")}
{header(1, "guides")}
<main class="wrap">
  {crumbs(1, [("Guides","index.html"),(g["title"],None)])}
  <article class="article">
    <span class="byline">{"Buying guide" if g.get("kind") == "buy" else "Tuning guide"} · {mins} min read</span>
    <h1>{g['title']}</h1>
    <p class="dek">{g['dek']}</p>
    {gb}
    <div class="cta-box">
      <b>Get today's wax for your mountain</b>
      <p>Wax color and iron temperature from the forecast for today, tomorrow or this weekend, plus edge settings for how you ski.</p>
      {resort_links(1)}
    </div>
  </article>
  <section class="block" aria-labelledby="moreH">
    <div class="section-head"><h2 id="moreH">Keep reading</h2></div>
    <div class="guide-grid">{rel}</div>
  </section>
</main>
{footer(1)}
<script src="../assets/tool.js"></script>"""
    return doc(True, head(f"{g['title']} | The Ski Advisor", g["desc"], f"guides/{g['slug']}.html", 1, ld), body)

def guides_index():
    card = lambda g: f'<a class="guide-card" href="{g["slug"]}.html"><small>{read_minutes(guide_body(g))} min read</small><b>{g["title"]}</b><span>{g["card"]}</span></a>'
    cards = "".join(card(g) for g in GUIDES if g.get("kind") not in ("buy", "xc"))
    xc = "".join(card(g) for g in GUIDES if g.get("kind") == "xc")
    buy = "".join(card(g) for g in GUIDES if g.get("kind") == "buy")
    body = f"""{page_info("guides")}
{header(1, "guides")}
<main class="wrap">
  {crumbs(1, [("Guides",None)])}
  <div class="hero">
    <h1>Ski tuning guides</h1>
    <p class="lede">How to wax, sharpen and set up your skis at home, from your first wax job to race day.</p>
  </div>
  <div class="guide-grid">{cards}</div>
  <section class="home-sec" aria-labelledby="xcH">
    <div class="section-head"><h2 id="xcH">Cross-country</h2><p class="muted">Grip wax, klister and glide wax for classic and skate skis.</p></div>
    <div class="guide-grid">{xc}</div>
  </section>
  <section class="home-sec" aria-labelledby="buyH">
    <div class="section-head"><h2 id="buyH">Buying guides</h2><p class="muted">What to buy, what to skip, and where to spend.</p></div>
    <div class="guide-grid">{buy}</div>
  </section>
</main>
{footer(1)}"""
    return doc(True, head("Ski Tuning Guides | The Ski Advisor", "Step-by-step guides to waxing and sharpening skis at home: wax temperature chart, edge angles, race wax, spring snow and more.", "guides/index.html", 1,
                          bc_ld([("Home",""),("Guides","guides/index.html")])), body)

# =====================================================================
# Write
# =====================================================================
import hashlib
ASSET_V = {}   # file name -> short content hash, so a changed stylesheet or script gets a new URL

# When each page's content last really changed, for the sitemap and the guides' dates. A page counts as
# changed only when its title, description or main content changes, not its inlined CSS, scripts, menu or
# footer, so a restyle or a renamed footer link doesn't tell Google that every page is new.
# Kept in src/page-dates.json and committed with site/.
DATES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page-dates.json")
PAGE_DATES = json.load(open(DATES_FILE)) if os.path.exists(DATES_FILE) else {}
def page_fingerprint(text):
    head = "".join(re.findall(r'<title>.*?</title>|<meta name="description"[^>]*>', text, flags=re.S))
    main = re.search(r'<main\b.*?</main>', text, flags=re.S)
    t = head + (main.group(0) if main else text)
    t = re.sub(r'<style\b.*?</style>|<script\b.*?</script>', '', t, flags=re.S | re.I)
    return hashlib.sha1(re.sub(r'\?v=[0-9a-f]+', '', t).encode()).hexdigest()[:16]

def write(rel, text):
    p = os.path.join(OUT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    if rel.startswith("assets/") and rel.endswith((".css", ".js")):
        ASSET_V[os.path.basename(rel)] = hashlib.sha1(text.encode()).hexdigest()[:10]
    if rel.endswith(".html"):
        text = version_assets(text)
        h, d = page_fingerprint(text), PAGE_DATES.get(rel)
        if not d: d = PAGE_DATES[rel] = {"hash": h, "published": TODAY, "modified": TODAY}
        elif d["hash"] != h: d.update(hash=h, modified=TODAY)
        text = text.replace("__DATE_PUBLISHED__", d["published"]).replace("__DATE_MODIFIED__", d["modified"])
    open(p, "w").write(text)

def version_assets(html_text):
    for name, v in ASSET_V.items():
        html_text = html_text.replace(f'assets/{name}"', f'assets/{name}?v={v}"')
    return html_text

def shards(n=6):
    """Split regions into n groups of similar size; the weather job refreshes one group per hour."""
    groups = [[] for _ in range(n)]; load = [0] * n
    for g in sorted(REGIONS.values(), key=lambda g: -len(g["resorts"])):
        i = load.index(min(load)); groups[i].append(g["code"]); load[i] += len(g["resorts"])
    return groups, load

def main():
    write("assets/site.css", SITE_CSS)   # kept for pages cached before the CSS went inline
    for f in ("geist-latin.woff2", "geist-latin-ext.woff2", "playfair-italic-latin.woff2", "OFL-Geist.txt", "OFL-PlayfairDisplay.txt"):
        dst = os.path.join(OUT, "assets", "fonts", f); os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(os.path.join(SRC, "fonts", f), "rb") as a, open(dst, "wb") as b: b.write(a.read())
    write("assets/tool.js", open(os.path.join(SRC, "tool.js")).read())
    write("assets/flyover.js", open(os.path.join(SRC, "flyover.js")).read())
    write("assets/resort-index.json", json.dumps([[x["id"], x["name"], x["short"], x["regionName"], x.get("locality") or "", x["lat"], x["lon"], pass_code(x)] for x in ALL], ensure_ascii=False, separators=(",", ":")))
    # resort list, shard plan and featured resorts for the Netlify weather functions
    lib = os.path.join(ROOT, "netlify", "lib"); os.makedirs(lib, exist_ok=True)
    with open(os.path.join(lib, "resorts.json"), "w") as f:
        json.dump([{"id": x["id"], "lat": x["lat"], "lon": x["lon"], "mid": x["mid"], "tz": x["tz"], "region": x["region"]} for x in ALL], f, separators=(",", ":"))
    groups, load = shards()
    with open(os.path.join(lib, "meta.json"), "w") as f:
        json.dump({"shards": groups, "featured": [{"id": x["id"], "region": x["region"]} for x in FEATURED]}, f, indent=1)
    for f in ("terrain.json", "terrain-height.png", "terrain-ground.webp", "terrain-ground-1k.webp", "terrain-forest.webp", "terrain-rock.webp"):
        dst = os.path.join(OUT, "assets", "terrain", f); os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(os.path.join(SRC, "terrain", f), "rb") as a, open(dst, "wb") as b: b.write(a.read())
    # remove pages for resorts that are no longer in the data
    for d in ("resorts", "regions"):
        p = os.path.join(OUT, d)
        if os.path.isdir(p):
            for fn in os.listdir(p): os.remove(os.path.join(p, fn))
    write("index.html", home(True))
    write("resorts/index.html", resorts_index())
    for x in ALL: write(f"resorts/{x['id']}.html", resort_page(x))
    for g in REGIONS.values(): write(f"regions/{g['code'].lower()}.html", region_page(g))
    for g in GUIDES: write(f"guides/{g['slug']}.html", guide_page(g))
    write("guides/index.html", guides_index())
    write("about.html", about_page())
    write("contact.html", contact_page())
    write("contact-sent.html", contact_sent_page())
    write("privacy.html", privacy_page())
    write("report-thanks.html", report_thanks_page())
    for k in PASS_INFO: write(f"passes/{k}.html", pass_page(k))
    write("404.html", not_found_page())
    for f in ("favicon.svg", "favicon-48.png", "apple-touch-icon.png", "og-image.jpg", "logo-header.webp", "logo-navy.webp"):
        src_f = os.path.join(SRC, "brand", f)
        if os.path.exists(src_f):
            dst = os.path.join(OUT, "assets" if f in ("og-image.jpg", "logo-header.webp", "logo-navy.webp") else "", f); os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src_f, "rb") as a, open(dst, "wb") as b: b.write(a.read())
    urls = ([""] + ["resorts/index.html"] + [f"regions/{c.lower()}.html" for c in sorted(REGIONS)] + [f"resorts/{x['id']}.html" for x in ALL] +
            ["passes/epic.html", "passes/ikon.html"] + ["guides/index.html"] + [f"guides/{g['slug']}.html" for g in GUIDES] + ["about.html", "contact.html", "privacy.html"])
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"  <url><loc>{DOMAIN}/{u}</loc><lastmod>{PAGE_DATES.get(u or 'index.html', {}).get('modified', TODAY)}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    with open(DATES_FILE, "w") as f: json.dump(dict(sorted(PAGE_DATES.items())), f, indent=0); f.write("\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    os.makedirs(os.path.join(ROOT, "preview"), exist_ok=True)
    open(os.path.join(ROOT, "preview", "index.html"), "w").write(version_assets(home(False)))
    print("built", len(urls), "pages;", len(ALL), "resorts in", len(REGIONS), "regions; weather shards:", load)

if __name__ == "__main__":
    main()
