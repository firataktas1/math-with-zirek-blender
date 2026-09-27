// Math with Zirek · "akşam, ağıl, 8 koyun, 8 çakıl, torbada tek çakıl" · shared story core
// Everything here is a pure function of time t (seconds). No clocks, no Math.random.
// World space is 1920x1080 (the wide shot). Each style draws this same story its own way.
(function () {
  const Z = {};
  Z.DUR = 10;
  Z.N = 8;                 // sheep = pebbles that leave
  Z.GAP = 0.73;            // seconds between sheep
  Z.T0 = 1.25;             // first sheep crosses the gate
  Z.PUSH0 = 7.0;           // slow push-in on the pouch
  Z.GLINT = 7.9;           // glint starts

  // ---------- helpers
  const cl = (x, a, b) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, u) => a + (b - a) * u;
  const smooth = (u) => { u = cl(u, 0, 1); return u * u * (3 - 2 * u); };
  const sineIO = (u) => 0.5 - 0.5 * Math.cos(Math.PI * cl(u, 0, 1));
  const outQ = (u) => { u = cl(u, 0, 1); return 1 - (1 - u) * (1 - u); };
  const outC = (u) => { u = cl(u, 0, 1); return 1 - Math.pow(1 - u, 3); };
  function hash(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
  // seeded PRNG for build-time drawing (deterministic)
  function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  Object.assign(Z, { cl, lerp, smooth, sineIO, outQ, outC, hash, rng });

  // ---------- geometry (wide shot)
  Z.PEN = { cx: 1265, cy: 548, rx: 520, ry: 124, h: 46 };   // stone pen, wall base ellipse; wall height
  Z.frontY = (x) => { const d = (x - Z.PEN.cx) / Z.PEN.rx; return Math.abs(d) >= 1 ? Z.PEN.cy : Z.PEN.cy + Z.PEN.ry * Math.sqrt(1 - d * d); };
  Z.backY = (x) => { const d = (x - Z.PEN.cx) / Z.PEN.rx; return Math.abs(d) >= 1 ? Z.PEN.cy : Z.PEN.cy - Z.PEN.ry * Math.sqrt(1 - d * d); };
  Z.POSTL = { x: 868, y: Z.frontY(868) };                    // gate posts (base points)
  Z.POSTR = { x: 1004, y: Z.frontY(1004) };
  Z.POST_H = 150;
  Z.GATE = { x: 936, y: (Z.POSTL.y + Z.POSTR.y) / 2 };
  Z.STICK = { x0: 996, y0: Z.POSTR.y - 132, x1: 1104, y1: Z.POSTR.y - 166 };  // wooden arm jammed in the right post
  Z.PEG = { x: 1094, y: Z.POSTR.y - 162 };                   // pouch cord hangs from the arm's end
  Z.MOUTH = { x: Z.PEG.x, y: Z.PEG.y + 64 };
  Z.POUCH = { x: Z.PEG.x, y: Z.MOUTH.y + 62, w: 176, h: 150 };  // pouch body centre
  Z.SLAB = { x: 1045, y: 808, rx: 280, ry: 64 };             // flat stone for the pebble row
  Z.ROW = [...Array(8)].map((_, k) => ({ x: 856 + k * 54, y: 800 + (k % 2) * 3 - 2 }));
  Z.PEB = { rx: 21, ry: 15.5 };

  // pebbles in the pouch: 9 slots relative to the mouth centre; index 0 is the one that stays
  Z.SLOTS = [
    [0, 2], [-35, 1], [35, 1],
    [-50, -13], [-17, -16], [17, -16], [50, -13],
    [-17, -31], [17, -31],
  ];
  // removal order: top first, the centre-bottom one (slot 0) is never taken
  Z.TAKE = [8, 7, 3, 6, 4, 5, 1, 2];

  // ---------- timing per sheep
  Z.tGate = (i) => Z.T0 + i * Z.GAP;
  Z.SPEED = 232;
  // rest spots inside the pen (feet), first sheep go deepest
  Z.REST = [[1600, 524], [1440, 486], [1660, 592], [1290, 494], [1500, 586], [1640, 460], [1330, 598], [1215, 560]];
  Z.REST_FACE = [-1, 1, -1, -1, 1, -1, -1, 1];
  const APPROACH = [[-300, 752], [420, 728], [700, 704], [870, 666], [Z.GATE.x, Z.GATE.y]];
  function polyLen(p) { let L = 0; for (let k = 1; k < p.length; k++) L += Math.hypot(p[k][0] - p[k - 1][0], p[k][1] - p[k - 1][1]); return L; }
  function polyAt(p, s) {
    for (let k = 1; k < p.length; k++) {
      const a = p[k - 1], b = p[k], L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (s <= L || k === p.length - 1) { const u = cl(s / L, 0, 1); return [lerp(a[0], b[0], u), lerp(a[1], b[1], u), b[0] - a[0], b[1] - a[1]]; }
      s -= L;
    }
  }
  Z.PATHS = Z.REST.map((r, i) => {
    const inside = [[Z.GATE.x + 70, Z.GATE.y - 34], [lerp(Z.GATE.x + 70, r[0], 0.5), lerp(Z.GATE.y - 34, r[1], 0.6) + (i % 2 ? -8 : 8)], r];
    const p = APPROACH.concat(inside);
    return { p, LG: polyLen(APPROACH), L: polyLen(p) };
  });
  // depth scale from feet y
  Z.depth = (y) => cl(0.74 + 0.47 * (y - 480) / 270, 0.6, 1.3);

  // sheep state: x,y (feet), s (scale), face (+1 right / -1 left), dist (for the walk cycle), v (0..1 speed)
  Z.sheep = function (i, t) {
    const P = Z.PATHS[i];
    const u = P.LG + Z.SPEED * (t - Z.tGate(i));
    const D = P.L, K = 150;
    let s, v;
    if (u < D - K) { s = u; v = 1; } else { const e = (u - (D - K)) / K; s = D - K + K * (1 - Math.exp(-e)); v = Math.exp(-e); }
    s = Math.max(s, 0);
    const q = polyAt(P.p, s);
    const x = q[0], y = q[1];
    // idle: tiny grazing sway once stopped
    const idle = 1 - v;
    // once stopped, some sheep turn round (2D flip through zero width)
    const tTurn = Z.tGate(i) + (D - K + 1.4 * K - P.LG) / Z.SPEED;
    const turn = smooth((t - tTurn) / 0.4);
    const faceS = lerp(1, Z.REST_FACE[i], turn);
    return { x, y, s: Z.depth(y), face: faceS >= 0 ? 1 : -1, faceS, turn, dist: s, v, idle, inPen: s > P.LG + 8, head: idle * (0.5 + 0.5 * Math.sin(t * 1.7 + i * 1.3)) };
  };
  // walk: leg angle for leg k (0..3), body bob
  Z.walk = function (st, k) {
    const ph = st.dist / 34 + (k === 0 || k === 3 ? 0 : Math.PI);
    return { leg: Math.sin(ph) * 26 * st.v, bob: -Math.abs(Math.sin(st.dist / 34)) * 5 * st.v };
  };

  // ---------- pebbles
  // pebble k (k = 0..7 leaves with sheep k) ; pebble 8 = the one that stays (slot 0)
  Z.LIFT = 0.2; Z.FLY = 0.52; Z.LAND = 0.22;
  Z.pebble = function (k, t) {
    if (k === 8) { const m = Z.mouthAt(t); return { x: m.x + Z.SLOTS[0][0], y: m.y + Z.SLOTS[0][1], inPouch: true, slot: 0, rot: -6, sq: 1, fly: false }; }
    const slot = Z.TAKE[k];
    const t0 = Z.tGate(k) - 0.05;
    const m = Z.mouthAt(t);
    const S = { x: m.x + Z.SLOTS[slot][0], y: m.y + Z.SLOTS[slot][1] };
    const E = Z.ROW[k];
    const rot0 = (hash(k + 7) - 0.5) * 50, rot1 = (hash(k + 17) - 0.5) * 24;
    if (t < t0) return { x: S.x, y: S.y, inPouch: true, slot, rot: rot0, sq: 1, fly: false };
    const a = t - t0;
    const top = { x: S.x + 6, y: m.y - 92 };
    if (a < Z.LIFT) { const u = outQ(a / Z.LIFT); return { x: lerp(S.x, top.x, u), y: lerp(S.y, top.y, u), inPouch: a < 0.06, slot, rot: rot0, sq: 1, fly: true }; }
    if (a < Z.LIFT + Z.FLY) {
      const u = (a - Z.LIFT) / Z.FLY, e = sineIO(u);
      const x = lerp(top.x, E.x, e);
      const y = lerp(top.y, E.y, u * u) - Math.sin(Math.PI * u) * 70;
      return { x, y, inPouch: false, slot, rot: lerp(rot0, rot1 + 360, e), sq: 1, fly: true };
    }
    const b = a - Z.LIFT - Z.FLY;
    const sq = b < Z.LAND ? 1 + 0.22 * Math.sin(Math.PI * b / Z.LAND) * Math.exp(-b * 6) : 1;
    return { x: E.x, y: E.y, inPouch: false, slot, rot: rot1, sq, fly: false, landed: true, age: b };
  };
  Z.landT = (k) => Z.tGate(k) - 0.05 + Z.LIFT + Z.FLY;

  // pouch: gentle swing each time a pebble leaves; belly slackens as it empties
  Z.swing = function (t) {
    let a = 0;
    for (let k = 0; k < Z.N; k++) { const d = t - (Z.tGate(k) - 0.02); if (d > 0) a += 5.5 * Math.exp(-d * 3.2) * Math.sin(d * 10); }
    return a;   // degrees, around the peg
  };
  Z.fill = function (t) { let n = 0; for (let k = 0; k < Z.N; k++) if (t > Z.tGate(k) + 0.1) n++; return n; };
  Z.slack = function (t) { let f = 0; for (let k = 0; k < Z.N; k++) f += smooth((t - Z.tGate(k)) / 0.35); return f / Z.N; };  // 0..1
  // mouth position including swing (rotate around the peg)
  Z.rotAround = (x, y, cx, cy, deg) => { const r = deg * Math.PI / 180, c = Math.cos(r), s = Math.sin(r); return { x: cx + (x - cx) * c - (y - cy) * s, y: cy + (x - cx) * s + (y - cy) * c }; };
  Z.mouthAt = (t) => Z.rotAround(Z.MOUTH.x, Z.MOUTH.y + 6 * Z.slack(t), Z.PEG.x, Z.PEG.y, Z.swing(t));

  // ---------- camera: screen = (world - F) * s + A
  Z.FOCUS = { x: Z.MOUTH.x, y: Z.MOUTH.y + 12 };
  Z.cam = function (t) {
    const drift = smooth(t / Z.PUSH0) * 0.03;
    const u = sineIO((t - Z.PUSH0) / (Z.DUR - Z.PUSH0));
    const s = lerp(1.2 + drift, 2.45, u);
    const F = { x: lerp(1112, Z.FOCUS.x, u), y: lerp(606, Z.FOCUS.y, u) };
    const A = { x: lerp(960, 900, u), y: lerp(540, 430, u) };
    return { s, F, A, u };
  };
  Z.toScreen = (c, x, y) => ({ x: (x - c.F.x) * c.s + c.A.x, y: (y - c.F.y) * c.s + c.A.y });
  // matrix for a layer with parallax factor p (1 = on the stage plane, <1 = farther)
  Z.camMatrix = (c, p) => {
    const s = 1 + (c.s - 1) * p;
    const Fx = lerp(960, c.F.x, p), Fy = lerp(540, c.F.y, p);
    const Ax = lerp(960, c.A.x, p), Ay = lerp(540, c.A.y, p);   // p<1: far layers drift and grow less
    return { s, tx: Ax - Fx * s, ty: Ay - Fy * s };
  };

  // ---------- glint on the last pebble: 0..1 intensity
  Z.glint = function (t) {
    const a = t - Z.GLINT;
    if (a <= 0) return 0;
    const rise = smooth(a / 0.7);
    return rise * (0.78 + 0.22 * Math.cos(a * 3.1));
  };

  window.ZS = Z;
})();
