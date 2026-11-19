# The Ski Advisor

Ski wax and edge tuning recommendations for today's snow at 11 North American resorts, plus home tuning guides.

## Layout

- `src/build.py` — content (resorts, guides) and page templates. Edit here.
- `src/tool.js`, `src/base.css`, `src/extra.css`, `src/flyover.js` — shared script, styles and the home-page flyover.
- `src/bake-terrain.js` — bakes the flyover terrain textures into `src/terrain/` (run once after changing the terrain).
- `site/` — the generated, deployable site. Point Netlify / Cloudflare Pages / GitHub Pages at this folder.

## Resort data

`src/resorts-data.json` lists every operating downhill ski area with a lift in the US, Canada and Mexico
(745 at the last import). It comes from OpenSkiMap / OpenStreetMap: data © OpenStreetMap contributors and
OpenSkiMap, Open Database License (ODbL), so the derived list is also offered under the ODbL.
To refresh it (at most occasionally; OpenSkiMap asks for no more than one download a day):

```bash
curl -o data-raw/ski_areas.geojson https://tiles.openskimap.org/geojson/ski_areas.geojson
python3 src/import-resorts.py
```

The 11 original resorts keep their hand-written text in `src/build.py`; every other resort page is
generated from its own numbers (elevations, lifts, runs) and its snow climate.

## Build

```bash
python3 src/build.py
```

`DOMAIN` at the top of `src/build.py` is the canonical domain (https://theskiadvisor.com); it drives canonical links, the sitemap and robots.txt.

To re-bake the flyover terrain (needs Node and Python with Pillow):

```bash
cd src && npm install && node bake-terrain.js
```

## Deploy (Netlify)

`netlify.toml` publishes the `site/` folder as-is; there is no build command. Connect this repository in Netlify, then add `theskiadvisor.com` under Domain management and follow Netlify's DNS instructions at GoDaddy.

## Data

Weather: MET Norway Locationforecast 2.0 (free, including commercial use, under CC BY 4.0 with attribution).
`netlify/functions/weather-update.mts` refreshes one sixth of the states/provinces each hour (every resort every 6 hours) and stores them in Netlify Blobs
(including a 72-hour record used for "new snow in the last 48 hours"); `netlify/functions/conditions.mts`
serves the result at `/api/conditions`. The resort list for the functions is written by `src/build.py`
to `netlify/lib/resorts.json`.
