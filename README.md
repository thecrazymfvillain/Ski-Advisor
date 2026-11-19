# The Ski Advisor

Ski wax and edge tuning recommendations for today's snow at 11 North American resorts, plus home tuning guides.

## Layout

- `src/build.py` — content (resorts, guides) and page templates. Edit here.
- `src/tool.js`, `src/base.css`, `src/extra.css`, `src/flyover.js` — shared script, styles and the home-page flyover.
- `src/bake-terrain.js` — bakes the flyover terrain textures into `src/terrain/` (run once after changing the terrain).
- `site/` — the generated, deployable site. Point Netlify / Cloudflare Pages / GitHub Pages at this folder.

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
`netlify/functions/weather-update.mts` fetches all resorts hourly and stores them in Netlify Blobs
(including a 72-hour record used for "new snow in the last 48 hours"); `netlify/functions/conditions.mts`
serves the result at `/api/conditions`. The resort list for the functions is written by `src/build.py`
to `netlify/lib/resorts.json`.
