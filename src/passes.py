"""Which resorts are on the Epic and Ikon passes, 2026-27 season (North America).

Pass lists change every season. Update this file each spring when Vail Resorts (Epic) and
Alterra (Ikon) announce the next season, then rebuild.

Sources used for 2026-27 (checked November 2026): published 2026-27 pass guides and
announcements (OnTheSnow buyer's guides, SKI, Lifted by Ikon Pass, ZRankings). Epic made no
North American changes from 2025-26. Ikon added SilverStar, Snowriver, Lutsen and Granite
Peak, added five bonus mountains, and lost Windham.

Values: "full" = on the pass (days and blackouts depend on the pass type);
"partner" / "bonus" = limited-day partner or bonus mountain.
"""
SEASON = "2026-27"

EPIC = {
    # Colorado
    "vail": "full", "beaver-creek-resort-arrowhead-mountain": "full", "breckenridge": "full",
    "keystone": "full", "crested-butte": "full", "telluride": "partner",
    # Utah, California / Nevada, Washington
    "parkcity": "full", "heavenly": "full", "northstar-at-tahoe": "full", "kirkwood": "full",
    "stevens-pass": "full",
    # Canada
    "whistler": "full",
    "fernie-alpine": "partner", "kicking-horse": "partner", "kimberley-alpine": "partner",
    "nakiska": "partner", "mont-sainte-anne": "partner", "station-touristique-stoneham": "partner",
    # Northeast
    "stowe": "full", "okemo-mountain": "full", "mount-snow": "full",
    "attitash": "full", "wildcat-mountain": "full", "mount-sunapee": "full", "crotched-mountain-ski-ride": "full",
    "hunter-mountain": "full",
    # Pennsylvania
    "seven-springs": "full", "hidden-valley-us-pa": "full", "laurel-mountain": "full",
    "liberty": "full", "roundtop": "full", "whitetail": "full", "jack-frost": "full",
    "big-boulder-ski-resort-area": "full",
    # Midwest
    "alpine-valley": "full", "boston-mills": "full", "brandywine": "full", "mad-river-mountain": "full",
    "mt-brighton": "full", "afton-alps": "full", "wilmot-mountain": "full",
    "hidden-valley": "full", "snow-creek": "full", "paoli-peaks": "full",
}

IKON = {
    # Colorado
    "aspen": "full", "aspen-mountain": "full", "aspen-highlands": "full", "buttermilk": "full",
    "steamboat": "full", "winter-park": "full", "copper-mountain": "full", "eldora": "full",
    "arapahoe-basin": "full",
    # Utah
    "alta": "full", "snowbird": "full", "brighton": "full", "solitude": "full",
    "deer-valley": "full", "snowbasin": "full",
    # California
    "palisades-tahoe-olympic-valley": "full", "palisades-tahoe-alpine-meadows": "full",
    "mammoth": "full", "june-mountain": "full", "bear-mountain": "full", "snow-summit": "full",
    "snow-valley": "full", "sierra-at-tahoe": "full",
    # Pacific Northwest, Rockies, Southwest, Alaska
    "crystal-mountain-us-wa": "full", "summit-west": "full", "three-summits": "full", "alpental": "full",
    "mt-bachelor": "full", "schweitzer": "full",
    "sun-valley-bald-mountain": "full", "sun-valley-dollar-mountain": "full",
    "bigsky": "full", "jackson": "full", "taos-ski-valley": "full", "arizona-snowbowl": "full",
    "alyeska": "full",
    # Northeast and Mid-Atlantic
    "stratton": "full", "sugarbush": "full", "killington": "full", "pico": "full",
    "loon": "full", "cranmore": "full", "sunday-river": "full", "sugarloaf": "full",
    "ski-butternut": "full", "camelback": "full", "blue": "full", "snowshoe-mountain": "full",
    # Midwest
    "boyne-mountain": "full", "boyne-highlands": "full",
    "jackson-creek-summit": "full", "black-river-basin": "full",   # Snowriver Mountain Resort
    "lutsen-mountains": "full", "granite-peak": "full",
    # Canada
    "mont-tremblant-resort-station-mont-tremblant": "full", "le-massif": "full", "blue-mountain": "full",
    "banff-sunshine-village": "full", "lake-louise": "full", "mt-norquay": "full",
    "revelstoke": "full", "red": "full", "cypress-mountain": "full", "panorama": "full",
    "sun-peaks": "full", "silver-star": "full",
    # 2026-27 bonus mountains (limited days)
    "devil-s-head": "bonus", "tamarack": "bonus", "giants-ridge": "bonus", "caberfae-peaks": "bonus",
    "snowy-range": "bonus",
}

PASS_INFO = {
    "epic": {"name": "Epic Pass", "owner": "Vail Resorts", "site": "https://www.epicpass.com/",
             "limited": "partner resort with limited days"},
    "ikon": {"name": "Ikon Pass", "owner": "Alterra Mountain Company", "site": "https://www.ikonpass.com/",
             "limited": "bonus mountain with limited days"},
}

def pass_of(resort_id):
    """(pass key, access) for a resort, or (None, None)."""
    if resort_id in EPIC: return "epic", EPIC[resort_id]
    if resort_id in IKON: return "ikon", IKON[resort_id]
    return None, None

assert not set(EPIC) & set(IKON), "a resort is listed on both passes"
