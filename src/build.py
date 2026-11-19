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
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800'
         '&family=Barlow:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap">')
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
        "Snowmass has long, wide groomers. A carver tune (0.7° base, 3° side) pays off on firm mornings.",
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

def shop(q): return f'<a class="shop" href="https://www.rei.com/search?q={q.replace(" ","+")}" target="_blank" rel="noopener sponsored">Shop</a>'

def resort_links(depth):
    r = "../"*depth
    return '<div class="related">' + "".join(f'<a href="{r}resorts/{x["id"]}.html">{x["name"]}</a>' for x in RESORTS) + '</div>'

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
 dict(slug="ski-edge-angles", title="Ski Edge Angles Explained: 89°, 88° and 87°",
  desc="Ski edge angles explained: what base bevel and side bevel do, how 88° and 87° edges are measured, and which angles to choose for how you ski.",
  card="Base bevel, side bevel, and what an 88° edge actually means.",
  dek="What base and side bevel do, how they add up to the number people quote, and which to pick for how you ski.",
  related=["how-to-sharpen-ski-edges","icy-and-man-made-snow","race-wax-vs-training-wax"],
  body="""
<h2>Two bevels</h2>
<p><b>Base bevel</b> is how far the edge is lifted off the flat of the base, usually 0.5° to 1°. More base bevel means the ski rolls onto its edge more gradually.</p>
<p><b>Side bevel</b> is how far the side of the edge is filed past vertical, usually 1° to 3°. More side bevel makes a sharper, more aggressive edge that bites harder snow.</p>
[[EDGEFIGS]]
<p class="disclose">Material removed by each bevel is shaded. Angles are drawn five times their real size so you can see them.</p>
<h2>What "88°" means</h2>
<p>Shops usually describe the side bevel by its angle: a 2° side bevel is called an 88° edge. The actual angle at the corner of the edge also includes the base bevel:</p>
<p><b>included angle = 90° − side bevel + base bevel</b></p>
<p>So a ski with 1° base and 2° side has an 89° included angle, even though everyone calls it an 88° edge.</p>
<h2>Which angles to choose</h2>
[[STYLETABLE]]
<h2>Leave base bevel to the shop</h2>
<p>Base bevel is set by a shop's stone grind and you should rarely change it at home. Too much base bevel makes the ski feel vague. At home, only deburr the base edge with one or two light passes in a base guide.</p>
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
<p class="disclose">Some links on this page may earn us a commission. It doesn't change what we recommend.</p>
<h2>Start here: waxing</h2>
<ul>
<li><b>Waxing iron:</b> a dedicated ski iron with a steady temperature. [[SHOP:ski waxing iron]]</li>
<li><b>Universal wax:</b> works across temperatures while you learn. [[SHOP:universal ski wax]]</li>
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
<li><b>Temperature-specific waxes</b> once you know your conditions. See the <a href="ski-wax-temperature-chart.html">wax chart</a>. [[SHOP:ski wax]]</li>
<li><b>Brass and horsehair brushes</b> for cold and warm wax. [[SHOP:horsehair ski brush]]</li>
<li><b>Base edge guide</b> for deburring the base edge. [[SHOP:base bevel guide]]</li>
<li><b>P-tex candles</b> for small base repairs. [[SHOP:p-tex candle]]</li>
<li><b>A polishing pad</b> for the final buff. [[SHOP:fibertex ski]]</li>
</ul>
"""),
]
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

def head(title, desc, path, depth, jsonld=None):
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
           '<meta name="twitter:card" content="summary">',
           FONTS,
           f'<link rel="stylesheet" href="{r}assets/site.css">']
    if jsonld:
        out.append('<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False) + '</script>')
    return "\n".join(out)

def header(depth, current="", chips=False):
    r = "../"*depth
    g_cur = ' aria-current="page"' if current == "guides" else ""
    chip_row = '\n    <nav class="chips" id="resortChips" aria-label="Choose a resort"></nav>' if chips else ""
    return f"""<header class="top">
  <div class="wrap">
    <div class="top-row">
      <a class="brand" href="{r}index.html">{DIAMOND}<span>The Ski Advisor</span></a>
      <nav class="nav" aria-label="Site"><a href="{r}index.html#resorts">Resorts</a><a href="{r}guides/index.html"{g_cur}>Guides</a></nav>
    </div>{chip_row}
  </div>
</header>"""

def footer(depth):
    r = "../"*depth
    res = "".join(f'<li><a href="{r}resorts/{x["id"]}.html">{x["name"]}</a></li>' for x in RESORTS)
    gds = "".join(f'<li><a href="{r}guides/{g["slug"]}.html">{g["title"]}</a></li>' for g in GUIDES)
    return f"""<footer class="site-foot">
  <div class="wrap" style="display:grid;gap:22px">
    <div class="foot-grid">
      <div><h3>Resorts</h3><ul>{res}</ul></div>
      <div><h3>Guides</h3><ul>{gds}</ul></div>
      <div><h3>The Ski Advisor</h3><p>Wax and edge recommendations from the forecast at each resort's mid-mountain elevation. Weather data from Open-Meteo.</p></div>
    </div>
    <p>Some shop links may earn us a commission. It doesn't change what we recommend. Recommendations are starting points: the temperature on your wax label wins, and a snow thermometer beats any forecast.</p>
  </div>
</footer>"""

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

def home(full):
    opts = "".join(f'<option value="{x["id"]}"{" selected" if x["id"]=="vail" else ""}>{x["name"]}, {x["region"]}</option>' for x in RESORTS)
    cards = "".join(f"""<a class="resort-card" href="resorts/{x['id']}.html">
  <span class="meta">{x['region']} · mid-mountain {ft(x['mid'])}</span>
  <h3>{x['name']}</h3>
  <p>{x['tag']}.</p>
  <span class="wax-chip" data-home-wax="{x['id']}"><i></i><span>Loading today's wax…</span></span>
</a>""" for x in RESORTS)
    cards += """<a class="resort-card alt" href="guides/ski-wax-temperature-chart.html">
  <span class="meta">Any mountain</span>
  <h3>Not on the list?</h3>
  <p>Use the wax temperature chart with your local forecast or a snow thermometer.</p>
  <span class="wax-chip"><span>Open the wax chart →</span></span>
</a>"""
    gcards = "".join(f'<a class="guide-card" href="guides/{g["slug"]}.html"><small>{read_minutes(guide_body(g))} min read</small><b>{g["title"]}</b><span>{g["card"]}</span></a>' for g in GUIDES)
    ld = {"@context":"https://schema.org","@type":"WebSite","name":"The Ski Advisor","url":DOMAIN+"/"}
    h = head("The Ski Advisor: Ski Wax and Edge Tuning for Today's Snow",
             "Wax color, iron temperature and edge angles for today's snow at 11 North American ski resorts, plus step-by-step home tuning guides.",
             "", 0, ld)
    body = f"""{page_info("home")}
{header(0)}
<section class="hero-fly" id="flyHero" aria-label="Flyover of a snowy ski mountain">
  {SIL}
  <canvas id="flyover" aria-hidden="true"></canvas>
  <button class="fly-ctrl" id="flyPause" type="button" aria-pressed="false">Pause flyover</button>
  <div class="hero-copy">
    <div class="wrap">
      <span class="label">Wax &amp; edges · 11 North American resorts</span>
      <h1>Your Mountain<br>Your Snow<br>Your Skis</h1>
      <p>Pick your mountain. Get the wax color, iron temperature and edge angles for today, tomorrow or this weekend, plus a step-by-step home tune to match.</p>
      <div class="hero-cta">
        <label class="sr" for="heroResort">Your mountain</label>
        <select id="heroResort">{opts}</select>
        <a class="btn" id="heroGo" href="resorts/vail.html">Show my tune</a>
        <a class="btn ghost" href="guides/index.html">Read the guides</a>
      </div>
    </div>
  </div>
</section>
<main class="wrap">
  <section class="home-sec" id="resorts" aria-labelledby="resortsH">
    <div class="section-head"><h2 id="resortsH">Pick your mountain</h2><p class="muted" id="homeDataNote">Today's wax pick for each resort, from the forecast at mid-mountain.</p></div>
    <div class="resort-grid">{cards}</div>
  </section>
  <section class="home-sec" aria-labelledby="howH">
    <div class="section-head"><h2 id="howH">How it works</h2></div>
    <ol class="how">
      <li><b>Forecast at mid-mountain</b><span>We pull temperature, humidity and new snow at the elevation you'll actually ski, not at the base.</span></li>
      <li><b>Snow, not air</b><span>We estimate the snow temperature and surface: new, packed, refrozen, man-made or wet.</span></li>
      <li><b>Wax, edges, steps</b><span>You get the wax color, iron setting and edge angles for how you ski, and a tune walkthrough set to match.</span></li>
    </ol>
  </section>
  <section class="home-sec" aria-labelledby="guidesH">
    <div class="section-head"><h2 id="guidesH">Tuning guides</h2><p class="muted">Everything you need to tune at home, from your first wax job to race day.</p></div>
    <div class="guide-grid">{gcards}</div>
  </section>
</main>
{footer(0)}
<script src="assets/tool.js"></script>
<script src="{THREE}"></script>
<script src="assets/flyover.js"></script>
<script>
(function(){{
  var s = document.getElementById("heroResort"), go = document.getElementById("heroGo");
  if(s && go) s.addEventListener("change", function(){{ go.href = "resorts/" + s.value + ".html"; }});
}})();
</script>"""
    return doc(full, h, body)

TOOL_FRAG = open(os.path.join(SRC, "tool-fragment.html")).read()

def resort_page(x):
    others = [g for g in ["ski-wax-temperature-chart","ski-edge-angles","how-to-wax-skis","icy-and-man-made-snow" if x["id"] in ("killington","vail","jackson","bigsky","parkcity") else "waxing-for-spring-snow","race-wax-vs-training-wax"]]
    rel = "".join(f'<a href="../guides/{s}.html">{G_BY[s]["title"]}</a>' for s in others)
    about = "".join(f"<p>{p}</p>" for p in x["about"])
    tips = "".join(f"<li>{t}</li>" for t in x["tips"])
    title = f"{x['name']} Ski Wax & Tuning: Today's Wax and Edge Angles"
    desc = f"Which wax and edge angles to use at {x['name']} today, tomorrow or this weekend, from the forecast at mid-mountain ({ft(x['mid'])}). Plus a step-by-step home tune."
    ld = bc_ld([("Home",""),("Resorts","index.html#resorts"),(x["name"],f"resorts/{x['id']}.html")])
    body = f"""{page_info("resort", x["id"])}
{header(1, chips=True)}
<main class="wrap">
  {crumbs(1, [("Resorts","../index.html#resorts"),(x["name"],None)])}
  <div class="hero">
    <span class="label" id="heroEyebrow">Today · {x['region']} · mid-mountain, {ft(x['mid'])}</span>
    <h1>Wax &amp; tune for <em>{x['name']}</em></h1>
    <p class="lede">{x['tag']}. Wax color, iron temperature and edge angles from the forecast at mid-mountain, with a step-by-step home tune.</p>
    <div class="hero-sub">
      <div class="seg" role="group" aria-label="When are you skiing?">
        <button type="button" id="dayToday" aria-pressed="true">Today</button>
        <button type="button" id="dayTomorrow" aria-pressed="false">Tomorrow</button>
        <button type="button" id="dayWeekend" aria-pressed="false">This weekend</button>
      </div>
      <div class="seg" role="group" aria-label="Units">
        <button type="button" id="unitF" aria-pressed="true">°F / in</button>
        <button type="button" id="unitC" aria-pressed="false">°C / cm</button>
      </div>
      <span class="badge" id="sourceBadge"><i></i><span id="sourceText">Loading conditions…</span></span>
    </div>
  </div>
{TOOL_FRAG}
  <section class="block" aria-labelledby="aboutH">
    <div class="about">
      <div class="prose"><h2 id="aboutH">Skiing {x['name']}'s snow</h2>{about}</div>
      <div class="card"><h3>Tuning tips for {x['name']}</h3><ul class="tips">{tips}</ul></div>
    </div>
  </section>
  <section class="block" aria-labelledby="relH">
    <div class="section-head"><h2 id="relH">Related guides</h2></div>
    <div class="related">{rel}</div>
  </section>
  <div class="notes">
    <p id="dataNote">Weather from the Open-Meteo forecast, downscaled to {x['name']}'s mid-mountain elevation.</p>
    <p>Snow temperature is estimated from air temperature and sky cover. A snow thermometer reading is better. Wax ranges vary by brand, so the temperature on the wax label wins. All waxes suggested here are fluoro-free.</p>
    <p>Base bevels are usually set by a shop's stone grind. If your skis are new or freshly ground, ask the shop what they set before you change anything.</p>
  </div>
</main>
{footer(1)}
<script src="../assets/tool.js"></script>"""
    return doc(True, head(title, desc, f"resorts/{x['id']}.html", 1, ld), body)

def guide_page(g):
    gb = guide_body(g)
    mins = read_minutes(gb)
    rel = "".join(f'<a class="guide-card" href="{s}.html"><small>{read_minutes(guide_body(G_BY[s]))} min read</small><b>{G_BY[s]["title"]}</b><span>{G_BY[s]["card"]}</span></a>' for s in g["related"])
    ld = [{"@context":"https://schema.org","@type":"Article","headline":g["title"],"description":g["desc"],
           "datePublished":TODAY,"dateModified":TODAY,"author":{"@type":"Organization","name":"The Ski Advisor"},
           "mainEntityOfPage":DOMAIN+f"/guides/{g['slug']}.html"},
          bc_ld([("Home",""),("Guides","guides/index.html"),(g["title"],f"guides/{g['slug']}.html")])]
    body = f"""{page_info("guide")}
{header(1, "guides")}
<main class="wrap">
  {crumbs(1, [("Guides","index.html"),(g["title"],None)])}
  <article class="article">
    <span class="byline">Tuning guide · {mins} min read</span>
    <h1>{g['title']}</h1>
    <p class="dek">{g['dek']}</p>
    {gb}
    <div class="cta-box">
      <b>Get today's wax for your mountain</b>
      <p>Wax color, iron temperature and edge angles from the forecast, for today, tomorrow or this weekend.</p>
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
    cards = "".join(f'<a class="guide-card" href="{g["slug"]}.html"><small>{read_minutes(guide_body(g))} min read</small><b>{g["title"]}</b><span>{g["card"]}</span></a>' for g in GUIDES)
    body = f"""{page_info("guides")}
{header(1, "guides")}
<main class="wrap">
  {crumbs(1, [("Guides",None)])}
  <div class="hero">
    <span class="label">Home tuning</span>
    <h1>Ski tuning guides</h1>
    <p class="lede">How to wax, sharpen and set up your skis at home, from your first wax job to race day.</p>
  </div>
  <div class="guide-grid">{cards}</div>
</main>
{footer(1)}"""
    return doc(True, head("Ski Tuning Guides | The Ski Advisor", "Step-by-step guides to waxing and sharpening skis at home: wax temperature chart, edge angles, race wax, spring snow and more.", "guides/index.html", 1,
                          bc_ld([("Home",""),("Guides","guides/index.html")])), body)

# =====================================================================
# Write
# =====================================================================
def write(rel, text):
    p = os.path.join(OUT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(text)

def main():
    css = open(os.path.join(SRC, "base.css")).read() + open(os.path.join(SRC, "extra.css")).read()
    js_res = [{k: x[k] for k in ("id","name","region","lat","lon","mid","ex")} for x in RESORTS]
    tool = open(os.path.join(SRC, "tool.js")).read().replace("/*RESORTS*/[]", json.dumps(js_res))
    write("assets/site.css", css)
    write("assets/tool.js", tool)
    write("assets/flyover.js", open(os.path.join(SRC, "flyover.js")).read())
    for f in ("terrain.json", "terrain-height.png", "terrain-ground.webp", "terrain-ground-1k.webp", "terrain-forest.webp", "terrain-rock.webp"):
        dst = os.path.join(OUT, "assets", "terrain", f); os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(os.path.join(SRC, "terrain", f), "rb") as a, open(dst, "wb") as b: b.write(a.read())
    write("index.html", home(True))
    for x in RESORTS: write(f"resorts/{x['id']}.html", resort_page(x))
    for g in GUIDES: write(f"guides/{g['slug']}.html", guide_page(g))
    write("guides/index.html", guides_index())
    urls = [""] + [f"resorts/{x['id']}.html" for x in RESORTS] + ["guides/index.html"] + [f"guides/{g['slug']}.html" for g in GUIDES]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"  <url><loc>{DOMAIN}/{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    # claude.ai preview entry: home page without the document wrapper (not part of the deployable site)
    os.makedirs(os.path.join(ROOT, "preview"), exist_ok=True)
    open(os.path.join(ROOT, "preview", "index.html"), "w").write(home(False))
    print("built", len(urls), "pages")

if __name__ == "__main__":
    main()
