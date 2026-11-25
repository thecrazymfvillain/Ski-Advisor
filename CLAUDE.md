# The Ski Advisor: notes for Claude

theskiadvisor.com gives the ski or snowboard wax color and iron temperature for today, tomorrow or this
weekend at 745 North American ski areas, from MET Norway's forecast at each resort's mid-mountain
elevation, plus edge settings by riding style, a step-by-step home tune, and tuning and buying guides.
README.md covers the data import and the flyover tools.

## Who decides

The person working with you is the site's owner and does most of the work now (Ryan has handed it off).
They are not a developer: explain things in plain language. Changes go straight to `main` once they've seen
the change and said to push. No pull requests or review needed.

## Rules that cost money or break the live site

- **Every push to `main` deploys to production and costs 15 Netlify credits** (the plan has 1,000 a month).
  Show the owner the change and get their go-ahead before each push that changes the site, and group related
  changes into one push to save credits.
- **Preview locally before every push that changes the site.** Build, run `python3 src/preview.py`, and show
  the owner screenshots of the changed pages (desktop and phone) from a headless browser. Push only after
  they've seen them and said go. Previews cost nothing; deploys cost credits.
- A commit that doesn't change the site (notes, docs) can go to `main` without a deploy if its message
  contains `[skip netlify]`. The next normal push deploys everything that has piled up, so say so.
- Never hand-edit `site/`. It's generated: change `src/`, run the build, and commit `src/` and `site/` together.
- Two people regenerating `site/` at once means merge conflicts in hundreds of files. Agree who works on
  what, pull first, and rebuild after merging rather than resolving `site/` conflicts by hand.

## Build and preview

```bash
python3 src/build.py                                  # writes all 816 pages to site/, plus netlify/lib/*.json
python3 src/preview.py                                # http://localhost:8000
```

`src/preview.py` serves `site/` and forwards `/api/...` to the live site, so previews show real weather
(it needs theskiadvisor.com reachable; without it, pages fall back to "Example conditions"). The live API is
`https://theskiadvisor.com/api/conditions/<region>` (e.g. `US-CO`, or `featured`).

## How it fits together

- `src/build.py`: all page templates and content: resorts, regions, Epic/Ikon pages, guides, About/Contact/
  Privacy, sitemap. Guides live in `GUIDES` (build.py), `src/guides_extra.py` and `src/guides_buy.py`.
- `src/tool.js`: everything in the browser: wax and edge picks, weekend Saturday/Sunday toggle, search and
  Near me, Epic/Ikon filter, My mountains, share image, wax log, Weekend Wax Report signup, mobile menu.
  The wax bands (`BANDS`) must match `BANDS` in build.py.
- `src/tool-fragment.html`: the resort-page tool. Styles: `src/base.css`, then `extra.css`, then `theme.css`
  (the current "Buildify" theme). All CSS is inlined into every page; fonts (Geist, Playfair Display italic)
  are self-hosted in `src/fonts/`. Keep it that way: no render-blocking third-party CSS or fonts.
- `src/passes.py`: 2026-27 Epic and Ikon lists. Update every spring when the passes announce next season.
- `src/resorts-data.json`: the 745 resorts (OpenSkiMap / OpenStreetMap, ODbL).
- `netlify/functions/weather-update.mts`: runs hourly at minute 11 UTC; refreshes one sixth of the regions
  from MET Norway (every resort every 6 hours) and stores them in Netlify Blobs ("weather" store).
- `netlify/functions/conditions.mts`: serves `/api/conditions/:key` from that store.
- `netlify/lib/met.mts`: forecast parsing, the snow estimate (`snowFrom`: MET's rain/sleet/snow label plus
  temperature), daily summaries, and the 48-hour new-snow history. MET requires the User-Agent it sets.

## Content rules

- Edge angles are a one-time setup by riding style; the conditions only change how much edge work to do.
- Every wax suggested is fluoro-free. The temperature on the wax label wins over the site's chart.
- Never claim hands-on product testing, never invent reviews, testimonials, partner logos or prices.
- Amazon Associates tag: `theskiadvisor-20` (amazon.com only), set in both build.py and tool.js.
- Anything new that collects or stores information about visitors needs a matching update to the privacy
  page (`privacy_page()` in build.py) and its effective date.
- Weather credit: MET Norway (CC BY 4.0). Resort data credit: OpenStreetMap contributors and OpenSkiMap (ODbL).

## Services

- Hosting: Netlify, publishing `site/` with no build command (`netlify.toml`). Netlify Forms handles the
  `contact` and `wax-report` forms. The domain uses Netlify DNS.
- Analytics: Cloudflare Web Analytics (cookie-free); token `CF_ANALYTICS_TOKEN` in build.py.
- Google Search Console is verified for theskiadvisor.com; the sitemap is `/sitemap.xml`.
