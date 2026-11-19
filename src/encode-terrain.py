#!/usr/bin/env python3
"""Encode the baked terrain images for the web (called by bake-terrain.js). Needs Pillow."""
import os, sys
from PIL import Image
raw, out = sys.argv[1], sys.argv[2]
g = Image.open(os.path.join(raw, "ground.png")).convert("RGB")
g.save(os.path.join(out, "terrain-ground.webp"), "WEBP", quality=82, method=6)
g.resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, "terrain-ground-1k.webp"), "WEBP", quality=82, method=6)
f = Image.open(os.path.join(raw, "forest.png")).convert("L")
f.convert("RGB").save(os.path.join(out, "terrain-forest.webp"), "WEBP", quality=75, method=6)
r = Image.open(os.path.join(raw, "rock.png")).convert("L")
r.convert("RGB").save(os.path.join(out, "terrain-rock.webp"), "WEBP", quality=75, method=6)
