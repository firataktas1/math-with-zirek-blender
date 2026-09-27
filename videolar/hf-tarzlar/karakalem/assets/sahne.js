/* Math with Zirek · "evening pebbles" scene model, shared by the b-group styles.
   Pure functions of time t (seconds): same t -> same state. No clocks, no Math.random.
   World units = pixels of the wide shot (1920x1080). Styles only decide how things look. */
(function () {
  const W = 1920, H = 1080, DUR = 10;
  const cl = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, u) => a + (b - a) * u;
  const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453123; return x - Math.floor(x); };
  const h2 = (a, b) => hash(a * 57.31 + b * 13.77);
  function prng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const E = {
    sine: (u) => 0.5 - 0.5 * Math.cos(Math.PI * cl(u, 0, 1)),
    qOut: (u) => { u = cl(u, 0, 1); return 1 - (1 - u) * (1 - u); },
    cOut: (u) => { u = cl(u, 0, 1); return 1 - Math.pow(1 - u, 3); },
    cInOut: (u) => { u = cl(u, 0, 1); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; },
  };
  const seg = (t, a, b) => cl((t - a) / (b - a), 0, 1);
  // depth scale: further (smaller y) is smaller
  const ds = (y) => 0.7 + 0.3 * (y - 260) / 440;

  // ---------------------------------------------------------------- layout
  const PEN = { cx: 1180, cy: 470, rx: 470, ry: 190 };
  const ep = (th) => ({ x: PEN.cx + PEN.rx * Math.cos(th), y: PEN.cy + PEN.ry * Math.sin(th) });
  const DEG = Math.PI / 180;
  const P1 = ep(160 * DEG);   // front gate pillar (nearer the viewer), pouch hangs on it
  const P2 = ep(200 * DEG);   // back gate pillar
  const GATE_Y = 432;         // sheep feet height while passing the gate
  const PEG = { x0: P1.x - 8, y0: 400, x1: P1.x - 38, y1: 409 };      // wooden peg sticking out of the front pillar
  const PS = 1.15;                                                    // pouch scale
  const MOUTH = { x: 684, y: 452, rx: 50 * PS, ry: 14 * PS };                  // pouch mouth centre
  const SLAB = { x: 445, y: 772, rx: 250, ry: 54, th: 17 };          // flat stone for the pebble row
  const TREE = { x: 250, y: 292 };
  const HORIZON = 214;

  // ------------------------------------------------------------ helpers for shapes
  function ellipsePts(cx, cy, rx, ry, n, rot, wob, seed) {
    const pts = [], c = Math.cos(rot || 0), s = Math.sin(rot || 0);
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const k = wob ? 1 + wob * (h2(seed || 0, i) - 0.5) * 2 : 1;
      const x = Math.cos(a) * rx * k, y = Math.sin(a) * ry * k;
      pts.push([cx + x * c - y * s, cy + x * s + y * c]);
    }
    return pts;
  }
  function blob(cx, cy, rx, ry, n, rot, seed, lo, hi) {
    const pts = [], c = Math.cos(rot), s = Math.sin(rot);
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + (h2(seed, i + 40) - 0.5) * 0.25;
      const k = lo + (hi - lo) * h2(seed, i);
      const x = Math.cos(a) * rx * k, y = Math.sin(a) * ry * k;
      pts.push([cx + x * c - y * s, cy + x * s + y * c]);
    }
    return pts;
  }
  // scalloped (woolly / leafy) outline
  function scallop(cx, cy, rx, ry, bumps, depth, seed, n) {
    n = n || bumps * 8;
    const pts = [], ph = (h2(seed, 3) - 0.5) * 0.8;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const b = Math.abs(Math.sin((a + ph) * bumps / 2));
      const k = 1 + depth * (Math.pow(b, 0.55) - 0.6) + 0.025 * (h2(seed, Math.floor(i / 8)) - 0.5);
      pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
    }
    return pts;
  }
  const xf = (pts, x, y, s, fx) => pts.map(([a, b]) => [x + a * s * (fx || 1), y + b * s]);
  function rotPts(pts, px, py, ang) {
    const c = Math.cos(ang), s = Math.sin(ang);
    return pts.map(([x, y]) => [px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c]);
  }

  // ------------------------------------------------------------ static geometry
  const STONES = [];
  (function buildWall() {
    const R = prng(7);
    const arcLen = (th) => Math.sqrt((PEN.rx * Math.sin(th)) ** 2 + (PEN.ry * Math.cos(th)) ** 2);
    const th0 = 206 * DEG, th1 = 514 * DEG;
    for (let row = 0; row < 3; row++) {
      let th = th0 + (row % 2) * 0.02;
      let id = 0;
      while (th < th1) {
        const b = ep(th), sc = ds(b.y);
        const w = ((row === 2 ? 46 : 40) + R() * 12) * 1.12, h = ((row === 2 ? 20 : 23) + R() * 5) * 1.12;
        const cyy = b.y - (row * 21.5 + 13) * sc;
        const seed = row * 1000 + id + 17;
        STONES.push({ x: b.x, y: cyy, base: b.y, key: b.y + row * 0.01, w: w * sc, h: h * sc, rot: (R() - 0.5) * 0.22 + Math.cos(th) * 0.08 * Math.sign(Math.sin(th)), seed, tone: R(), row, front: Math.sin(th) > 0, pts: blob(b.x, cyy, w * sc / 2, h * sc / 2, 11, (R() - 0.5) * 0.2, seed, 0.86, 1.05) });
        th += (w * sc * 0.93) / arcLen(th) / sc * sc;   // arc step ~ stone width
        id++;
      }
    }
    // gate pillars: tall stacks
    [[P1, 0], [P2, 1]].forEach(([P, pi]) => {
      const sc = ds(P.y);
      for (let r = 0; r < 7; r++) {
        const w = (54 - r * 2 + R() * 8) * 1.1, h = (22 + R() * 4) * 1.1;
        const cyy = P.y - (r * 22.5 + 13) * sc, cx = P.x + (R() - 0.5) * 6;
        const seed = 5000 + pi * 100 + r;
        STONES.push({ x: cx, y: cyy, base: P.y, key: P.y + 0.02 + r * 0.01, w: w * sc, h: h * sc, rot: (R() - 0.5) * 0.16, seed, tone: R(), row: r, pillar: pi, front: pi === 0, pts: blob(cx, cyy, w * sc / 2, h * sc / 2, 11, (R() - 0.5) * 0.15, seed, 0.88, 1.04) });
      }
    });
  })();

  // grass tufts (static). Nothing in the lower-right third, nothing on the slab.
  const TUFTS = [];
  (function () {
    const R = prng(99);
    let n = 0;
    while (TUFTS.length < 34 && n < 2000) {
      n++;
      const x = R() * W, y = HORIZON + 30 + R() * (H - HORIZON - 30);
      if (x > 1240 && y > 690) continue;
      if (Math.abs((x - SLAB.x) / (SLAB.rx + 40)) ** 2 + Math.abs((y - SLAB.y) / (SLAB.ry + 40)) ** 2 < 1) continue;
      const q = ((x - PEN.cx) / PEN.rx) ** 2 + ((y - PEN.cy) / PEN.ry) ** 2;
      if (q > 0.8 && q < 1.25) continue;             // not inside the wall band
      if (y > 380 && y < 540 && x < 780) continue;   // not on the sheep path
      TUFTS.push({ x, y, s: ds(y) * (0.8 + R() * 0.5), seed: n });
    }
    // tufts along the foot of the front wall
    for (let i = 0; i < 12; i++) {
      const th = (30 + i * 10 + R() * 5) * DEG, b = ep(th);
      if (b.x > 1240) continue;
      TUFTS.push({ x: b.x + (R() - 0.5) * 20, y: b.y + 4 + R() * 6, s: ds(b.y) * (0.9 + R() * 0.4), seed: 300 + i, wall: true });
    }
  })();
  function tuftPts(tf) {
    // three blades
    const s = tf.s * 1.1, blades = [];
    for (let k = 0; k < 3; k++) {
      const dx = (k - 1) * 5 * s, hgt = (12 + h2(tf.seed, k) * 8) * s, lean = (k - 1) * 4 * s + (h2(tf.seed, k + 9) - 0.5) * 4 * s;
      blades.push([[tf.x + dx - 1.5 * s, tf.y], [tf.x + dx + lean, tf.y - hgt], [tf.x + dx + 1.5 * s, tf.y]]);
    }
    return blades;
  }

  const HILLS = [
    // far hill line and nearer hill line (open polylines, left to right)
    (() => { const p = []; for (let i = 0; i <= 48; i++) { const x = -60 + i * 42; p.push([x, 206 - 26 * Math.sin(i * 0.23 + 0.6) - 12 * Math.sin(i * 0.61 + 1.1)]); } return p; })(),
    (() => { const p = []; for (let i = 0; i <= 48; i++) { const x = -60 + i * 42; p.push([x, HORIZON + 4 - 10 * Math.sin(i * 0.17 + 2.0) - 5 * Math.sin(i * 0.53)]); } return p; })(),
  ];

  const SLAB_TOP = blob(SLAB.x, SLAB.y, SLAB.rx, SLAB.ry, 26, 0.02, 811, 0.93, 1.04);
  const SLAB_SIDE = (() => {
    // lower half of the top outline pushed down by the thickness
    const lower = SLAB_TOP.filter(([x, y]) => y >= SLAB.y - 6).sort((a, b) => a[0] - b[0]);
    const top = lower.map(([x, y]) => [x, y]);
    const bot = lower.slice().reverse().map(([x, y]) => [x, y + SLAB.th]);
    return top.concat(bot);
  })();
  const ROW = [...Array(8)].map((_, k) => ({ x: SLAB.x + (k - 3.5) * 57 + (h2(k, 5) - 0.5) * 6, y: SLAB.y - 2 + (h2(k, 6) - 0.5) * 8, rot: (h2(k, 7) - 0.5) * 0.5 }));

  const TREE_SHAPES = {
    trunk: [[TREE.x - 6, TREE.y], [TREE.x - 4, TREE.y - 40], [TREE.x - 9, TREE.y - 70], [TREE.x + 3, TREE.y - 72], [TREE.x + 5, TREE.y - 40], [TREE.x + 7, TREE.y]],
    crowns: [scallop(TREE.x - 26, TREE.y - 108, 42, 36, 9, 0.16, 71), scallop(TREE.x + 24, TREE.y - 112, 44, 38, 9, 0.16, 72), scallop(TREE.x - 2, TREE.y - 142, 46, 38, 9, 0.16, 73)],
  };

  // ---------------------------------------------------------------- sheep
  const N = 8, TG0 = 0.9, DT = 0.73, V = 330, START_X = -210;
  const TG = [...Array(N)].map((_, i) => TG0 + i * DT);          // gate time of sheep i (= pebble tick)
  const SPOTS = [[1450, 372], [1255, 336], [1545, 488], [1065, 350], [1350, 470], [1150, 462], [1250, 580], [960, 468]];
  const T_OUT = (P1.x + 10 - START_X) / V;
  const GX = P1.x + 10;
  function bez(p0, p1, p2, u) { const a = 1 - u; return [a * a * p0[0] + 2 * a * u * p1[0] + u * u * p2[0], a * a * p0[1] + 2 * a * u * p1[1] + u * u * p2[1]]; }
  function sheepPos(i, t) {
    const tg = TG[i];
    if (t < tg) {
      const u = (t - (tg - T_OUT)) / T_OUT;
      const x = lerp(START_X, GX, u);
      const y = GATE_Y + 70 * Math.pow(cl(1 - u, 0, 1), 1.6) + (i % 2 ? 8 : -6) * cl(1 - u, 0, 1);
      return { x, y, d: V * (t - (tg - T_OUT)), inside: false };
    }
    const TIN = 1.6, u = seg(t, tg, tg + TIN);
    // the path inside: straight on through the gate, then curve to the spot; speed continuous with V at the gate
    const p0 = [GX, GATE_Y], p1 = [GX + 150, GATE_Y], p2 = SPOTS[i];
    const L = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) + Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
    // distance profile: s(u) with s'(0)=V*TIN/L (matching speed), s(1)=1, s'(1)=0  -> cubic
    const a0 = cl(V * TIN / L, 0, 2.9);
    const s = a0 * u + (3 - 2 * a0) * u * u + (a0 - 2) * u * u * u;
    const q = bez(p0, p1, p2, cl(s, 0, 1));
    return { x: q[0], y: q[1], d: V * T_OUT + L * cl(s, 0, 1), inside: true };
  }
  function sheepState(i, t) {
    const p = sheepPos(i, t), pb = sheepPos(i, t - 1 / 30);
    const sp = Math.hypot(p.x - pb.x, p.y - pb.y) * 30;           // px/s
    const walk = cl(sp / V, 0, 1);
    const arrive = TG[i] + 1.6;
    const graze = E.sine(seg(t, arrive - 0.1, arrive + 0.7)) * (0.75 + 0.25 * Math.sin((t - arrive) * 1.7 + i));
    const size = [1.0, 0.96, 1.04, 0.98, 1.02, 0.95, 1.0, 1.03][i];
    return { i, x: p.x, y: p.y, sc: ds(p.y) * size * 1.5, phase: p.d / 44 * Math.PI, walk, graze, inside: p.inside, seed: 900 + i * 37, visible: p.x > -150 };
  }
  // sheep parts in LOCAL coords (facing right, feet at y=0). Styles draw them under translate/scale.
  const SHEEP_BODY = [...Array(N)].map((_, i) => scallop(0, -46, 47, 27, 14, 0.13, 900 + i * 37, 140));
  function sheepParts(st) {
    const bob = -Math.abs(Math.sin(st.phase)) * 2.6 * st.walk;
    const sw = Math.sin(st.phase) * 0.42 * st.walk;
    const body = SHEEP_BODY[st.i].map(([x, y]) => [x, y + bob]);
    const g = st.graze;
    const hx = lerp(46, 52, g), hy = lerp(-54, -30, g) + bob, hr = lerp(0.42, 1.05, g);
    const head = ellipsePts(hx, hy, 16, 11, 28, hr);
    // make the muzzle narrower: pinch the far end of the head ellipse
    const hc = Math.cos(hr), hs = Math.sin(hr);
    const headT = head.map(([x, y]) => { const lx = (x - hx) * hc + (y - hy) * hs, ly = -(x - hx) * hs + (y - hy) * hc; const k = lx > 0 ? 1 - 0.28 * (lx / 16) : 1; const ny = ly * k; return [hx + lx * hc - ny * hs, hy + lx * hs + ny * hc]; });
    const ear = ellipsePts(hx - 6 * hc + 7 * hs, hy - 6 * hs - 8 * hc + 2, 9, 3.6, 16, hr - 0.9 + 0.06 * Math.sin(st.phase * 0.5));
    const earFar = ellipsePts(hx - 2 * hc + 9 * hs, hy - 9 * hc, 8, 3.2, 16, hr - 1.4);
    const tuft = scallop(hx - 7 * hc + 4 * hs, hy - 9 * hc - 3, 8, 6, 6, 0.2, st.seed + 5, 36);
    const eye = [hx + 5 * hc + 2 * hs, hy + 5 * hs - 3 * hc];
    const tail = scallop(-48, -52 + bob, 8, 7, 5, 0.2, st.seed + 7, 30);
    const legs = [
      // [hipX, hipY, footX, footY, near]
      [-22, -26, -22 + Math.sin(sw) * 24, 0, 0], [24, -26, 24 + Math.sin(-sw) * 24, 0, 0],
      [-28, -26, -28 + Math.sin(-sw) * 24, 0, 1], [18, -26, 18 + Math.sin(sw) * 24, 0, 1],
    ].map(([a, b, c, d, nr]) => ({ hip: [a + (nr ? 0 : 5), b + bob], foot: [c + (nr ? 0 : 5), d - (nr ? 0 : 2) - Math.max(0, Math.sin(nr ? st.phase : st.phase + Math.PI)) * 4 * st.walk], near: nr }));
    const shadow = ellipsePts(22, 1, 54, 7.5, 24, 0);
    return { body, head: headT, ear, earFar, tuft, eye, tail, legs, shadow, bob };
  }

  // ---------------------------------------------------------------- pebbles and pouch
  // slots relative to the pouch mouth centre; index 8 stays to the end
  const SLOTS = [[0, -31], [-14, -20], [14, -19], [-26, -8], [26, -7], [0, -10], [-30, 3], [30, 4], [0, 1]].map(([x, y]) => [x * PS * 1.08, y * PS * 1.08]);
  const PEB = { rx: 17, ry: 12 };
  const LIFT = 0.22, FLY = 0.62, SQ = 0.16;
  const T_LEAVE = TG.map((t) => t + 0.06);
  function sway(t) {
    let a = 0;
    for (let k = 0; k < N; k++) { const dt = t - T_LEAVE[k]; if (dt > 0) a += 0.075 * Math.exp(-dt * 3.2) * Math.sin(dt * 12); }
    return a;
  }
  const PIVOT = [PEG.x1 + 4, PEG.y1 + 1];
  function pebbleState(k, t) {
    // returns { where: 'pouch'|'air'|'row', x, y, sc, rot, squash }
    const a = sway(t);
    const inPouch = (sl) => { const p = rotPts([[MOUTH.x + sl[0], MOUTH.y + sl[1]]], PIVOT[0], PIVOT[1], a)[0]; return p; };
    if (k === 8 || t < T_LEAVE[k]) { const p = inPouch(SLOTS[k]); return { where: 'pouch', x: p[0], y: p[1], sc: 0.92, rot: (h2(k, 1) - 0.5) * 0.6 + a, squash: 0 }; }
    const t0 = T_LEAVE[k], p0 = inPouch(SLOTS[k]), R = ROW[k];
    const up = [p0[0] - 6, p0[1] - 62];
    if (t < t0 + LIFT) { const u = E.qOut((t - t0) / LIFT); return { where: 'air', x: lerp(p0[0], up[0], u), y: lerp(p0[1], up[1], u), sc: lerp(0.92, 1.0, u), rot: u * 0.8, squash: 0 }; }
    if (t < t0 + LIFT + FLY) {
      const u = (t - t0 - LIFT) / FLY;
      const c = [lerp(up[0], R.x, 0.62), up[1] - 330];   // high arc: travels above the flock, drops steeply onto the row
      const q = bez(up, c, [R.x, R.y], u);
      return { where: 'air', x: q[0], y: q[1], sc: lerp(1.0, ds(R.y) * 0.98, u), rot: 0.8 + u * 2.4, squash: 0, u };
    }
    const dt = t - t0 - LIFT - FLY;
    const sq = dt < SQ ? Math.sin((dt / SQ) * Math.PI) * 0.22 : 0;
    return { where: 'row', x: R.x, y: R.y, sc: ds(R.y) * 0.98, rot: R.rot + 0.8 + 2.4, squash: sq, landed: dt };
  }
  function pebblePath(k, t) {
    // the full flight curve of pebble k (for styles that draw trajectories)
    const t0 = T_LEAVE[k];
    const pts = [];
    for (let j = 0; j <= 40; j++) { const tt = t0 + (LIFT + FLY) * j / 40; const s = pebbleState(k, Math.min(tt, t0 + LIFT + FLY - 1e-4)); pts.push([s.x, s.y]); }
    return pts;
  }
  function pouchParts(t) {
    const a = sway(t);
    const M = MOUTH, k = PS;
    const Lp = (pts) => pts.map(([x, y]) => [M.x + x * k, M.y + y * k]);
    const rim = Lp(scallop(0, 0, 50, 14, 11, 0.1, 481, 88));
    // cloth sack: flared ruffled mouth, gathered neck, round belly
    const side = [[-50, 0], [-40, 9], [-31, 17], [-38, 27], [-52, 42], [-60, 60], [-56, 80], [-40, 95], [-18, 101], [0, 102]];
    const right = side.slice(0, -1).reverse().map(([x, y]) => [-x * 0.98 + 1, y + (y > 30 ? 1.5 : 0)]);
    const front = []; for (let j = 1; j < 20; j++) { const an = Math.PI - (j / 20) * Math.PI; front.push([50 * Math.cos(an), 14 * Math.sin(an) + 1.2 * Math.sin(an * 11)]); }
    const body = Lp(side.concat(right).concat(front.reverse().map(([x, y]) => [x, y])));
    const tie = Lp([[-33, 13], [0, 20], [33, 13], [34, 20], [0, 27], [-34, 20]]);
    const shade = Lp([[8, 30], [46, 34], [60, 58], [55, 80], [38, 95], [10, 102], [-20, 101], [18, 84], [32, 58]]);
    const folds = [Lp([[-18, 24], [-26, 46], [-30, 70]]), Lp([[4, 26], [6, 52], [2, 80]]), Lp([[22, 23], [32, 44], [40, 62]])];
    const R = (p) => rotPts(p, PIVOT[0], PIVOT[1], a);
    const att = [M.x + 36 * k, M.y - 9 * k];
    const rope = [[PEG.x1 + 4, PEG.y1 + 1], [lerp(PEG.x1, att[0], 0.5) + 3, lerp(PEG.y1, att[1], 0.5) + 2], att];
    const peg = [[PEG.x0, PEG.y0 - 5], [PEG.x1, PEG.y1 - 4], [PEG.x1 - 3, PEG.y1 + 1], [PEG.x1, PEG.y1 + 5], [PEG.x0, PEG.y0 + 5]];
    return { rim: R(rim), body: R(body), tie: R(tie), shade: R(shade), folds: folds.map(R), rope: [rope[0]].concat(R(rope.slice(1))), peg, a, mouth: R([[M.x, M.y]])[0] };
  }
  function pebblePts(ps, seed) {
    return ellipsePts(ps.x, ps.y - PEB.ry * ps.sc * (1 - ps.squash) * 0.2, PEB.rx * ps.sc * (1 + ps.squash), PEB.ry * ps.sc * (1 - ps.squash), 18, ps.rot * 0.25, 0.07, seed);
  }

  // ---------------------------------------------------------------- camera and glint
  const FOCUS = { x: MOUTH.x, y: MOUTH.y + 2 };
  const PUSH0 = 6.9, S_END = 2.6, A_END = { x: 800, y: 530 };
  function camera(t) {
    const s0 = 1.08 + 0.025 * seg(t, 0, PUSH0);
    const u = E.sine(seg(t, PUSH0, DUR + 0.25));
    const s = Math.exp(lerp(Math.log(s0), Math.log(S_END), u));
    const wide = { x: (FOCUS.x - 905) * s0 + 960, y: (FOCUS.y - 552) * s0 + 540 };
    const sx = lerp(wide.x, A_END.x, u), sy = lerp(wide.y, A_END.y, u);
    return { s, e: sx - FOCUS.x * s, f: sy - FOCUS.y * s, u };
  }
  function glint(t) {
    const g = E.sine(seg(t, 7.9, 8.7));
    return g * (0.86 + 0.14 * Math.sin((t - 8.7) * 2.6));
  }

  // ---------------------------------------------------------------- draw order
  // items that need depth sorting: stones, sheep, pouch, tufts, tree
  function items(t) {
    const L = [];
    for (const s of STONES) L.push({ k: s.key, type: 'stone', o: s });
    for (const tf of TUFTS) L.push({ k: tf.y - (tf.wall ? 0 : 0.5), type: 'tuft', o: tf });
    for (let i = 0; i < N; i++) { const st = sheepState(i, t); if (st.visible) L.push({ k: st.y + 0.3, type: 'sheep', o: st }); }
    L.push({ k: P1.y + 0.5, type: 'pouch' });
    L.push({ k: TREE.y, type: 'tree' });
    L.sort((a, b) => a.k - b.k);
    return L;
  }

  // ---------------------------------------------------------------- canvas path helpers
  function smooth(ctx, pts, closed) {
    const n = pts.length;
    if (n < 3) { ctx.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < n; i++) ctx.lineTo(pts[i][0], pts[i][1]); if (closed) ctx.closePath(); return; }
    const P = (i) => closed ? pts[(i + n) % n] : pts[cl(i, 0, n - 1)];
    ctx.moveTo(P(0)[0], P(0)[1]);
    const last = closed ? n : n - 1;
    for (let i = 0; i < last; i++) {
      const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
      ctx.bezierCurveTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6, p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]);
    }
    if (closed) ctx.closePath();
  }
  function poly(ctx, pts, closed) { ctx.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]); if (closed) ctx.closePath(); }
  function jitter(pts, amp, seed) { return pts.map(([x, y], i) => [x + (h2(seed, i * 2) - 0.5) * 2 * amp, y + (h2(seed, i * 2 + 1) - 0.5) * 2 * amp]); }
  // smooth low-frequency wobble (hand-drawn lines): neighbours move together
  function wobble(pts, amp, seed, freq) {
    freq = freq || 0.35;
    return pts.map(([x, y], i) => {
      const u = i * freq, i0 = Math.floor(u), f = u - i0, sm = f * f * (3 - 2 * f);
      const nx = lerp(h2(seed, i0 * 2), h2(seed, i0 * 2 + 2), sm) - 0.5, ny = lerp(h2(seed + 7, i0 * 2), h2(seed + 7, i0 * 2 + 2), sm) - 0.5;
      return [x + nx * 2 * amp, y + ny * 2 * amp];
    });
  }
  function polyLen(pts, closed) { let L = 0; const n = pts.length; for (let i = 1; i < n + (closed ? 1 : 0); i++) { const a = pts[i - 1], b = pts[i % n]; L += Math.hypot(b[0] - a[0], b[1] - a[1]); } return L; }
  // draw the first fraction f of a polyline (draw-on)
  function partial(ctx, pts, closed, f) {
    if (f <= 0) return;
    const P = closed ? pts.concat([pts[0]]) : pts;
    const L = polyLen(P, false) * cl(f, 0, 1);
    ctx.moveTo(P[0][0], P[0][1]);
    let acc = 0;
    for (let i = 1; i < P.length; i++) {
      const a = P[i - 1], b = P[i], d = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (acc + d >= L) { const u = (L - acc) / (d || 1); ctx.lineTo(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u); return; }
      ctx.lineTo(b[0], b[1]); acc += d;
    }
  }

  window.SAHNE = {
    W, H, DUR, N, TG, PEN, P1, P2, PEG, MOUTH, SLAB, TREE, HORIZON, STONES, TUFTS, HILLS, SLAB_TOP, SLAB_SIDE, ROW, TREE_SHAPES, SPOTS, PEB, SLOTS, LIFT, FLY, T_LEAVE, FOCUS,
    cl, lerp, hash, h2, prng, E, seg, ds, ellipsePts, blob, scallop, xf, rotPts, tuftPts,
    sheepState, sheepParts, pebbleState, pebblePath, pebblePts, pouchParts, sway, camera, glint, items,
    smooth, poly, jitter, wobble, polyLen, partial,
  };
})();
