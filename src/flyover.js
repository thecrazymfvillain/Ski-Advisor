/* Drone-style flyover: a procedural mountain with ski runs, orbited by a slow, banking camera.
   Needs THREE (r128 UMD). Falls back to the static SVG silhouette behind the canvas. */
(function(){
"use strict";
const hero = document.getElementById("flyHero");
const canvas = document.getElementById("flyover");
if(!hero || !canvas) return;
const btn = document.getElementById("flyPause");
const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
if(!window.THREE){ if(btn) btn.hidden = true; return; }

let renderer;
try{ renderer = new THREE.WebGLRenderer({canvas, antialias:true, powerPreference:"low-power"}); }
catch(e){ if(btn) btn.hidden = true; return; }
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

/* ---- noise ---- */
function hash(x, y){
  let h = (Math.imul(x|0, 374761393) + Math.imul(y|0, 668265263)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}
function vnoise(x, y){
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf*xf*(3-2*xf), v = yf*yf*(3-2*yf);
  const a = hash(xi,yi), b = hash(xi+1,yi), c = hash(xi,yi+1), d = hash(xi+1,yi+1);
  return a + (b-a)*u + (c-a)*v + (a-b-c+d)*u*v;
}
const ROT = [Math.cos(0.6), Math.sin(0.6)];
function ridged(x, y){
  let sum = 0, amp = 0.55, prev = 1;
  for(let o=0;o<6;o++){
    let n = 1 - Math.abs(vnoise(x, y)*2 - 1); n *= n;
    sum += n*amp*prev; prev = Math.min(1, n*1.6);
    const nx = (x*ROT[0] - y*ROT[1])*2.03, ny = (x*ROT[1] + y*ROT[0])*2.03;
    x = nx + 17.1; y = ny + 3.7; amp *= 0.5;
  }
  return sum;
}
function fbm(x, y){
  let s = 0, a = 0.5;
  for(let o=0;o<5;o++){ s += a*vnoise(x, y); const nx = (x*ROT[0]-y*ROT[1])*2.01, ny = (x*ROT[1]+y*ROT[0])*2.01; x = nx+5.3; y = ny+9.1; a *= 0.5; }
  return s;
}
const smooth = (a, b, t) => { const k = Math.min(1, Math.max(0, (t-a)/(b-a))); return k*k*(3-2*k); };

/* ---- terrain ---- */
const SIZE = 7200, SEG = 260;
function height(x, z){
  const r = Math.hypot(x, z);
  const summit = 640*Math.exp(-(r*r)/(2*520*520));
  const shoulder = 240*Math.exp(-((x+800)*(x+800)+(z-600)*(z-600))/(2*600*600));
  const ridges = ridged(x/1500 + 4.2, z/1500 + 1.3)*470;
  const rolling = fbm(x/2600 + 2.0, z/2600 + 8.0)*320;
  return ridges + rolling + summit + shoulder - 330;
}

const geo = new THREE.PlaneGeometry(SIZE, SIZE, SEG, SEG);
geo.rotateX(-Math.PI/2);
const pos = geo.attributes.position;
for(let i=0;i<pos.count;i++){ pos.setY(i, height(pos.getX(i), pos.getZ(i))); }
geo.computeVertexNormals();

const nrm = geo.attributes.normal;
const colors = new Float32Array(pos.count*3);
const SNOW = new THREE.Color(0xF2F6FA), ROCK = new THREE.Color(0x5A616B), TREE = new THREE.Color(0x1E3A2B), DARK = new THREE.Color(0x3B424C);
const TRAILS = [0.35, 1.25, 2.1, 3.0, 3.9, 4.8, 5.6];
const col = new THREE.Color();
for(let i=0;i<pos.count;i++){
  const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i), ny = nrm.getY(i);
  col.copy(SNOW);
  // forest below treeline, speckled so it reads as trees on snow
  const treeline = 110 + (fbm(x/600, z/600)-0.5)*200;
  let trees = smooth(treeline+40, treeline-80, y) * smooth(0.55, 0.8, ny);
  trees *= smooth(0.3, 0.75, fbm(x/26 + 1.7, z/26 + 2.9));
  // ski runs cut through the trees, radiating from the summit
  const r = Math.hypot(x, z);
  if(r > 160 && r < 2200){
    const th = Math.atan2(z, x) + Math.PI;
    for(const t0 of TRAILS){
      const wob = 0.12*Math.sin(r/300 + t0*3) + 0.03*Math.sin(r/110 + t0);
      let d = Math.abs(th - t0 - wob); d = Math.min(d, Math.PI*2 - d);
      if(d*r < 24 + r*0.016){ trees *= 0.04; break; }
    }
  }
  col.lerp(TREE, Math.min(0.8, trees));
  // exposed rock on steep faces
  const rock = smooth(0.7, 0.46, ny);
  col.lerp(ny < 0.4 ? DARK : ROCK, rock*0.85);
  colors[i*3] = col.r; colors[i*3+1] = col.g; colors[i*3+2] = col.b;
}
geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

const scene = new THREE.Scene();
const HORIZON = 0xD6E3EF;
const sky = document.createElement("canvas"); sky.width = 4; sky.height = 256;
const sg = sky.getContext("2d"), grad = sg.createLinearGradient(0,0,0,256);
grad.addColorStop(0, "#3F6FB0"); grad.addColorStop(0.55, "#9CBBDD"); grad.addColorStop(1, "#D6E3EF");
sg.fillStyle = grad; sg.fillRect(0,0,4,256);
scene.background = new THREE.CanvasTexture(sky);
scene.fog = new THREE.Fog(HORIZON, 2200, 6400);

const terrain = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({vertexColors:true}));
scene.add(terrain);
scene.add(new THREE.HemisphereLight(0xD6E6F8, 0x4A515C, 0.78));
const sun = new THREE.DirectionalLight(0xFFE6C8, 0.8);
sun.position.set(-1, 0.55, -0.7);
scene.add(sun);

// light snowfall around the camera
const FLAKES = 900, BOX = 520;
const fpos = new Float32Array(FLAKES*3);
for(let i=0;i<FLAKES;i++){
  let x, y, z; do { x = (Math.random()-.5)*BOX; y = (Math.random()-.5)*BOX; z = (Math.random()-.5)*BOX; } while(Math.hypot(x, z) < 60);
  fpos[i*3] = x; fpos[i*3+1] = y; fpos[i*3+2] = z;
}
const dot = document.createElement("canvas"); dot.width = dot.height = 32;
const dg = dot.getContext("2d"), rg = dg.createRadialGradient(16,16,0,16,16,16);
rg.addColorStop(0, "rgba(255,255,255,1)"); rg.addColorStop(0.5, "rgba(255,255,255,.6)"); rg.addColorStop(1, "rgba(255,255,255,0)");
dg.fillStyle = rg; dg.fillRect(0,0,32,32);
const fgeo = new THREE.BufferGeometry(); fgeo.setAttribute("position", new THREE.BufferAttribute(fpos, 3));
const flakes = new THREE.Points(fgeo, new THREE.PointsMaterial({color:0xFFFFFF, size:3.2, map:new THREE.CanvasTexture(dot), transparent:true, opacity:0.8, depthWrite:false}));
scene.add(flakes);

const camera = new THREE.PerspectiveCamera(50, 2, 5, 12000);
let camY = height(2100, 0) + 420;

function resize(){
  const w = hero.clientWidth, h = hero.clientHeight;
  if(!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w/h;
  camera.fov = w < 600 ? 62 : 50;
  camera.updateProjectionMatrix();
}
resize();
if(window.ResizeObserver) new ResizeObserver(resize).observe(hero); else addEventListener("resize", resize);

let t = 18, last = performance.now(), running = !reduce, visible = true, shown = false;
function frame(now){
  const dt = Math.min(0.05, (now - last)/1000); last = now;
  if(running) t += dt;
  const a = t*0.045;
  const R = 2100 + 220*Math.sin(t*0.05);
  const cx = Math.cos(a)*R, cz = Math.sin(a)*R;
  let ground = 0;
  for(let k=0;k<4;k++){ const aa = a + k*0.05; ground = Math.max(ground, height(Math.cos(aa)*R, Math.sin(aa)*R)); }
  camY += ((ground + 420) - camY) * Math.min(1, dt*0.8);
  camera.position.set(cx, camY + 18*Math.sin(t*0.4), cz);
  const ta = a + 0.4;
  camera.lookAt(Math.cos(ta)*320, 220, Math.sin(ta)*320);
  camera.rotateZ(0.035*Math.sin(t*0.23));
  // snow follows the camera
  const p = fgeo.attributes.position;
  for(let i=0;i<FLAKES;i++){
    let y = p.getY(i) - dt*28*(running?1:0); if(y < -BOX/2) y += BOX;
    p.setY(i, y);
  }
  p.needsUpdate = true;
  flakes.position.copy(camera.position);
  renderer.render(scene, camera);
  if(!shown){ shown = true; hero.classList.add("ready"); }
  if(running && visible && !document.hidden) requestAnimationFrame(frame);
}
function kick(){ last = performance.now(); requestAnimationFrame(frame); }
kick();

if(reduce){ if(btn) btn.hidden = true; }
if(btn){
  btn.addEventListener("click", ()=>{
    running = !running;
    btn.setAttribute("aria-pressed", String(!running));
    btn.textContent = running ? "Pause flyover" : "Play flyover";
    if(running) kick();
  });
}
if(window.IntersectionObserver){
  new IntersectionObserver(es=>{ const was = visible; visible = es[0].isIntersecting; if(visible && !was && running) kick(); }).observe(hero);
}
document.addEventListener("visibilitychange", ()=>{ if(!document.hidden && running && visible) kick(); });
})();
