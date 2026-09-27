# Math with Zirek · sahne G, LOWPOLY sürüm (akşam, koyunlar girer, taş çıkar, tek taş kalır)
# Blender 5.2, Cycles. Tamamen yordamsal: düz gölgelenmiş (flat shading) az çokgenli 3B, yumuşak pastel renkler,
# hafif renk geçişleri, sakin ortam ışığı. Dış varlık yok.
# Hikâye, zamanlama ve kamera vuruşları kil / kâğıt / gerçekçi sürümlerle aynı (8 koyun, 0,73 sn, son 3 sn yaklaşma).
# Kullanım:
#   blender -b -P sahne.py -- --mod kare --kareler 68,180,290 --w 960 --h 540 --ornek 32 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 60 --cikti out            (1920x1080)
#   blender -b -P sahne.py -- --mod yok                                            (yalnız kurar, KADRAJ yazar)
import bpy, bmesh, math, random, sys, os, time, argparse
from mathutils import Vector, Matrix, Quaternion, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--mod', default='kare')
ap.add_argument('--kareler', default='68,180,290')
ap.add_argument('--bas', type=int, default=1)
ap.add_argument('--son', type=int, default=300)
ap.add_argument('--w', type=int, default=1920)
ap.add_argument('--h', type=int, default=1080)
ap.add_argument('--ornek', type=int, default=64)
ap.add_argument('--cikti', default='out')
ap.add_argument('--cihaz', default='auto')
ap.add_argument('--bulanik', type=int, default=1)
ap.add_argument('--blend', action='store_true')
A = ap.parse_args(argv)
T_START = time.time()

FPS = 30
N_FRAMES = 300
N_SHEEP = 8
T_GATE0 = 40          # ilk koyunun kapıdan geçtiği kare
T_GAP = 22            # koyunlar arası (0,73 sn)
SPEED = 2.1 / FPS     # m/kare

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = N_FRAMES


def rng(seed):
    return random.Random(seed)


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def smoother(t):
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def link(ob):
    scene.collection.objects.link(ob)
    return ob


def bm_obj(name, bm, mats):
    """bmesh -> düz gölgeli nesne. mats: malzeme listesi (face.material_index ile)."""
    for f in bm.faces:
        f.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    return link(bpy.data.objects.new(name, me))


def gem(bm, center, radii, subdiv=1, amp=0.12, seed=0, rot=None, mi=0, nscale=1.7):
    """Az çokgenli yuvarlak taş/yün topağı: ikosfer + gürültüyle köşe oynatma."""
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=subdiv, radius=1.0)
    o = Vector((seed * 3.1, seed * 1.7, seed * 0.9))
    for v in tmp.verts:
        n = v.co.normalized()
        d = 1.0 + amp * noise.noise(n * nscale + o)
        v.co = Vector((n.x * radii[0], n.y * radii[1], n.z * radii[2])) * d
    M = Matrix.Translation(center)
    if rot is not None:
        M = M @ rot.to_matrix().to_4x4()
    tmp.transform(M)
    for f in tmp.faces:
        f.material_index = mi
    me = bpy.data.meshes.new('_t')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def prism(bm, p0, p1, r0, r1, seg=6, mi=0, rot=0.0):
    """p0'dan p1'e altıgen (seg köşeli) kesik koni."""
    d = (p1 - p0)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=d.length,
                          matrix=Matrix.Translation(p0 + d / 2) @ q.to_matrix().to_4x4() @ Matrix.Rotation(rot, 4, 'Z'))
    for f in tmp.faces:
        f.material_index = mi
    me = bpy.data.meshes.new('_t')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


# ---------------------------------------------------------------- malzemeler: düz renk + hafif geçiş
def mat(name, color, color2=None, axis='Z', lo=0.0, hi=1.0, rough=0.9, coord='Object', facet=0.05, sheen=0.0):
    """Mat pastel yüzey. color2 verilirse nesne ekseni boyunca yumuşak geçiş (lo..hi). facet: yüz başına küçük ton farkı."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = 0.15
    if sheen:
        b.inputs['Sheen Weight'].default_value = sheen
    base = N.new('ShaderNodeRGB')
    base.outputs[0].default_value = (*color, 1)
    col = base.outputs[0]
    if color2 is not None:
        tc = N.new('ShaderNodeTexCoord')
        sp = N.new('ShaderNodeSeparateXYZ')
        L.new(tc.outputs[coord], sp.inputs[0])
        mr = N.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = lo
        mr.inputs['From Max'].default_value = hi
        L.new(sp.outputs[axis], mr.inputs['Value'])
        c2 = N.new('ShaderNodeRGB')
        c2.outputs[0].default_value = (*color2, 1)
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L.new(mr.outputs[0], mx.inputs['Factor'])
        L.new(base.outputs[0], mx.inputs['A']); L.new(c2.outputs[0], mx.inputs['B'])
        col = mx.outputs['Result']
    if facet > 0:
        # yüz başına ton: yüzeyin gerçek normaline göre küçük gürültü (düz yüzler ayrı ayrı okunur)
        gm = N.new('ShaderNodeNewGeometry')
        oi = N.new('ShaderNodeObjectInfo')
        ad = N.new('ShaderNodeVectorMath'); ad.operation = 'ADD'
        L.new(gm.outputs['True Normal'], ad.inputs[0])
        L.new(oi.outputs['Location'], ad.inputs[1])
        wn = N.new('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '3D'
        sc = N.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'; sc.inputs['Scale'].default_value = 3.0
        L.new(ad.outputs[0], sc.inputs[0]); L.new(sc.outputs[0], wn.inputs['Vector'])
        mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY_ADD'
        mm.inputs[1].default_value = facet * 2; mm.inputs[2].default_value = 1.0 - facet
        L.new(wn.outputs['Value'], mm.inputs[0])
        hs = N.new('ShaderNodeHueSaturation')
        L.new(col, hs.inputs['Color']); L.new(mm.outputs[0], hs.inputs['Value'])
        col = hs.outputs['Color']
    L.new(col, b.inputs['Base Color'])
    return m


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N = m.node_tree.nodes
    for n in list(N):
        if n.type == 'BSDF_PRINCIPLED':
            N.remove(n)
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1.0)
    em.inputs['Strength'].default_value = strength
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    m.node_tree.links.new(em.outputs[0], out.inputs['Surface'])
    return m


# pastel, sıcak akşam paleti (kanal: sıcak ışık, krem; soğuk/karanlık renk alınmaz)
M_GROUND = mat('zemin', (0.50, 0.66, 0.42), (0.66, 0.70, 0.46), axis='Y', lo=-4.0, hi=22.0, coord='Object', facet=0.035)
M_GRASS = mat('ot', (0.36, 0.56, 0.34), facet=0.06)
M_GRASS2 = mat('ot2', (0.55, 0.70, 0.38), facet=0.06)
M_FLOWER = mat('cicek', (0.98, 0.86, 0.72), facet=0.0)
M_FLOWER2 = mat('cicek2', (0.96, 0.66, 0.62), facet=0.0)
M_WALL = [mat('duvar1', (0.80, 0.74, 0.72), facet=0.06), mat('duvar2', (0.72, 0.68, 0.72), facet=0.06),
          mat('duvar3', (0.86, 0.79, 0.72), facet=0.06)]
M_CAP = mat('kapak', (0.90, 0.84, 0.78), facet=0.05)
M_WOOL = mat('yun', (0.97, 0.92, 0.83), facet=0.045, sheen=0.3)
M_WOOL2 = mat('yun2', (0.93, 0.86, 0.76), facet=0.045, sheen=0.3)
M_FACE = mat('yuz', (0.36, 0.28, 0.30), facet=0.05)
M_EYE = mat('goz', (0.08, 0.06, 0.07), rough=0.5, facet=0.0)
M_POUCH = mat('kese', (0.33, 0.58, 0.64), (0.45, 0.68, 0.72), axis='Z', lo=-0.4, hi=0.05, facet=0.05)
M_POUCH_IN = mat('kese_ic', (0.16, 0.30, 0.34), facet=0.0)
M_CORD = mat('ip', (0.98, 0.90, 0.74), facet=0.03)
M_WOOD = mat('civi', (0.62, 0.42, 0.34), facet=0.05)
M_PEBBLE = mat('cakil', (0.95, 0.46, 0.28), facet=0.07)
M_SLAB = mat('yassi_tas', (0.93, 0.89, 0.80), facet=0.04)
M_TREE = mat('agac', (0.44, 0.64, 0.46), facet=0.07)
M_TREE2 = mat('agac2', (0.62, 0.74, 0.50), facet=0.07)
M_TRUNK = mat('govde', (0.62, 0.46, 0.40), facet=0.04)
M_HILL = [mat('tepe_uzak', (0.93, 0.76, 0.72), facet=0.03), mat('tepe_orta', (0.84, 0.74, 0.70), facet=0.03),
          mat('tepe_yakin', (0.66, 0.72, 0.56), facet=0.04)]
M_ROCK = mat('kaya', (0.80, 0.72, 0.74), facet=0.07)

# ---------------------------------------------------------------- yerleşim (öteki sürümlerle aynı)
PEN_C = Vector((0.0, 6.0))
PEN_R = 4.0
GATE_ANG = math.radians(228)
GAP_HALF = 0.25
WALL_H = 0.78
POST_R = 0.34
POST_H = 1.30


def hfun(x, y):
    """Tepe: ağılın olduğu yer düz, arkaya ve yanlara yumuşak yükselir."""
    p = Vector((x, y))
    d = (p - PEN_C).length
    h = 0.0
    h += 0.9 * smooth(PEN_R + 2.0, PEN_R + 12.0, d) * (0.6 + 0.4 * math.sin(x * 0.21 + 1.0))
    h += 0.12 * noise.noise(Vector((x * 0.15, y * 0.15, 0.3)))
    return h


def ang_dist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def ring_pos(a, r=PEN_R):
    return Vector((PEN_C.x + r * math.cos(a), PEN_C.y + r * math.sin(a)))


gu = Vector((math.cos(GATE_ANG), math.sin(GATE_ANG)))
GATE_PT = PEN_C + gu * PEN_R
CAM_AZ = GATE_ANG + math.radians(40)
CAM_DIST = 7.2
_cxy = GATE_PT + Vector((math.cos(CAM_AZ), math.sin(CAM_AZ))) * CAM_DIST
CAM_POS0 = Vector((_cxy.x, _cxy.y, hfun(_cxy.x, _cxy.y) + 3.4))
_FC = (CAM_POS0.xy - GATE_PT).normalized()          # kapıdan kameraya
_RT = Vector((-_FC.y, _FC.x))                        # ekranda sağ (kamera kapıya bakarken)
_f = -_FC
RIGHT = Vector((_f.y, -_f.x)).normalized()
RIGHT3 = RIGHT.to_3d()
FACE3 = _FC.to_3d()


# ---------------------------------------------------------------- zemin: üçgenlerden yumuşak tepe
def build_ground():
    bm = bmesh.new()
    X0, X1, Y0, Y1, n = -34.0, 34.0, -16.0, 40.0, 96
    nx, ny = n, int(n * (Y1 - Y0) / (X1 - X0))
    r = rng(3)
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = X0 + (X1 - X0) * i / nx
            y = Y0 + (Y1 - Y0) * j / ny
            if 0 < i < nx and 0 < j < ny:
                x += r.uniform(-0.22, 0.22) * (X1 - X0) / nx
                y += r.uniform(-0.22, 0.22) * (Y1 - Y0) / ny
            row.append(bm.verts.new((x, y, hfun(x, y))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            a, b, c, d = grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]
            if (i + j) % 2:
                bm.faces.new((a, b, c)); bm.faces.new((a, c, d))
            else:
                bm.faces.new((a, b, d)); bm.faces.new((b, c, d))
    return bm_obj('zemin', bm, [M_GROUND])


def build_backdrop():
    """Uzak, katman katman pastel tepeler + birkaç az çokgenli ağaç."""
    fwd = (-_FC).to_3d()
    for k, (dist, h, width, m, seg) in enumerate(((46.0, 7.0, 120.0, M_HILL[0], 22), (34.0, 4.6, 100.0, M_HILL[1], 20),
                                                  (25.0, 2.6, 80.0, M_HILL[2], 18))):
        bm = bmesh.new()
        rr = rng(80 + k)
        top, bot = [], []
        ph = rr.uniform(0, 6)
        for s in range(seg + 1):
            u = -width / 2 + width * s / seg
            z = h * (0.55 + 0.3 * math.sin(u * 0.09 + ph) + 0.15 * math.sin(u * 0.23 + 2 * ph)) + rr.uniform(-0.3, 0.3)
            c = GATE_PT.to_3d() + fwd * dist + RIGHT3 * u
            top.append(bm.verts.new((c.x, c.y, z)))
            c2 = c - fwd * 6.0
            bot.append(bm.verts.new((c2.x, c2.y, -1.5)))
        for s in range(seg):
            bm.faces.new((bot[s], bot[s + 1], top[s + 1], top[s]))
        bm_obj('tepe_%d' % k, bm, [m])
    # ağaçlar: ağılın arkasında ve solunda (sağ alt boş kalır)
    r = rng(91)
    spots = [(-7.5, 13.0, 1.25), (-5.2, 15.5, 1.0), (6.8, 14.8, 1.1), (9.6, 12.0, 0.9), (-10.5, 9.0, 1.15), (3.2, 16.8, 0.85)]
    for k, (x, y, s) in enumerate(spots):
        z = hfun(x, y)
        bm = bmesh.new()
        prism(bm, Vector((x, y, z - 0.1)), Vector((x, y, z + 0.9 * s)), 0.09 * s, 0.06 * s, seg=5, mi=0)
        bm_obj('agac_govde_%d' % k, bm, [M_TRUNK])
        bm = bmesh.new()
        if k % 2 == 0:
            gem(bm, Vector((x, y, z + 1.45 * s)), (0.72 * s, 0.72 * s, 0.85 * s), subdiv=1, amp=0.1, seed=90 + k)
        else:
            for t in range(3):
                prism(bm, Vector((x, y, z + (0.7 + 0.45 * t) * s)), Vector((x, y, z + (1.45 + 0.42 * t) * s)),
                      (0.62 - 0.16 * t) * s, 0.02, seg=7, rot=r.uniform(0, 1))
        bm_obj('agac_tac_%d' % k, bm, [M_TREE if k % 3 else M_TREE2])


# ---------------------------------------------------------------- ağıl: iri, köşeli pastel taşlardan duvar
def build_pen():
    bms = [bmesh.new() for _ in M_WALL]
    cap = bmesh.new()
    r = rng(11)
    a0 = GATE_ANG + GAP_HALF
    a1 = GATE_ANG - GAP_HALF + 2 * math.pi
    courses = 3
    for c in range(courses):
        z0 = c * WALL_H / courses
        hh = WALL_H / courses
        s = r.uniform(0, 0.25)
        arc = (a1 - a0) * PEN_R
        while s < arc - 0.15:
            w = r.uniform(0.42, 0.62)
            a = a0 + (s + w / 2) / PEN_R
            p = ring_pos(a)
            k = r.randrange(len(M_WALL))
            rot = Quaternion((0, 0, 1), a + math.pi / 2) @ Quaternion((1, 0, 0), r.uniform(-0.1, 0.1))
            gem(bms[k], Vector((p.x, p.y, hfun(p.x, p.y) + z0 + hh * 0.55)), (w * 0.55, 0.26, hh * 0.62),
                subdiv=1, amp=0.14, seed=r.randrange(10000), rot=rot)
            s += w + r.uniform(-0.02, 0.03)
    # üst sıra: yassı kapak taşları
    s = 0.1
    arc = (a1 - a0) * PEN_R
    while s < arc - 0.15:
        w = r.uniform(0.5, 0.7)
        a = a0 + (s + w / 2) / PEN_R
        p = ring_pos(a)
        rot = Quaternion((0, 0, 1), a + math.pi / 2 + r.uniform(-0.1, 0.1))
        gem(cap, Vector((p.x, p.y, hfun(p.x, p.y) + WALL_H + 0.05)), (w * 0.55, 0.3, 0.1),
            subdiv=1, amp=0.1, seed=r.randrange(10000), rot=rot)
        s += w - 0.02
    for k, bm in enumerate(bms):
        bm_obj('duvar_%d' % k, bm, [M_WALL[k]])
    bm_obj('duvar_kapak', cap, [M_CAP])
    posts = []
    for side, sgn in (('on', 1), ('arka', -1)):
        a = GATE_ANG + sgn * GAP_HALF
        p = ring_pos(a)
        z = hfun(p.x, p.y)
        bm = bmesh.new()
        n = 4
        for k in range(n):
            h0 = z + POST_H * k / n
            h1 = z + POST_H * (k + 1) / n
            rr = POST_R * (1.0 - 0.05 * k)
            tmp_rot = r.uniform(0, 1)
            prism(bm, Vector((p.x, p.y, h0 - 0.01)), Vector((p.x, p.y, h1 - 0.015)), rr, rr * 0.96, seg=6, rot=tmp_rot)
        prism(bm, Vector((p.x, p.y, z + POST_H - 0.02)), Vector((p.x, p.y, z + POST_H + 0.1)), POST_R * 1.2, POST_R * 1.05, seg=6,
              rot=0.3)
        bm_obj('direk_' + side, bm, [M_WALL[2] if sgn > 0 else M_WALL[0]])
        posts.append((side, a, p))
    return posts


# ---------------------------------------------------------------- ot tutamları ve küçük çiçekler
def grass_tufts(avoid):
    r = rng(123)
    bm1, bm2, bmf = bmesh.new(), bmesh.new(), bmesh.new()
    k = 0
    tries = 0
    while k < 260 and tries < 20000:
        tries += 1
        x = r.uniform(-12, 10); y = r.uniform(-4.0, 14.0)
        p = Vector((x, y))
        if any(f(p) for f in avoid):
            continue
        dpen = (p - PEN_C).length
        near_wall = abs(dpen - PEN_R) < 0.9
        if not near_wall and r.random() < 0.7:
            continue
        z = hfun(x, y)
        s = r.uniform(0.7, 1.2)
        bm = bm1 if r.random() < 0.6 else bm2
        for b in range(3):
            ang = r.uniform(0, 6.28)
            lean = Vector((math.cos(ang), math.sin(ang), 0)) * 0.05 * s
            prism(bm, Vector((x, y, z - 0.02)), Vector((x, y, z + r.uniform(0.14, 0.24) * s)) + lean, 0.035 * s, 0.002, seg=3,
                  rot=ang)
        if r.random() < 0.18:
            gem(bmf, Vector((x + 0.05, y, z + 0.2 * s)), (0.035, 0.035, 0.03), subdiv=1, amp=0.0, seed=k)
        k += 1
    bm_obj('ot1', bm1, [M_GRASS]); bm_obj('ot2', bm2, [M_GRASS2]); bm_obj('cicek', bmf, [M_FLOWER])
    # birkaç küçük kaya (sol arka, sahneyi dengeler)
    bm = bmesh.new()
    for k, (x, y, s) in enumerate(((-4.6, 9.8, 0.5), (-4.1, 10.4, 0.32), (5.3, 11.6, 0.42), (-8.2, 5.0, 0.55))):
        gem(bm, Vector((x, y, hfun(x, y) + 0.12 * s / 0.5)), (s, s * 0.8, s * 0.55), subdiv=1, amp=0.2, seed=300 + k)
    bm_obj('kayalar', bm, [M_ROCK])


# ---------------------------------------------------------------- koyun: yün topakları (ikosfer), altıgen bacaklar
def build_sheep(i):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('koyun_%d' % i, None))
    s = r.uniform(0.95, 1.05)
    bob = link(bpy.data.objects.new('koyun_%d_govde' % i, None))
    bob.parent = root
    bob.scale = (s, s, s)
    bm = bmesh.new()
    # gövde: ortada büyük topak + üstte ve yanlarda küçük topaklar (bulut gibi, ama köşeli)
    gem(bm, Vector((0, 0, 0.62)), (0.46, 0.30, 0.27), subdiv=2, amp=0.06, seed=i * 7, nscale=2.2)
    for k in range(9):
        a = 2 * math.pi * k / 9 + r.uniform(-0.2, 0.2)
        cx = 0.30 * math.cos(a) * 1.05
        cz = 0.62 + 0.17 * math.sin(a) + 0.05
        cy = r.choice((-1, 1)) * r.uniform(0.08, 0.14)
        rr = r.uniform(0.15, 0.19)
        gem(bm, Vector((cx, cy, cz)), (rr, rr, rr * 0.92), subdiv=1, amp=0.08, seed=i * 31 + k,
            mi=0 if k % 3 else 1)
    for k in range(4):
        gem(bm, Vector((r.uniform(-0.25, 0.2), r.choice((-1, 1)) * 0.2, 0.56 + r.uniform(-0.05, 0.08))),
            (0.15, 0.12, 0.14), subdiv=1, amp=0.08, seed=i * 53 + k, mi=1)
    gem(bm, Vector((-0.47, 0, 0.72)), (0.08, 0.07, 0.07), subdiv=1, amp=0.1, seed=i * 3 + 1)     # kuyruk
    body = bm_obj('koyun_%d_yun' % i, bm, [M_WOOL, M_WOOL2])
    body.parent = bob
    # baş: pivot boynun dibinde
    head = link(bpy.data.objects.new('koyun_%d_bas' % i, None))
    head.parent = bob
    head.location = (0.40, 0, 0.74)
    bm = bmesh.new()
    prism(bm, Vector((0.02, 0, 0.02)), Vector((0.27, 0, -0.07)), 0.105, 0.065, seg=6, mi=0, rot=0.52)
    gem(bm, Vector((0.28, 0, -0.075)), (0.05, 0.062, 0.055), subdiv=1, amp=0.0, seed=1, mi=0)     # burun ucu
    for sy in (-1, 1):
        # kulaklar: yassı, yana açılan
        prism(bm, Vector((0.05, sy * 0.07, 0.07)), Vector((0.02, sy * 0.21, 0.05)), 0.035, 0.012, seg=4, mi=0, rot=0.78)
        gem(bm, Vector((0.14, sy * 0.068, 0.035)), (0.019, 0.012, 0.022), subdiv=1, amp=0.0, seed=2, mi=1)   # göz
    gem(bm, Vector((0.04, 0, 0.1)), (0.1, 0.09, 0.07), subdiv=1, amp=0.1, seed=i + 77, mi=2)            # alında yün
    hd = bm_obj('koyun_%d_yuz' % i, bm, [M_FACE, M_EYE, M_WOOL])
    hd.parent = head
    legs = []
    for k, (lx, ly) in enumerate(((0.24, 0.13), (0.24, -0.13), (-0.24, 0.13), (-0.24, -0.13))):
        leg = link(bpy.data.objects.new('koyun_%d_bacak_%d' % (i, k), None))
        leg.parent = bob
        leg.location = (lx, ly, 0.46)
        bm = bmesh.new()
        prism(bm, Vector((0, 0, 0.02)), Vector((0, 0, -0.43)), 0.045, 0.036, seg=6, mi=0)
        prism(bm, Vector((0.005, 0, -0.40)), Vector((0.01, 0, -0.465)), 0.045, 0.048, seg=6, mi=0)
        g = bm_obj('koyun_%d_bacak_%d_m' % (i, k), bm, [M_FACE])
        g.parent = leg
        legs.append(leg)
    return root, bob, head, legs


# ---------------------------------------------------------------- yol
def catmull(pts, per=24):
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for k in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[k - 1], P[k], P[k + 1], P[k + 2]
        for s in range(per):
            t = s / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


class Path:
    def __init__(self, pts):
        self.p = catmull([Vector(q) for q in pts], 40)
        self.s = [0.0]
        for k in range(1, len(self.p)):
            self.s.append(self.s[-1] + (self.p[k] - self.p[k - 1]).length)
        self.total = self.s[-1]

    def at(self, s):
        s = max(0.0, min(self.total, s))
        lo, hi = 0, len(self.s) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.s[mid] <= s:
                lo = mid
            else:
                hi = mid
        seg = self.s[hi] - self.s[lo]
        t = 0 if seg == 0 else (s - self.s[lo]) / seg
        return self.p[lo].lerp(self.p[hi], t), self.p[hi] - self.p[lo]

    def closest_s(self, q):
        best, bs = 1e9, 0
        for k, p in enumerate(self.p):
            d = (p - q).length
            if d < best:
                best, bs = d, self.s[k]
        return bs


INSIDE = GATE_PT - gu * 1.3
OUT1 = GATE_PT - _RT * 0.9 + _FC * 1.5
SPOTS = []
_rs = rng(77)
while len(SPOTS) < N_SHEEP:
    a = _rs.uniform(0, 2 * math.pi)
    rr = _rs.uniform(0.6, PEN_R - 1.0)
    q = PEN_C + Vector((rr * math.cos(a), rr * math.sin(a)))
    if (q - INSIDE).length < 1.0:
        continue
    if all((q - o).length > 1.3 for o in SPOTS):
        SPOTS.append(q)
SPOTS.sort(key=lambda q: -(q - INSIDE).length)
# sürü sol önden gelir: ilk karede ilk koyun kadrajın solunda görünür
START = [GATE_PT - _RT * 12.0 + _FC * 3.2, GATE_PT - _RT * 3.6 + _FC * 2.6]
paths = []
for i in range(N_SHEEP):
    jit = _FC * (0.16 * ((i * 7) % 3 - 1))
    paths.append(Path([START[0] + jit, START[1] + jit * 0.7, OUT1, GATE_PT, INSIDE, SPOTS[i]]))

# ---------------------------------------------------------------- sahneyi kur
build_ground()
build_backdrop()
posts = build_pen()
front_post = [p for p in posts if p[0] == 'on'][0]
_, FA, FP = front_post
TO_CAM0 = (CAM_POS0.xy - FP).normalized()
PEB_R = 0.075                       # çakıl yarı boyu (14-15 cm): geniş planda telefonda okunur
ROW_GAP = 0.19
ROW_START = FP + TO_CAM0 * (POST_R + 0.75) - RIGHT * 0.05
ROW_DIR = RIGHT
ROW_CENTER = ROW_START + ROW_DIR * (ROW_GAP * 3.5)


def near_path(p):
    return min((q - p).length for q in paths[0].p[::3]) < 0.7


grass_tufts([lambda p: abs((p - PEN_C).length - PEN_R) < 0.35,
             lambda p: (p - ROW_CENTER).length < 1.2,
             near_path,
             lambda p: (p - FP).length < POST_R + 0.3,
             lambda p: (p - ring_pos(GATE_ANG - GAP_HALF)).length < POST_R + 0.3,
             lambda p: (p - PEN_C).length < PEN_R - 0.4 and (p - PEN_C).length > 0.0])

# yassı taş: açık krem, çakıllar üstünde mercan rengi (yüksek karşıtlık)
slab_c = ROW_CENTER
bm = bmesh.new()
gem(bm, Vector((0, 0, 0)), (ROW_GAP * 4 + 0.22, 0.3, 0.06), subdiv=2, amp=0.05, seed=55, nscale=1.3)
SLAB = bm_obj('yassi_tas', bm, [M_SLAB])
SLAB.location = (slab_c.x, slab_c.y, hfun(slab_c.x, slab_c.y) + 0.0)
SLAB.rotation_euler = (0, 0, math.atan2(ROW_DIR.y, ROW_DIR.x))
SLAB_TOP = hfun(slab_c.x, slab_c.y) + 0.058
print('t sahne %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- çivi, kese
PEG_Z = 1.02
_out = Vector((math.cos(FA), math.sin(FA)))
pegdir2 = (TO_CAM0 * 0.8 + _out * 0.2).normalized()
pegdir = Vector((pegdir2.x, pegdir2.y, 0.18)).normalized()
z_post = hfun(FP.x, FP.y)
peg_base = Vector((FP.x, FP.y, z_post + PEG_Z)) + pegdir2.to_3d() * (POST_R - 0.1)
PEG_LEN = 0.30
bm = bmesh.new()
prism(bm, peg_base, peg_base + pegdir * PEG_LEN, 0.03, 0.026, seg=6)
gem(bm, peg_base + pegdir * PEG_LEN, (0.028, 0.028, 0.028), subdiv=1, amp=0.0, seed=4)
bm_obj('civi', bm, [M_WOOD])
HANG = peg_base + pegdir * (PEG_LEN - 0.07) + Vector((0, 0, 0.02))

POUCH_S = 1.0
DROP = 0.50          # çividen kesenin dibine
PROF = [(0.0, 0.0), (0.12, 0.012), (0.19, 0.06), (0.215, 0.13), (0.205, 0.2), (0.17, 0.26), (0.12, 0.30),
        (0.105, 0.325), (0.125, 0.35), (0.16, 0.38), (0.175, 0.40)]
LIP_Z = 0.40 - DROP
NECK_Z = 0.318 - DROP


def build_pouch():
    seg = 12
    bm = bmesh.new()
    bottom = bm.verts.new((0, 0, -DROP))
    rings = []
    rr = rng(71)
    for k, (r_, z) in enumerate(PROF[1:]):
        ring = []
        for s in range(seg):
            th = 2 * math.pi * s / seg + (0.5 * math.pi / seg if k % 2 else 0)
            dz = 0.0
            if k == len(PROF) - 2:
                dz = 0.03 * (1 if s % 2 else -0.3)           # ağız: köşeli fırfır
            ring.append(bm.verts.new((r_ * math.cos(th) * (1 + rr.uniform(-0.04, 0.04)),
                                      r_ * math.sin(th) * 0.92 * (1 + rr.uniform(-0.04, 0.04)), z - DROP + dz)))
        rings.append(ring)
    for s in range(seg):
        bm.faces.new((bottom, rings[0][s], rings[0][(s + 1) % seg]))
    for k in range(len(rings) - 1):
        for s in range(seg):
            bm.faces.new((rings[k][s], rings[k + 1][s], rings[k + 1][(s + 1) % seg], rings[k][(s + 1) % seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = bm_obj('kese', bm, [M_POUCH])
    sol = ob.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.018; sol.material_offset = 1; sol.use_flip_normals = False
    ob.data.materials.append(M_POUCH_IN)
    # iç karanlık disk: ağızdan bakınca taşlar koyu zeminde okunur
    bm = bmesh.new()
    gem(bm, Vector((0, 0, NECK_Z + 0.01)), (0.1, 0.09, 0.012), subdiv=1, amp=0.0, seed=3)
    inn = bm_obj('kese_ic', bm, [M_POUCH_IN])
    inn.parent = ob
    # büzgü ipi: boğazda halka + fiyonk uçları + çiviye asma halkası
    bm = bmesh.new()
    n = 10
    for s in range(n):
        a0_, a1_ = 2 * math.pi * s / n, 2 * math.pi * (s + 1) / n
        r0 = 0.112
        p0 = Vector((r0 * math.cos(a0_), r0 * math.sin(a0_) * 0.92, NECK_Z + 0.006))
        p1 = Vector((r0 * math.cos(a1_), r0 * math.sin(a1_) * 0.92, NECK_Z + 0.006))
        prism(bm, p0, p1, 0.016, 0.016, seg=5)
    return ob, bm


pouch, cord_bm = build_pouch()
pouch.location = HANG
pouch.rotation_mode = 'QUATERNION'
# kese kameraya hafif dönük: ağız görünsün diye kameraya doğru 14° eğik
_tilt_axis = Vector((-TO_CAM0.y, TO_CAM0.x, 0)).normalized()
POUCH_Q0 = Quaternion(_tilt_axis, math.radians(-14))
pouch.rotation_quaternion = POUCH_Q0
# kese çivinin önünde: ağzının arka kenarı çiviye yakın, ip arka kenardan çıkar
_back = POUCH_Q0.inverted() @ (-TO_CAM0.to_3d()); _back.z = 0; _back.normalize()
POUCH_OFF = -_back * 0.16
pouch.data.transform(Matrix.Translation(POUCH_OFF))
for ch in pouch.children:
    ch.location = POUCH_OFF
cord_bm.transform(Matrix.Translation(POUCH_OFF))
_front = -_back
_side = Vector((-_front.y, _front.x, 0))
_kn = POUCH_OFF + _front * 0.115 + Vector((0, 0, NECK_Z + 0.006))
prism(cord_bm, _kn, _kn + _front * 0.03 + _side * 0.07 + Vector((0, 0, -0.08)), 0.014, 0.012, seg=5)
prism(cord_bm, _kn, _kn + _front * 0.03 - _side * 0.05 + Vector((0, 0, -0.1)), 0.014, 0.012, seg=5)
gem(cord_bm, _kn + _front * 0.01, (0.026, 0.026, 0.024), subdiv=1, amp=0.0, seed=8)
_bk = POUCH_OFF + _back * 0.11 + Vector((0, 0, NECK_Z + 0.006))
prism(cord_bm, _bk, Vector((0, 0, 0.0)), 0.012, 0.012, seg=5)
cord = bm_obj('ip', cord_bm, [M_CORD])
cord.parent = pouch


def pouch_quat(f):
    ax1 = _tilt_axis
    ax2 = TO_CAM0.to_3d()
    a1 = a2 = 0.0
    for i in range(N_SHEEP):
        tp = T_GATE0 + T_GAP * i - 3
        if f > tp:
            dt = f - tp
            a1 += 0.05 * math.exp(-dt / 14.0) * math.sin(dt * 0.32)
            a2 += 0.03 * math.exp(-dt / 14.0) * math.sin(dt * 0.27 + 1.0)
    return Quaternion(ax1, a1) @ Quaternion(ax2, a2) @ POUCH_Q0


def pouch_matrix(f):
    return Matrix.Translation(HANG) @ pouch_quat(f).to_matrix().to_4x4()


for f in range(-2, N_FRAMES + 3):
    pouch.rotation_quaternion = pouch_quat(f)
    pouch.keyframe_insert('rotation_quaternion', frame=f)


# ---------------------------------------------------------------- çakıllar (mercan rengi, köşeli, mat)
def pebble_mesh(name, seed):
    r = rng(seed)
    bm = bmesh.new()
    gem(bm, Vector((0, 0, 0)), (PEB_R * r.uniform(0.95, 1.08), PEB_R * r.uniform(0.78, 0.88), PEB_R * r.uniform(0.55, 0.62)),
        subdiv=1, amp=0.09, seed=seed, nscale=1.2)
    ob = bm_obj(name, bm, [M_PEBBLE])
    ob.rotation_mode = 'QUATERNION'
    return ob


# kesedeki yığın (kese yerel ekseni): 0 = en son kalan, ağzın ortasında en üstte
heap_local = [POUCH_OFF + Vector((0.0, 0.0, LIP_Z - 0.035))]
for k in range(5):
    th = 2 * math.pi * k / 5 + 0.3
    heap_local.append(POUCH_OFF + Vector((0.09 * math.cos(th), 0.08 * math.sin(th), LIP_Z - 0.065)))
for k in range(3):
    th = 2 * math.pi * k / 3 + 0.9
    heap_local.append(POUCH_OFF + Vector((0.045 * math.cos(th), 0.045 * math.sin(th), LIP_Z - 0.01)))
take_order = [8, 7, 6, 5, 4, 3, 2, 1]
pebbles = [pebble_mesh('cakil_%d' % k, 3000 + k) for k in range(9)]
LAST = pebbles[0]
LAND = []
_rr = rng(4000)
for k in range(N_SHEEP):
    p = ROW_START + ROW_DIR * (ROW_GAP * k) + Vector((_rr.uniform(-0.01, 0.01), _rr.uniform(-0.01, 0.01)))
    LAND.append(p)
local_rot = [Quaternion((0, 0, 1), rng(5000 + k).uniform(0, 6.28)) @ Quaternion((1, 0, 0), rng(5100 + k).uniform(-0.25, 0.25))
             for k in range(9)]
FLIGHT = 22


def qfix(q, prev):
    return -q if (prev is not None and q.dot(prev) < 0) else q


for idx, peb in enumerate(pebbles):
    order = take_order.index(idx) if idx in take_order else None
    prev_q = None
    t_take = T_GATE0 + T_GAP * order - 3 if order is not None else 10 ** 6
    land_q = Quaternion((0, 0, 1), math.atan2(ROW_DIR.y, ROW_DIR.x) + rng(6000 + idx).uniform(-0.35, 0.35))
    for f in range(-2, N_FRAMES + 3):
        if f <= t_take:
            M = pouch_matrix(f) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            loc, q, _ = M.decompose()
        else:
            M0 = pouch_matrix(t_take) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            p0, q0, _ = M0.decompose()
            L2 = LAND[order]
            p1 = Vector((L2.x, L2.y, SLAB_TOP + PEB_R * 0.5))
            t = min(1.0, (f - t_take) / FLIGHT)
            e = smoother(t)
            if t < 0.28:
                loc = p0 + Vector((0, 0, 0.2 * smoother(t / 0.28)))
            else:
                v = smoother((t - 0.28) / 0.72)
                loc = (p0 + Vector((0, 0, 0.2))).lerp(p1, v) + Vector((0, 0, 0.25 * 4 * v * (1 - v)))
            q = q0.slerp(land_q, e)
            q = Quaternion((1, 0, 0), 2.0 * math.sin(math.pi * e)) @ q if t < 1 else q
            if t >= 1:
                dt = f - t_take - FLIGHT
                loc = p1 + Vector((0, 0, 0.018 * math.exp(-dt / 2.0) * abs(math.sin(dt * 1.3))))
        q = qfix(q, prev_q)
        prev_q = q
        peb.location = loc
        peb.rotation_quaternion = q
        peb.keyframe_insert('location', frame=f)
        peb.keyframe_insert('rotation_quaternion', frame=f)

# ---------------------------------------------------------------- koyunlar
sheep = [build_sheep(i) for i in range(N_SHEEP)]


def sheep_s(i, f):
    P = paths[i]
    sg = P.closest_s(GATE_PT)
    u = sg + SPEED * (f - (T_GATE0 + T_GAP * i))
    ease = 1.1
    x = (u - (P.total - ease)) / (2 * ease)
    if x <= 0:
        return max(0.0, u)
    if x >= 1:
        return P.total
    return P.total - ease + 2 * ease * (x - x * x / 2)


for i, (root, bob, head, legs) in enumerate(sheep):
    prev_yaw = None
    prev_s = sheep_s(i, -3)
    for f in range(-2, N_FRAMES + 3):
        s = sheep_s(i, f)
        pos, d = paths[i].at(s)
        if d.length < 1e-6:
            _, d = paths[i].at(s - 0.05)
        yaw = math.atan2(d.y, d.x)
        if prev_yaw is not None:
            while yaw - prev_yaw > math.pi:
                yaw -= 2 * math.pi
            while yaw - prev_yaw < -math.pi:
                yaw += 2 * math.pi
        prev_yaw = yaw
        moving = min(1.0, max(0.0, (s - prev_s) / SPEED))
        prev_s = s
        phase = s / 0.95 * 2 * math.pi + i
        root.location = (pos.x, pos.y, hfun(pos.x, pos.y))
        root.rotation_euler = (0, 0, yaw)
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        bob.location = (0, 0, 0.03 * abs(math.sin(phase)) * moving)
        bob.rotation_euler = (0.025 * math.sin(phase) * moving, 0.02 * math.sin(2 * phase) * moving, 0)
        bob.keyframe_insert('location', frame=f)
        bob.keyframe_insert('rotation_euler', frame=f)
        # yürürken baş hafif aşağıda, durunca otlar gibi eğilip kalkar
        head.rotation_euler = (0.05 * math.sin(f * 0.07 + i),
                               0.06 * math.sin(phase) * moving + (0.35 + 0.2 * math.sin(f * 0.05 + i * 2)) * (1 - moving),
                               0.2 * math.sin(f * 0.03 + i) * (1 - moving))
        head.keyframe_insert('rotation_euler', frame=f)
        for k, leg in enumerate(legs):
            off = 0 if k in (0, 3) else math.pi
            leg.rotation_euler = (0, 0.38 * math.sin(phase + off) * moving, 0)
            leg.keyframe_insert('rotation_euler', frame=f)
print('t anim %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- ışık: yumuşak ortam + alçak sıcak güneş
world = bpy.data.worlds.new('dunya')
scene.world = world
world.use_nodes = True
WN, WL = world.node_tree.nodes, world.node_tree.links
bg = next(n for n in WN if n.type == 'BACKGROUND')
wo = next(n for n in WN if n.type == 'OUTPUT_WORLD')
# gökyüzü: kameraya görünen yumuşak geçiş (ufukta şeftali, yukarıda açık leylak); ışık olarak sıcak, düz ortam
tc = WN.new('ShaderNodeTexCoord')
sp = WN.new('ShaderNodeSeparateXYZ'); WL.new(tc.outputs['Generated'], sp.inputs[0])
cr = WN.new('ShaderNodeValToRGB')
els = cr.color_ramp.elements
els[0].position = 0.0; els[0].color = (1.0, 0.80, 0.66, 1)
els[1].position = 0.35; els[1].color = (0.80, 0.78, 0.92, 1)
e2 = els.new(0.1); e2.color = (1.0, 0.72, 0.62, 1)
mr = WN.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0
WL.new(sp.outputs['Z'], mr.inputs['Value'])
WL.new(mr.outputs[0], cr.inputs['Fac'])
lp = WN.new('ShaderNodeLightPath')
amb = WN.new('ShaderNodeBackground')
amb.inputs['Color'].default_value = (1.0, 0.86, 0.80, 1)
amb.inputs['Strength'].default_value = 0.85
sky = WN.new('ShaderNodeBackground')
WL.new(cr.outputs['Color'], sky.inputs['Color'])
sky.inputs['Strength'].default_value = 1.0
mixs = WN.new('ShaderNodeMixShader')
WL.new(lp.outputs['Is Camera Ray'], mixs.inputs['Fac'])
WL.new(amb.outputs[0], mixs.inputs[1])
WL.new(sky.outputs[0], mixs.inputs[2])
WL.new(mixs.outputs[0], wo.inputs['Surface'])


def light(name, kind, energy, color, loc=None, direction=None, size=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    ob = link(bpy.data.objects.new(name, ld))
    if loc is not None:
        ob.location = loc
    if direction is not None:
        ob.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    if size is not None:
        if kind == 'SUN':
            ld.angle = size
        elif kind == 'AREA':
            ld.size = size
        else:
            ld.shadow_soft_size = size
    return ob


SUN_AZ = math.radians(200.0)
SUN_EL = math.radians(26.0)
SUN_VEC = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))
light('gunes', 'SUN', 2.6, (1.0, 0.82, 0.66), direction=-SUN_VEC, size=math.radians(6.0))

# ---------------------------------------------------------------- kamera
cam_data = bpy.data.cameras.new('kamera')
cam_data.lens = 35
cam_data.sensor_width = 36
cam = link(bpy.data.objects.new('kamera', cam_data))
scene.camera = cam
target = link(bpy.data.objects.new('hedef', None))
tr = cam.constraints.new('TRACK_TO')
tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'
tr.up_axis = 'UP_Y'
cam_data.dof.use_dof = True
cam_data.dof.aperture_blades = 6


def last_world(f):
    return (pouch_matrix(f) @ Matrix.Translation(heap_local[0])).to_translation()


P_END = last_world(N_FRAMES)
_g3 = Vector((GATE_PT.x, GATE_PT.y, hfun(GATE_PT.x, GATE_PT.y) + 0.5))
_row3 = Vector((ROW_CENTER.x, ROW_CENTER.y, SLAB_TOP))
TGT0 = _g3.lerp(_row3, 0.45) + RIGHT3 * 0.9 + Vector((0, 0, 0.55))
TGT1 = TGT0 + Vector((0, 0, -0.05)) - RIGHT3 * 0.12
CAM1 = CAM_POS0 + (TGT0 - CAM_POS0).normalized() * 0.6
v_end = (CAM1 - P_END); v_end.z = 0
v_end = Matrix.Rotation(math.radians(8), 3, 'Z') @ v_end.normalized()
CAM_END = P_END + (v_end * 0.85 + Vector((0, 0, 0.55))).normalized() * 1.25
PUSH0, PUSH1 = 212, 296
for f in range(-2, N_FRAMES + 3):
    t0 = max(0.0, min(1.0, (f - 1) / (PUSH0 - 1)))
    t0 = t0 * t0 * (3 - 2 * t0) * 0.5 + t0 * 0.5
    cpos = CAM_POS0.lerp(CAM1, t0)
    tpos = TGT0.lerp(TGT1, t0)
    e = smoother((f - PUSH0) / (PUSH1 - PUSH0))
    cpos = cpos.lerp(CAM_END, e)
    tpos = tpos.lerp(P_END + Vector((0, 0, -0.04)), e)
    cam.location = cpos
    cam.keyframe_insert('location', frame=f)
    target.location = tpos
    target.keyframe_insert('location', frame=f)
    focus = _g3.lerp(P_END, smoother((f - PUSH0 + 10) / (PUSH1 - PUSH0 - 10)))
    cam_data.dof.focus_distance = (cpos - focus).length
    cam_data.dof.keyframe_insert('focus_distance', frame=f)
    cam_data.dof.aperture_fstop = 5.6 - 3.4 * e          # geniş planda her şey net; yakında hafif arka flu
    cam_data.dof.keyframe_insert('aperture_fstop', frame=f)
    cam_data.lens = 35 + 10 * e
    cam_data.keyframe_insert('lens', frame=f)

# ---------------------------------------------------------------- parıltı: son çakılda küçük, sıcak, yumuşak dört kollu yıldız
cam_dir_end = (CAM_END - P_END).normalized()
glint = light('parilti', 'POINT', 0.0, (1.0, 0.8, 0.55), loc=P_END + Vector((0, 0, 0.35)) + cam_dir_end * 0.2, size=0.05)
glint.visible_camera = False
for f, en in ((1, 0.0), (258, 0.0), (278, 1.2), (300, 1.0)):
    glint.data.energy = en
    glint.data.keyframe_insert('energy', frame=f)
b2 = bmesh.new()
bmesh.ops.create_icosphere(b2, subdivisions=2, radius=0.0045)
me = bpy.data.meshes.new('parilti_nokta'); b2.to_mesh(me); b2.free()
spark = link(bpy.data.objects.new('parilti_nokta', me))
M_SPARK = emissive('parilti_mat', (1.0, 0.86, 0.62), 0.0)
spark.data.materials.append(M_SPARK)
spark.parent = LAST
_M300 = pouch_matrix(N_FRAMES) @ Matrix.Translation(heap_local[0]) @ local_rot[0].to_matrix().to_4x4()
_l3, _q3, _s3 = _M300.decompose()
_top = (cam_dir_end * 0.4 + Vector((0, 0, 1))).normalized()
spark.location = (Matrix.Translation(_l3) @ _q3.to_matrix().to_4x4()).inverted() @ (P_END + _top * PEB_R * 0.62 + RIGHT3 * PEB_R * 0.2)
for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission'):
    setattr(spark, attr, False)
_sp = next(n for n in M_SPARK.node_tree.nodes if n.type == 'EMISSION').inputs['Strength']
for f, v in ((1, 0.0), (262, 0.0), (272, 240.0), (281, 110.0), (290, 190.0), (300, 140.0)):
    _sp.default_value = v
    _sp.keyframe_insert('default_value', frame=f)
# yakın planda keseye yumuşak ön dolgu (geniş planda kapalı)
_fill = light('yakin_dolgu', 'AREA', 0.0, (1.0, 0.86, 0.74), loc=CAM_END + Vector((0, 0, 0.5)) + (CAM_END - P_END).normalized() * 0.4,
              direction=(P_END - (CAM_END + Vector((0, 0, 0.5)))), size=1.2)
_fill.visible_camera = False
for f, en in ((1, 0.0), (205, 0.0), (270, 9.0), (300, 9.0)):
    _fill.data.energy = en
    _fill.data.keyframe_insert('energy', frame=f)

# ---------------------------------------------------------------- render ayarları
R = scene.render
R.engine = 'CYCLES'
C = scene.cycles


def pick_device():
    if A.cihaz == 'cpu':
        return 'CPU'
    try:
        pr = bpy.context.preferences.addons['cycles'].preferences
        for dt in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
            try:
                pr.compute_device_type = dt
            except Exception:
                continue
            pr.get_devices()
            gpus = [d for d in pr.devices if d.type == dt]
            if gpus:
                for d in pr.devices:
                    d.use = (d.type == dt)
                return 'GPU'
    except Exception as ex:
        print('GPU aranamadı', ex)
    return 'CPU'


C.device = pick_device()
C.samples = A.ornek
C.use_adaptive_sampling = True
C.adaptive_threshold = 0.02
C.use_denoising = True
for k, v in (('denoiser', 'OPENIMAGEDENOISE'), ('denoising_input_passes', 'RGB_ALBEDO_NORMAL'),
             ('denoising_prefilter', 'ACCURATE'), ('denoising_quality', 'HIGH')):
    try:
        setattr(C, k, v)
    except Exception as ex:
        print('ayar yok', k, ex)
C.max_bounces = 4
C.diffuse_bounces = 2
C.glossy_bounces = 1
C.transmission_bounces = 0
C.transparent_max_bounces = 2
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.seed = 7
C.sample_clamp_indirect = 4.0
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = bool(A.bulanik)
R.motion_blur_shutter = 0.3
R.use_persistent_data = True
vs = scene.view_settings
vs.view_transform = 'AgX'
vs.look = 'AgX - Medium High Contrast' if False else 'None'
vs.exposure = 0.15

ng = bpy.data.node_groups.new('kompozit', 'CompositorNodeTree')
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
scene.compositing_node_group = ng
rl = ng.nodes.new('CompositorNodeRLayers')
out = ng.nodes.new('NodeGroupOutput')
gl = ng.nodes.new('CompositorNodeGlare')
for nm, val in (('Type', 'Streaks'), ('Quality', 'High'), ('Threshold', 30.0), ('Strength', 0.28), ('Streaks', 4),
                ('Streaks Angle', 0.0), ('Fade', 0.72), ('Size', 0.22), ('Saturation', 0.9), ('Tint', (1.0, 0.8, 0.55, 1.0))):
    if nm in gl.inputs:
        try:
            gl.inputs[nm].default_value = val
        except Exception as ex:
            print('glare', nm, ex)
fg = ng.nodes.new('CompositorNodeGlare')
for nm, val in (('Type', 'Fog Glow'), ('Quality', 'High'), ('Threshold', 30.0), ('Strength', 0.3), ('Size', 0.35),
                ('Tint', (1.0, 0.78, 0.5, 1.0))):
    if nm in fg.inputs:
        try:
            fg.inputs[nm].default_value = val
        except Exception as ex:
            print('fog', nm, ex)
ng.links.new(rl.outputs['Image'], fg.inputs['Image'])
ng.links.new(fg.outputs['Image'], gl.inputs['Image'])
ng.links.new(gl.outputs['Image'], out.inputs[0])

from bpy_extras.object_utils import world_to_camera_view
for _f in (1, 68, 180, 212, 290):
    scene.frame_set(_f)
    for _nm, _p in (('kapi', _g3), ('kese', HANG + Vector((0, 0, -0.3))), ('dizi_bas', LAND[0].to_3d() + Vector((0, 0, SLAB_TOP))),
                    ('dizi_son', LAND[-1].to_3d() + Vector((0, 0, SLAB_TOP))), ('son_tas', P_END)):
        _c = world_to_camera_view(scene, cam, _p)
        print('KADRAJ f%d %-8s x=%.2f y(ust)=%.2f' % (_f, _nm, _c.x, 1 - _c.y))
    for _i in (0, 7):
        _c = world_to_camera_view(scene, cam, sheep[_i][0].matrix_world.to_translation() + Vector((0, 0, 0.6)))
        print('KADRAJ f%d koyun%d   x=%.2f y(ust)=%.2f' % (_f, _i, _c.x, 1 - _c.y))
print('sahne kuruldu: %.1f sn' % (time.time() - T_START), flush=True)
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(A.cikti), 'lowpoly.blend'))

_t = {}
bpy.app.handlers.render_pre.append(lambda sc, *a: _t.__setitem__('t', time.time()))
bpy.app.handlers.render_post.append(lambda sc, *a: print('KARE %d: %.1f sn' % (sc.frame_current, time.time() - _t.get('t', time.time())), flush=True))

R.image_settings.file_format = 'PNG'
R.image_settings.color_mode = 'RGB'
R.image_settings.color_depth = '8'
if A.mod == 'kare':
    for f in [int(x) for x in A.kareler.split(',') if x.strip()]:
        scene.frame_set(f)
        R.filepath = os.path.join(os.path.abspath(A.cikti), 'kare_%04d.png' % f)
        bpy.ops.render.render(write_still=True)
elif A.mod == 'parca':
    scene.frame_start = A.bas
    scene.frame_end = A.son
    R.filepath = os.path.join(os.path.abspath(A.cikti), 'k_')
    bpy.ops.render.render(animation=True)
print('BITTI toplam %.1f sn' % (time.time() - T_START))
