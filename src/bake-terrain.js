#!/usr/bin/env node
/* Bakes the home-page flyover terrain.
   An eroded mountain with forest, ski runs, lift lines, a base area and an access road,
   lit by a low winter sun with soft shadows and sky light. Deterministic (seeded).

   Outputs (src/terrain/):
     terrain-height.png   heights for the 3D mesh, 16-bit packed into R (high byte) + G (low byte)
     terrain-color.jpg    2048² color texture with lighting baked in
     terrain-color-1k.jpg 1024² version for slow connections
     terrain.json         scale, sun, summit, base area and colors the runtime needs

   Run:  cd src && npm install && node bake-terrain.js            */
"use strict";
const fs = require("fs"), path = require("path");
const { PNG } = require("pngjs");

const OUT = path.join(__dirname, "terrain");
const N = 1025;                 // simulation grid
const SIZE = 10000;             // meters, edge to edge
const HALF = SIZE / 2, CELL = SIZE / (N - 1);
const MESH_N = 513;             // shipped heightmap (every 2nd sample)
const T = 2048;                 // texture size
const SUN_AZ = 18 * Math.PI / 180, SUN_EL = 23 * Math.PI / 180;   // azimuth from +x (east) toward +z (south)
const L = { x: Math.cos(SUN_EL) * Math.cos(SUN_AZ), y: Math.sin(SUN_EL), z: Math.cos(SUN_EL) * Math.sin(SUN_AZ) };
const t0 = Date.now();
const log = (...a) => console.log(((Date.now() - t0) / 1000).toFixed(1) + "s", ...a);

/* ---------------- noise ---------------- */
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function ihash(x, y) {
  let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16; return h >>> 0;
}
const GX = new Float32Array(256), GY = new Float32Array(256);
for (let i = 0; i < 256; i++) { const a = i / 256 * Math.PI * 2; GX[i] = Math.cos(a); GY[i] = Math.sin(a); }
function perlin(x, y) {          // ~[-1, 1]
  const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
  const u = fx * fx * fx * (fx * (fx * 6 - 15) + 10), v = fy * fy * fy * (fy * (fy * 6 - 15) + 10);
  const a = ihash(ix, iy) & 255, b = ihash(ix + 1, iy) & 255, c = ihash(ix, iy + 1) & 255, d = ihash(ix + 1, iy + 1) & 255;
  const n00 = GX[a] * fx + GY[a] * fy, n10 = GX[b] * (fx - 1) + GY[b] * fy;
  const n01 = GX[c] * fx + GY[c] * (fy - 1), n11 = GX[d] * (fx - 1) + GY[d] * (fy - 1);
  const x0 = n00 + (n10 - n00) * u, x1 = n01 + (n11 - n01) * u;
  return (x0 + (x1 - x0) * v) * 1.41;
}
function vnoise(x, y) {          // [0, 1]
  const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  const a = ihash(ix, iy) / 4294967296, b = ihash(ix + 1, iy) / 4294967296, c = ihash(ix, iy + 1) / 4294967296, d = ihash(ix + 1, iy + 1) / 4294967296;
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
const RC = Math.cos(0.5), RS = Math.sin(0.5);
function fbm(x, y, oct) {        // ~[-1, 1]
  let s = 0, a = 0.5, n = 0;
  for (let o = 0; o < oct; o++) { s += a * perlin(x, y); n += a; const nx = (x * RC - y * RS) * 2.02 + 3.1, ny = (x * RS + y * RC) * 2.02 + 1.7; x = nx; y = ny; a *= 0.5; }
  return s / n;
}
function ridged(x, y, oct) {     // ~[0, 1]
  let s = 0, a = 0.5, w = 1, n = 0;
  for (let o = 0; o < oct; o++) {
    let r = 1 - Math.abs(perlin(x, y)); r *= r; r *= w; w = Math.min(1, Math.max(0, r * 2));
    s += r * a; n += a; const nx = (x * RC - y * RS) * 2.05 + 5.3, ny = (x * RS + y * RC) * 2.05 + 9.1; x = nx; y = ny; a *= 0.5;
  }
  return s / n;
}
const sq = v => v * v;
const clamp01 = v => v < 0 ? 0 : v > 1 ? 1 : v;
const smooth = (a, b, t) => { const k = clamp01((t - a) / (b - a)); return k * k * (3 - 2 * k); };
const lerp = (a, b, t) => a + (b - a) * t;

/* ---------------- base terrain ---------------- */
function baseHeight(x, z) {
  const wx = x + 1300 * fbm(x / 5200 + 3.1, z / 5200 + 1.7, 4);
  const wz = z + 1300 * fbm(x / 5200 - 2.3, z / 5200 + 5.9, 4);
  const r = Math.hypot(wx * 0.95, wz * 1.1);
  let h = 1250 * Math.exp(-sq(r / 2500));
  h += 640 * Math.exp(-(sq(wx + 2300) + sq(wz - 1500)) / sq(1500));
  h += 560 * Math.exp(-(sq(wx - 2000) + sq(wz + 2200)) / sq(1350));
  h += 430 * Math.exp(-(sq(wx - 700) + sq(wz - 2900)) / sq(1250));
  h += 380 * Math.exp(-(sq(wx + 2600) + sq(wz + 2400)) / sq(1300));
  const mask = 0.3 + 0.7 * Math.exp(-sq(r / 4300));
  h += 760 * ridged(wx / 2300 + 7.7, wz / 2300 + 2.2, 7) * mask;
  h += 170 * fbm(x / 1900 + 9, z / 1900 + 4, 4);
  return h;
}

let H = new Float32Array(N * N);
for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) H[j * N + i] = baseHeight(-HALF + i * CELL, -HALF + j * CELL);
{ // shift so low ground sits near 0, soften below it, and flatten toward the borders
  const s = Array.from(H).sort((a, b) => a - b), p = s[Math.floor(s.length * 0.12)];
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const k = j * N + i, x = -HALF + i * CELL, z = -HALF + j * CELL;
    let h = H[k] - p; h = 70 * Math.log(1 + Math.exp(h / 70));
    const d = Math.max(Math.abs(x), Math.abs(z)) / HALF, w = smooth(0.8, 0.97, d);
    H[k] = lerp(h, 25 + 15 * fbm(x / 600, z / 600, 2), w);
  }
}
log("base terrain");

/* ---------------- hydraulic erosion (particle based) ---------------- */
const SCALE = 1700;   // meters per normalized unit
const flow = new Float32Array(N * N);
function erode(Hn, drops, seed, rad) {
  const rng = mulberry32(seed);
  const inertia = 0.05, capF = 4, minCap = 0.01, erodeS = 0.3, depS = 0.3, evap = 0.012, grav = 4, life = 32;
  const bx = [], by = [], bw = []; let ws = 0;
  for (let dy = -rad; dy <= rad; dy++) for (let dx = -rad; dx <= rad; dx++) { const d = Math.hypot(dx, dy); if (d < rad) { const w = 1 - d / rad; bx.push(dx); by.push(dy); bw.push(w); ws += w; } }
  for (let k = 0; k < bw.length; k++) bw[k] /= ws;
  const B = bw.length;
  for (let it = 0; it < drops; it++) {
    let px = 1 + rng() * (N - 3), py = 1 + rng() * (N - 3), dx = 0, dy = 0, sp = 1, wa = 1, sed = 0;
    for (let l = 0; l < life; l++) {
      const nx = px | 0, ny = py | 0, i = ny * N + nx, cx = px - nx, cy = py - ny;
      const a = Hn[i], b = Hn[i + 1], c = Hn[i + N], d = Hn[i + N + 1];
      const gx = (b - a) * (1 - cy) + (d - c) * cy, gy = (c - a) * (1 - cx) + (d - b) * cx;
      const h0 = a * (1 - cx) * (1 - cy) + b * cx * (1 - cy) + c * (1 - cx) * cy + d * cx * cy;
      dx = dx * inertia - gx * (1 - inertia); dy = dy * inertia - gy * (1 - inertia);
      const len = Math.hypot(dx, dy); if (len === 0) break; dx /= len; dy /= len;
      px += dx; py += dy;
      if (px < 0 || px >= N - 1 || py < 0 || py >= N - 1) break;
      const mx = px | 0, my = py | 0, j = my * N + mx, ex = px - mx, ey = py - my;
      const h1 = Hn[j] * (1 - ex) * (1 - ey) + Hn[j + 1] * ex * (1 - ey) + Hn[j + N] * (1 - ex) * ey + Hn[j + N + 1] * ex * ey;
      const dh = h1 - h0;
      const cap = Math.max(-dh * sp * wa * capF, minCap);
      if (sed > cap || dh > 0) {
        const amt = dh > 0 ? Math.min(dh, sed) : (sed - cap) * depS;
        sed -= amt;
        Hn[i] += amt * (1 - cx) * (1 - cy); Hn[i + 1] += amt * cx * (1 - cy); Hn[i + N] += amt * (1 - cx) * cy; Hn[i + N + 1] += amt * cx * cy;
      } else {
        const amt = Math.min((cap - sed) * erodeS, -dh);
        for (let q = 0; q < B; q++) {
          const xx = nx + bx[q], yy = ny + by[q];
          if (xx < 0 || yy < 0 || xx >= N || yy >= N) continue;
          const k = yy * N + xx, w = amt * bw[q], take = Hn[k] < w ? Hn[k] : w;
          Hn[k] -= take; sed += take;
        }
      }
      sp = Math.sqrt(Math.max(0, sp * sp - dh * grav));
      wa *= 1 - evap;
      flow[i] += wa;
    }
  }
}
for (let k = 0; k < N * N; k++) H[k] /= SCALE;
erode(H, 900000, 7, 4);
erode(H, 500000, 11, 2);
for (let k = 0; k < N * N; k++) H[k] *= SCALE;
log("erosion");

function blur(src, r, passes) {
  let a = Float32Array.from(src), b = new Float32Array(src.length);
  for (let p = 0; p < passes; p++) {
    for (let j = 0; j < N; j++) { let acc = 0, cnt = 0; for (let i = -r; i <= r; i++) { if (i >= 0 && i < N) { acc += a[j * N + i]; cnt++; } }
      for (let i = 0; i < N; i++) { b[j * N + i] = acc / cnt; const o = i - r, n = i + r + 1; if (o >= 0) { acc -= a[j * N + o]; cnt--; } if (n < N) { acc += a[j * N + n]; cnt++; } } }
    for (let i = 0; i < N; i++) { let acc = 0, cnt = 0; for (let j = -r; j <= r; j++) { if (j >= 0 && j < N) { acc += b[j * N + i]; cnt++; } }
      for (let j = 0; j < N; j++) { a[j * N + i] = acc / cnt; const o = j - r, n = j + r + 1; if (o >= 0) { acc -= b[o * N + i]; cnt--; } if (n < N) { acc += b[n * N + i]; cnt++; } } }
  }
  return a;
}
{ // knock down single-cell spikes and pits left by the droplets
  const s = blur(H, 1, 1); for (let k = 0; k < N * N; k++) H[k] = H[k] * 0.55 + s[k] * 0.45;
}
let hMin = Infinity, hMax = -Infinity, sIdx = 0;
for (let k = 0; k < N * N; k++) { if (H[k] < hMin) hMin = H[k]; if (H[k] > hMax) { hMax = H[k]; sIdx = k; } }
const summit = { x: -HALF + (sIdx % N) * CELL, z: -HALF + Math.floor(sIdx / N) * CELL, h: hMax };
log("relief", Math.round(hMin), "→", Math.round(hMax), "m; summit", Math.round(summit.x), Math.round(summit.z));

/* ---------------- derived fields ---------------- */
function bil(A, gx, gz) {
  if (gx < 0) gx = 0; if (gz < 0) gz = 0; if (gx > N - 1.001) gx = N - 1.001; if (gz > N - 1.001) gz = N - 1.001;
  const i = gx | 0, j = gz | 0, fx = gx - i, fz = gz - j, k = j * N + i;
  return (A[k] * (1 - fx) + A[k + 1] * fx) * (1 - fz) + (A[k + N] * (1 - fx) + A[k + N + 1] * fx) * fz;
}
const toG = v => (v + HALF) / CELL;
const hAt = (x, z) => bil(H, toG(x), toG(z));

const NX = new Float32Array(N * N), NY = new Float32Array(N * N), NZ = new Float32Array(N * N);
for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
  const k = j * N + i;
  const l = H[j * N + Math.max(0, i - 1)], r = H[j * N + Math.min(N - 1, i + 1)];
  const u = H[Math.max(0, j - 1) * N + i], d = H[Math.min(N - 1, j + 1) * N + i];
  let nx = (l - r) / (2 * CELL), nz = (u - d) / (2 * CELL), ny = 1; const n = Math.hypot(nx, ny, nz);
  NX[k] = nx / n; NY[k] = ny / n; NZ[k] = nz / n;
}
const convex = (() => { const b = blur(H, 4, 2); const c = new Float32Array(N * N); for (let k = 0; k < N * N; k++) c[k] = H[k] - b[k]; return c; })();
const flowN = (() => { const b = blur(flow, 1, 1); let m = 0; for (let k = 0; k < N * N; k++) if (b[k] > m) m = b[k]; const f = new Float32Array(N * N); const lm = Math.log(1 + m); for (let k = 0; k < N * N; k++) f[k] = Math.log(1 + b[k]) / lm; return f; })();
log("normals, ridges, flow");

// Sun visibility: march toward the sun over the heightmap, with a soft penumbra.
const SH = new Float32Array(N * N);
{
  const hor = Math.hypot(L.x, L.z), sx = L.x / hor, sz = L.z / hor, rise = (L.y / hor) * CELL;
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    let x = i, z = j, h = H[j * N + i] + 2, res = 1;
    for (let t = 1; t < 1600; t++) {
      x += sx; z += sz; h += rise;
      if (x < 0 || z < 0 || x >= N - 1 || z >= N - 1 || h > hMax) break;
      const diff = h - bil(H, x, z);
      if (diff <= 0) { res = 0; break; }
      const v = 28 * diff / (t * CELL); if (v < res) res = v;
    }
    SH[j * N + i] = smooth(0, 1, res);
  }
}
log("sun shadows");

// Sky visibility: horizon scan in 16 directions.
const AO = new Float32Array(N * N);
{
  const D = 16, R = [12, 24, 42, 70, 110, 170, 260, 400, 620, 950, 1450, 2200];
  const dxs = [], dzs = []; for (let d = 0; d < D; d++) { const a = (d + 0.5) / D * Math.PI * 2; dxs.push(Math.cos(a)); dzs.push(Math.sin(a)); }
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const h0 = H[j * N + i]; let sum = 0;
    for (let d = 0; d < D; d++) {
      let m = 0;
      for (let r = 0; r < R.length; r++) {
        const dh = bil(H, i + dxs[d] * R[r] / CELL, j + dzs[d] * R[r] / CELL) - h0;
        if (dh > 0) { const s = dh / Math.hypot(R[r], dh); if (s > m) m = s; }
      }
      sum += 1 - m;
    }
    AO[j * N + i] = sum / D;
  }
}
log("sky visibility");

/* ---------------- ski area layout ---------------- */
const rng = mulberry32(2024);
const Hs = blur(H, 10, 2);                       // smoothed field: runs follow the broad fall line
const hsAt = (x, z) => bil(Hs, toG(x), toG(z));
const efrac = h => (h - hMin) / (hMax - hMin);
const sunAz = Math.atan2(L.z, L.x);
const faceAz = sunAz - 0.25;                     // the ski area faces the morning sun
function walkOut(az, eTarget) {                  // from the summit outward until the ground drops below eTarget
  for (let r = 150; r < HALF * 0.9; r += 10) {
    const x = summit.x + Math.cos(az) * r, z = summit.z + Math.sin(az) * r;
    if (efrac(hAt(x, z)) < eTarget) return { x, z, r };
  }
  return null;
}
const base = walkOut(faceAz, 0.1) || { x: summit.x + Math.cos(faceAz) * 3500, z: summit.z + Math.sin(faceAz) * 3500 };
const runs = [], lifts = [];
const K = 11;
for (let k = 0; k < K; k++) {
  const az = faceAz + (k / (K - 1) - 0.5) * 1.7 + (rng() - 0.5) * 0.1;
  const start = walkOut(az, k % 3 === 0 ? 0.86 : 0.64 + rng() * 0.14);
  if (!start) continue;
  let x = start.x, z = start.z, dx = 0, dz = 0;
  const pts = [[x, z]], phase = rng() * 6.28, wl = 300 + rng() * 260, width = 36 + rng() * 34;
  for (let s = 0; s < 1400; s++) {
    const e = 18, gx = (hsAt(x + e, z) - hsAt(x - e, z)) / (2 * e), gz = (hsAt(x, z + e) - hsAt(x, z - e)) / (2 * e);
    let downX = -gx, downZ = -gz; const gl = Math.hypot(downX, downZ) || 1; downX /= gl; downZ /= gl;
    let tbx = base.x - x, tbz = base.z - z; const bl = Math.hypot(tbx, tbz) || 1; tbx /= bl; tbz /= bl;
    const m = Math.sin(s * 8 / wl + phase) * 0.32 * smooth(160, 700, bl);
    const wb = 0.34 + 0.46 * smooth(2600, 300, bl);
    let nx = downX * (1 - wb) + tbx * wb - downZ * m, nz = downZ * (1 - wb) + tbz * wb + downX * m;
    const nl = Math.hypot(nx, nz) || 1; nx /= nl; nz /= nl;
    dx = s ? dx * 0.82 + nx * 0.18 : nx; dz = s ? dz * 0.82 + nz * 0.18 : nz;
    const dl = Math.hypot(dx, dz) || 1; x += dx / dl * 8; z += dz / dl * 8;
    pts.push([x, z]);
    if (bl < 200 || Math.abs(x) > HALF * 0.85 || Math.abs(z) > HALF * 0.85) break;
  }
  const end = pts[pts.length - 1];
  if (Math.hypot(end[0] - base.x, end[1] - base.z) > 320) continue;   // only runs that finish at the base
  runs.push({ pts, width });
}
for (const idx of [1, Math.floor(runs.length / 2), runs.length - 2]) {
  if (!runs[idx]) continue;
  const p = runs[idx].pts, top = p[Math.floor(p.length * 0.05)];
  lifts.push([[base.x + (rng() - 0.5) * 160, base.z + (rng() - 0.5) * 160], top]);
}
const out = { x: base.x - summit.x, z: base.z - summit.z }; { const l = Math.hypot(out.x, out.z); out.x /= l; out.z /= l; }
const road = [];
{
  let x = base.x + out.x * 320, z = base.z + out.z * 320, dx = out.x, dz = out.z; const ph = rng() * 6;
  for (let s = 0; s < 900; s++) {
    road.push([x, z]);
    const e = 30, gx = (hsAt(x + e, z) - hsAt(x - e, z)) / (2 * e), gz = (hsAt(x, z + e) - hsAt(x, z - e)) / (2 * e);
    const m = Math.sin(s / 23 + ph) * 0.35;
    let nx = out.x * 0.6 - gx * 40 - out.z * m, nz = out.z * 0.6 - gz * 40 + out.x * m;
    const nl = Math.hypot(nx, nz) || 1; dx = dx * 0.8 + nx / nl * 0.2; dz = dz * 0.8 + nz / nl * 0.2;
    const dl = Math.hypot(dx, dz); x += dx / dl * 10; z += dz / dl * 10;
    if (Math.abs(x) > HALF || Math.abs(z) > HALF) break;
  }
}
log("layout:", runs.length, "runs,", lifts.length, "lifts, base at", Math.round(base.x), Math.round(base.z));

/* ---------------- raster masks at texture resolution ---------------- */
const TX = SIZE / T;
const toT = v => (v + HALF) / TX - 0.5;
const runM = new Float32Array(T * T), liftM = new Float32Array(T * T), roadM = new Float32Array(T * T), clearM = new Float32Array(T * T);
function stampSeg(M, ax, az, bx, bz, half, feather) {
  const minx = Math.max(0, Math.floor(toT(Math.min(ax, bx) - half - feather))), maxx = Math.min(T - 1, Math.ceil(toT(Math.max(ax, bx) + half + feather)));
  const minz = Math.max(0, Math.floor(toT(Math.min(az, bz) - half - feather))), maxz = Math.min(T - 1, Math.ceil(toT(Math.max(az, bz) + half + feather)));
  const vx = bx - ax, vz = bz - az, vl = vx * vx + vz * vz || 1;
  for (let tj = minz; tj <= maxz; tj++) for (let ti = minx; ti <= maxx; ti++) {
    const x = -HALF + (ti + 0.5) * TX, z = -HALF + (tj + 0.5) * TX;
    let t = ((x - ax) * vx + (z - az) * vz) / vl; t = t < 0 ? 0 : t > 1 ? 1 : t;
    const d = Math.hypot(x - (ax + vx * t), z - (az + vz * t));
    const v = 1 - smooth(half - feather, half + feather, d);
    const k = tj * T + ti; if (v > M[k]) M[k] = v;
  }
}
for (const r of runs) {
  for (let i = 1; i < r.pts.length; i++) {
    const f = i / r.pts.length, w = r.width * (0.75 + 0.45 * f) * (0.85 + 0.3 * vnoise(i / 15, r.width));
    stampSeg(runM, r.pts[i - 1][0], r.pts[i - 1][1], r.pts[i][0], r.pts[i][1], w / 2, 7);
  }
}
for (const [a, b] of lifts) stampSeg(liftM, a[0], a[1], b[0], b[1], 7, 2.5);
for (let i = 1; i < road.length; i++) { stampSeg(roadM, road[i - 1][0], road[i - 1][1], road[i][0], road[i][1], 4, 1.5); stampSeg(clearM, road[i - 1][0], road[i - 1][1], road[i][0], road[i][1], 12, 4); }
{ // base clearing
  const c = 260; for (let a = 0; a < 64; a++) {
    const r1 = c * (0.75 + 0.5 * vnoise(a / 5, 3));
    stampSeg(clearM, base.x, base.z, base.x + Math.cos(a / 64 * 6.283) * r1, base.z + Math.sin(a / 64 * 6.283) * r1, 30, 20);
  }
}
// parking lots and lodges, lined up with the road
const lots = [], lodges = [];
{
  const px = -out.z, pz = out.x;
  for (let i = 0; i < 3; i++) {
    const along = 330 + i * 125, side = (i % 2 ? 1 : -1) * 70;
    lots.push({ x: base.x + out.x * along + px * side, z: base.z + out.z * along + pz * side, w: 120, d: 55 });
  }
  for (let i = 0; i < 6; i++) {
    const along = 150 + rng() * 140, side = (rng() - 0.5) * 260;
    lodges.push({ x: base.x + out.x * along + px * side, z: base.z + out.z * along + pz * side, w: 22 + rng() * 26, d: 14 + rng() * 12 });
  }
}
function inRect(x, z, r, pad) {
  const px = -out.z, pz = out.x, dx = x - r.x, dz = z - r.z;
  const a = dx * out.x + dz * out.z, b = dx * px + dz * pz;
  return Math.abs(a) < r.d / 2 + pad && Math.abs(b) < r.w / 2 + pad;
}
log("masks");

/* ---------------- color + lighting ---------------- */
const SUNC = [1.0, 0.94, 0.86], SKYC = [0.50, 0.62, 0.86];
const CANOPY = [0.105, 0.13, 0.115];   // canopy color relative to the lit ground under it (matches the shader)
const tone = v => { const a = v * (2.51 * v + 0.03), b = v * (2.43 * v + 0.59) + 0.14; return Math.pow(clamp01(a / b), 1 / 2.2); };
const Lh = Math.hypot(L.x, L.z), lhx = L.x / Lh, lhz = L.z / Lh;
const img = Buffer.alloc(T * T * 4), forestMap = new Float32Array(T * T), rockMap = new Float32Array(T * T);
let edgeAcc = [0, 0, 0], edgeN = 0;
const treeAt = (x, z, thr) => smooth(thr - 0.07, thr + 0.07, 0.62 * vnoise(x / 6.2, z / 6.2) + 0.38 * vnoise(x / 2.7 + 31, z / 2.7 + 17));
for (let tj = 0; tj < T; tj++) for (let ti = 0; ti < T; ti++) {
  const x = -HALF + (ti + 0.5) * TX, z = -HALF + (tj + 0.5) * TX, gx = toG(x), gz = toG(z);
  const h = bil(H, gx, gz);
  let nx = bil(NX, gx, gz), ny = bil(NY, gx, gz), nz = bil(NZ, gx, gz); const nl = Math.hypot(nx, ny, nz); nx /= nl; ny /= nl; nz /= nl;
  const sh = bil(SH, gx, gz), ao = bil(AO, gx, gz), fl = bil(flowN, gx, gz), cv = bil(convex, gx, gz);
  const e = efrac(h), slope = Math.acos(ny) * 180 / Math.PI;
  const k = tj * T + ti;
  const run = runM[k], lift = liftM[k], rd = roadM[k], clr = clearM[k];
  const nRock = fbm(x / 150 + 5, z / 150 + 2, 3);

  // forest
  const tl = 0.58 + 0.08 * fbm(x / 900, z / 900, 3);
  let forest = smooth(tl + 0.04, tl - 0.12, e) * smooth(43, 31, slope);
  forest *= 1 - 0.85 * smooth(0.55, 0.8, fl) * smooth(24, 34, slope) * smooth(0.15, 0.3, e);   // avalanche paths
  forest *= 0.62 + 0.38 * smooth(-0.5, 0.45, fbm(x / 340 + 3, z / 340 + 8, 3));                // thick and thin stands
  forest *= 1 - 0.45 * smooth(6, 2, slope) * smooth(0.14, 0.05, e) * smooth(0.35, 0.7, vnoise(x / 420, z / 420));  // valley meadows
  forest *= 1 - Math.max(run, lift, clr);
  forest = clamp01(forest);
  forestMap[k] = forest;
  const tree = 0, treeSh = 0;

  // exposed rock: steep faces, wind-scoured ridges, with snow left on ledges
  let rock = smooth(36, 52, slope + nRock * 7);
  rock = Math.max(rock, smooth(4, 12, cv) * smooth(0.6, 0.9, e) * 0.7);
  rock *= 1 - 0.65 * smooth(-2, -9, cv);
  rock *= 1 - run;
  rock = clamp01(rock);
  rockMap[k] = rock;

  // albedo
  const sn = 1 - 0.035 * vnoise(x / 40, z / 40) - 0.02 * vnoise(x / 9, z / 9);
  let ar = 0.90 * sn, ag = 0.92 * sn, ab = 0.95 * sn;
  ar = lerp(ar, 0.95, run * 0.8); ag = lerp(ag, 0.96, run * 0.8); ab = lerp(ab, 0.975, run * 0.8);
  let flatSun = false;
  for (const r of lots) if (inRect(x, z, r, 0)) {
    const car = vnoise(x / 3, z / 3) > 0.62 && (Math.floor((x * out.x + z * out.z) / 6) % 3 !== 0);
    const cc = car ? 0.08 + 0.5 * vnoise(x / 2, z / 2 + 9) : 0.24;
    ar = cc; ag = cc; ab = cc * 1.03; flatSun = true;
  }
  for (const r of lodges) {
    if (inRect(x, z, r, 0)) { ar = 0.78; ag = 0.79; ab = 0.81; }
    else if (inRect(x - lhx * 9, z - lhz * 9, r, 0)) { ar *= 0.55; ag *= 0.6; ab *= 0.7; }  // building shadow
  }
  if (rd > 0) { ar = lerp(ar, 0.17, rd); ag = lerp(ag, 0.17, rd); ab = lerp(ab, 0.18, rd); }

  // lighting
  const ndl = Math.max(0, nx * L.x + ny * L.y + nz * L.z);
  const sun = (flatSun ? Math.max(ndl, L.y) : ndl) * sh * (1 - treeSh * 0.7) * (1 - tree * 0.25);
  const sky = ao * (0.6 + 0.4 * ny) * (1 - tree * 0.3);
  const bounce = 0.07 * (1 - ny) + 0.03;
  const r = tone(ar * (SUNC[0] * 1.2 * sun + SKYC[0] * 0.6 * sky + bounce));
  const g = tone(ag * (SUNC[1] * 1.2 * sun + SKYC[1] * 0.6 * sky + bounce));
  const b = tone(ab * (SUNC[2] * 1.2 * sun + SKYC[2] * 0.6 * sky + bounce));
  const o = k * 4; img[o] = Math.round(r * 255); img[o + 1] = Math.round(g * 255); img[o + 2] = Math.round(b * 255); img[o + 3] = 255;
  if (ti < 12 || tj < 12 || ti >= T - 12 || tj >= T - 12) {   // what the far view looks like at the border: ground mixed with average canopy
    const cov = 1 - smooth(0.22, 0.78, 1 - forest * 0.82);
    edgeAcc[0] += img[o] * lerp(1, CANOPY[0], cov); edgeAcc[1] += img[o + 1] * lerp(1, CANOPY[1], cov); edgeAcc[2] += img[o + 2] * lerp(1, CANOPY[2], cov); edgeN++;
  }
}
log("texture");

/* ---------------- write ---------------- */
fs.mkdirSync(OUT, { recursive: true });
const RAW = path.join(__dirname, "terrain-raw"); fs.mkdirSync(RAW, { recursive: true });
{
  const png = new PNG({ width: T, height: T }); img.copy(png.data);
  fs.writeFileSync(path.join(RAW, "ground.png"), PNG.sync.write(png, { colorType: 2 }));
  const F = T / 2, fp = new PNG({ width: F, height: F });
  for (let j = 0; j < F; j++) for (let i = 0; i < F; i++) {
    const a = 2 * j * T + 2 * i, v = (forestMap[a] + forestMap[a + 1] + forestMap[a + T] + forestMap[a + T + 1]) / 4;
    const o = (j * F + i) * 4, b = Math.round(clamp01(v) * 255); fp.data[o] = b; fp.data[o + 1] = b; fp.data[o + 2] = b; fp.data[o + 3] = 255;
  }
  fs.writeFileSync(path.join(RAW, "forest.png"), PNG.sync.write(fp, { colorType: 0 }));
  const rp = new PNG({ width: F, height: F });
  for (let j = 0; j < F; j++) for (let i = 0; i < F; i++) {
    const a = 2 * j * T + 2 * i, v = (rockMap[a] + rockMap[a + 1] + rockMap[a + T] + rockMap[a + T + 1]) / 4;
    const o = (j * F + i) * 4, b = Math.round(clamp01(v) * 255); rp.data[o] = b; rp.data[o + 1] = b; rp.data[o + 2] = b; rp.data[o + 3] = 255;
  }
  fs.writeFileSync(path.join(RAW, "rock.png"), PNG.sync.write(rp, { colorType: 0 }));
}
{
  const png = new PNG({ width: MESH_N, height: MESH_N, colorType: 2, inputHasAlpha: true });
  for (let j = 0; j < MESH_N; j++) for (let i = 0; i < MESH_N; i++) {
    const v = Math.round(clamp01((H[(2 * j) * N + 2 * i] - hMin) / (hMax - hMin)) * 65535), o = (j * MESH_N + i) * 4;
    png.data[o] = v >> 8; png.data[o + 1] = v & 255; png.data[o + 2] = 0; png.data[o + 3] = 255;
  }
  fs.writeFileSync(path.join(OUT, "terrain-height.png"), PNG.sync.write(png, { colorType: 2 }));
}
const meta = {
  size: SIZE, meshN: MESH_N, hMin: +hMin.toFixed(1), hMax: +hMax.toFixed(1),
  summit: { x: Math.round(summit.x), z: Math.round(summit.z), h: Math.round(summit.h) },
  base: { x: Math.round(base.x), z: Math.round(base.z) }, faceAz: +faceAz.toFixed(3),
  sun: { x: +L.x.toFixed(4), y: +L.y.toFixed(4), z: +L.z.toFixed(4) },
  edgeColor: edgeAcc.map(v => Math.round(v / edgeN)), canopy: CANOPY, sunH: [+lhx.toFixed(4), +lhz.toFixed(4)]
};
fs.writeFileSync(path.join(OUT, "terrain.json"), JSON.stringify(meta, null, 1));
require("child_process").execFileSync("python3", [path.join(__dirname, "encode-terrain.py"), RAW, OUT], { stdio: "inherit" });
for (const f of fs.readdirSync(OUT)) log(f, (fs.statSync(path.join(OUT, f)).size / 1024).toFixed(0) + " KB");
