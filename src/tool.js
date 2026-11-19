(function(){
"use strict";
const PI = (document.getElementById("pageInfo") || document.body).dataset;

/* ---------- Data ---------- */
// Each page carries the resorts it shows (and which weather group to load) in #resortData.
const RD = (()=>{ try{ return JSON.parse((document.getElementById("resortData")||{}).textContent || "{}"); }catch(e){ return {}; } })();
const RESORTS = RD.resorts || [];

const STYLES = {
  cruiser:{label:"Cruiser", sub:"Groomers, relaxed pace", sym:"circle", base:1, side:1,
    detune:"Dull the first and last few centimeters of edge, past the tip and tail contact points, so the ski doesn't hook."},
  allmtn:{label:"All-mountain", sub:"Some of everything", sym:"square", base:1, side:2,
    detune:"Lightly dull the edge just past the tip and tail contact points. Leave the rest sharp."},
  carver:{label:"Carver", sub:"Hard snow, high edge angles", sym:"diamond", base:0.7, side:3,
    detune:"Barely touch the contact points, if at all. You want the whole edge working."},
  racer:{label:"Racer", sub:"Gates, GS and slalom", sym:"double", base:0.5, side:3,
    detune:"No detune. Race skis use the full length of the edge."},
  park:{label:"Park", sub:"Rails, boxes, jumps", sym:"park", base:1, side:1,
    detune:"Detune tip and tail firmly, and lightly underfoot, so the edges don't catch on rails and boxes."},
  powder:{label:"Powder", sub:"Off-piste, soft snow", sym:"pow", base:1, side:1,
    detune:"Light detune at tip and tail. Soft snow doesn't need a razor edge."},
  snowboard:{label:"Snowboard", sub:"Any board, any terrain", sym:"board", base:1, side:1,
    detune:"Lightly dull the edge at the nose and tail contact points so the board doesn't catch. Park riders detune more; carvers barely at all."}
};

// Coldest → warmest. lo/hi = snow-temperature range in °C as printed on typical wax labels.
const BANDS = [
  {id:"polar",  name:"Polar",     color:"var(--wax-polar)",  lo:-30, hi:-15, iron:150, ex:"Swix PS Polar or a polar/arctic wax",  race:"Swix HS5 Turquoise"},
  {id:"turq",   name:"Turquoise", color:"var(--wax-turq)",   lo:-18, hi:-10, iron:145, ex:"Swix PS5 Turquoise or a very cold wax", race:"Swix HS5 Turquoise"},
  {id:"blue",   name:"Blue",      color:"var(--wax-blue)",   lo:-12, hi:-6,  iron:140, ex:"Swix PS6 Blue or a cold wax",           race:"Swix HS6 Blue"},
  {id:"violet", name:"Violet",    color:"var(--wax-violet)", lo:-8,  hi:-2,  iron:135, ex:"Swix PS7 Violet or a cool/mid wax",     race:"Swix HS7 Violet"},
  {id:"red",    name:"Red",       color:"var(--wax-red)",    lo:-4,  hi:4,   iron:130, ex:"Swix PS8 Red or a mild wax",            race:"Swix HS8 Red"},
  {id:"yellow", name:"Yellow",    color:"var(--wax-yellow)", lo:0,   hi:10,  iron:120, ex:"Swix PS10 Yellow or a warm wax",        race:"Swix HS10 Yellow"}
];
// Non-overlapping picking thresholds on the strip (°C): segment edges.
const STRIP_MIN = -24, STRIP_MAX = 6;
const SEG = [[-24,-17],[-17,-11],[-11,-7],[-7,-3],[-3,1],[1,6]];

const SURFACES = {
  new:{label:"New snow"}, packed:{label:"Packed groomers"}, refrozen:{label:"Refrozen / firm"},
  manmade:{label:"Man-made"}, wet:{label:"Wet / spring"}
};

const WMO = c => c===0?"Clear":c<=2?"Partly cloudy":c===3?"Overcast":(c===45||c===48)?"Fog":
  (c>=51&&c<=67)?"Rain or drizzle":(c>=71&&c<=77)?"Snowing":(c>=80&&c<=82)?"Showers":
  (c===85||c===86)?"Snow showers":c>=95?"Storms":"—";

/* ---------- State ---------- */
const store = {
  get(k, d){ try{ const v = localStorage.getItem("ew:"+k); return v===null? d : JSON.parse(v); }catch(e){ return d; } },
  set(k, v){ try{ localStorage.setItem("ew:"+k, JSON.stringify(v)); }catch(e){} }
};
const state = {
  resort: PI.resort || "vail",
  unit: store.get("unit","F"),
  day: "today",
  wkPick: null,   // weekend: 0 = Saturday, 1 = Sunday, null = the colder day
  style: store.get("style","allmtn"),
  raceMode: store.get("raceMode","race") === "training" ? "training" : "race",
  adj: {air:null, snow48:null, surface:"auto"},
  live: null,          // {id: conditions}
  updatedAt: null,
  diag: null,          // {base, side} when user overrides diagram
  done: store.get("done", {})
};
if(!RESORTS.some(r=>r.id===state.resort)) state.resort="vail";
if(!STYLES[state.style]) state.style="allmtn";
if(state.unit!=="F" && state.unit!=="C") state.unit="F";

/* ---------- Formatting ---------- */
const $ = id => document.getElementById(id);
const c2f = c => c*9/5+32;
function num(v, d){ const r = Number(v.toFixed(d)); return (r<0?"−":"") + Math.abs(r).toFixed(d); }
function fmtT(c, d=0){ const v = state.unit==="F"? c2f(c) : c; return num(Object.is(Math.round(v),-0)?0:v, d)+"°"+state.unit; }
function fmtTshort(c){ const v = state.unit==="F"? c2f(c) : c; return num(v,0)+"°"; }
function fmtSnow(cm){ if(state.unit==="F"){ const i=cm/2.54; return (i>0&&i<1? i.toFixed(1): Math.round(i))+" in"; } return Math.round(cm)+" cm"; }
function fmtElev(m){ return state.unit==="F"? (Math.round(m*3.28084/10)*10).toLocaleString("en-US")+" ft" : m.toLocaleString("en-US")+" m"; }
function fmtIron(c){ return state.unit==="F"? Math.round(c2f(c)/5)*5+"°F" : c+"°C"; }
function fmtRange(b){ return state.unit==="F"? `${Math.round(c2f(b.lo))}° to ${Math.round(c2f(b.hi))}°F` : `${num(b.lo,0)}° to ${b.hi>0?"+":""}${num(b.hi,0)}°C`; }
const resort = () => RESORTS.find(r=>r.id===state.resort);

/* ---------- Conditions logic ---------- */
function rawConditions(){
  const r = resort();
  return (state.live && state.live[r.id]) || r.ex;
}
// A week of daily forecasts, index 0 = today. Live data supplies it; example data synthesizes one.
function dayList(raw){
  if(raw.days && raw.days.length >= 3) return raw.days;
  const now = new Date(), out = [];
  for(let i=0;i<8;i++){
    const date = new Date(now.getFullYear(), now.getMonth(), now.getDate()+i), dow = date.getDay();
    let min = raw.tmrMin, max = raw.tmrMax, snow = 0;
    if(i===0){ min = raw.air-3; max = raw.air+2; snow = raw.snow48/2; }
    else if(i===1){ snow = raw.tmrSnow; }
    else if(dow===6){ min = raw.tmrMin-2; max = raw.tmrMax-1; snow = raw.snow48>=8 ? 6 : 1; }
    else if(dow===0){ min = raw.tmrMin+1; max = raw.tmrMax+2; }
    out.push({date, min, max, snow});
  }
  return out;
}
// Conditions for a forecast day: weight toward the skiing hours, count the day before's snow.
function forecastDay(days, i, raw){
  const d = days[i], prev = i>0 ? days[i-1] : null;
  return {
    air:(d.min + 2*d.max)/3,
    snow48:(prev ? prev.snow : raw.snow48/2) + d.snow,
    cloudy:d.snow>0.5,
    pastMax:Math.max(prev ? prev.max : raw.pastMax, d.max),
    rh:null,
    sky:d.snow>0.5 ? "Snow forecast" : "Mostly dry",
    date:d.date
  };
}
function finalize(b){
  const air = state.adj.air!==null ? state.adj.air : b.air;
  const snow48 = state.adj.snow48!==null ? state.adj.snow48 : b.snow48;
  // Snow surface can't exceed 0°C; clear skies radiate heat away so the surface runs colder than air.
  const snowTemp = Math.min(0, air - (b.cloudy? 0.5 : 1.5));
  let surface = state.adj.surface;
  if(surface==="auto"){
    if(air > 0.5) surface = "wet";
    else if(snow48 >= 8) surface = "new";
    else if(b.pastMax > 1) surface = "refrozen";
    else surface = "packed";
  }
  return Object.assign({}, b, {air, snow48, snowTemp, surface});
}
function conditions(){
  const raw = rawConditions();
  if(state.day==="today")
    return finalize({air:raw.air, snow48:raw.snow48, cloudy:raw.cloud>=60, pastMax:raw.pastMax, rh:raw.rh, sky:raw.sky || WMO(raw.code)});
  const days = dayList(raw);
  if(state.day==="tomorrow") return finalize(forecastDay(days, 1, raw));
  // Weekend: the next Saturday and Sunday (today and tomorrow if it's Saturday).
  let sat = days.findIndex(d=>d.date.getDay()===6);
  if(sat<0 || sat+1>=days.length) sat = Math.max(0, days.length-2);
  const idxs = [sat, sat+1];
  const both = idxs.map(i=>finalize(forecastDay(days, i, raw)));
  const picks = both.map(pickWax);
  // One wax job for two days: take the colder wax. It lasts longer and drags less if the forecast is off.
  const colder = picks[0].idx < picks[1].idx ? 0 : picks[1].idx < picks[0].idx ? 1 : (both[0].snowTemp <= both[1].snowTemp ? 0 : 1);
  const k = state.wkPick === 0 || state.wkPick === 1 ? state.wkPick : colder;   // Saturday/Sunday toggle
  const c = both[k];
  c.weekend = {
    daysOut: sat, chosen: k, colder, picked: k !== colder || state.wkPick !== null, differ: picks[0].idx!==picks[1].idx,
    days: idxs.map((i,j)=>({date:days[i].date, min:days[i].min, max:days[i].max, snow:days[i].snow, band:picks[j].band}))
  };
  return c;
}

function pickWax(c){
  const T = c.surface==="wet" ? Math.max(c.air, 0.5) : c.snowTemp;
  let seg = SEG.findIndex(([lo,hi]) => T>=lo && T<hi);
  if(seg<0) seg = T<STRIP_MIN? 0 : SEG.length-1;
  let idx = seg, shifted = null;
  if((c.surface==="new"||c.surface==="manmade") && idx>0){ idx -= 1; shifted = c.surface; }
  if(c.surface==="wet") idx = SEG.length-1;
  return {band:BANDS[idx], idx, T, shifted};
}

function pickEdges(c){
  const s = STYLES[state.style];
  const base = s.base, side = s.side;
  const hard = c.surface==="refrozen" || c.surface==="manmade";
  // Angles are a one-time setup for how you ski. Today's snow only changes how much edge work is worth doing.
  let note = `Typical settings for ${state.style==="snowboard" ? "snowboarding; riders who carve firm snow often use a 2° side edge" : s.label.toLowerCase()+" skiing"}. Most people set their angles once, usually at a shop, and keep them; you don't change angles for the conditions. Already have different angles? Keep yours and sharpen to match. `;
  if(hard) note += state.style==="park"
    ? `<strong>Firm snow today:</strong> sharpen the side edge at your current angle, and keep the tips and tails detuned so they don't catch on features.`
    : `<strong>Firm snow today:</strong> sharpen or polish the side edge at your current angle before you ski. On firm snow a sharp edge does most of the work.`;
  else if(c.surface==="new" || c.surface==="wet") note += `<strong>Soft snow today:</strong> edges matter less than usual. A quick deburr is enough if they're already in shape.`;
  else note += `<strong>Today:</strong> a quick polish with a fine stone is all most edges need.`;
  if(state.style==="racer") note += state.raceMode==="race"
    ? " <strong>Race day:</strong> give the side edge a final polish with a fine stone the night before."
    : " <strong>Training:</strong> a quick polish with a fine stone every couple of days keeps the edge consistent.";
  return {base, side, incl: 90 - side + base, note, hard};
}

/* ---------- Rendering: static pieces ---------- */
function symSVG(kind){
  const s = 'width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"';
  switch(kind){
    case "circle": return `<svg ${s}><circle cx="10" cy="10" r="8" fill="#2F9E44"/></svg>`;
    case "square": return `<svg ${s}><rect x="2" y="2" width="16" height="16" fill="#1F5FD1"/></svg>`;
    case "diamond": return `<svg ${s}><rect x="10" y="1.5" width="12" height="12" transform="rotate(45 10 1.5)" fill="currentColor"/></svg>`;
    case "double": return `<svg width="26" height="20" viewBox="0 0 26 20" aria-hidden="true"><rect x="7" y="3" width="9" height="9" transform="rotate(45 7 3)" fill="currentColor"/><rect x="19" y="3" width="9" height="9" transform="rotate(45 19 3)" fill="currentColor"/></svg>`;
    case "board": return `<svg ${s}><rect x="7.2" y="0.8" width="5.6" height="18.4" rx="2.8" transform="rotate(35 10 10)" fill="currentColor"/></svg>`;
    case "park": return `<svg ${s}><rect x="1" y="4" width="18" height="12" rx="6" fill="var(--sym-park)"/></svg>`;
    default: return `<svg ${s}><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 2v16M3 6l14 8M17 6L3 14"/></g></svg>`;
  }
}

function buildStyles(){
  $("styles").innerHTML = Object.entries(STYLES).map(([k,s]) =>
    `<button type="button" class="style-btn" data-k="${k}" aria-pressed="${k===state.style}"><span class="sym">${symSVG(s.sym)}</span><span><b>${s.label}</b><span class="s">${s.sub}</span></span></button>`).join("");
  $("styles").addEventListener("click", e => {
    const b = e.target.closest(".style-btn"); if(!b) return;
    state.style = b.dataset.k; store.set("style", state.style); state.diag = null; render();
  });
}
function buildStripBands(){
  $("stripBands").innerHTML = SEG.map(([lo,hi],i) =>
    `<span data-i="${i}" style="width:${(hi-lo)/(STRIP_MAX-STRIP_MIN)*100}%;background:${BANDS[i].color}"></span>`).join("");
}
function buildTicks(){
  const pos = c => (Math.min(STRIP_MAX,Math.max(STRIP_MIN,c))-STRIP_MIN)/(STRIP_MAX-STRIP_MIN)*100;
  const ticks = state.unit==="F" ? [-10,0,10,20,30,40].map(f=>({c:(f-32)*5/9, t:f+"°"})) : [-20,-15,-10,-5,0,5].map(c=>({c, t:num(c,0)+"°"}));
  $("stripTicks").innerHTML = ticks.filter(t=>t.c>STRIP_MIN && t.c<STRIP_MAX).map(t=>`<span style="left:${pos(t.c)}%">${t.t}</span>`).join("");
  return pos;
}
function buildSnowSelect(){
  const opts = [0,3,8,15,25,40];
  const cur = $("snowSel").value;
  $("snowSel").innerHTML = `<option value="">From forecast</option>` + opts.map(cm=>`<option value="${cm}">${cm===0?"None":fmtSnow(cm)}${cm===40?"+":""}</option>`).join("");
  $("snowSel").value = cur;
}

/* ---------- Edge diagram ---------- */
function edgeSVG(b, s){
  const k=5, B=b*k*Math.PI/180, S=s*k*Math.PI/180;
  const x0=118, R=356, baseY=166, L=76, topY=26, steelTop=124, baseThick=16;
  const C={x:x0, y:baseY - L*Math.sin(B)};
  const E={x:x0 + L*Math.cos(B), y:baseY};
  const sx = y => x0 + (C.y - y)*Math.tan(S);
  const P = pts => pts.map(p=>p.map(v=>v.toFixed(1)).join(",")).join(" ");
  const core = P([[sx(topY),topY],[R,topY],[R,baseY-baseThick],[E.x,baseY-baseThick],[E.x,steelTop],[sx(steelTop),steelTop]]);
  const steel = P([[sx(steelTop),steelTop],[E.x,steelTop],[E.x,E.y],[C.x,C.y]]);
  const base = P([[E.x,baseY-baseThick],[R,baseY-baseThick],[R,baseY],[E.x,baseY]]);
  const cutSide = P([[C.x,C.y],[x0,topY],[sx(topY),topY]]);
  const cutBase = P([[x0,baseY],[E.x,E.y],[C.x,C.y]]);
  const incl = 90 - s + b;
  return `<svg viewBox="0 0 370 222" role="img" aria-label="Edge cross-section: base bevel ${b} degrees, side bevel ${s} degrees, edge angle ${incl} degrees">
    <rect class="d-snow" x="0" y="${baseY}" width="370" height="56"/>
    <text class="d-sub" x="${R-4}" y="${baseY+22}" text-anchor="end">snow</text>
    <polygon class="d-core" points="${core}"/>
    <polygon class="d-base" points="${base}"/>
    <polygon class="d-steel" points="${steel}"/>
    <polygon class="d-cut" points="${cutSide}"/>
    <polygon class="d-cut" points="${cutBase}"/>
    <line class="d-ref" x1="${x0}" y1="${topY}" x2="${x0}" y2="${baseY}"/>
    <line class="d-ref" x1="${x0-26}" y1="${baseY}" x2="${E.x}" y2="${baseY}"/>
    <text class="d-sub" x="${(R+E.x)/2}" y="${(baseY-baseThick+steelTop)/2 - 18}" text-anchor="middle">ski core</text>
    <text class="d-sub" x="${(R+E.x)/2+20}" y="${baseY-4}" text-anchor="middle" style="fill:#F2F5F8">base</text>
    <text class="d-sub" x="${x0+L/2}" y="${steelTop-6}" text-anchor="middle">steel edge</text>
    <text class="d-txt" x="${x0-10}" y="74" text-anchor="end">side ${s}°</text>
    <text class="d-sub" x="${x0-10}" y="90" text-anchor="end">bevel</text>
    <text class="d-txt" x="${x0+L+6}" y="${baseY+40}" text-anchor="start">base ${b}°</text>
    <text class="d-sub" x="${x0+L+6}" y="${baseY+54}" text-anchor="start">bevel</text>
    <path d="M${x0+L+2} ${baseY+30} L${x0+L/2} ${baseY+4}" stroke="var(--muted)" stroke-width="1" fill="none"/>
    <circle cx="${C.x}" cy="${C.y}" r="3.5" fill="var(--ink)"/>
    <text class="d-txt" x="${x0-10}" y="${baseY+40}" text-anchor="end">${incl}° edge</text>
    <path d="M${x0-12} ${baseY+30} L${C.x-3} ${C.y+3}" stroke="var(--muted)" stroke-width="1" fill="none"/>
  </svg>`;
}
function buildRadio(rowId, values, fmt, key){
  $(rowId).innerHTML = values.map(v=>`<button type="button" data-v="${v}" aria-pressed="false">${fmt(v)}</button>`).join("");
  $(rowId).addEventListener("click", e => {
    const b = e.target.closest("button"); if(!b) return;
    const rec = pickEdges(conditions());
    state.diag = Object.assign({base:rec.base, side:rec.side}, state.diag||{}, {[key]: Number(b.dataset.v)});
    renderDiagram(rec);
  });
}
function renderDiagram(rec){
  const d = state.diag || {base:rec.base, side:rec.side};
  $("diagram").innerHTML = edgeSVG(d.base, d.side);
  [["baseRow",d.base],["sideRow",d.side]].forEach(([id,v])=>{
    $(id).querySelectorAll("button").forEach(b=>b.setAttribute("aria-pressed", Number(b.dataset.v)===v));
  });
  const incl = 90 - d.side + d.base;
  const feel = d.side>=3 ? "a very sharp edge that grips ice and hard groomers, but catches easily if you're sloppy"
             : d.side===2 ? "a sharp, forgiving edge that suits most resort snow"
             : d.side===4 ? "race-room sharpness, mostly for slalom on injected snow"
             : "an easygoing edge that releases easily, good for soft snow and park";
  const roll = d.base<=0.5 ? "The low base bevel makes the ski bite the instant you tip it." : d.base>=1 ? "The 1° base bevel lets the ski roll onto its edge gradually." : "The 0.7° base bevel splits the difference: quick, but not twitchy.";
  $("diagramText").textContent = `${d.base}° base and ${d.side}° side give an included edge angle of ${incl}°: ${feel}. ${roll}`;
  $("diagReset").hidden = !state.diag;
}

/* ---------- Steps + kit ---------- */
// Snowboard wording for the same tune: nose and tail, one wide base, no brakes.
const boardText = t => t.replace(/tip to tail/g, "nose to tail").replace(/\bthe ski\b/g, "the board").replace(/tips and tails/g, "nose and tail").replace(/tip and tail/g, "nose and tail");
function boardify(step){
  const o = Object.assign({}, step);
  if(o.id==="setup"){ o.tools = "Snowboard vise or padded bench supports"; o.body = "Lay the board base-up on padded supports or a snowboard vise, one under each binding so the base sits flat. The bindings can stay on."; }
  if(o.id==="wax") o.body = o.body.replace("drip a line down each side of the base", "drip it in a zigzag across the whole base");
  if(o.id==="deburr") o.tip = "The contact points are where the base starts to lift off a flat surface near the nose and tail.";
  for(const k of ["t", "body", "tip", "tools"]) if(o[k]) o[k] = boardText(o[k]);
  return o;
}
function stepsFor(c, wax, edges){
  const r = resort(), st = STYLES[state.style], band = wax.band;
  const coldBand = wax.idx <= 2, racer = state.style==="racer", raceDay = racer && state.raceMode==="race";
  const list = [
    {id:"setup", t:"Set up the bench", m:"5 min", tools:"Vise or straps, rubber bands",
     body:"Clamp the ski base-up in a vise, or strap it flat to a table. Loop a thick rubber band over the brake arms to hold them up out of the way.",
     tip:"Run a fingernail across the edge in a few spots. If it catches or feels rough, give the edge steps extra time."},
    {id:"clean", t:"Clean the base", m:"10 min", tools:"Brass or nylon brush, soft wax, iron",
     body:"Brush tip to tail to open the base structure. If the base is dirty, hot-scrape it: iron on a soft, warm wax and scrape it off while it's still warm. It lifts dirt out of the base.",
     tip:"Skip citrus base cleaners unless the base is very dirty. They dry the base out."},
    {id:"repair", t:"Fill gouges (if any)", m:"15 min", tools:"P-tex candle, steel scraper",
     body:"Light a P-tex candle and drip it into the clean gouge, keeping the flame low so the drips stay clear, not black. Let it cool, then scrape flush with a sharp steel scraper.",
     tip:"If you can see wood or metal in the gouge, that's a core shot. Take it to a shop."},
    {id:"base", t:"Deburr the base edge", m:"10 min", tools:`Base guide at your existing base angle (often ${edges.base}°), fine diamond stone`,
     body:`Base bevel is set by the shop's grind, so at home you only maintain it. Put a fine diamond stone in a base guide at your skis' existing angle and make one or two light passes tip to tail to remove burrs.`,
     tip:"Taking too much off the base edge makes the ski feel vague. Less is more here."},
    {id:"side", t:"Sharpen the side edge", m:"15 min", tools:`Side guide at your existing angle (often ${edges.side}°, an ${90-edges.side}° edge), 200/400/600 diamond stones`, flag: edges.hard ? "Priority today" : null,
     body:`Set a side guide at your skis' existing angle on the edge. If you don't know it, a shop can tell you, or use the setting above. Work coarse to fine: 200 grit diamond, then 400, then 600, in long overlapping strokes tip to tail. Give every edge the same number of passes. Use a file only if the edge is badly damaged or you're changing the angle.` +
       (edges.hard ? ` Snow at ${r.name} is firm right now, so the side edge is the step that matters most.` : ""),
     tip:"Wet the diamond stones with water or alcohol. They cut cleaner and last longer."},
    {id:"deburr", t:"Deburr and detune", m:"5 min", tools:"Gummy stone",
     body:`Run a gummy stone lightly along the base and side edges to knock off the tiny burr the stones leave. ${st.detune}`,
     tip:"Find the contact points by laying the skis base to base: where they touch near tip and tail."},
    raceDay ?
    {id:"wax", t:`Hot wax: base layer, then ${band.name} race wax`, m:"25 min", tools:`Waxing iron, hard base-layer wax, ${band.race} or equivalent`, flag:"Race prep",
     body:`Iron in a hard, cold base-layer wax first, let it cool, then scrape and brush it out. It protects the base on abrasive race snow. Then iron in ${band.race} or an equivalent fluoro-free race wax at about ${fmtIron(band.iron)}, in slow, steady passes tip to tail. Keep the iron moving.` +
       (c.surface==="wet" ? " For wet snow, two thin race-wax layers beat one thick one." : ""),
     tip:"Many racers build two or three race-wax layers over the week before a race. Each layer adds durability. The wax label's iron temperature beats this number."}
    :
    {id:"wax", t:`Hot wax: ${band.name}${racer ? " training wax" : ""}`, m:"10 min", tools:`Waxing iron, ${band.name.toLowerCase()} wax`, flag: c.surface==="wet" ? "Wet snow" : null,
     body:`Set a dedicated waxing iron to about ${fmtIron(band.iron)}. Hold the wax bar against the iron and drip a line down each side of the base, then spread it in slow, steady passes tip to tail. Keep the iron moving. If the wax smokes, the iron is too hot. The topsheet should feel warm, never hot.` +
       (c.surface==="wet" ? " For wet snow, two thin coats beat one thick one." : ""),
     tip: racer ? "Training wax: one layer is enough. Man-made training snow strips wax fast, so re-wax every few training days."
        : "The temperature on the wax's own label beats this number. Colder, harder waxes need more heat."},
    {id:"cool", t:"Let it cool", m:"30 min+", tools:"Time",
     body:"Leave the ski at room temperature for at least 30 minutes, overnight if you can. Wax hardens as it cools, and scraping too early pulls it back out of the base.",
     tip: state.day==="weekend" ? "Tuning days before the trip? Leave this coat unscraped. It protects the base and edges while the skis travel. Scrape and brush the night before you ski."
        : state.day==="tomorrow" ? "Waxing the night before is ideal. Scrape and brush in the morning."
        : "Don't put warm skis outside to speed it up. Cooling too fast leaves less wax in the base."},
    {id:"scrape", t:"Scrape", m:"10 min", tools:"Plexi scraper",
     body:"Hold a plastic (plexi) scraper at a slight forward lean and pull it tip to tail until only fine dust comes off. Clear the edges and sidewalls with the scraper's notch.",
     tip:"Never use a metal scraper on wax. It gouges the base."},
    {id:"brush", t:"Brush and polish", m:"10 min", tools: coldBand ? "Brass, nylon brushes; polishing pad" : "Nylon, horsehair brushes; polishing pad", flag: c.surface==="wet" ? "Brush extra" : null,
     body: (coldBand ? "Cold, hard wax: start with a brass brush, then nylon, tip to tail, until the base shines." : "Start with a nylon brush, then horsehair, tip to tail, until the base shines.") +
       (c.surface==="wet" ? " Extra brushing reopens the base structure, which breaks the suction of wet snow." : "") +
       " Finish with a light buff from a Fibertex pad or polishing cloth." +
       (raceDay ? " Race morning: apply a fluoro-free top coat in the same temperature range, following its instructions, then cork or brush it in." : ""),
     tip:"Brush in one direction only, tip to tail."}
  ];
  return state.style==="snowboard" ? list.map(boardify) : list;
}
function renderSteps(c, wax, edges){
  const steps = stepsFor(c, wax, edges);
  const openIds = new Set([...$("steps").querySelectorAll("details[open]")].map(d=>d.dataset.id));
  $("steps").innerHTML = steps.map((s,i)=>{
    const done = !!state.done[s.id];
    return `<li class="step${done?" done":""}">
      <input type="checkbox" id="chk-${s.id}" data-id="${s.id}" ${done?"checked":""} aria-label="Mark step ${i+1} done">
      <details data-id="${s.id}" ${openIds.has(s.id)?"open":""}>
        <summary><span class="step-n">${String(i+1).padStart(2,"0")}</span><span class="step-t">${s.t}</span>${s.flag?`<span class="flag">${s.flag}</span>`:""}<span class="step-time">${s.m}</span></summary>
        <div class="step-body"><p>${s.body}</p><p class="step-tools"><b>Tools:</b> ${s.tools}</p><p class="tip">${s.tip}</p></div>
      </details></li>`;
  }).join("");
  const n = steps.filter(s=>state.done[s.id]).length;
  $("progBar").style.width = (n/steps.length*100)+"%";
  $("progText").textContent = `${n} of ${steps.length}`;
}
// Amazon Associates search link with our tracking tag (amazon.com; Amazon.ca is a separate program).
const AMAZON_TAG = "skiadvisor-20";
const amazonSearch = q => "https://www.amazon.com/s?k=" + encodeURIComponent(q) + "&tag=" + AMAZON_TAG;
function renderKit(wax, edges){
  const band = wax.band, training = state.style==="racer" && state.raceMode==="training";
  const racer = state.style==="racer" && !training;
  const items = [
    state.style==="snowboard" ? {n:"Snowboard vise or bench supports", w:"Holds the board flat and base-up while you work.", q:"snowboard tuning vise"}
      : {n:"Ski vise or straps", w:"Holds the ski steady and base-up while you work.", q:"ski tuning vise"},
    {n:"Waxing iron", w:"A dedicated iron holds a steady temperature. Clothes irons run hot and uneven.", q:"ski waxing iron"},
    racer ? {n:`${band.name} race wax`, w:`Fluoro-free race wax for snow ${fmtRange(band)}, such as ${band.race}.`, q:`${band.race} race wax`}
          : {n:`${band.name} ${training ? "training " : ""}wax`, w:`For snow ${fmtRange(band)}. ${band.ex}.`, q:`${band.ex.split(" or ")[0]} ski wax`},
    racer ? {n:"Base-layer wax", w:"A hard, cold wax ironed in under the race wax so it lasts on abrasive race snow.", q:"Swix cold base prep ski wax"}
          : {n:"Universal wax", w:"An all-temperature wax for cleaning and for weeks you don't want to think about it.", q:"Swix universal ski wax"},
    {n:"Plexi scraper", w:"Removes excess wax without hurting the base. Keep its edge sharp.", q:"ski wax scraper"},
    {n:"Brushes", w:"Brass, nylon and horsehair cover every wax and snow type.", q:"ski wax brush"},
    {n:"Base edge guide", w:`Matches your skis' base angle (often ${edges.base}°) so you only remove burrs.`, q:`${edges.base} degree base bevel guide`},
    {n:"Side edge guide", w:`Matches your skis' side angle (often ${edges.side}°, an ${90-edges.side}° edge) so every sharpening keeps it.`, q:`${edges.side} degree side edge guide`},
    {n:"Diamond stones", w:"200, 400 and 600 grit for sharpening and polishing the edge.", q:"diamond stone ski edge"},
    {n:"Gummy stone", w:"Takes off burrs and detunes tips and tails.", q:"gummy stone ski"},
    racer ? {n:"Race top coat", w:"A fluoro-free top coat (block, powder or liquid) for race morning, in the same temperature range.", q:"Swix fluoro free race top coat"}
          : {n:"P-tex candles", w:"Fills small base gouges at home.", q:"p-tex candle"},
    {n:"Polishing pad", w:"A Fibertex pad or cloth for the final buff.", q:"fibertex ski"}
  ];
  $("kitGrid").innerHTML = items.map(it =>
    `<div class="kit-item"><b>${it.n}</b><p>${it.w}</p><a href="${amazonSearch(it.q)}" target="_blank" rel="noopener sponsored">Shop on Amazon</a></div>`).join("");
}

/* ---------- Main render ---------- */
function render(){
  const r = resort(), c = conditions(), wax = pickWax(c), edges = pickEdges(c), band = wax.band;
  document.querySelectorAll("#styles .style-btn").forEach(b=>b.setAttribute("aria-pressed", b.dataset.k===state.style));
  $("unitF").setAttribute("aria-pressed", state.unit==="F"); $("unitC").setAttribute("aria-pressed", state.unit==="C");
  $("dayToday").setAttribute("aria-pressed", state.day==="today"); $("dayTomorrow").setAttribute("aria-pressed", state.day==="tomorrow");
  $("dayWeekend").setAttribute("aria-pressed", state.day==="weekend");

  $("heroEyebrow").textContent = `${{today:"Today",tomorrow:"Tomorrow",weekend:"This weekend"}[state.day]} · ${r.region} · mid-mountain, ${fmtElev(r.mid)}`;

  const adjusted = state.adj.air!==null || state.adj.snow48!==null || state.adj.surface!=="auto";
  const isLive = !!(state.live && state.live[r.id]);
  const badge = $("sourceBadge");
  badge.className = "badge " + (adjusted ? "" : isLive ? "live" : "example");
  $("sourceText").textContent = adjusted ? "Adjusted by you" :
    isLive ? `Live forecast · ${state.updatedAt.toLocaleTimeString([], {hour:"numeric", minute:"2-digit"})}` :
    state.live===null ? "Loading conditions…" : "Example conditions";

  const wk = c.weekend;
  const dayName = d => d.toLocaleDateString("en-US", {weekday:"long"});
  $("condLabel").textContent = state.day==="today" ? "Estimated snow temperature"
    : state.day==="tomorrow" ? "Tomorrow's estimated snow temperature"
    : `${dayName(wk.days[wk.chosen].date)}'s estimated snow temperature${wk.differ && wk.chosen === wk.colder ? " (the colder day)" : ""}`;
  $("snowTemp").textContent = c.surface==="wet" && c.air>0 ? fmtT(0)+" wet" : fmtT(c.snowTemp);
  $("surfacePill").textContent = SURFACES[c.surface].label;
  $("statAir").textContent = fmtT(c.air);
  $("statRh").textContent = c.rh===null ? "—" : Math.round(c.rh)+"%";
  $("statSnowLabel").textContent = state.day==="today" ? "New snow, 48 h" : `New snow by ${c.date.toLocaleDateString("en-US",{weekday:"short"})}`;
  $("statSnow").textContent = fmtSnow(c.snow48);
  $("statSky").textContent = c.sky;

  // weekend breakdown
  $("wkBox").hidden = !wk; $("wkNote").hidden = !(wk && wk.daysOut>=3);
  if(wk){
    const fmtDay = d => d.toLocaleDateString("en-US", {weekday:"short", month:"short", day:"numeric"});
    $("wkBox").innerHTML = `<span class="label">Weekend forecast · low / high · new snow · tap a day</span>` +
      wk.days.map((d,j)=>`<button type="button" class="wk-row${j===wk.chosen?" pick":""}" data-wk="${j}" aria-pressed="${j===wk.chosen}"><b>${fmtDay(d.date)}</b><span class="wk-chip"><i style="background:${d.band.color}"></i>${d.band.name}</span><span class="mono">${fmtTshort(d.min)} / ${fmtT(d.max)} · ${fmtSnow(d.snow)}</span></button>`).join("") +
      (wk.differ ? `<p class="note">The two days call for different waxes. Waxing once for both? Use the colder day's wax; it lasts longer and drags less if the forecast is off.</p>` : "");
    if(wk.daysOut>=3) $("wkNote").innerHTML = `<strong>${dayName(wk.days[0].date)} is ${wk.daysOut} days out.</strong> Forecasts that far ahead often miss by several degrees. Wax now, check this page again the night before you leave, and switch waxes if the color changed.`;
  }
  $("statElev").textContent = fmtElev(r.mid);
  $("statPastMax").textContent = fmtT(c.pastMax);

  // adjust controls mirror current values
  $("airRange").value = c.air; $("airRangeVal").textContent = fmtT(c.air,0);
  buildSnowSelect(); $("snowSel").value = state.adj.snow48===null ? "" : String(state.adj.snow48);
  $("surfSel").value = state.adj.surface;

  // wax
  $("waxBar").style.background = band.color;
  $("waxName").textContent = band.name;
  $("waxRange").textContent = fmtRange(band);
  $("waxIron").textContent = fmtIron(band.iron);
  document.querySelectorAll("#stripBands span").forEach(s=>s.classList.toggle("on", Number(s.dataset.i)===wax.idx));
  const pos = buildTicks();
  $("stripMarker").style.left = pos(wax.T)+"%";
  $("stripMarker").firstChild ? $("stripMarker").firstChild.nodeValue = fmtTshort(wax.T) : $("stripMarker").textContent = fmtTshort(wax.T);
  const why = [];
  why.push(c.surface==="wet" ? `Air is above freezing (${fmtT(c.air)}), so the snow is wet.` : `Snow is about ${fmtT(c.snowTemp)} at mid-mountain${c.cloudy?"":", a little colder than the air under clear skies"}.`);
  if(wax.shifted==="new") why.push("Fresh snow has sharp crystals, so go one step colder (harder) than the temperature alone suggests.");
  if(wax.shifted==="manmade") why.push("Man-made snow is abrasive, so go one step colder (harder) than the temperature alone suggests.");
  if(c.surface==="wet") why.push("Wet snow causes suction. Warm wax plus extra brushing breaks it up. For dirty spring snow, a graphite wax helps.");
  if(c.surface==="refrozen") why.push("The surface has thawed and refrozen. Wax choice matters less today than sharp edges.");
  if(c.rh>=85 && c.surface!=="wet" && wax.T>-6) why.push(`Humidity is high (${Math.round(c.rh)}%). If you're between two waxes, pick the warmer one.`);
  if(state.style==="cruiser" || state.style==="powder") why.push("Waxing only once in a while? A universal all-temperature wax does fine. Use this one for the best glide.");
  const racer = state.style==="racer", raceDay = racer && state.raceMode==="race";
  if(raceDay) why.push("Race day: build the wax in three layers, below. Fluorinated waxes are banned in FIS racing, so everything here is fluoro-free.");
  else if(racer) why.push("Training day: one durable layer of performance wax. Save the race wax and top coat for race day.");
  $("waxWhy").innerHTML = why.map(w=>`<li>${w}</li>`).join("");
  $("raceSeg").hidden = !racer;
  $("modeTraining").setAttribute("aria-pressed", state.raceMode==="training");
  $("modeRace").setAttribute("aria-pressed", state.raceMode==="race");
  $("raceList").hidden = !racer;
  if(racer){
    const layers = raceDay ? [
      ["Base layer", "A hard, cold wax ironed in, cooled and scraped. It makes the race wax last on abrasive, injected or man-made race snow. Skip it on soft, warm days."],
      [`Race wax: ${band.race}`, `Or an equivalent fluoro-free race wax for ${fmtRange(band)}. Iron at about ${fmtIron(band.iron)}, cool fully, scrape and brush.`],
      ["Top coat, race morning", "A fluoro-free race top coat (block, powder or liquid) in the same temperature range, corked or brushed in per its instructions."]
    ] : [
      [`Training wax: ${band.ex.split(" or ")[0]}`, `Or any fluoro-free performance wax for ${fmtRange(band)}. Iron at about ${fmtIron(band.iron)}, cool, scrape and brush. One layer is enough.`],
      ["Built to last", "Training laps on injected or man-made snow strip wax fast. Re-wax every few training days. When you're between two waxes, pick the colder, harder one."]
    ];
    $("raceList").innerHTML = layers.map(([t,d],i)=>`<li><span class="ln">${i+1}</span><span><b>${t}</b><span class="d">${d}</span></span></li>`).join("");
  }
  $("waxEx").textContent = raceDay
    ? "Toko, Holmenkol, Vauhti and others make fluoro-free race lines too. Match the temperature on the label."
    : racer ? "Any brand's fluoro-free performance wax works for training. Match the temperature on the label."
    : `Examples: ${band.ex}. Toko, Holmenkol and others make equivalents; match the temperature on the label.`;

  // edges
  $("eBase").textContent = edges.base+"°";
  $("eSide").textContent = edges.side+"°";
  $("eIncl").textContent = edges.incl+"°";
  $("edgeNote").innerHTML = edges.note;

  renderDiagram(edges);
  renderSteps(c, wax, edges);
  renderKit(wax, edges);
}

/* ---------- Live data ---------- */
function toLive(d){
  return Object.assign({}, d, { days: d.days.map(x=>{ const [y,m,dd] = x.date.split("-").map(Number); return {date:new Date(y,m-1,dd), min:x.min, max:x.max, snow:x.snow}; }) });
}
async function loadLive(){
  // Served by the Netlify function in netlify/functions/conditions.mts (MET Norway data, refreshed hourly).
  const ctl = new AbortController(); const timer = setTimeout(()=>ctl.abort(), 8000);
  try{
    const res = await fetch("/api/conditions/" + encodeURIComponent(RD.api || "featured"), {signal:ctl.signal});
    if(!res.ok) throw new Error("HTTP "+res.status);
    const data = await res.json();
    const live = {};
    for(const r of RESORTS){
      const d = data.resorts && data.resorts[r.id];
      if(!d || !Array.isArray(d.days) || !d.days.length) continue;
      live[r.id] = toLive(d);
    }
    if(!Object.keys(live).length) throw new Error("empty");
    state.live = Object.assign(state.live || {}, live); state.updatedAt = new Date(data.updated || Date.now());
    setText("dataNote", "Weather from MET Norway's forecast at each resort's mid-mountain elevation, updated hourly.");
  }catch(e){
    state.live = state.live || {};
    setText("dataNote", "Live weather couldn't load here, so the page is showing example conditions. On theskiadvisor.com, conditions come from MET Norway's forecast at each resort's mid-mountain elevation.");
  }finally{ clearTimeout(timer); (PAGE==="resort" ? render : renderHome)(); }
}

/* ---------- Home + guides ---------- */
function setText(id, t){ const el = $(id); if(el) el.textContent = t; }
function renderHome(){
  const live = !!(state.live && Object.keys(state.live).length);
  const keep = state.resort;
  document.querySelectorAll("[data-home-wax]").forEach(el=>{
    state.resort = el.dataset.homeWax;
    const c = conditions(), wax = pickWax(c);
    el.innerHTML = `<i style="background:${wax.band.color}"></i><span>${wax.band.name} wax · snow ${fmtT(c.snowTemp)}${live ? "" : " (example)"}</span>`;
  });
  state.resort = keep;
  setText("homeDataNote", live ? "Wax picks use today's live forecast at each resort's mid-mountain elevation."
    : "These wax picks use example conditions. Live forecasts load on the hosted site.");
}

/* ---------- Search ---------- */
const escH = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fold = s => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const indexCache = {};
function loadIndex(url){ return indexCache[url] || (indexCache[url] = fetch(url).then(r=>r.json()).catch(()=>[])); }
function kmBetween(la1, lo1, la2, lo2){
  const r = Math.PI/180, a = Math.sin((la2-la1)*r/2)**2 + Math.cos(la1*r)*Math.cos(la2*r)*Math.sin((lo2-lo1)*r/2)**2;
  return 12742 * Math.asin(Math.sqrt(a));
}
// "Near me": the browser's location stays in the browser; it only sorts the resort list.
function initNearMe(){
  document.querySelectorAll("[data-search]").forEach(form=>{
    const btn = form.querySelector("[data-near]"), list = form.querySelector("ul"), msg = form.querySelector(".near-msg");
    if(!btn) return;
    if(!("geolocation" in navigator)){ btn.hidden = true; return; }
    btn.addEventListener("click", ()=>{
      msg.hidden = false; msg.textContent = "Finding resorts near you…";
      navigator.geolocation.getCurrentPosition(async pos=>{
        const idx = await loadIndex(form.dataset.index);
        const { latitude: la, longitude: lo } = pos.coords;
        const near = idx.map(e=>({e, km: kmBetween(la, lo, e[5], e[6])})).sort((a,b)=>a.km-b.km).slice(0, 8);
        const dist = km => state.unit==="F" ? Math.round(km*0.621371) + " mi" : Math.round(km) + " km";
        list.innerHTML = near.map(({e, km}) => `<li><a href="${form.dataset.prefix}${encodeURIComponent(e[0])}.html"><b>${escH(e[1])}</b><span>${dist(km)} away · ${escH(e[4] ? e[4] + ", " : "")}${escH(e[3])}</span></a></li>`).join("");
        list.hidden = false; msg.hidden = true;
      }, err=>{
        msg.textContent = err.code === 1 ? "Location is off for this site. Search by name instead." : "Couldn't get your location. Search by name instead.";
      }, { timeout: 10000, maximumAge: 600000 });
    });
  });
}
// "My mountains": saved on this device only.
const favs = () => { const v = store.get("fav", []); return Array.isArray(v) ? v : []; };
function initFavButton(){
  const btn = $("favBtn"), me = RESORTS[0];
  if(!btn || !me) return;
  const sync = () => {
    const on = favs().some(f=>f.id===me.id);
    btn.setAttribute("aria-pressed", String(on));
    btn.querySelector("span").textContent = on ? "Saved to My mountains" : "Save to My mountains";
  };
  btn.hidden = false; sync();
  btn.addEventListener("click", ()=>{
    const list = favs(), i = list.findIndex(f=>f.id===me.id);
    if(i >= 0) list.splice(i, 1); else list.push(Object.assign({}, me));
    store.set("fav", list.slice(-24)); sync();
  });
}
async function initMyMountains(){
  const box = $("myMtns"), grid = $("myMtnsGrid"), list = favs();
  if(!box || !grid || !list.length) return;
  box.hidden = false;
  grid.innerHTML = list.map(f=>`<a class="resort-card" href="resorts/${encodeURIComponent(f.id)}.html"><span class="meta">${escH(f.region)} · mid-mountain ${fmtElev(f.mid)}</span><h3>${escH(f.name)}</h3><span class="wax-chip" data-home-wax="${escH(f.id)}"><i></i><span>Loading today's wax…</span></span></a>`).join("");
  for(const f of list) if(!RESORTS.some(r=>r.id===f.id)) RESORTS.push(f);
  renderHome();
  const keys = [...new Set(list.map(f=>f.api).filter(Boolean))];
  await Promise.all(keys.map(k => fetch("/api/conditions/" + encodeURIComponent(k)).then(r => r.ok ? r.json() : null).then(d=>{
    if(!d || !d.resorts) return;
    state.live = state.live || {};
    for(const f of list){ const x = d.resorts[f.id]; if(x && Array.isArray(x.days) && x.days.length) state.live[f.id] = toLive(x); }
  }).catch(()=>{})));
  renderHome();
}
function initSearch(){
  document.querySelectorAll("[data-search]").forEach(form=>{
    const input = form.querySelector("input"), list = form.querySelector("ul");
    let idx = null, loading = null;
    const load = () => loading || (loading = loadIndex(form.dataset.index).then(d=>{ idx = d.map(e=>({e, hay: fold(e.slice(1, 5).join(" "))})); }));
    function show(){
      const q = fold(input.value.trim());
      if(!q || !idx){ list.hidden = true; list.innerHTML = ""; return; }
      const terms = q.split(/\s+/);
      const hits = idx.filter(x => terms.every(t => x.hay.includes(t)))
        .sort((a,b) => (fold(a.e[1]).startsWith(terms[0]) ? 0 : 1) - (fold(b.e[1]).startsWith(terms[0]) ? 0 : 1)).slice(0, 8);
      list.innerHTML = hits.length
        ? hits.map(({e}) => `<li><a href="${form.dataset.prefix}${encodeURIComponent(e[0])}.html"><b>${escH(e[1])}</b><span>${escH(e[4] ? e[4] + ", " : "")}${escH(e[3])}</span></a></li>`).join("")
        : `<li class="none">No ski resort matches “${escH(input.value.trim())}”.</li>`;
      list.hidden = false;
    }
    input.addEventListener("focus", load);
    input.addEventListener("input", () => load().then(show));
    input.addEventListener("keydown", e => { if(e.key === "Escape"){ list.hidden = true; } });
    form.addEventListener("submit", e => { e.preventDefault(); const a = list.querySelector("a"); if(a) location.href = a.href; });
    document.addEventListener("click", e => { if(!form.contains(e.target)) list.hidden = true; });
  });
}

/* ---------- Wire up ---------- */
const PAGE = PI.page;
initSearch();
initNearMe();
document.querySelectorAll("[data-edge-diagram]").forEach(el=>{ el.innerHTML = edgeSVG(Number(el.dataset.base), Number(el.dataset.side)); });
if(PAGE==="resort"){
  buildStyles(); buildStripBands();
  buildRadio("baseRow", [0.5,0.7,1], v=>v+"°", "base");
  buildRadio("sideRow", [1,2,3,4], v=>`${v}° (${90-v}°)`, "side");
  $("unitF").onclick = ()=>{ state.unit="F"; store.set("unit","F"); render(); };
  $("unitC").onclick = ()=>{ state.unit="C"; store.set("unit","C"); render(); };
  $("dayToday").onclick = ()=>{ state.day="today"; state.adj={air:null,snow48:null,surface:"auto"}; render(); };
  $("dayTomorrow").onclick = ()=>{ state.day="tomorrow"; state.adj={air:null,snow48:null,surface:"auto"}; render(); };
  $("modeTraining").onclick = ()=>{ state.raceMode="training"; store.set("raceMode","training"); render(); };
  $("modeRace").onclick = ()=>{ state.raceMode="race"; store.set("raceMode","race"); render(); };
  $("wkBox").addEventListener("click", e=>{ const b = e.target.closest("[data-wk]"); if(!b) return; state.wkPick = Number(b.dataset.wk); state.diag = null; render(); });
  $("dayWeekend").onclick =()=>{ state.day="weekend"; state.wkPick=null; state.adj={air:null,snow48:null,surface:"auto"}; render(); };
  $("airRange").addEventListener("input", e=>{ state.adj.air = Number(e.target.value); state.diag=null; render(); });
  $("snowSel").addEventListener("change", e=>{ state.adj.snow48 = e.target.value==="" ? null : Number(e.target.value); render(); });
  $("surfSel").addEventListener("change", e=>{ state.adj.surface = e.target.value; state.diag=null; render(); });
  $("resetAdj").onclick = ()=>{ state.adj={air:null,snow48:null,surface:"auto"}; render(); };
  $("diagReset").onclick = ()=>{ state.diag=null; render(); };
  $("steps").addEventListener("change", e=>{
    if(e.target.matches("input[type=checkbox]")){ state.done[e.target.dataset.id] = e.target.checked; store.set("done", state.done); render(); }
  });
  $("stepsReset").onclick = ()=>{ state.done={}; store.set("done",{}); render(); };
  initFavButton();
  render();
  loadLive();
} else if(document.querySelector("[data-home-wax]")){
  renderHome();
  loadLive();
  initMyMountains();
}
})();
