//! Math with Zirek · "akşam, ağıl, 8 koyun, 8 çakıl, torbada tek çakıl" (10 s, 1920x1080, 30 fps)
//!
//! Faithful fframes port of the HyperFrames flat-2D scene `videolar/hf-tarzlar/duz2d`
//! (index.html + assets/sahne.js). Every value is a pure function of time `t = frame / 30`,
//! with the same seeded PRNG (mulberry32) so walls, stones and scallops come out identical.
use fframes::{AudioMap, Color, Duration, FFramesContext, Frame, Svgr, Video, include_media_dir};
use std::f64::consts::PI;

include_media_dir!(pub struct ZirekMedia, "media");

pub const WIDTH: usize = 1920;
pub const HEIGHT: usize = 1080;
const INK: &str = "#3A2F3F";

// ------------------------------------------------------------------ shapes
#[derive(Clone)]
pub enum Sh {
    P { d: String, fill: &'static str, stroke: &'static str, sw: f64, op: f64 },
    E { cx: f64, cy: f64, rx: f64, ry: f64, fill: &'static str, stroke: &'static str, sw: f64, op: f64 },
    C { cx: f64, cy: f64, r: f64, fill: &'static str, stroke: &'static str, sw: f64, op: f64 },
    R { x: f64, y: f64, w: f64, h: f64, rx: f64, fill: &'static str, stroke: &'static str, sw: f64, op: f64 },
    G { tf: String, op: f64, kids: Vec<Sh> },
}

fn path(d: String, fill: &'static str, stroke: &'static str, sw: f64, op: f64) -> Sh {
    Sh::P { d, fill, stroke, sw, op }
}
fn ell(cx: f64, cy: f64, rx: f64, ry: f64, fill: &'static str, stroke: &'static str, sw: f64, op: f64) -> Sh {
    Sh::E { cx, cy, rx, ry, fill, stroke, sw, op }
}
fn circ(cx: f64, cy: f64, r: f64, fill: &'static str, stroke: &'static str, sw: f64, op: f64) -> Sh {
    Sh::C { cx, cy, r, fill, stroke, sw, op }
}
fn grp(tf: String, op: f64, kids: Vec<Sh>) -> Sh {
    Sh::G { tf, op, kids }
}
const ID: &str = "matrix(1 0 0 1 0 0)";

pub fn draw(s: Sh) -> Svgr<'static> {
    match s {
        Sh::P { d, fill, stroke, sw, op } => fframes::svgr!(
            <path d={d} fill={fill} stroke={stroke} stroke-width={sw} opacity={op} stroke-linecap="round" stroke-linejoin="round" />
        ),
        Sh::E { cx, cy, rx, ry, fill, stroke, sw, op } => fframes::svgr!(
            <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={fill} stroke={stroke} stroke-width={sw} opacity={op} />
        ),
        Sh::C { cx, cy, r, fill, stroke, sw, op } => fframes::svgr!(
            <circle cx={cx} cy={cy} r={r} fill={fill} stroke={stroke} stroke-width={sw} opacity={op} />
        ),
        Sh::R { x, y, w, h, rx, fill, stroke, sw, op } => fframes::svgr!(
            <rect x={x} y={y} width={w} height={h} rx={rx} fill={fill} stroke={stroke} stroke-width={sw} opacity={op} />
        ),
        Sh::G { tf, op, kids } => {
            let v: Vec<Svgr<'static>> = kids.into_iter().map(draw).collect();
            fframes::svgr!(<g transform={tf} opacity={op}>{v}</g>)
        }
    }
}

// ------------------------------------------------------------------ helpers (sahne.js)
fn cl(x: f64, a: f64, b: f64) -> f64 {
    x.max(a).min(b)
}
fn lerp(a: f64, b: f64, u: f64) -> f64 {
    a + (b - a) * u
}
fn smooth(u: f64) -> f64 {
    let u = cl(u, 0., 1.);
    u * u * (3. - 2. * u)
}
fn sine_io(u: f64) -> f64 {
    0.5 - 0.5 * (PI * cl(u, 0., 1.)).cos()
}
fn out_q(u: f64) -> f64 {
    let u = cl(u, 0., 1.);
    1. - (1. - u) * (1. - u)
}
fn hash(n: f64) -> f64 {
    let s = (n * 127.1 + 311.7).sin() * 43758.5453;
    s - s.floor()
}
/// mulberry32, bit-identical to the JS version.
struct Rng(u32);
impl Rng {
    fn new(seed: u32) -> Self {
        Rng(seed)
    }
    fn next(&mut self) -> f64 {
        self.0 = self.0.wrapping_add(0x6D2B79F5);
        let a = self.0;
        let mut t = (a ^ (a >> 15)).wrapping_mul(1 | a);
        t = t.wrapping_add((t ^ (t >> 7)).wrapping_mul(61 | t)) ^ t;
        ((t ^ (t >> 14)) as f64) / 4294967296.0
    }
}

// ------------------------------------------------------------------ geometry (wide shot)
const DUR: f64 = 10.;
const N: usize = 8;
const GAP: f64 = 0.73;
const T0: f64 = 1.25;
const PUSH0: f64 = 7.0;
const GLINT: f64 = 7.9;
const PEN_CX: f64 = 1265.;
const PEN_CY: f64 = 548.;
const PEN_RX: f64 = 520.;
const PEN_RY: f64 = 124.;
const PEN_H: f64 = 46.;
const POST_H: f64 = 150.;
const SPEED: f64 = 232.;
const PEB_RX: f64 = 21.;
const PEB_RY: f64 = 15.5;
const SLOTS: [[f64; 2]; 9] = [
    [0., 2.], [-35., 1.], [35., 1.],
    [-50., -13.], [-17., -16.], [17., -16.], [50., -13.],
    [-17., -31.], [17., -31.],
];
const TAKE: [usize; 8] = [8, 7, 3, 6, 4, 5, 1, 2];
const REST: [[f64; 2]; 8] = [[1600., 524.], [1440., 486.], [1660., 592.], [1290., 494.], [1500., 586.], [1705., 530.], [1330., 598.], [1392., 540.]];
const REST_FACE: [f64; 8] = [-1., 1., -1., -1., 1., -1., -1., 1.];
const LIFT: f64 = 0.2;
const FLY: f64 = 0.52;
const LAND: f64 = 0.22;
const SLAB_X: f64 = 1045.;
const SLAB_Y: f64 = 808.;
const SLAB_RX: f64 = 280.;
const SLAB_RY: f64 = 64.;
const WALLC: [&str; 5] = ["#BDB8B4", "#ADA8A6", "#C8C2BA", "#A39FA2", "#B6B0AC"];
const PEB_COL: [&str; 9] = ["#D6904A", "#DDA05A", "#CF8A48", "#E0A862", "#D39352", "#DB9B55", "#D08C4C", "#DEA25E", "#D8964F"];
const HIPS: [[f64; 2]; 4] = [[-30., -36.], [30., -36.], [-22., -36.], [38., -36.]];

fn front_y(x: f64) -> f64 {
    let d = (x - PEN_CX) / PEN_RX;
    if d.abs() >= 1. { PEN_CY } else { PEN_CY + PEN_RY * (1. - d * d).sqrt() }
}
fn back_y(x: f64) -> f64 {
    let d = (x - PEN_CX) / PEN_RX;
    if d.abs() >= 1. { PEN_CY } else { PEN_CY - PEN_RY * (1. - d * d).sqrt() }
}

#[derive(Clone, Copy)]
struct Pt {
    x: f64,
    y: f64,
}
struct Geo {
    postl: Pt,
    postr: Pt,
    gate: Pt,
    peg: Pt,
    mouth: Pt,
    stick: [f64; 4],
    row: Vec<Pt>,
    paths: Vec<(Vec<[f64; 2]>, f64, f64)>, // points, LG, L
}
fn poly_len(p: &[[f64; 2]]) -> f64 {
    p.windows(2).map(|w| (w[1][0] - w[0][0]).hypot(w[1][1] - w[0][1])).sum()
}
fn poly_at(p: &[[f64; 2]], mut s: f64) -> (f64, f64) {
    for k in 1..p.len() {
        let (a, b) = (p[k - 1], p[k]);
        let l = (b[0] - a[0]).hypot(b[1] - a[1]);
        if s <= l || k == p.len() - 1 {
            let u = cl(s / l, 0., 1.);
            return (lerp(a[0], b[0], u), lerp(a[1], b[1], u));
        }
        s -= l;
    }
    (p[0][0], p[0][1])
}
impl Geo {
    fn new() -> Self {
        let postl = Pt { x: 868., y: front_y(868.) };
        let postr = Pt { x: 1004., y: front_y(1004.) };
        let gate = Pt { x: 936., y: (postl.y + postr.y) / 2. };
        let peg = Pt { x: 1136., y: postr.y - 167. };
        let mouth = Pt { x: peg.x, y: peg.y + 64. };
        let stick = [996., postr.y - 132., 1146., postr.y - 172.];
        let row = (0..8).map(|k| Pt { x: 856. + k as f64 * 54., y: 800. + (k % 2) as f64 * 3. - 2. }).collect();
        let approach = vec![[-300., 752.], [420., 728.], [700., 704.], [870., 666.], [gate.x, gate.y]];
        let lg = poly_len(&approach);
        let paths = REST
            .iter()
            .enumerate()
            .map(|(i, r)| {
                let mut p = approach.clone();
                p.push([gate.x + 70., gate.y - 34.]);
                p.push([lerp(gate.x + 70., r[0], 0.5), lerp(gate.y - 34., r[1], 0.6) + if i % 2 == 1 { -8. } else { 8. }]);
                p.push(*r);
                let l = poly_len(&p);
                (p, lg, l)
            })
            .collect();
        Geo { postl, postr, gate, peg, mouth, stick, row, paths }
    }
    fn t_gate(i: usize) -> f64 {
        T0 + i as f64 * GAP
    }
    fn swing(t: f64) -> f64 {
        let mut a = 0.;
        for k in 0..N {
            let d = t - (Self::t_gate(k) - 0.02);
            if d > 0. {
                a += 5.5 * (-d * 3.2).exp() * (d * 10.).sin();
            }
        }
        a
    }
    fn slack(t: f64) -> f64 {
        (0..N).map(|k| smooth((t - Self::t_gate(k)) / 0.35)).sum::<f64>() / N as f64
    }
    fn mouth_at(&self, t: f64) -> Pt {
        rot_around(self.mouth.x, self.mouth.y + 6. * Self::slack(t), self.peg.x, self.peg.y, Self::swing(t))
    }
}
fn rot_around(x: f64, y: f64, cx: f64, cy: f64, deg: f64) -> Pt {
    let r = deg * PI / 180.;
    let (c, s) = (r.cos(), r.sin());
    Pt { x: cx + (x - cx) * c - (y - cy) * s, y: cy + (x - cx) * s + (y - cy) * c }
}

struct SheepSt {
    x: f64,
    y: f64,
    s: f64,
    face_s: f64,
    dist: f64,
    v: f64,
    head: f64,
}
fn depth(y: f64) -> f64 {
    cl(0.74 + 0.47 * (y - 480.) / 270., 0.6, 1.3)
}
fn sheep_state(g: &Geo, i: usize, t: f64) -> SheepSt {
    let (p, lg, d) = &g.paths[i];
    let u = lg + SPEED * (t - Geo::t_gate(i));
    let k = 150.;
    let (mut s, v);
    if u < d - k {
        s = u;
        v = 1.;
    } else {
        let e = (u - (d - k)) / k;
        s = d - k + k * (1. - (-e).exp());
        v = (-e).exp();
    }
    s = s.max(0.);
    let (x, y) = poly_at(p, s);
    let idle = 1. - v;
    let t_turn = Geo::t_gate(i) + (d - k + 1.4 * k - lg) / SPEED;
    let turn = smooth((t - t_turn) / 0.4);
    let face_s = lerp(1., REST_FACE[i], turn);
    SheepSt { x, y, s: depth(y), face_s, dist: s, v, head: idle * (0.5 + 0.5 * (t * 1.7 + i as f64 * 1.3).sin()) }
}
fn walk(st: &SheepSt, k: usize) -> (f64, f64) {
    let ph = st.dist / 34. + if k == 0 || k == 3 { 0. } else { PI };
    (ph.sin() * 26. * st.v, -(st.dist / 34.).sin().abs() * 5. * st.v)
}

struct PebSt {
    x: f64,
    y: f64,
    in_pouch: bool,
    slot: usize,
    rot: f64,
    sq: f64,
    landed: bool,
    age: f64,
}
fn pebble(g: &Geo, k: usize, t: f64) -> PebSt {
    if k == 8 {
        let m = g.mouth_at(t);
        return PebSt { x: m.x + SLOTS[0][0], y: m.y + SLOTS[0][1], in_pouch: true, slot: 0, rot: -6., sq: 1., landed: false, age: 0. };
    }
    let slot = TAKE[k];
    let t0 = Geo::t_gate(k) - 0.05;
    let m = g.mouth_at(t);
    let s = Pt { x: m.x + SLOTS[slot][0], y: m.y + SLOTS[slot][1] };
    let e = g.row[k];
    let kf = k as f64;
    let rot0 = (hash(kf + 7.) - 0.5) * 50.;
    let rot1 = (hash(kf + 17.) - 0.5) * 24.;
    let base = PebSt { x: s.x, y: s.y, in_pouch: true, slot, rot: rot0, sq: 1., landed: false, age: 0. };
    if t < t0 {
        return base;
    }
    let a = t - t0;
    let top = Pt { x: s.x + 6., y: m.y - 92. };
    if a < LIFT {
        let u = out_q(a / LIFT);
        return PebSt { x: lerp(s.x, top.x, u), y: lerp(s.y, top.y, u), in_pouch: a < 0.06, ..base };
    }
    if a < LIFT + FLY {
        let u = (a - LIFT) / FLY;
        let ee = sine_io(u);
        let x = lerp(top.x, e.x, ee);
        let y = lerp(top.y, e.y, u * u) - (PI * u).sin() * 70.;
        return PebSt { x, y, in_pouch: false, rot: lerp(rot0, rot1 + 360., ee), ..base };
    }
    let b = a - LIFT - FLY;
    let sq = if b < LAND { 1. + 0.22 * (PI * b / LAND).sin() * (-b * 6.).exp() } else { 1. };
    PebSt { x: e.x, y: e.y, in_pouch: false, slot, rot: rot1, sq, landed: true, age: b }
}

struct Cam {
    s: f64,
    fx: f64,
    fy: f64,
    ax: f64,
    ay: f64,
}
fn cam(g: &Geo, t: f64) -> Cam {
    let drift = smooth(t / PUSH0) * 0.03;
    let u = sine_io((t - PUSH0) / (DUR - PUSH0));
    Cam {
        s: lerp(1.2 + drift, 2.45, u),
        fx: lerp(1112., g.mouth.x, u),
        fy: lerp(606., g.mouth.y + 12., u),
        ax: lerp(960., 900., u),
        ay: lerp(540., 430., u),
    }
}
fn cam_matrix(c: &Cam, p: f64) -> String {
    let s = 1. + (c.s - 1.) * p;
    let (fx, fy) = (lerp(960., c.fx, p), lerp(540., c.fy, p));
    let (ax, ay) = (lerp(960., c.ax, p), lerp(540., c.ay, p));
    format!("matrix({s:.5} 0 0 {s:.5} {:.2} {:.2})", ax - fx * s, ay - fy * s)
}
fn glint(t: f64) -> f64 {
    let a = t - GLINT;
    if a <= 0. {
        return 0.;
    }
    smooth(a / 0.7) * (0.78 + 0.22 * (a * 3.1).cos())
}

// ------------------------------------------------------------------ builders (index.html)
fn f(v: f64) -> String {
    format!("{:.1}", v)
}
fn scallop(cx: f64, cy: f64, rx: f64, ry: f64, n: usize, bump: f64, seed: u32) -> String {
    let mut r = Rng::new(seed);
    let pts: Vec<(f64, f64, f64)> = (0..n)
        .map(|k| {
            let a = (k as f64 / n as f64) * PI * 2. + 0.2;
            let j = 1. + (r.next() - 0.5) * 0.08;
            (cx + a.cos() * rx * j, cy + a.sin() * ry * j, a)
        })
        .collect();
    let mut d = format!("M{} {}", f(pts[0].0), f(pts[0].1));
    for k in 0..n {
        let (p, q) = (pts[k], pts[(k + 1) % n]);
        let am = (p.2 + q.2 + if k == n - 1 { PI * 2. } else { 0. }) / 2.;
        d += &format!(" Q{} {} {} {}", f(cx + am.cos() * rx * bump), f(cy + am.sin() * ry * bump), f(q.0), f(q.1));
    }
    d + " Z"
}
fn stone(x: f64, y: f64, w: f64, h: f64, fill: &'static str, rot: f64) -> Sh {
    grp(
        format!("rotate({} {} {})", f(rot), f(x), f(y)),
        1.,
        vec![Sh::R { x: x - w / 2., y: y - h / 2., w, h, rx: h * 0.48, fill, stroke: INK, sw: 2.4, op: 1. }],
    )
}
fn wall(x0: f64, x1: f64, arc: fn(f64) -> f64, seed: u32, out: &mut Vec<Sh>) {
    let mut r = Rng::new(seed);
    let h = PEN_H;
    let mut d = String::new();
    let mut x = x0;
    while x <= x1 + 0.1 {
        d += &format!("{}{} {} ", if d.is_empty() { "M" } else { "L" }, f(x), f(arc(x) - h));
        x += 4.;
    }
    let mut x = x1;
    while x >= x0 - 0.1 {
        d += &format!("L{} {} ", f(x), f(arc(x) + 2.));
        x -= 4.;
    }
    d += "Z";
    out.push(path(d, "#8F8A8E", INK, 3., 1.));
    let mut pts: Vec<(f64, f64, f64)> = Vec::new();
    let mut ll = 0.;
    let mut x = x0;
    while x <= x1 + 0.01 {
        let y = arc(x);
        if let Some(last) = pts.last() {
            ll += 1f64.hypot(y - last.1);
        }
        pts.push((x, y, ll));
        x += 1.;
    }
    let at = |l: f64| -> (f64, f64, f64) {
        let (mut lo, mut hi) = (0usize, pts.len() - 1);
        while hi - lo > 1 {
            let m = (lo + hi) >> 1;
            if pts[m].2 < l { lo = m } else { hi = m }
        }
        let (p, q) = (pts[lo], pts[hi]);
        let dx = if q.0 - p.0 == 0. { 1e-3 } else { q.0 - p.0 };
        (p.0, p.1, (q.1 - p.1).atan2(dx) * 180. / PI)
    };
    let mut course = |y_off: f64, h_min: f64, cols: &[&'static str], cap: bool, out: &mut Vec<Sh>| {
        let mut l = if cap { 2. } else { r.next() * 14. };
        while l < ll - 6. {
            let w = if cap { 30. } else { 24. } + r.next() * 16.;
            let lm = (l + w / 2.).min(ll - 8.);
            let (x, y, ang) = at(lm);
            let rot = ang.clamp(-38., 38.) * 0.8 + (r.next() - 0.5) * 7.;
            let wf = (w * (0.55 + 0.45 * (ang * PI / 180.).cos().abs())).max(12.);
            let hh = h_min + r.next() * 3.;
            let col = cols[(r.next() * cols.len() as f64).floor() as usize];
            out.push(stone(x, y + y_off, wf - 2., hh, col, rot));
            l += w;
        }
    };
    for c in 0..3 {
        course(-8. - c as f64 * 15., 14., &WALLC, false, out);
    }
    course(-h + 2., 12., &["#D9D2C6", "#CFC8BD", "#E0D9CC"], true, out);
}
fn post(x: f64, yb: f64, h: f64, seed: u32, out: &mut Vec<Sh>) {
    let mut r = Rng::new(seed);
    out.push(ell(x + 34., yb + 2., 54., 9., "#4B3B5A", "none", 0., 0.2));
    let mut y = yb - 10.;
    while y > yb - h {
        let w = 48. + r.next() * 12.;
        let hh = 17. + r.next() * 5.;
        let ox = (r.next() - 0.5) * 6.;
        let col = WALLC[(r.next() * 5.).floor() as usize];
        let rot = (r.next() - 0.5) * 8.;
        out.push(stone(x + ox, y, w, hh, col, rot));
        y -= hh - 1.5;
    }
    let rot = (r.next() - 0.5) * 6.;
    out.push(stone(x, y + 2., 58., 16., "#D9D2C6", rot));
}
fn pebble_shapes(k: usize) -> Vec<Sh> {
    let (rx, ry) = (PEB_RX, PEB_RY);
    vec![
        ell(0., 0., rx, ry, PEB_COL[k % 9], INK, 3., 1.),
        path(
            format!(
                "M{} 3 C {} {}, {} {}, {} 2 C {} {}, {} {}, {} 3 Z",
                -rx + 5., -rx + 8., ry - 2., rx - 8., ry - 1., rx - 3., rx - 6., ry - 5., -rx + 10., ry - 5., -rx + 5.
            ),
            "#A9642F",
            "none",
            0.,
            0.45,
        ),
        ell(-7., -6., 7., 4., "#F6CE92", "none", 0., 0.9),
    ]
}

struct SheepParts {
    legs: [Vec<Sh>; 4],
    tail: Sh,
    mid: Vec<Sh>,
    bas_a: Vec<Sh>,
    kulak: Vec<Sh>,
    bas_b: Vec<Sh>,
}
fn sheep_parts(i: u32) -> SheepParts {
    let leg = |x: f64, col: &'static str| {
        vec![
            path(format!("M{x} -36 L{x} -3"), "none", col, 10., 1.),
            path(format!("M{} -4 L{} -4", x - 5., x + 6.), "none", "#241D29", 7., 1.),
        ]
    };
    SheepParts {
        legs: [leg(-30., "#2A232F"), leg(30., "#2A232F"), leg(-22., "#3F3547"), leg(38., "#3F3547")],
        tail: path("M-56 -66 q-14 -2 -12 12 q4 8 12 2".into(), "#F2E8D6", INK, 3., 1.),
        mid: vec![
            path(scallop(0., -58., 58., 33., 12, 1.2, 100 + i), "#E9DDC6", INK, 3.6, 1.),
            path(scallop(-6., -63., 47., 24., 10, 1.18, 200 + i), "#FFFAF0", "none", 0., 1.),
            path("M-26 -52 q6 -6 12 0 M4 -46 q6 -6 12 0 M-10 -70 q6 -6 12 0 M22 -66 q5 -5 10 0".into(), "none", "#D8C9AE", 2.6, 1.),
        ],
        bas_a: vec![grp("rotate(-35 44 -80)".into(), 1., vec![ell(44., -80., 12., 6., "#2F2836", "none", 0., 1.)])],
        kulak: vec![
            grp("rotate(28 50 -66)".into(), 1., vec![ell(50., -66., 14., 6.5, "#3F3547", INK, 2., 1.)]),
            grp("rotate(28 51 -65)".into(), 1., vec![ell(51., -65., 8., 3., "#C98F86", "none", 0., 1.)]),
        ],
        bas_b: vec![
            path("M44 -84 C 60 -92, 86 -80, 92 -62 C 96 -50, 88 -42, 76 -44 C 62 -46, 48 -58, 44 -70 Z".into(), "#3F3547", INK, 3., 1.),
            path("M84 -52 q5 2 6 -3".into(), "none", "#6E5E72", 2., 1.),
            circ(72., -70., 5.2, "#FFFAF0", "none", 0., 1.),
            circ(73.6, -69.5, 2.8, "#1E1822", "none", 0., 1.),
            circ(72.4, -71., 1., "#FFFFFF", "none", 0., 1.),
            path(scallop(52., -84., 13., 10., 6, 1.3, 300 + i), "#FFFAF0", INK, 2.6, 1.),
        ],
    }
}

// ------------------------------------------------------------------ video
pub struct ZirekVideo {
    g: Geo,
    sky: Vec<Sh>,
    clouds: Vec<Sh>,
    far: Vec<Sh>,
    mid: Vec<Sh>,
    stage_a: Vec<Sh>,
    stage_b: Vec<Sh>,
    stage_c: Vec<Sh>,
    cords: Vec<Sh>,
    pouch_top: Vec<Sh>,
    pouch_body: Vec<Sh>,
    slab: Vec<Sh>,
    sheep: Vec<SheepParts>,
    peb: Vec<Vec<Sh>>,
    pile_order: Vec<usize>,
}

impl Default for ZirekVideo {
    fn default() -> Self {
        Self::new()
    }
}

impl ZirekVideo {
    pub fn new() -> Self {
        let g = Geo::new();
        // sky (L0)
        let sky = vec![circ(300., 300., 250., "url(#gunesHale)", "none", 0., 1.), circ(300., 300., 62., "#FFF3D0", "none", 0., 1.)];
        let clouds = [(0.0, 11u32), (0.0, 12), (0.0, 13)]
            .iter()
            .map(|&(_, sd)| {
                grp(
                    ID.into(),
                    1.,
                    vec![
                        path(scallop(0., 0., 120., 26., 9, 1.35, sd), "#FBE9D4", "none", 0., 0.9),
                        path("M-110 12 L110 12".into(), "none", "#E6BFA0", 5., 0.7),
                    ],
                )
            })
            .collect();
        // far hills (L1)
        let far = vec![
            path("M-400 420 C 0 340, 380 330, 720 372 C 1000 405, 1260 330, 1560 318 C 1800 310, 2050 350, 2400 380 L2400 1400 L-400 1400 Z".into(), "#C7B98E", INK, 3., 1.),
            path("M-400 440 C 100 390, 500 400, 900 420 C 1300 440, 1700 400, 2400 420 L2400 1400 L-400 1400 Z".into(), "#B7B784", "none", 0., 0.9),
            grp(
                "translate(540 392)".into(),
                1.,
                vec![
                    path("M-6 0 L-4 -60 L4 -60 L7 0 Z".into(), "#6E5140", INK, 2.5, 1.),
                    path(scallop(0., -92., 46., 40., 9, 1.22, 21), "#8FA06A", INK, 3., 1.),
                    path(scallop(-10., -100., 30., 24., 7, 1.2, 22), "#A3B277", "none", 0., 1.),
                    ell(34., 2., 46., 5., "#4B3B5A", "none", 0., 0.2),
                ],
            ),
        ];
        let mid = vec![path("M-400 470 C 200 432, 700 440, 1100 430 C 1500 420, 1900 440, 2400 452 L2400 1400 L-400 1400 Z".into(), "#AFB779", INK, 3., 1.)];
        // stage (L3)
        let (gx, gy) = (g.gate.x, g.gate.y);
        let mut a = vec![
            path("M-500 500 C 0 480, 600 470, 1100 470 C 1600 468, 2000 478, 2500 490 L2500 1700 L-500 1700 Z".into(), "#B8C07F", "none", 0., 1.),
            path("M-500 760 C 300 700, 1200 720, 2500 700 L2500 1700 L-500 1700 Z".into(), "#B2BB79", "none", 0., 0.8),
            path(
                format!("M-300 720 C 200 700, 500 690, 720 680 C 820 674, 880 652, {} {} L {} {} C 900 690, 820 706, 720 714 C 500 736, 200 760, -300 800 Z", gx, gy - 8., gx + 20., gy + 8.),
                "#D4C597",
                "none",
                0.,
                0.85,
            ),
        ];
        for (x, y, s) in [(120., 640., 1.), (300., 860., 1.2), (520., 940., 1.3), (180., 990., 1.4), (640., 612., 0.9), (760., 860., 1.1), (1840., 560., 0.8), (1380., 700., 0.9), (60., 820., 1.2), (1720., 690., 0.9)] {
            a.push(path(
                format!(
                    "M{} {} q{} {} {} {} M{} {} q{} {} {} {} M{} {} q{} {} {} {}",
                    x - 8. * s, y, 2. * s, -12. * s, -4. * s, -20. * s,
                    x, y, 1. * s, -14. * s, 2. * s, -24. * s,
                    x + 8. * s, y, -1. * s, -12. * s, 6. * s, -19. * s
                ),
                "none",
                "#7F8C52",
                2.6 * s,
                1.,
            ));
        }
        a.push(ell(PEN_CX, PEN_CY, PEN_RX, PEN_RY, "#A6B06E", "none", 0., 1.));
        a.push(ell(PEN_CX + 40., PEN_CY + 20., PEN_RX - 90., PEN_RY - 40., "#B3BC78", "none", 0., 0.7));
        wall(PEN_CX - PEN_RX + 2., PEN_CX + PEN_RX - 2., back_y, 1, &mut a);
        let mut b = Vec::new();
        wall(PEN_CX - PEN_RX + 2., g.postl.x - 16., front_y, 2, &mut b);
        post(g.postl.x, g.postl.y, POST_H, 3, &mut b);
        let mut c = Vec::new();
        wall(g.postr.x + 16., PEN_CX + PEN_RX - 2., front_y, 4, &mut c);
        let m = g.mouth;
        c.push(ell(m.x + 40., m.y + 96., 84., 70., "#4B3B5A", "none", 0., 0.18));
        post(g.postr.x, g.postr.y, POST_H, 5, &mut c);
        let [x0, y0, x1, y1] = g.stick;
        c.push(path(format!("M{x0} {y0} L{x1} {y1}"), "none", INK, 14., 1.));
        c.push(path(format!("M{x0} {y0} L{x1} {y1}"), "none", "#8A6242", 8., 1.));
        c.push(path(format!("M{} {} L{} {}", x0 + 8., y0 - 5., x1 - 6., y1 - 3.), "none", "#B88B5E", 2.5, 1.));
        // pouch
        let cords = vec![
            path(format!("M{} {} L{} {} M{} {} L{} {}", g.peg.x, g.peg.y, m.x - 40., m.y - 6., g.peg.x, g.peg.y, m.x + 40., m.y - 6.), "none", "#5A3E2C", 4.5, 1.),
            circ(g.peg.x, g.peg.y, 7., "#5A3E2C", "none", 0., 1.),
        ];
        let pouch_top = vec![ell(m.x, m.y, 70., 20., "#A8472F", INK, 3.5, 1.), ell(m.x, m.y + 3., 56., 13., "#4A1C15", "none", 0., 1.)];
        let (mx, my) = (m.x, m.y);
        let body = format!(
            "M{} {} C {} {}, {} {}, {} {} C {} {}, {} {}, {} {} C {} {}, {} {}, {} {} Z",
            mx - 44., my + 28., mx - 104., my + 52., mx - 112., my + 138., mx - 52., my + 154.,
            mx - 22., my + 161., mx + 22., my + 161., mx + 52., my + 154.,
            mx + 112., my + 138., mx + 104., my + 52., mx + 44., my + 28.
        );
        let mut rim = String::new();
        for k in 0..=12 {
            let an = PI - (k as f64 / 12.) * PI;
            rim += &format!(" L{} {}", f(mx + an.cos() * 70.), f(my + an.sin() * 19. + if k % 2 == 1 { 3. } else { 0. }));
        }
        let frill = format!(
            "M{} {}{} C {} {}, {} {}, {} {} L {} {} C {} {}, {} {}, {} {} Z",
            mx - 70., my, rim, mx + 66., my + 12., mx + 52., my + 22., mx + 44., my + 30., mx - 44., my + 30.,
            mx - 52., my + 22., mx - 66., my + 12., mx - 70., my
        );
        let knot = format!("M{} {} q -14 18 -8 36 M{} {} q 10 18 22 26", mx - 8., my + 36., mx - 2., my + 36.);
        let cord = format!("M{} {} Q {} {} {} {}", mx - 50., my + 30., mx, my + 40., mx + 50., my + 30.);
        let pouch_body = vec![
            path(body, "#C65A3A", INK, 4., 1.),
            path(format!("M{} {} C {} {}, {} {}, {} {} C {} {}, {} {}, {} {} Z", mx + 24., my + 40., mx + 92., my + 62., mx + 94., my + 132., mx + 44., my + 152., mx + 74., my + 118., mx + 66., my + 72., mx + 24., my + 40.), "#A5432D", "none", 0., 0.85),
            path(format!("M{} {} C {} {}, {} {}, {} {}", mx - 62., my + 62., mx - 84., my + 90., mx - 78., my + 122., mx - 56., my + 136.), "none", "#E2845F", 10., 0.85),
            path(
                format!(
                    "M{} {} C {} {}, {} {}, {} {} M{} {} C {} {}, {} {}, {} {} M{} {} C {} {}, {} {}, {} {}",
                    mx - 26., my + 36., mx - 40., my + 70., mx - 38., my + 100., mx - 30., my + 118.,
                    mx + 6., my + 36., mx + 4., my + 62., mx + 8., my + 84., mx + 12., my + 100.,
                    mx + 34., my + 36., mx + 52., my + 60., mx + 58., my + 84., mx + 58., my + 100.
                ),
                "none",
                "#96392A",
                3.,
                0.8,
            ),
            path(frill, "#D46E4B", INK, 3.5, 1.),
            path(
                format!(
                    "M{} {} q 6 8 4 14 M{} {} q 3 6 2 10 M{} {} q 1 6 0 9 M{} {} q -2 6 -2 10 M{} {} q -5 8 -4 14",
                    mx - 50., my + 12., mx - 24., my + 18., mx + 2., my + 20., mx + 28., my + 18., mx + 52., my + 12.
                ),
                "none",
                "#A8472F",
                2.5,
                1.,
            ),
            path(cord.clone(), "none", INK, 11., 1.),
            path(cord, "none", "#E7B04E", 5.5, 1.),
            path(knot.clone(), "none", INK, 7., 1.),
            path(knot, "none", "#E7B04E", 3.5, 1.),
            circ(mx - 5., my + 36., 6., "#E7B04E", INK, 2.5, 1.),
            path(format!("M{} {} l8 4 M{} {} l8 4 M{} {} l8 3", mx - 76., my + 104., mx - 66., my + 122., mx - 52., my + 136.), "none", "#8C3624", 3., 1.),
        ];
        // slab
        let (sx, sy, srx, sry) = (SLAB_X, SLAB_Y, SLAB_RX, SLAB_RY);
        let slab = vec![
            ell(sx + 40., sy + 20., srx + 20., sry, "#4B3B5A", "none", 0., 0.2),
            path(
                format!(
                    "M{} {} C {} {}, {} {}, {} {} C {} {}, {} {}, {} {} C {} {}, {} {}, {} {} Z",
                    sx - srx, sy + 4., sx - srx + 10., sy - sry, sx + srx - 30., sy - sry - 6., sx + srx, sy - 6.,
                    sx + srx + 8., sy + 22., sx + srx - 40., sy + sry, sx, sy + sry - 2.,
                    sx - srx + 40., sy + sry, sx - srx - 6., sy + 30., sx - srx, sy + 4.
                ),
                "#CFC6B6",
                INK,
                3.5,
                1.,
            ),
            path(
                format!(
                    "M{} {} C {} {}, {} {}, {} {} C {} {}, {} {}, {} {} Z",
                    sx - srx + 16., sy + 12., sx - 120., sy + 44., sx + 140., sy + 46., sx + srx - 10., sy + 8.,
                    sx + srx - 30., sy + 50., sx - 150., sy + 60., sx - srx + 16., sy + 12.
                ),
                "#B5AB9A",
                "none",
                0.,
                1.,
            ),
            path(format!("M{} {} C {} {}, {} {}, {} {}", sx - 150., sy - 38., sx - 60., sy - 52., sx + 80., sy - 54., sx + 170., sy - 42.), "none", "#E8E1D4", 5., 1.),
        ];
        let sheep = (0..8).map(sheep_parts).collect();
        let peb = (0..9).map(pebble_shapes).collect();
        // pile order: back (top) pebbles first, front row last (stable sort like JS)
        let mut pile: Vec<(usize, f64)> = (0..9).map(|k| (k, SLOTS[if k == 8 { 0 } else { TAKE[k] }][1])).collect();
        pile.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
        let pile_order = pile.into_iter().map(|p| p.0).collect();
        ZirekVideo { g, sky, clouds, far, mid, stage_a: a, stage_b: b, stage_c: c, cords, pouch_top, pouch_body, slab, sheep, peb, pile_order }
    }

    fn sheep_shape(&self, i: usize, st: &SheepSt, t: f64) -> Sh {
        let p = &self.sheep[i];
        let fs = if st.face_s.abs() < 0.04 {
            let sg = if st.face_s == 0. { 1. } else { st.face_s.signum() };
            0.04 * sg
        } else {
            st.face_s
        };
        let (_, bob) = walk(st, 0);
        let if64 = i as f64;
        let legs: Vec<Sh> = (0..4)
            .map(|k| {
                let (lg, _) = walk(st, k);
                grp(format!("rotate({} {} {})", f(lg), HIPS[k][0], HIPS[k][1]), 1., p.legs[k].clone())
            })
            .collect();
        let nod = st.head * 22. + (t * 2.3 + if64).sin() * 3. * st.v;
        let flick = ((t * 1.3 + if64 * 2.1).sin() - 0.93).max(0.) * 300.;
        let tail = grp(format!("rotate({} -56 -62)", f((t * 9. + if64).sin() * 14. * st.v)), 1., vec![p.tail.clone()]);
        let mut bas = p.bas_a.clone();
        bas.push(grp(format!("rotate({} 44 -68)", f(flick)), 1., p.kulak.clone()));
        bas.extend(p.bas_b.iter().cloned());
        let mut bobk = vec![legs[0].clone(), legs[1].clone(), tail, legs[2].clone(), legs[3].clone()];
        bobk.extend(p.mid.iter().cloned());
        bobk.push(grp(format!("rotate({} 46 -62)", f(nod)), 1., bas));
        grp(
            format!("translate({} {}) scale({:.4} {:.4})", f(st.x), f(st.y), st.s * fs, st.s),
            1.,
            vec![grp(format!("translate(0 {})", f(bob)), 1., bobk)],
        )
    }

    /// The whole camera-space scene (sky .. glint) for time `t`.
    fn world(&self, t: f64) -> Vec<Sh> {
        let g = &self.g;
        let c = cam(g, t);
        // L0 sky + drifting clouds
        let mut l0 = self.sky.clone();
        for (k, cl) in self.clouds.iter().enumerate() {
            let (x0, y, sc) = [(760., 170., 1.0), (1450., 110., 0.8), (1780., 250., 0.6)][k];
            let x = x0 + t * (6. + k as f64 * 3.);
            if let Sh::G { kids, .. } = cl {
                l0.push(grp(format!("translate({} {}) scale({})", f(x), y, sc), 1., kids.clone()));
            }
        }
        // sheep, split behind / in front of the front wall, sorted by feet y
        let mut order: Vec<(usize, SheepSt)> = (0..8).map(|i| (i, sheep_state(g, i, t))).collect();
        order.sort_by(|a, b| a.1.y.partial_cmp(&b.1.y).unwrap());
        let (mut sh_b, mut sheep_b, mut sh_m, mut sheep_m) = (vec![], vec![], vec![], vec![]);
        for (i, st) in &order {
            let behind = st.y < front_y(st.x) - 2. && st.x > g.postl.x - 40.;
            let shadow = ell(st.x + 34. * st.s, st.y + 1., 86. * st.s, 10. * st.s, "#4B3B5A", "none", 0., 0.2);
            let body = self.sheep_shape(*i, st, t);
            if behind {
                sh_b.push(shadow);
                sheep_b.push(body);
            } else {
                sh_m.push(shadow);
                sheep_m.push(body);
            }
        }
        // pouch
        let sw = Geo::swing(t);
        let sl = Geo::slack(t);
        let m = g.mouth;
        let mut pile = Vec::new();
        let mut flying = Vec::new();
        let mut shadows = Vec::new();
        let mut puffs = Vec::new();
        let states: Vec<PebSt> = (0..9).map(|k| pebble(g, k, t)).collect();
        for &k in &self.pile_order {
            let q = &states[k];
            let slot = SLOTS[q.slot];
            if q.in_pouch {
                pile.push(grp(format!("translate({} {}) rotate({})", m.x + slot[0], m.y + slot[1], f(q.rot)), 1., self.peb[k].clone()));
            }
        }
        for k in 0..8 {
            let q = &states[k];
            if !q.in_pouch {
                flying.push(grp(format!("translate({} {}) scale({:.3} {:.3}) rotate({})", f(q.x), f(q.y), q.sq, 1. / q.sq, f(q.rot)), 1., self.peb[k].clone()));
            }
            if q.landed {
                shadows.push(ell(q.x + 8., q.y + 13., 24., 7., "#4B3B5A", "none", 0., 0.26));
                if q.age < 0.5 {
                    for j in 0..4 {
                        let a = q.age / 0.5;
                        let dir = if j < 2 { -1. } else { 1. };
                        let off = (j % 2) as f64 * 10.;
                        puffs.push(circ(q.x + dir * (22. + a * 26. + off), q.y + 10. - a * 12. - off * 0.5, 4. + a * 5. - off * 0.2, "#F6EBD5", INK, 2., (1. - a) * 0.9));
                    }
                }
            }
        }
        let mut ic = self.pouch_top.clone();
        ic.extend(pile);
        let sc = 1. - 0.07 * sl;
        ic.push(grp(
            format!("translate({} {}) scale({sc:.4} {sc:.4}) translate({} {})", m.x, m.y + 30., -m.x, -m.y - 30.),
            1.,
            self.pouch_body.clone(),
        ));
        let mut kese = self.cords.clone();
        kese.push(grp(format!("translate(0 {})", f(6. * sl)), 1., ic));

        let mut l3 = self.stage_a.clone();
        l3.extend(sh_b);
        l3.extend(sheep_b);
        l3.extend(self.stage_b.iter().cloned());
        l3.extend(sh_m);
        l3.extend(sheep_m);
        l3.extend(self.stage_c.iter().cloned());
        l3.push(grp(format!("rotate({:.3} {} {})", sw, g.peg.x, g.peg.y), 1., kese));
        l3.extend(self.slab.iter().cloned());
        l3.extend(shadows);
        l3.extend(puffs);
        l3.extend(flying);
        let gi = glint(t);
        if gi > 0. {
            let mm = g.mouth_at(t);
            let k = 0.8 + 0.2 * gi;
            l3.push(grp(
                format!("translate({} {}) scale({:.3})", f(mm.x + SLOTS[0][0] - 7.), f(mm.y + SLOTS[0][1] - 6.), 0.5 + 0.2 * gi),
                gi,
                vec![
                    circ(0., 0., 58., "url(#parlakHale)", "none", 0., 0.8),
                    grp(
                        format!("rotate({}) scale({k:.3} {k:.3})", f((t - GLINT) * 6.)),
                        1.,
                        vec![path("M0 -34 Q 2.6 -2.6 24 0 Q 2.6 2.6 0 34 Q -2.6 2.6 -24 0 Q -2.6 -2.6 0 -34 Z".into(), "#FFF3D6", "none", 0., 1.)],
                    ),
                    circ(0., 0., 3.5, "#FFFFFF", "none", 0., 1.),
                ],
            ));
        }
        vec![
            grp(cam_matrix(&c, 0.08), 1., l0),
            grp(cam_matrix(&c, 0.3), 1., self.far.clone()),
            grp(cam_matrix(&c, 0.6), 1., self.mid.clone()),
            grp(cam_matrix(&c, 1.0), 1., l3),
        ]
    }
}

impl Video for ZirekVideo {
    const FPS: usize = 30;
    const WIDTH: usize = WIDTH;
    const HEIGHT: usize = HEIGHT;
    const BACKGROUND_COLOR: Color = Color::WHITE;

    fn duration(&self) -> Duration<'_> {
        Duration::Seconds(10.0)
    }

    fn audio(&self) -> AudioMap<'_> {
        AudioMap::none()
    }

    fn render_frame<'a>(&'a self, frame: Frame, ctx: &FFramesContext<'a, '_>) -> Svgr<'a> {
        let t = frame.index as f64 / 30.0;
        let world: Vec<Svgr<'static>> = self.world(t).into_iter().map(draw).collect();
        // paper grain: the same pre-baked 640 px tile as duz2d, repeated with an SVG pattern
        let grain = match ctx.get_image("kagit-tane.png") {
            Some(img) => fframes::svgr!(
                <g>
                    <defs>
                        <pattern id="tane" patternUnits="userSpaceOnUse" x="0" y="0" width="640" height="640">
                            <image href={img.href()} x="0" y="0" width="640" height="640" />
                        </pattern>
                    </defs>
                    <rect x="0" y="0" width="1920" height="1080" fill="url(#tane)" opacity="0.36" />
                </g>
            ),
            None => Svgr::empty(),
        };
        fframes::svgr!(
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width={WIDTH} height={HEIGHT}>
                <defs>
                    <linearGradient id="gok" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0" stop-color="#E9B79A" />
                        <stop offset="0.45" stop-color="#F4CFA3" />
                        <stop offset="1" stop-color="#FBE6BF" />
                    </linearGradient>
                    <radialGradient id="gunesHale">
                        <stop offset="0" stop-color="#FFF4D2" stop-opacity="0.9" />
                        <stop offset="0.35" stop-color="#FFE3A8" stop-opacity="0.45" />
                        <stop offset="1" stop-color="#FFE3A8" stop-opacity="0" />
                    </radialGradient>
                    <radialGradient id="parlakHale">
                        <stop offset="0" stop-color="#FFF1C8" stop-opacity="0.95" />
                        <stop offset="0.4" stop-color="#FFD58A" stop-opacity="0.45" />
                        <stop offset="1" stop-color="#FFC870" stop-opacity="0" />
                    </radialGradient>
                    // CSS linear-gradient(100deg, ...) of #isik, as an SVG gradient line
                    <linearGradient id="isik" gradientUnits="userSpaceOnUse" x1="-63.4" y1="359.6" x2="1983.4" y2="720.4">
                        <stop offset="0" stop-color="#FFC478" stop-opacity="0.16" />
                        <stop offset="0.45" stop-color="#FFC478" stop-opacity="0" />
                    </linearGradient>
                    // CSS radial-gradient(ellipse 78% 72% at 48% 46%, ...) of #vinyet
                    <radialGradient id="vinyet" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1" gradientTransform="matrix(1497.6 0 0 777.6 921.6 496.8)">
                        <stop offset="0" stop-color="#462628" stop-opacity="0" />
                        <stop offset="0.58" stop-color="#462628" stop-opacity="0" />
                        <stop offset="1" stop-color="#462628" stop-opacity="0.30" />
                    </radialGradient>
                </defs>
                <rect x="0" y="0" width="1920" height="1080" fill="#F3E6CF" />
                <rect x="-100" y="-100" width="2120" height="1280" fill="url(#gok)" />
                {world}
                <rect x="0" y="0" width="1920" height="1080" fill="url(#isik)" />
                <rect x="0" y="0" width="1920" height="1080" fill="url(#vinyet)" />
                {grain}
            </svg>
        )
    }
}
