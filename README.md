# Edge & Wax

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

Set `DOMAIN` at the top of `src/build.py` to the real domain before launch (canonical links + sitemap).

To re-bake the flyover terrain:

```bash
cd src && npm install && node bake-terrain.js
```

## Data

Weather: Open-Meteo forecast API (free tier is for non-commercial use; check their terms before monetizing).
