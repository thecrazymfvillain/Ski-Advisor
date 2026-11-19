/* Drone flyover for the home-page hero.
   Terrain, lighting, ski runs and the forest map are baked offline (src/bake-terrain.js);
   this file draws them with a level, gimbal-steady drone camera, sky, haze, foothills and
   distant ranges. Individual trees are drawn on the GPU from the forest map so they stay
   sharp up close. Needs THREE (r128 UMD). Without WebGL or the assets, the SVG behind the
   canvas stays. */
(function () {
"use strict";
const hero = document.getElementById("flyHero");
const canvas = document.getElementById("flyover");
if (!hero || !canvas) return;
const btn = document.getElementById("flyPause");
const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
const ASSETS = "assets/terrain/";
const fail = () => { if (btn) btn.hidden = true; };
if (!window.THREE) { fail(); return; }

/* ---------- small noise for foothills and distant ranges ---------- */
function ihash(x, y) { let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16; return h >>> 0; }
function vnoise(x, y) {
  const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy, u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  const a = ihash(ix, iy) / 4294967296, b = ihash(ix + 1, iy) / 4294967296, c = ihash(ix, iy + 1) / 4294967296, d = ihash(ix + 1, iy + 1) / 4294967296;
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function ridged(x, y, oct) { let s = 0, a = 0.5, n = 0, w = 1; for (let o = 0; o < oct; o++) { let r = 1 - Math.abs(vnoise(x, y) * 2 - 1); r *= r * w; w = Math.min(1, r * 2); s += r * a; n += a; const nx = x * 1.62 - y * 1.18 + 3.1, ny = x * 1.18 + y * 1.62 + 7.7; x = nx; y = ny; a *= 0.5; } return s / n; }
function fbm(x, y, oct) { let s = 0, a = 0.5, n = 0; for (let o = 0; o < oct; o++) { s += a * vnoise(x, y); n += a; const nx = x * 1.62 - y * 1.18 + 5.3, ny = x * 1.18 + y * 1.62 + 1.9; x = nx; y = ny; a *= 0.5; } return s / n; }
const smooth = (a, b, t) => { const k = Math.min(1, Math.max(0, (t - a) / (b - a))); return k * k * (3 - 2 * k); };

/* ---------- colors (display space) ---------- */
const ZENITH = new THREE.Color(0x3D6BB3), HORIZON = new THREE.Color(0xCCD9E8), SUNGLOW = new THREE.Color(0xFFD9A8);
const FOG_DENSITY = 0.000058;

function loadImageData(url) {
  return fetch(url).then(r => { if (!r.ok) throw new Error(url); return r.blob(); }).then(blob => {
    const draw = src => { const c = document.createElement("canvas"); c.width = src.width; c.height = src.height; const g = c.getContext("2d"); g.drawImage(src, 0, 0); return g.getImageData(0, 0, c.width, c.height); };
    if (window.createImageBitmap) return createImageBitmap(blob, { premultiplyAlpha: "none", colorSpaceConversion: "none" }).then(draw);
    return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(draw(im)); im.onerror = rej; im.src = URL.createObjectURL(blob); });
  });
}
function loadTexture(url) { return new Promise((res, rej) => new THREE.TextureLoader().load(url, res, undefined, rej)); }

function start() {
  let renderer;
  try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" }); }
  catch (e) { fail(); return; }
  const small = Math.min(innerWidth, innerHeight) < 700;
  const conn = navigator.connection || {};
  const lite = conn.saveData || /2g|3g/.test(conn.effectiveType || "");
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2));

  Promise.all([
    fetch(ASSETS + "terrain.json").then(r => r.json()),
    loadImageData(ASSETS + "terrain-height.png"),
    loadTexture(ASSETS + (lite ? "terrain-ground-1k.webp" : "terrain-ground.webp")),
    loadTexture(ASSETS + "terrain-forest.webp"),
    loadTexture(ASSETS + "terrain-rock.webp")
  ]).then(([meta, hImg, groundTex, forestTex, rockTex]) => build(renderer, meta, hImg, groundTex, forestTex, rockTex, small))
    .catch(() => { fail(); renderer.dispose(); });
}

function build(renderer, meta, hImg, groundTex, forestTex, rockTex, small) {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(HORIZON.getHex(), FOG_DENSITY);
  const SIZE = meta.size, HALF = SIZE / 2, HN = hImg.width;
  const sun = new THREE.Vector3(meta.sun.x, meta.sun.y, meta.sun.z).normalize();

  /* heights */
  const H = new Float32Array(HN * HN), span = meta.hMax - meta.hMin;
  for (let i = 0; i < HN * HN; i++) H[i] = meta.hMin + ((hImg.data[i * 4] << 8) | hImg.data[i * 4 + 1]) / 65535 * span;
  const hAt = (x, z) => {
    let gx = (x + HALF) / SIZE * (HN - 1), gz = (z + HALF) / SIZE * (HN - 1);
    gx = Math.max(0, Math.min(HN - 1.001, gx)); gz = Math.max(0, Math.min(HN - 1.001, gz));
    const i = gx | 0, j = gz | 0, fx = gx - i, fz = gz - j, k = j * HN + i;
    return (H[k] * (1 - fx) + H[k + 1] * fx) * (1 - fz) + (H[k + HN] * (1 - fx) + H[k + HN + 1] * fx) * fz;
  };

  /* terrain mesh */
  const SEG = small ? 256 : HN - 1, step = (HN - 1) / SEG, V = SEG + 1;
  const pos = new Float32Array(V * V * 3), uv = new Float32Array(V * V * 2);
  for (let j = 0; j < V; j++) for (let i = 0; i < V; i++) {
    const k = j * V + i, hi = Math.min(HN - 1, Math.round(j * step)) * HN + Math.min(HN - 1, Math.round(i * step));
    pos[k * 3] = -HALF + i / SEG * SIZE; pos[k * 3 + 1] = H[hi]; pos[k * 3 + 2] = -HALF + j / SEG * SIZE;
    uv[k * 2] = i / SEG; uv[k * 2 + 1] = 1 - j / SEG;
  }
  const idx = new Uint32Array(SEG * SEG * 6); let q = 0;
  for (let j = 0; j < SEG; j++) for (let i = 0; i < SEG; i++) {
    const a = j * V + i, b = a + 1, c = a + V, d = c + 1;
    idx[q++] = a; idx[q++] = c; idx[q++] = b; idx[q++] = b; idx[q++] = c; idx[q++] = d;
  }
  const tgeo = new THREE.BufferGeometry();
  tgeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  tgeo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  tgeo.setIndex(new THREE.BufferAttribute(idx, 1));

  const aniso = renderer.capabilities.getMaxAnisotropy();
  for (const t of [groundTex, forestTex, rockTex]) { t.anisotropy = aniso; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; }
  const tmat = new THREE.ShaderMaterial({
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {
      groundMap: { value: null }, forestMap: { value: null }, rockMap: { value: null },
      sunH: { value: new THREE.Vector2(meta.sunH[0], meta.sunH[1]) },
      canopy: { value: new THREE.Vector3(meta.canopy[0], meta.canopy[1], meta.canopy[2]) }
    }]),
    vertexShader: `
      varying vec2 vUv; varying vec3 vWorld;
      #include <fog_pars_vertex>
      void main() {
        vUv = uv;
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vWorld = wp.xyz;
        vec4 mvPosition = viewMatrix * wp;
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: `
      uniform sampler2D groundMap; uniform sampler2D forestMap; uniform sampler2D rockMap; uniform vec2 sunH; uniform vec3 canopy;
      varying vec2 vUv; varying vec3 vWorld;
      #include <fog_pars_fragment>
      float hash(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
      float vnoise(vec2 p) {
        vec2 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
        return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
      }
      float trees(vec2 p) { return 0.62 * vnoise(p * (1.0 / 6.2)) + 0.38 * vnoise(p * (1.0 / 2.7) + 31.0); }
      void main() {
        vec2 p = vWorld.xz;
        vec3 g = texture2D(groundMap, vUv).rgb;
        float f = texture2D(forestMap, vUv).r;
        float r = texture2D(rockMap, vUv).r;
        float fp = length(fwidth(p));                       // meters covered by this pixel

        // rock: sharp-edged outcrops up close, averaged coverage far away
        float rockT = r;
        float rw = 1.0 - smoothstep(3.0, 12.0, fp);
        if (rw > 0.0 && r > 0.01) {
          float rn = 0.5 * vnoise(p * (1.0 / 9.0)) + 0.3 * vnoise(p * (1.0 / 3.6) + 17.0) + 0.2 * vnoise(p * (1.0 / 1.5) + 5.0);
          float th = 0.95 - 0.9 * r;
          rockT = mix(r, smoothstep(th - 0.035, th + 0.035, rn), rw);
        }
        float lw = 1.0 - smoothstep(1.5, 5.0, fp);
        if (lw > 0.0 && r > 0.01) {                          // broken snow ledges roughly following the contours
          float band = vnoise(vec2(dot(p, vec2(0.6, 0.8)) / 90.0, vWorld.y / 6.0 + vnoise(p / 40.0) * 3.0));
          float ledge = smoothstep(0.62, 0.74, band) * smoothstep(0.35, 0.65, vnoise(p / 28.0 + 2.0));
          rockT *= 1.0 - 0.6 * ledge * lw;
        }
        vec3 rockC = g * vec3(0.45, 0.43, 0.41) * (0.55 + 0.5 * vnoise(p * (1.0 / 6.0) + 3.0) + 0.3 * vnoise(p * (1.0 / 2.2) + 9.0));
        float near = 1.0 - smoothstep(2.0, 8.0, fp);          // wind texture in nearby snow
        vec3 snowG = g * (1.0 + (0.6 * vnoise(p * (1.0 / 9.0)) + 0.4 * vnoise(p * (1.0 / 3.0) + 4.0) - 0.5) * 0.07 * near);
        vec3 base = mix(snowG, rockC, rockT * 0.95);

        // forest: clumps at middle distance, single trees and their shadows up close
        float thr = 1.0 - f * 0.82;
        float cover = 1.0 - smoothstep(0.22, 0.78, thr);
        float t = cover, sh = cover * (1.0 - cover) * 0.8;
        if (f > 0.01) {
          float mw = 1.0 - smoothstep(7.0, 20.0, fp);
          if (mw > 0.0) {
            float cn = 0.55 * vnoise(p * (1.0 / 18.0) + 7.0) + 0.45 * vnoise(p * (1.0 / 8.5) + 3.0);
            t = mix(cover, smoothstep(thr - 0.09, thr + 0.09, cn), mw * 0.9);
          }
          float nw = 1.0 - smoothstep(2.0, 6.0, fp);
          if (nw > 0.0) {
            float tn = smoothstep(thr - 0.07, thr + 0.07, trees(p));
            float ts = smoothstep(thr - 0.07, thr + 0.07, trees(p + sunH * 7.0)) * (1.0 - tn);
            t = mix(t, tn, nw); sh = mix(sh, ts, nw);
          }
        }
        float lum = dot(g, vec3(0.299, 0.587, 0.114));
        float lit = smoothstep(0.72, 0.88, lum);
        vec3 ground = base * mix(vec3(1.0), vec3(0.6, 0.66, 0.78), sh * lit);
        vec3 cc = g * canopy * (0.85 + 0.45 * vnoise(p * (1.0 / 3.3)));
        gl_FragColor = vec4(mix(ground, cc, t), 1.0);
        #include <fog_fragment>
      }`,
    fog: true,
    extensions: { derivatives: true }
  });
  tmat.uniforms.groundMap.value = groundTex;
  tmat.uniforms.forestMap.value = forestTex;
  tmat.uniforms.rockMap.value = rockTex;
  scene.add(new THREE.Mesh(tgeo, tmat));

  /* foothills around the terrain tile: snow-lit color and forest density per vertex, forest texture per pixel */
  const floorH = meta.hMin - 4, SNOW = new THREE.Color(0xE3E8EF), SK = 76000, SN = 160, SV = SN + 1;
  const ramp = (x, z) => smooth(5000, 11000, Math.max(Math.abs(x), Math.abs(z)));
  const hill = (x, z) => {
    const w = ramp(x, z);
    return w <= 0 ? floorH : floorH + w * (150 + 1600 * ridged(x / 14000 + 3.3, z / 14000 + 1.1, 5) + 320 * fbm(x / 5000, z / 5000, 3));
  };
  const spos = new Float32Array(SV * SV * 3), stint = new Float32Array(SV * SV * 3), swoods = new Float32Array(SV * SV);
  const flatShade = 0.5 + 0.7 * sun.y;
  for (let j = 0; j < SV; j++) for (let i = 0; i < SV; i++) {
    const k = j * SV + i, x = -SK / 2 + i / SN * SK, z = -SK / 2 + j / SN * SK, h = hill(x, z), e = 160;
    const nx = hill(x - e, z) - hill(x + e, z), nz = hill(x, z - e) - hill(x, z + e), ny = 2 * e, nl = Math.hypot(nx, ny, nz);
    const ndl = Math.max(0, (nx * sun.x + ny * sun.y + nz * sun.z) / nl);
    const shade = Math.min(1.12, Math.max(0.5, (0.5 + 0.7 * ndl) / flatShade));
    const snowLine = smooth(0.34, 0.66, (h - floorH) / 1700 + 0.2 * (fbm(x / 4000, z / 4000, 2) - 0.5));
    spos[k * 3] = x; spos[k * 3 + 1] = h; spos[k * 3 + 2] = z;
    stint[k * 3] = SNOW.r * shade; stint[k * 3 + 1] = SNOW.g * shade; stint[k * 3 + 2] = SNOW.b * shade;
    swoods[k] = (1 - snowLine) * (0.45 + 0.4 * smooth(0.35, 0.62, fbm(x / 2600 + 7, z / 2600 + 3, 3)));
  }
  const sidx = new Uint32Array(SN * SN * 6); q = 0;
  for (let j = 0; j < SN; j++) for (let i = 0; i < SN; i++) { const a = j * SV + i, b = a + 1, c = a + SV, d = c + 1; sidx[q++] = a; sidx[q++] = c; sidx[q++] = b; sidx[q++] = b; sidx[q++] = c; sidx[q++] = d; }
  const sgeo = new THREE.BufferGeometry();
  sgeo.setAttribute("position", new THREE.BufferAttribute(spos, 3));
  sgeo.setAttribute("tint", new THREE.BufferAttribute(stint, 3));
  sgeo.setAttribute("woods", new THREE.BufferAttribute(swoods, 1));
  sgeo.setIndex(new THREE.BufferAttribute(sidx, 1));
  const smat = new THREE.ShaderMaterial({
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { canopy: { value: new THREE.Vector3(meta.canopy[0], meta.canopy[1], meta.canopy[2]) } }]),
    vertexShader: `
      attribute vec3 tint; attribute float woods;
      varying vec3 vTint; varying float vWoods; varying vec3 vWorld;
      #include <fog_pars_vertex>
      void main() {
        vTint = tint; vWoods = woods;
        vec4 wp = modelMatrix * vec4(position, 1.0); vWorld = wp.xyz;
        vec4 mvPosition = viewMatrix * wp; gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: `
      uniform vec3 canopy; varying vec3 vTint; varying float vWoods; varying vec3 vWorld;
      #include <fog_pars_fragment>
      float hash(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
      float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
        return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y); }
      void main() {
        vec2 p = vWorld.xz;
        float fp = length(fwidth(p));
        float n = 0.5 * vnoise(p / 260.0) + 0.3 * vnoise(p / 95.0 + 11.0) + 0.2 * vnoise(p / 36.0 + 5.0);
        float thr = 1.0 - vWoods;
        float w = mix(smoothstep(thr - 0.07, thr + 0.07, n), vWoods, smoothstep(60.0, 160.0, fp));
        gl_FragColor = vec4(mix(vTint, vTint * canopy * 1.25, w), 1.0);
        #include <fog_fragment>
      }`,
    fog: true, extensions: { derivatives: true }
  });
  scene.add(new THREE.Mesh(sgeo, smat));

  /* distant ranges: hazy silhouettes, lit or backlit depending on where the sun is */
  const sunAz = Math.atan2(sun.z, sun.x);
  function range(R, peak, contrast, seed) {
    const M = 720, rp = new Float32Array((M + 1) * 3 * 3), rc = new Float32Array((M + 1) * 3 * 3), ri = [];
    const LIT = new THREE.Color(0xF4F7FA), BACK = new THREE.Color(0x71859E);
    for (let m = 0; m <= M; m++) {
      const a = m / M * Math.PI * 2, cx = Math.cos(a), cz = Math.sin(a);
      const h = peak * (0.25 + 0.75 * ridged(cx * 3.2 + seed, cz * 3.2 - seed, 6)) + 300 * fbm(cx * 9 + seed, cz * 9, 3);
      const facing = -Math.cos(a - sunAz);           // > 0: the side we see faces the sun
      const top = HORIZON.clone().lerp(facing > 0 ? LIT : BACK, contrast * (0.35 + 0.65 * Math.abs(facing)));
      const mid = HORIZON.clone().lerp(top, 0.55);
      const ys = [-800, h * 0.55, h], cs = [HORIZON, mid, top];
      for (let r = 0; r < 3; r++) {
        const o = (m * 3 + r) * 3; rp[o] = cx * R; rp[o + 1] = ys[r]; rp[o + 2] = cz * R;
        rc[o] = cs[r].r; rc[o + 1] = cs[r].g; rc[o + 2] = cs[r].b;
      }
      if (m < M) for (let r = 0; r < 2; r++) { const a0 = m * 3 + r, b0 = a0 + 1, c0 = a0 + 3, d0 = c0 + 1; ri.push(a0, b0, c0, b0, d0, c0); }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(rp, 3)); g.setAttribute("color", new THREE.BufferAttribute(rc, 3)); g.setIndex(ri);
    const mesh = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true, fog: false, side: THREE.DoubleSide }));
    mesh.renderOrder = -1; return mesh;
  }
  scene.add(range(52000, 4200, 0.30, 11.1));
  scene.add(range(40000, 3000, 0.48, 4.7));

  /* sky */
  const sky = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 24), new THREE.ShaderMaterial({
    uniforms: { zenith: { value: ZENITH }, horizon: { value: HORIZON }, glow: { value: SUNGLOW }, sunDir: { value: sun } },
    vertexShader: `varying vec3 vDir; void main() { vDir = position; gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0); gl_Position.z = gl_Position.w; }`,
    fragmentShader: `
      uniform vec3 zenith; uniform vec3 horizon; uniform vec3 glow; uniform vec3 sunDir; varying vec3 vDir;
      void main() {
        vec3 d = normalize(vDir);
        float t = pow(clamp(d.y, 0.0, 1.0), 0.42);
        vec3 col = mix(horizon, zenith, t);
        float s = max(dot(d, sunDir), 0.0);
        col += glow * (0.22 * pow(s, 5.0) + 0.5 * pow(s, 60.0)) * (1.0 - 0.5 * t);
        col = mix(col, vec3(1.0, 0.99, 0.96), smoothstep(0.99955, 0.9998, s));
        col = mix(col, horizon, smoothstep(0.0, -0.05, d.y));
        gl_FragColor = vec4(col, 1.0);
      }`,
    side: THREE.BackSide, depthWrite: false, depthTest: false, fog: false
  }));
  sky.renderOrder = -2; sky.scale.setScalar(1000);
  scene.add(sky);

  /* drone camera: slow orbit around the summit, level horizon, steady altitude above the ground */
  const camera = new THREE.PerspectiveCamera(50, 2, 20, 120000);
  const S = meta.summit, A0 = meta.faceAz + 0.62, RAD = 4300;
  const groundMax = (x, z) => { let m = -1e9; for (let k = 0; k < 9; k++) { const a = k / 9 * Math.PI * 2, r = k ? 420 : 0; const h = hAt(x + Math.cos(a) * r, z + Math.sin(a) * r); if (h > m) m = h; } return m; };
  let camY = null;
  const target = new THREE.Vector3();
  function place(t, dt) {
    const a = A0 + t * 0.017;
    const R = RAD - 380 * Math.sin(t * 0.021);
    const x = S.x + Math.cos(a) * R, z = S.z + Math.sin(a) * R;
    let ahead = groundMax(x, z);
    for (let k = 1; k <= 3; k++) ahead = Math.max(ahead, groundMax(S.x + Math.cos(a + k * 0.05) * R, S.z + Math.sin(a + k * 0.05) * R));
    const want = Math.max(ahead + 520, S.h * 0.74);
    camY = camY === null ? want : camY + (want - camY) * Math.min(1, dt * 0.6);
    camera.position.set(x, camY + 12 * Math.sin(t * 0.31), z);
    const ta = a + Math.PI + 0.16;                                    // look past the summit, slightly ahead of the turn
    target.set(S.x + Math.cos(ta) * 300, S.h * 0.5, S.z + Math.sin(ta) * 300);
    camera.lookAt(target);
  }

  function resize() {
    const w = hero.clientWidth, h = hero.clientHeight; if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = w / h < 1 ? 66 : 50;
    camera.updateProjectionMatrix();
  }
  resize();
  if (window.ResizeObserver) new ResizeObserver(resize).observe(hero); else addEventListener("resize", resize);

  let t = Number(new URLSearchParams(location.search).get("flyT")) || 0;   // ?flyT=60 jumps ahead (testing)
  let last = performance.now(), running = !reduce, visible = true, shown = false, queued = false;
  function frame(now) {
    queued = false;
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    if (running) t += dt;
    place(t, shown ? dt : 1);
    sky.position.copy(camera.position);
    renderer.render(scene, camera);
    if (!shown) { shown = true; hero.classList.add("ready"); }
    if (running && visible && !document.hidden) kick();
  }
  function kick() { if (!queued) { queued = true; requestAnimationFrame(frame); } }
  last = performance.now(); kick();

  if (reduce && btn) btn.hidden = true;
  if (btn) btn.addEventListener("click", () => {
    running = !running;
    btn.setAttribute("aria-pressed", String(!running));
    btn.textContent = running ? "Pause flyover" : "Play flyover";
    if (running) { last = performance.now(); kick(); }
  });
  if (window.IntersectionObserver) new IntersectionObserver(es => { visible = es[0].isIntersecting; if (visible && running) { last = performance.now(); kick(); } }).observe(hero);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && running && visible) { last = performance.now(); kick(); } });
}

// Load after the page itself, so the flyover never delays the headline or the resort list.
const go = () => (window.requestIdleCallback ? requestIdleCallback(start, { timeout: 1500 }) : setTimeout(start, 200));
if (document.readyState === "complete") go(); else addEventListener("load", go);
})();
