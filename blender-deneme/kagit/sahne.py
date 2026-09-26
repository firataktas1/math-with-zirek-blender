# Math with Zirek · sahne G, KÂĞIT KESİK sürüm (akşam, koyunlar girer, taş çıkar, tek taş kalır)
# Blender 5.2 LTS, Cycles. Tamamen yordamsal: her parça kalın kartondan kesilmiş gibi (lif dokusu, hafif
# pürüzlü kesik kenar, hafif bükülme, katmanlar arası küçük boşluk ve yumuşak gölge). Dış varlık yok.
# Yerleşim, zamanlama ve kamera vuruşları gerçekçi sürümle (../gercekci/sahne.py) ve kil sürümüyle aynı.
# Kullanım:
#   blender -b -P sahne.py -- --mod kare --kareler 60,150,290 --w 640 --h 360 --ornek 16 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 15 --cikti out            (1920x1080)
import bpy, bmesh, math, random, sys, os, time, argparse
from mathutils import Vector, Matrix, Quaternion, Euler, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--mod', default='kare')
ap.add_argument('--kareler', default='60,150,290')
ap.add_argument('--bas', type=int, default=1)
ap.add_argument('--son', type=int, default=300)
ap.add_argument('--w', type=int, default=1920)
ap.add_argument('--h', type=int, default=1080)
ap.add_argument('--ornek', type=int, default=128)
ap.add_argument('--cikti', default='out')
ap.add_argument('--cihaz', default='auto')
ap.add_argument('--bulanik', type=int, default=1)
ap.add_argument('--blend', action='store_true')
A = ap.parse_args(argv)
T_START = time.time()

FPS = 30
N_FRAMES = 300
N_SHEEP = 8
T_GATE0 = 40
T_GAP = 22
SPEED = 2.1 / FPS

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


# ---------------------------------------------------------------- yerleşim (gerçekçi sürümle aynı)
PEN_C = Vector((0.0, 6.0))
PEN_R = 4.0
GATE_ANG = math.radians(228)
GAP_HALF = 0.27            # kâğıt kukla yana dönük geçtiği için kapı gerçekçi sürümden geniş
WALL_H = 0.95
POST_R = 0.33
POST_H = 1.22


def hfun(x, y):
    return 0.0          # masa üstü maket: zemin düz karton, tepeler arka katmanlarda


def ang_dist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def ring_pos(a, r=PEN_R):
    return Vector((PEN_C.x + r * math.cos(a), PEN_C.y + r * math.sin(a)))


gu = Vector((math.cos(GATE_ANG), math.sin(GATE_ANG)))
GATE_PT = PEN_C + gu * PEN_R
CAM_AZ = GATE_ANG + math.radians(40)
_cxy = GATE_PT + Vector((math.cos(CAM_AZ), math.sin(CAM_AZ))) * 4.6
CAM_POS0 = Vector((_cxy.x, _cxy.y, hfun(_cxy.x, _cxy.y) + 1.75))
FACE = (CAM_POS0.xy - GATE_PT).normalized()          # kukla düzlemlerinin baktığı yön (kameraya)
RIGHT = Vector((-FACE.y, FACE.x)) * -1                  # ekranda sağ
RIGHT = Vector((FACE.y, -FACE.x)) if Vector((FACE.y, -FACE.x)).dot(Vector((-FACE.y, FACE.x))) < 0 else RIGHT
# ekranda sağ: kameranın ileri yönü f = -FACE, sağ = (f.y, -f.x)
_f = -FACE
RIGHT = Vector((_f.y, -_f.x)).normalized()
FACE3 = Vector((FACE.x, FACE.y, 0.0))
RIGHT3 = Vector((RIGHT.x, RIGHT.y, 0.0))
UP3 = Vector((0, 0, 1))
M_FACING = Matrix((RIGHT3, UP3, FACE3)).transposed().to_4x4()   # yerel X=sağ, Y=yukarı, Z=kameraya


# ---------------------------------------------------------------- kâğıt malzemeleri
def paper(name, color, edge_light=0.12, fiber=0.7, mottle=0.10, sss=0.0, rough=0.82, stretch=(1.0, 3.2, 1.0)):
    """Renkli karton: lif kabartması, hafif lekelenme, ışık geçirgenliği. Kenar malzemesi ayrı (kesik yüz açık renk)."""
    mats = []
    for kind in ('yuz', 'kenar'):
        m = bpy.data.materials.new('%s_%s' % (name, kind))
        N, L = m.node_tree.nodes, m.node_tree.links
        b = N['Principled BSDF']
        tc = N.new('ShaderNodeTexCoord')
        oi = N.new('ShaderNodeObjectInfo')
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
        L.new(tc.outputs['Object'], mp.inputs['Vector'])
        col = Vector(color)
        if kind == 'kenar':
            col = col.lerp(Vector((0.97, 0.93, 0.84)), edge_light)
        hs = N.new('ShaderNodeHueSaturation')
        hs.inputs['Color'].default_value = (*col, 1)
        # parça başına küçük ton farkı + geniş lekelenme
        mt = N.new('ShaderNodeTexNoise'); mt.inputs['Scale'].default_value = 3.0; mt.inputs['Detail'].default_value = 4.0
        L.new(tc.outputs['Object'], mt.inputs['Vector'])
        mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY_ADD'
        mm.inputs[1].default_value = mottle * 2; mm.inputs[2].default_value = 1.0 - mottle
        L.new(mt.outputs['Fac'], mm.inputs[0])
        vr = N.new('ShaderNodeMath'); vr.operation = 'MULTIPLY_ADD'
        vr.inputs[1].default_value = 0.08; vr.inputs[2].default_value = 0.96
        L.new(oi.outputs['Random'], vr.inputs[0])
        vv = N.new('ShaderNodeMath'); vv.operation = 'MULTIPLY'
        L.new(mm.outputs[0], vv.inputs[0]); L.new(vr.outputs[0], vv.inputs[1])
        L.new(vv.outputs[0], hs.inputs['Value'])
        # lifler: uzamış ince gürültü + seyrek koyu lif
        fb = N.new('ShaderNodeTexNoise'); fb.inputs['Scale'].default_value = 140.0; fb.inputs['Detail'].default_value = 10.0
        fb.inputs['Roughness'].default_value = 0.65
        L.new(mp.outputs['Vector'], fb.inputs['Vector'])
        grain = N.new('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value = 900.0; grain.inputs['Detail'].default_value = 2.0
        L.new(tc.outputs['Object'], grain.inputs['Vector'])
        fl = N.new('ShaderNodeTexWave'); fl.wave_type = 'BANDS'; fl.inputs['Scale'].default_value = 60.0
        fl.inputs['Distortion'].default_value = 18.0; fl.inputs['Detail'].default_value = 6.0
        L.new(mp.outputs['Vector'], fl.inputs['Vector'])
        fr = N.new('ShaderNodeValToRGB')
        fr.color_ramp.elements[0].position = 0.0; fr.color_ramp.elements[0].color = (0.9, 0.88, 0.85, 1)
        fr.color_ramp.elements[1].position = 0.06; fr.color_ramp.elements[1].color = (1, 1, 1, 1)
        L.new(fl.outputs['Fac'], fr.inputs['Fac'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        L.new(hs.outputs['Color'], mx.inputs['A']); L.new(fr.outputs['Color'], mx.inputs['B'])
        # kâğıt benekleri: seyrek, küçük açık/koyu lifler (geniş planda da doku okunur)
        sp = N.new('ShaderNodeTexNoise'); sp.inputs['Scale'].default_value = 70.0; sp.inputs['Detail'].default_value = 3.0
        L.new(mp.outputs['Vector'], sp.inputs['Vector'])
        spr = N.new('ShaderNodeValToRGB')
        spr.color_ramp.elements[0].position = 0.66; spr.color_ramp.elements[0].color = (1, 1, 1, 1)
        spr.color_ramp.elements[1].position = 0.72; spr.color_ramp.elements[1].color = (0.84, 0.82, 0.78, 1)
        L.new(sp.outputs['Fac'], spr.inputs['Fac'])
        mx2 = N.new('ShaderNodeMix'); mx2.data_type = 'RGBA'; mx2.blend_type = 'MULTIPLY'; mx2.inputs['Factor'].default_value = 1.0
        L.new(mx.outputs['Result'], mx2.inputs['A']); L.new(spr.outputs['Color'], mx2.inputs['B'])
        L.new(mx2.outputs['Result'], b.inputs['Base Color'])
        h1 = N.new('ShaderNodeMath'); h1.operation = 'MULTIPLY_ADD'; h1.inputs[1].default_value = 0.5
        L.new(fb.outputs['Fac'], h1.inputs[0]); L.new(grain.outputs['Fac'], h1.inputs[2])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = fiber; bp.inputs['Distance'].default_value = 0.002
        L.new(h1.outputs[0], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
        b.inputs['Roughness'].default_value = rough
        b.inputs['Specular IOR Level'].default_value = 0.3
        b.inputs['Sheen Weight'].default_value = 0.25
        b.inputs['Sheen Tint'].default_value = (1.0, 0.95, 0.88, 1)
        if sss > 0:
            b.inputs['Subsurface Weight'].default_value = sss
            b.inputs['Subsurface Radius'].default_value = (1.0, 0.8, 0.6)
            b.inputs['Subsurface Scale'].default_value = 0.01
        mats.append(m)
    return mats


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    N = m.node_tree.nodes
    N.remove(N['Principled BSDF'])
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1.0)
    em.inputs['Strength'].default_value = strength
    m.node_tree.links.new(em.outputs[0], N['Material Output'].inputs['Surface'])
    return m


P_SKY_TOP = paper('gok_ust', (0.93, 0.86, 0.70), sss=0.0)
P_SKY_MID = paper('gok_orta', (0.98, 0.80, 0.56), sss=0.0)
P_SKY_LOW = paper('gok_alt', (0.99, 0.70, 0.45), sss=0.0)
P_SUN = paper('gunes_kagit', (1.0, 0.86, 0.52), sss=0.3)
P_CLOUD = paper('bulut', (0.99, 0.93, 0.80))
P_HILL = [paper('tepe_uzak', (0.70, 0.66, 0.44)), paper('tepe_orta', (0.60, 0.62, 0.34)),
          paper('tepe_yakin', (0.50, 0.58, 0.27)), paper('tepe_okra', (0.80, 0.62, 0.30))]
P_GROUND = paper('zemin', (0.33, 0.45, 0.16), fiber=0.25)
P_TRAIL = paper('yol', (0.56, 0.56, 0.26), fiber=0.3)
P_GRASS = [paper('ot1', (0.30, 0.45, 0.16)), paper('ot2', (0.48, 0.60, 0.22)), paper('ot3', (0.62, 0.64, 0.28))]
P_WALL = paper('duvar', (0.28, 0.29, 0.30), sss=0.02)
P_STONE = [paper('tas1', (0.50, 0.50, 0.48), sss=0.02), paper('tas2', (0.36, 0.37, 0.39), sss=0.02),
           paper('tas3', (0.44, 0.45, 0.44), sss=0.02), paper('tas4', (0.47, 0.47, 0.45), sss=0.02)]
P_WOOL = paper('yun', (0.96, 0.91, 0.80), sss=0.08)
P_WOOL2 = paper('yun_arka', (0.84, 0.78, 0.66))
P_BLACK = paper('kara', (0.07, 0.06, 0.06), edge_light=0.05, sss=0.0)
P_EYE = paper('goz_ak', (0.97, 0.94, 0.86))
P_KRAFT = paper('kese', (0.50, 0.21, 0.15), edge_light=0.3)
P_KRAFT2 = paper('kese_arka', (0.33, 0.13, 0.10), edge_light=0.25)
P_STRING = paper('ip', (0.80, 0.70, 0.52))
P_WOOD = paper('civi', (0.30, 0.18, 0.10), edge_light=0.25)
P_PEBBLE = paper('cakil', (0.80, 0.50, 0.24), edge_light=0.18)
P_PEBBLE_HI = paper('cakil_acik', (0.88, 0.64, 0.38), edge_light=0.1)
P_PEBBLE_LO = paper('cakil_koyu', (0.55, 0.32, 0.15), edge_light=0.1)
P_SLAB = paper('yassi_tas', (0.42, 0.43, 0.43))
P_TREE = paper('agac', (0.36, 0.47, 0.20))
P_TRUNK = paper('govde', (0.45, 0.32, 0.20))


# ---------------------------------------------------------------- karton parça üreticisi
def deckle(pts, amp, seed, closed=True):
    """Makasla kesilmiş kenar: çevreyi sık örnekle, hafif gürültüyle titret."""
    out = []
    n = len(pts)
    off = seed * 13.7
    tot = 0.0
    per = sum((Vector(pts[(k + 1) % n]) - Vector(pts[k])).length for k in range(n))
    step = max(0.012, per / 700.0)          # büyük parçalar (tepe, gök) gereksiz sık olmasın
    for k in range(n if closed else n - 1):
        a, b = Vector(pts[k]), Vector(pts[(k + 1) % n])
        m = max(1, int((b - a).length / step))
        for j in range(m):
            p = a.lerp(b, j / m)
            t = (b - a).normalized()
            nn = Vector((-t.y, t.x))
            tot += (b - a).length / m
            d = amp * (noise.noise(Vector((tot * 9.0 / max(1.0, step / 0.012), off, 0.3))) + 0.35 * noise.noise(Vector((tot * 40.0 / max(1.0, step / 0.012), off, 1.7))))
            out.append(p + nn * d)
    return out


def piece(name, pts, thick, mats, amp=0.004, seed=0, bend=0.0, warp=0.0, dedupe=True):
    """2B çevreden kalın karton parça. mats=(yüz, kenar). Yerel XY düzleminde, kalınlık +Z."""
    pp = deckle(pts, amp, seed) if amp > 0 else [Vector(p) for p in pts]
    if dedupe:
        q = [pp[0]]
        for p in pp[1:]:
            if (p - q[-1]).length > 1e-4:
                q.append(p)
        pp = q
    bm = bmesh.new()
    vs = [bm.verts.new((p.x, p.y, 0.0)) for p in pp]
    try:
        f = bm.faces.new(vs)
    except ValueError:
        bm.free()
        return None
    # üçgenlemeye gerek yok: içbükey çokgeni Blender'in kendi bölmesi doğru doldurur
    faces = list(bm.faces)
    ex = bmesh.ops.extrude_face_region(bm, geom=faces)
    new_verts = [e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_verts, vec=(0, 0, thick))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for fc in bm.faces:
        fc.material_index = 0 if abs(fc.normal.z) > 0.7 else 1
        fc.smooth = False
    if bend or warp:
        o = Vector((seed * 1.3, seed * 0.7, 0))
        for v in bm.verts:
            v.co.z += bend * v.co.x * v.co.x + warp * noise.noise(Vector((v.co.x * 1.5, v.co.y * 1.5, 0)) + o)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mats[0])
    me.materials.append(mats[1])
    ob = link(bpy.data.objects.new(name, me))
    return ob


def ellipse_pts(rx, ry, n=48, bumps=0, bump_amp=0.0, cx=0.0, cy=0.0, rot=0.0, jitter=0.0, seed=0):
    r = rng(seed)
    out = []
    ph = r.uniform(0, 6.28)
    for k in range(n):
        t = 2 * math.pi * k / n
        f = 1.0
        if bumps:
            f += bump_amp * (1 - abs(math.cos(bumps * t / 2 + ph)))
        f += jitter * noise.noise(Vector((math.cos(t) * 2, math.sin(t) * 2, seed * 0.37)))
        x, y = rx * math.cos(t) * f, ry * math.sin(t) * f
        c, s = math.cos(rot), math.sin(rot)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def place_facing(ob, loc, extra=None):
    """Parçayı kameraya bakan düzleme koy (yerel X=ekranda sağ, Y=yukarı, Z=kameraya)."""
    M = Matrix.Translation(loc) @ M_FACING
    if extra is not None:
        M = M @ extra
    ob.matrix_world = M


# ---------------------------------------------------------------- gökyüzü ve uzak tepeler (sahne arka perdesi)
def backdrop():
    fwd = -FACE3
    base = CAM_POS0 + fwd * 60.0
    base.z = 0.0
    # gök bantları
    for k, (mat, h0, h1) in enumerate(((P_SKY_TOP, 9.0, 40.0), (P_SKY_MID, 4.0, 13.0), (P_SKY_LOW, -2.0, 6.5))):
        pts = [(-80, h0)] + [(-80 + 160 * j / 40, h1 + (0.9 * math.sin(j * 0.9 + k) if k else 0)) for j in range(41)] + [(80, h0)]
        if k:
            pts = [(-80, -5.0)] + [(-80 + 160 * j / 40, h1 + 0.8 * math.sin(j * 0.7 + k * 2)) for j in range(41)] + [(80, -5.0)]
        ob = piece('gok_%d' % k, pts, 0.08, mat, amp=0.12, seed=40 + k)
        place_facing(ob, base + fwd * (0.8 * (2 - k)) + Vector((0, 0, 0)))
        ob.visible_shadow = False
    # bulutlar
    r = rng(7)
    for k in range(5):
        cx = r.uniform(-45, 40); cy = r.uniform(9, 20)
        pts = ellipse_pts(r.uniform(5, 9), r.uniform(1.0, 1.8), 64, bumps=9, bump_amp=0.25, seed=70 + k)
        pts = [(x, max(y, -0.4)) for (x, y) in pts]
        ob = piece('bulut_%d' % k, pts, 0.06, P_CLOUD, amp=0.06, seed=70 + k)
        place_facing(ob, base - fwd * 0.4 + RIGHT3 * cx + Vector((0, 0, cy)))
        ob.visible_shadow = False
    # tepe katmanları (uzaktan yakına)
    for k, (dist, h, amp, mat) in enumerate(((42.0, 2.6, 1.0, P_HILL[0]), (32.0, 1.9, 0.8, P_HILL[3]),
                                             (24.0, 1.3, 0.6, P_HILL[1]), (17.0, 0.8, 0.4, P_HILL[2]))):
        rr = rng(80 + k)
        ph = rr.uniform(0, 6)
        W = 70 + dist
        pts = [(-W, -3.0)]
        for j in range(81):
            x = -W + 2 * W * j / 80
            y = h + amp * math.sin(x * 0.11 + ph) + 0.5 * amp * math.sin(x * 0.23 + 2 * ph) + 0.2 * math.sin(x * 0.6)
            pts.append((x, y))
        pts.append((W, -3.0))
        c = CAM_POS0 + fwd * dist
        c.z = hfun(c.x, c.y) - 0.5
        ob = piece('tepe_%d' % k, pts, 0.1, mat, amp=0.05, seed=80 + k)
        place_facing(ob, c)
        # tepede birkaç kâğıt ağaç
        if k in (1, 2):
            for t in range(3 if k == 1 else 2):
                tx = rr.uniform(-20, 25)
                ty = h + amp * math.sin(tx * 0.11 + ph) + 0.5 * amp * math.sin(tx * 0.23 + 2 * ph) - 0.1
                s = 1.4 if k == 1 else 1.9
                tr_ = piece('agac_govde', [(-0.08 * s, 0), (0.08 * s, 0), (0.06 * s, 1.1 * s), (-0.06 * s, 1.1 * s)], 0.06, P_TRUNK, amp=0.01, seed=90 + t)
                place_facing(tr_, c + RIGHT3 * tx + Vector((0, 0, ty)) + FACE3 * 0.12)
                cr = piece('agac_tac', ellipse_pts(0.6 * s, 0.75 * s, 40, bumps=7, bump_amp=0.12, cy=1.5 * s, seed=95 + t), 0.06, P_TREE, amp=0.02, seed=95 + t)
                place_facing(cr, c + RIGHT3 * tx + Vector((0, 0, ty)) + FACE3 * 0.2)


# ---------------------------------------------------------------- zemin: büyük yeşil karton + kesik ot şeritleri
def ground():
    """Düz yeşil karton zemin + kameraya bakan dalgalı kenarlı üst üste kâğıt katmanları + sürünün açık renkli yolu."""
    base = piece('zemin', [(-60, -60), (60, -60), (60, 90), (-60, 90)], 0.01, P_GROUND, amp=0.0, seed=1)
    base.location = (0, 0, -0.012)
    fwd = -FACE3
    for k, (dist, mat, amp) in enumerate(((2.9, P_GRASS[0], 0.12), (13.4, P_HILL[2], 0.3), (17.5, P_HILL[1], 0.4))):
        r = rng(200 + k)
        pts = []
        W = 40.0
        for j in range(161):
            x = -W + 2 * W * j / 160
            pts.append((x, amp * (0.6 * math.sin(x * 0.9 + k) + 0.4 * math.sin(x * 2.3 + 2 * k)) + r.uniform(-0.02, 0.02)))
        pts = [(-W, -60.0)] + pts + [(W, -60.0)] if k == 0 else [(-W, 60.0)] + list(reversed(pts)) + [(W, 60.0)]
        ob = piece('zemin_kat_%d' % k, pts, 0.012, mat, amp=0.0, seed=200 + k)
        c = CAM_POS0 + fwd * dist
        # yerel X = ekranda sağ, yerel Y = ileri (kameradan uzağa), Z = yukarı
        M = Matrix((RIGHT3, fwd, UP3)).transposed().to_4x4()
        ob.matrix_world = Matrix.Translation((c.x, c.y, 0.001 * (k + 1))) @ M
    # sürünün yolu: çiğnenmiş, açık yeşil-okra kâğıt şerit (yol boyunca)
    pts_l, pts_r = [], []
    P = paths[0]
    for j in range(0, len(P.p), 4):
        q = P.p[j]
        if (q - GATE_PT).length < 0.2 or (q - PEN_C).length < PEN_R - 0.3:
            continue
        d = P.p[min(j + 1, len(P.p) - 1)] - P.p[max(j - 1, 0)]
        if d.length < 1e-6:
            continue
        n = Vector((-d.y, d.x)).normalized()
        w = 0.55 + 0.08 * noise.noise(Vector((j * 0.1, 0.3, 0.0)))
        pts_l.append(q + n * w); pts_r.append(q - n * w)
    trail = piece('yol', [tuple(p) for p in pts_l] + [tuple(p) for p in reversed(pts_r)], 0.006, P_TRAIL, amp=0.02, seed=210)
    trail.location = (0, 0, 0.004)


def grass_strip(name, width, height, seed, mat):
    r = rng(seed)
    pts = [(-width / 2, -0.02)]
    n = max(3, int(width / 0.05))
    for k in range(n):
        x0 = -width / 2 + width * k / n
        x1 = -width / 2 + width * (k + 0.5) / n
        pts.append((x0 + r.uniform(0, 0.006), height * r.uniform(0.25, 0.4)))
        pts.append((x1 + r.uniform(-0.01, 0.01), height * r.uniform(0.7, 1.15)))
    pts.append((width / 2, height * 0.3))
    pts.append((width / 2, -0.02))
    return piece(name, pts, 0.008, mat, amp=0.0, seed=seed, dedupe=True)


def grass_field(avoid):
    r = rng(123)
    protos = [grass_strip('ot_ornek_%d' % k, r.uniform(0.25, 0.45), r.uniform(0.07, 0.16), 300 + k, P_GRASS[k % 3])
              for k in range(9)]
    for p in protos:
        p.location = (0, 0, -100)
    k = 0
    tries = 0
    while k < 520 and tries < 20000:
        tries += 1
        x = r.uniform(-9, 7); y = r.uniform(-3.0, 12.0)
        p = Vector((x, y))
        if any(f(p) for f in avoid):
            continue
        dpen = (p - PEN_C).length
        near_wall = abs(dpen - PEN_R) < 1.0
        if not near_wall and r.random() < 0.55:
            continue
        src = protos[r.randrange(len(protos))]
        ob = link(bpy.data.objects.new('ot_%d' % k, src.data))
        s = r.uniform(0.8, 1.4) * (1.3 if near_wall else 1.0)
        ob.matrix_world = Matrix.Translation((x, y, hfun(x, y))) @ M_FACING @ Matrix.Rotation(r.uniform(-0.12, 0.12), 4, 'Z') @ Matrix.Scale(s, 4)
        k += 1


# ---------------------------------------------------------------- ağıl: kıvrılmış kalın karton şerit + yapıştırılmış taş parçaları
def ring_strip(name, a0, a1, radius, center, h0, height_fn, thick, mats, step=0.04):
    bm = bmesh.new()
    n = max(2, int(abs(a1 - a0) * radius / step))
    outer, inner = [], []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        c, s = math.cos(a), math.sin(a)
        H = height_fn(a)
        row = []
        for (rr, zz) in ((radius + thick / 2, 0.0), (radius + thick / 2, H), (radius - thick / 2, H), (radius - thick / 2, 0.0)):
            x, y = center.x + rr * c, center.y + rr * s
            row.append(bm.verts.new((x, y, hfun(x, y) + h0 + zz - (0.05 if zz == 0 else 0))))
        outer.append(row)
    for i in range(n):
        for j in range(4):
            j2 = (j + 1) % 4
            if j == 3:
                continue
            f = bm.faces.new((outer[i][j], outer[i + 1][j], outer[i + 1][j2], outer[i][j2]))
            f.material_index = 1 if j == 1 else 0
    if abs(a1 - a0) < 2 * math.pi - 1e-3:
        for row in (outer[0], outer[-1]):
            f = bm.faces.new(row)
            f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(mats[0]); me.materials.append(mats[1])
    return link(bpy.data.objects.new(name, me))


def cut_stone(w, hh, r):
    """Makasla kesilmiş taş: 6-8 köşeli, yassı, düzensiz çokgen."""
    n = r.randint(6, 8)
    angs = sorted(r.uniform(0, 2 * math.pi) for _ in range(n))
    pts = []
    for a in angs:
        rr = r.uniform(0.85, 1.0)
        x, y = math.cos(a) * rr, math.sin(a) * rr
        # dikdörtgene yakın: köşelere doğru it
        x = math.copysign(abs(x) ** 0.6, x)
        y = math.copysign(abs(y) ** 0.75, y)
        pts.append((x * w / 2, y * hh / 2))
    return pts


def stone_patches(name_prefix, center, radius, a0, a1, height_fn, side, seed, courses=6, wmin=0.18, wmax=0.34, total_h=WALL_H):
    """Duvar yüzüne yapıştırılmış taş biçimli karton parçalar (3 ton, tek nesnede birleşik)."""
    r = rng(seed)
    bms = [bmesh.new() for _ in P_STONE]
    r.random()
    arc_len = abs(a1 - a0) * radius
    for c in range(courses):
        z0 = 0.03 + c * (total_h / courses)
        hh = total_h / courses * r.uniform(0.78, 0.92)
        if c == courses - 1:
            hh *= 1.45          # üst sıra duvarın üstünden taşar: düzensiz taş tepe
        s = r.uniform(0, 0.15)
        while s < arc_len - 0.05:
            w = r.uniform(wmin, wmax)
            a = a0 + (a1 - a0) * (s + w / 2) / arc_len
            H = height_fn(a)
            if z0 + hh * 0.6 > H:
                s += w + 0.03
                continue
            pts = cut_stone(w, hh, r)
            k = r.randrange(len(P_STONE))
            bm = bms[k]
            tmp = bmesh.new()
            vs = [tmp.verts.new((x, y, 0)) for (x, y) in deckle(pts, 0.004, r.randrange(1000))]
            f = tmp.faces.new(vs)
            pass
            ex = bmesh.ops.extrude_face_region(tmp, geom=list(tmp.faces))
            bmesh.ops.translate(tmp, verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, 0.012))
            bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
            for fc in tmp.faces:
                fc.material_index = 0 if abs(fc.normal.z) > 0.7 else 1
            ca, sa = math.cos(a), math.sin(a)
            rr = radius + side * (0.03 + 0.004 * r.random())
            pos = Vector((center.x + rr * ca, center.y + rr * sa, 0))
            pos.z = hfun(pos.x, pos.y) + z0 + hh / 2
            nrm = Vector((ca, sa, 0)) * side
            tang = Vector((-sa, ca, 0)) * side
            M = Matrix.Translation(pos) @ Matrix((tang, Vector((0, 0, 1)), nrm)).transposed().to_4x4() @ Matrix.Rotation(r.uniform(-0.08, 0.08), 4, 'Z')
            tmp.transform(M)
            me = bpy.data.meshes.new('tmp')
            tmp.to_mesh(me); tmp.free()
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
            s += w + r.uniform(0.01, 0.04)
    for k, bm in enumerate(bms):
        me = bpy.data.meshes.new('%s_%d' % (name_prefix, k))
        bm.to_mesh(me); bm.free()
        me.materials.append(P_STONE[k][0]); me.materials.append(P_STONE[k][1])
        link(bpy.data.objects.new(me.name, me))


def build_pen():
    a0 = GATE_ANG + GAP_HALF
    a1 = GATE_ANG - GAP_HALF + 2 * math.pi

    def hf(a):
        return WALL_H + 0.05 * noise.noise(Vector((math.cos(a) * 3, math.sin(a) * 3, 0.5)))
    ring_strip('duvar', a0, a1, PEN_R, PEN_C, 0.0, hf, 0.10, P_WALL)
    stone_patches('duvar_tas_dis', PEN_C, PEN_R + 0.05, a0, a1, hf, 1, 11)
    stone_patches('duvar_tas_ic', PEN_C, PEN_R - 0.05, a0, a1, hf, -1, 12)
    posts = []
    for side, sgn in (('on', 1), ('arka', -1)):
        a = GATE_ANG + sgn * GAP_HALF
        p = ring_pos(a)
        ring_strip('direk_' + side, 0.0, 2 * math.pi, POST_R, p, 0.0, lambda aa: POST_H, 0.04, P_WALL, step=0.03)
        stone_patches('direk_tas_' + side, p, POST_R + 0.02, 0.0, 2 * math.pi, lambda aa: POST_H, 1, 20 + sgn, courses=12, wmin=0.1, wmax=0.17, total_h=POST_H)
        cap = piece('direk_kapak_' + side, cut_stone(2 * POST_R + 0.16, 2 * POST_R + 0.1, rng(30 + sgn)), 0.06,
                    P_STONE[1], amp=0.006, seed=30 + sgn)
        cap.location = (p.x, p.y, hfun(p.x, p.y) + POST_H)
        cap.rotation_euler = (0.03, -0.02, rng(31 + sgn).uniform(0, 6.28))
        cap2 = piece('direk_kapak2_' + side, cut_stone(POST_R + 0.1, POST_R * 0.8, rng(33 + sgn)), 0.05,
                     P_STONE[3], amp=0.005, seed=33 + sgn)
        cap2.location = (p.x + 0.03, p.y - 0.02, hfun(p.x, p.y) + POST_H + 0.06)
        cap2.rotation_euler = (0.0, 0.04, rng(34 + sgn).uniform(0, 6.28))
        posts.append((side, a, p))
    return posts


# ---------------------------------------------------------------- koyun kuklası (katmanlı karton)
def build_sheep(i):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('koyun_%d' % i, None))
    turn = link(bpy.data.objects.new('koyun_%d_don' % i, None))    # ekranda yön (sağa/sola) çevirme
    turn.parent = root
    bob = link(bpy.data.objects.new('koyun_%d_govde' % i, None))
    bob.parent = turn
    s = r.uniform(0.92, 1.05)
    root.scale = (s, s, s)
    parts = []

    def add(ob, loc, rot=0.0, parent=bob):
        ob.parent = parent
        ob.location = loc
        ob.rotation_euler = (0, 0, rot)
        parts.append(ob)
        return ob
    # arka bacaklar (uzak taraf, koyu)
    legs = []
    for k, (lx, dz) in enumerate(((0.30, -0.05), (-0.30, -0.05), (0.26, 0.07), (-0.34, 0.07))):
        far = dz < 0
        leg = link(bpy.data.objects.new('koyun_%d_bacak_%d' % (i, k), None))
        leg.parent = bob
        leg.location = (lx, 0.47, dz)
        g = piece('koyun_%d_bacak_%d_k' % (i, k), [(-0.032, 0.02), (0.032, 0.02), (0.028, -0.40), (0.04, -0.46), (-0.035, -0.46), (-0.028, -0.40)],
                  0.012, P_BLACK, amp=0.002, seed=i * 10 + k)
        g.parent = leg
        if far:
            g.data.materials[0] = P_WOOL2[0] if False else P_BLACK[0]
        legs.append(leg)
    # yün: arka katman (koyu krem), ön katman (açık krem), ön katmanda birkaç ayrı bukle
    body_back = piece('koyun_%d_yun_arka' % i, ellipse_pts(0.62, 0.36, 72, bumps=13, bump_amp=0.11, seed=i + 5), 0.014,
                      P_WOOL2, amp=0.004, seed=i + 5, bend=0.05)
    add(body_back, (0.0, 0.70, -0.02))
    body = piece('koyun_%d_yun' % i, ellipse_pts(0.58, 0.33, 72, bumps=11, bump_amp=0.12, seed=i + 7), 0.014,
                 P_WOOL, amp=0.004, seed=i + 7, bend=0.05)
    add(body, (-0.02, 0.71, 0.02))
    belly = piece('koyun_%d_karin' % i, ellipse_pts(0.5, 0.14, 48, bumps=9, bump_amp=0.18, seed=i + 6), 0.01, P_WOOL2, amp=0.003, seed=i + 6)
    add(belly, (0.0, 0.45, 0.034))
    for k in range(7):
        cx = r.uniform(-0.42, 0.36); cy = r.uniform(-0.16, 0.2)
        cl = piece('koyun_%d_bukle_%d' % (i, k), ellipse_pts(r.uniform(0.09, 0.14), r.uniform(0.06, 0.09), 30, bumps=5, bump_amp=0.2, seed=i * 20 + k),
                   0.01, P_WOOL, amp=0.003, seed=i * 20 + k)
        add(cl, (cx, 0.71 + cy, 0.045))
    tail = piece('koyun_%d_kuyruk' % i, ellipse_pts(0.08, 0.06, 24, bumps=4, bump_amp=0.2, seed=i + 9), 0.012, P_WOOL, amp=0.003, seed=i + 9)
    add(tail, (-0.6, 0.78, 0.0))
    # baş: kara karton, uzun burun; kulak; göz
    head = link(bpy.data.objects.new('koyun_%d_bas' % i, None))
    head.parent = bob
    head.location = (0.56, 0.86, 0.06)
    hp = [(-0.09, 0.07), (0.0, 0.10), (0.08, 0.07), (0.20, -0.04), (0.24, -0.11), (0.20, -0.16), (0.10, -0.14),
          (0.0, -0.08), (-0.08, -0.05)]
    hd = piece('koyun_%d_yuz' % i, hp, 0.014, P_BLACK, amp=0.003, seed=i + 11)
    hd.parent = head
    ear = piece('koyun_%d_kulak' % i, [(0, 0), (0.05, 0.015), (0.13, -0.005), (0.14, -0.03), (0.05, -0.035)], 0.01, P_BLACK, amp=0.002, seed=i + 12)
    ear.parent = head
    ear.location = (-0.03, 0.05, 0.02)
    ear.rotation_euler = (0, 0, math.radians(200))
    ear2 = piece('koyun_%d_kulak2' % i, [(0, 0), (0.05, 0.015), (0.13, -0.005), (0.14, -0.03), (0.05, -0.035)], 0.01, P_BLACK, amp=0.002, seed=i + 13)
    ear2.parent = head
    ear2.location = (0.0, 0.06, -0.025)
    ear2.rotation_euler = (0, 0, math.radians(160))
    tuft = piece('koyun_%d_percem' % i, ellipse_pts(0.075, 0.05, 24, bumps=5, bump_amp=0.25, seed=i + 14), 0.01, P_WOOL, amp=0.002, seed=i + 14)
    tuft.parent = head
    tuft.location = (-0.02, 0.09, 0.02)
    eye = piece('koyun_%d_goz' % i, ellipse_pts(0.022, 0.017, 20, seed=i + 15), 0.006, P_EYE, amp=0.0, seed=i + 15)
    eye.parent = head
    eye.location = (0.06, 0.02, 0.016)
    pup = piece('koyun_%d_bebek' % i, ellipse_pts(0.011, 0.012, 16, seed=i + 16), 0.004, P_BLACK, amp=0.0, seed=i + 16)
    pup.parent = eye
    pup.location = (0.006, -0.002, 0.006)
    return root, turn, bob, head, legs


# ---------------------------------------------------------------- yol (gerçekçi sürümle aynı)
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
_FC = (CAM_POS0.xy - GATE_PT).normalized()          # kapıdan kameraya
_RT = Vector((-_FC.y, _FC.x))                           # ekranda sağ
# sürü sol önden (kameranın solundan) çapraz gelip kapıya girer: ilk koyun ilk karede kadrajın solunda
OUT1 = GATE_PT - _RT * 0.9 + _FC * 1.5
SPOTS = []
_rs = rng(77)
while len(SPOTS) < N_SHEEP:
    a = _rs.uniform(0, 2 * math.pi)
    rr = _rs.uniform(0.6, PEN_R - 1.1)
    q = PEN_C + Vector((rr * math.cos(a), rr * math.sin(a)))
    if (q - INSIDE).length < 1.0:
        continue
    if all((q - o).length > 1.35 for o in SPOTS):
        SPOTS.append(q)
SPOTS.sort(key=lambda q: -(q - INSIDE).length)
START = [CAM_POS0.xy - _RT * 14.0 + _FC * 1.5, CAM_POS0.xy - _RT * 2.6 - _FC * 1.6]
paths = []
for i in range(N_SHEEP):
    jit = _FC * (0.14 * ((i * 7) % 3 - 1))
    paths.append(Path([START[0] + jit, START[1] + jit * 0.7, OUT1, GATE_PT, INSIDE, SPOTS[i]]))

# ---------------------------------------------------------------- sahneyi kur
backdrop()
ground()
posts = build_pen()
front_post = [p for p in posts if p[0] == 'on'][0]
_, FA, FP = front_post
TO_CAM0 = (CAM_POS0.xy - FP).normalized()
ROW_START = FP + TO_CAM0 * (POST_R + 0.6) - RIGHT * 0.3
ROW_DIR = RIGHT
ROW_CENTER = ROW_START + ROW_DIR * 0.3


def near_path(p):
    return min((q - p).length for q in paths[0].p[::3]) < 0.55


grass_field([lambda p: abs((p - PEN_C).length - PEN_R) < 0.12,
             lambda p: (p - ROW_CENTER).length < 0.75,
             near_path,
             lambda p: (p - CAM_POS0.xy).length < 1.5,
             lambda p: (p - FP).length < POST_R + 0.1,
             lambda p: (p - ring_pos(GATE_ANG - GAP_HALF)).length < POST_R + 0.1])

# yassı taş (çakılların dizildiği yer): yere yatık gri karton
slab_c = ROW_START + ROW_DIR * 0.33
SLAB = piece('yassi_tas', ellipse_pts(0.52, 0.22, 40, jitter=0.08, seed=55), 0.035, P_SLAB, amp=0.01, seed=55)
SLAB.location = (slab_c.x, slab_c.y, hfun(slab_c.x, slab_c.y) + 0.002)
SLAB.rotation_euler = (0, 0, math.atan2(ROW_DIR.y, ROW_DIR.x))
SLAB_TOP = hfun(slab_c.x, slab_c.y) + 0.037
print('t sahne %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- kese (düz, katmanlı kraft kâğıt), çivi
POUCH_W = 0.30
PEG_Z = 1.02
peg_root = FP.to_3d() + FACE3 * (POST_R + 0.02) + Vector((0, 0, hfun(FP.x, FP.y) + PEG_Z))
# çivi: direğe saplanmış kısa tahta kazık, kameraya göre sağa ve yukarı eğik (yanından görünür, uç yuvarlak)
_peg_rot = Matrix.Rotation(math.radians(-38), 4, 'Y') @ Matrix.Rotation(math.radians(-14), 4, 'X')
peg = piece('civi', [(-0.018, -0.016), (0.018, -0.016), (0.02, 0.016), (-0.016, 0.018)], 0.15, P_WOOD, amp=0.002, seed=61)
place_facing(peg, peg_root + FACE3 * -0.03, _peg_rot)
peg_end = piece('civi_ucu', ellipse_pts(0.021, 0.019, 24, jitter=0.08, seed=62), 0.008, P_WOOD, amp=0.002, seed=62)
place_facing(peg_end, peg_root + FACE3 * -0.03 + (M_FACING.to_3x3() @ _peg_rot.to_3x3() @ Vector((0, 0, 0.15))), _peg_rot)
HANG = peg_root + FACE3 * -0.03 + (M_FACING.to_3x3() @ _peg_rot.to_3x3() @ Vector((0, 0, 0.11))) + Vector((0, 0, -0.012))

pouch = link(bpy.data.objects.new('kese', None))       # sallanma ekseni: çivi
pouch.matrix_world = Matrix.Translation(HANG) @ M_FACING
pouch.rotation_mode = 'QUATERNION'
POUCH_Q0 = pouch.rotation_quaternion.copy()


PROF = [(0.0, 0.0), (0.05, 0.003), (0.085, 0.014), (0.108, 0.034), (0.12, 0.06), (0.123, 0.088), (0.118, 0.115),
        (0.104, 0.14), (0.083, 0.16), (0.062, 0.174), (0.05, 0.183), (0.052, 0.19), (0.06, 0.199), (0.07, 0.208),
        (0.078, 0.216), (0.083, 0.224), (0.086, 0.231)]
PS = 1.4                     # gerçekçi sürümdeki keseyle aynı boy
TOP_Y = -0.02                # ağız çivinin 2 cm altında
BOT_Y = TOP_Y - 0.231 * PS


def bag_outline(seed, clip_y=None, widen=1.0):
    """Önden büzgülü kese: yuvarlak gövde, dar boğaz, fırfırlı ağız. clip_y: ön katman boğazda düz kesilir."""
    r = rng(seed)
    R = 0.155 * widen
    cy = BOT_Y + R
    right = []
    for k in range(21):                       # gövde: alttan en geniş yere
        a = -math.pi / 2 + (math.pi / 2) * k / 20
        right.append((R * math.cos(a) * (1.0 + 0.04 * math.sin(3 * a)), cy + R * math.sin(a) * 0.95))
    neck_y = NECK_Y
    x0, y0 = right[-1]
    for k in range(1, 13):                    # yuvarlak omuz, boğaza doğru toplanan kumaş
        t = k / 12
        right.append((0.045 * widen + (x0 - 0.045 * widen) * math.cos(t * math.pi / 2) ** 1.3, y0 + (neck_y - y0) * t))
    if clip_y is not None:
        right = [p for p in right if p[1] <= clip_y]
        xs = right[-1][0]
        top = [(xs - 2 * xs * k / 8, clip_y + 0.003 * math.sin(k * 2.1 + seed)) for k in range(9)]
        return [(0.0, BOT_Y)] + right[1:] + top[1:-1] + [(-x, y) for (x, y) in reversed(right[1:])]
    for k in range(1, 5):                     # boğazdan ağıza dışa açılma
        t = k / 4
        right.append((0.045 * widen + (0.095 * widen - 0.045 * widen) * smoother(t), neck_y + (TOP_Y - neck_y) * t))
    n = 10
    top = []
    xt = right[-1][0]
    for k in range(n + 1):                    # fırfır
        x = xt - 2 * xt * k / n
        y = TOP_Y + (0.012 if k % 2 == 0 else -0.004) + r.uniform(-0.004, 0.004)
        top.append((x * (1.08 if k % 2 == 0 else 1.0), y))
    return [(0.0, BOT_Y)] + right[1:] + top[1:-1] + [(-x, y) for (x, y) in reversed(right[1:])]


NECK_Y = TOP_Y - 0.068


bag_back = piece('kese_arka', bag_outline(71, widen=1.03), 0.012, P_KRAFT2, amp=0.003, seed=71, bend=0.4)
bag_back.parent = pouch
bag_back.location = (0.0, 0.0, -0.035)
bag_front = piece('kese_on', bag_outline(72, clip_y=NECK_Y + 0.004), 0.012, P_KRAFT, amp=0.003, seed=72, bend=0.5)
bag_front.parent = pouch
bag_front.location = (0.0, 0.0, 0.03)
# kumaş kırışıkları: ön katmanın üstünde birkaç ince koyu kesik şerit
for k, (x, ang, ln) in enumerate(((-0.03, 0.55, 0.08), (-0.012, 0.2, 0.06), (0.008, -0.1, 0.07), (0.028, -0.45, 0.085), (0.04, -0.8, 0.05))):
    cr = piece('kese_kirisik_%d' % k, [(-0.0035, 0), (0.0035, 0), (0.0015, -ln), (-0.0015, -ln)], 0.003, P_KRAFT2, amp=0.0008, seed=76 + k)
    cr.parent = pouch
    cr.location = (x, NECK_Y - 0.006, 0.047)
    cr.rotation_euler = (0, 0, ang)
# büzgü ipi: boğazda krem şerit, çiviye çıkan halka, sarkan iki uç ve düğüm
nz = NECK_Y
nw = 0.045
cord = piece('ip_bogaz', [(-nw - 0.012, nz - 0.008), (nw + 0.012, nz - 0.01), (nw + 0.014, nz + 0.006), (-nw - 0.012, nz + 0.008)],
             0.006, P_STRING, amp=0.0015, seed=73)
cord.parent = pouch
cord.location = (0.0, 0.0, 0.046)
loop = piece('ip_aski', [(-0.009, nz), (0.009, nz), (0.006, 0.004), (-0.006, 0.004)], 0.005, P_STRING, amp=0.001, seed=74)
loop.parent = pouch
loop.location = (-0.02, 0.0, -0.045)
loop.rotation_euler = (0, 0, 0.12)
knot = piece('ip_dugum', ellipse_pts(0.012, 0.01, 16, seed=75), 0.008, P_STRING, amp=0.001, seed=75)
knot.parent = pouch
knot.location = (nw + 0.01, nz, 0.052)
for k, (x, rot, ln) in enumerate(((nw + 0.008, -0.25, 0.075), (nw + 0.016, 0.1, 0.06))):
    tail = piece('ip_uc_%d' % k, [(-0.004, 0), (0.004, 0), (0.0035, -ln), (-0.0035, -ln)], 0.004, P_STRING, amp=0.001, seed=77 + k)
    tail.parent = pouch
    tail.location = (x, nz - 0.004, 0.05)
    tail.rotation_euler = (0, 0, rot)
H_BAG = TOP_Y - BOT_Y


def pouch_quat(f):
    a1 = 0.0
    for i in range(N_SHEEP):
        tp = T_GATE0 + T_GAP * i - 3
        if f > tp:
            dt = f - tp
            a1 += 0.06 * math.exp(-dt / 14.0) * math.sin(dt * 0.3)
    return POUCH_Q0 @ Quaternion((0, 0, 1), a1)


def pouch_matrix(f):
    return Matrix.Translation(HANG) @ pouch_quat(f).to_matrix().to_4x4()


for f in range(-2, N_FRAMES + 3):
    pouch.rotation_quaternion = pouch_quat(f)
    pouch.keyframe_insert('rotation_quaternion', frame=f)


# ---------------------------------------------------------------- çakıllar: üç katman kalın karton (koyu alt, aşı gövde, açık üst)
def pebble_outline(rx, ry, seed):
    """Düzensiz, yuvarlatılmış çakıl silueti (jeton gibi tam elips olmasın)."""
    r = rng(seed)
    n = 7
    ph = r.uniform(0, 6.28)
    ctrl = [(math.cos(ph + 2 * math.pi * k / n) * rx * r.uniform(0.8, 1.05),
             math.sin(ph + 2 * math.pi * k / n) * ry * r.uniform(0.75, 1.05)) for k in range(n)]
    out = []
    for k in range(n):                       # köşe kesme (Chaikin) ile yumuşat
        p0, p1 = Vector(ctrl[k]), Vector(ctrl[(k + 1) % n])
        out.append(tuple(p0.lerp(p1, 0.25))); out.append(tuple(p0.lerp(p1, 0.75)))
    out2 = []
    for k in range(len(out)):
        p0, p1 = Vector(out[k]), Vector(out[(k + 1) % len(out)])
        out2.append(tuple(p0.lerp(p1, 0.25))); out2.append(tuple(p0.lerp(p1, 0.75)))
    return out2


def pebble(name, seed):
    r = rng(seed)
    root = link(bpy.data.objects.new(name, None))
    root.rotation_mode = 'QUATERNION'
    rx, ry = r.uniform(0.040, 0.047), r.uniform(0.027, 0.033)
    base = pebble_outline(rx, ry, seed)
    lo = piece(name + '_alt', base, 0.008, P_PEBBLE_LO, amp=0.0015, seed=seed)
    lo.parent = root; lo.location = (0.002, -0.004, -0.012)
    mid = piece(name + '_govde', [(x * 0.96, y * 0.96) for (x, y) in base], 0.01, P_PEBBLE, amp=0.0015, seed=seed + 1)
    mid.parent = root; mid.location = (0, 0, -0.003)
    hi = piece(name + '_ust', pebble_outline(rx * 0.42, ry * 0.3, seed + 2), 0.004, P_PEBBLE_HI, amp=0.001, seed=seed + 2)
    hi.parent = root; hi.location = (-rx * 0.25, ry * 0.3, 0.008)
    return root


# ağızdaki yığın (kese yerel ekseninde: X sağ, Y yukarı, Z kameraya). 0 = en son kalan
heap = [Vector((0.0, NECK_Y + 0.016, 0.0))]
for k, (x, y) in enumerate(((-0.05, -0.062), (0.05, -0.06), (-0.028, -0.045), (0.03, -0.043), (-0.06, -0.03),
                            (0.06, -0.028), (-0.012, -0.018), (0.02, -0.01))):
    heap.append(Vector((x, y, -0.006 + 0.003 * k)))
take_order = [8, 7, 6, 5, 4, 3, 2, 1]
pebbles = [pebble('cakil_%d' % k, 3000 + k) for k in range(9)]
LAST = pebbles[0]
LAND = []
_rr = rng(4000)
for k in range(N_SHEEP):
    p = ROW_START + ROW_DIR * (0.092 * k) + Vector((_rr.uniform(-0.006, 0.006), _rr.uniform(-0.006, 0.006)))
    LAND.append(p)
FLIGHT = 22
Q_FACE = M_FACING.to_quaternion()


def qfix(q, prev):
    return -q if (prev is not None and q.dot(prev) < 0) else q


for idx, peb in enumerate(pebbles):
    order = take_order.index(idx) if idx in take_order else None
    t_take = T_GATE0 + T_GAP * order - 3 if order is not None else 10 ** 6
    tilt = rng(6000 + idx).uniform(-0.25, 0.25)
    q_land = Q_FACE @ Quaternion((0, 0, 1), tilt)
    prev_q = None
    for f in range(-2, N_FRAMES + 3):
        if f <= t_take:
            M = pouch_matrix(f) @ Matrix.Translation(heap[idx]) @ Matrix.Rotation(rng(5000 + idx).uniform(-0.5, 0.5), 4, 'Z')
            loc, q, _ = M.decompose()
        else:
            M0 = pouch_matrix(t_take) @ Matrix.Translation(heap[idx])
            p0, q0, _ = M0.decompose()
            L2 = LAND[order]
            p1 = Vector((L2.x, L2.y, SLAB_TOP + 0.03))
            t = min(1.0, (f - t_take) / FLIGHT)
            e = smoother(t)
            if t < 0.28:
                loc = p0 + Vector((0, 0, 0.13 * smoother(t / 0.28)))
            else:
                v = smoother((t - 0.28) / 0.72)
                loc = (p0 + Vector((0, 0, 0.13))).lerp(p1, v) + Vector((0, 0, 0.16 * 4 * v * (1 - v)))
            # uçarken kâğıt jeton gibi bir tur döner
            q = q0.slerp(q_land, e) @ Quaternion((0, 1, 0), 2 * math.pi * e)
            if t >= 1:
                dt = f - t_take - FLIGHT
                loc = p1 + Vector((0, 0, 0.012 * math.exp(-dt / 2.0) * abs(math.sin(dt * 1.3))))
                q = q_land
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


for i, (root, turn, bob, head, legs) in enumerate(sheep):
    prev_s = sheep_s(i, -3)
    face_dir = 1.0
    for f in range(-2, N_FRAMES + 3):
        s = sheep_s(i, f)
        pos, d = paths[i].at(s)
        moving = min(1.0, max(0.0, (s - prev_s) / SPEED))
        prev_s = s
        sx = d.dot(RIGHT)
        if moving > 0.3 and abs(sx) > 1e-4:
            want = 1.0 if sx > 0 else -1.0
            face_dir += max(-0.25, min(0.25, want - face_dir))     # kukla kısa sürede döner (kenardan görünür)
        phase = s / 0.95 * 2 * math.pi + i
        root.matrix_world = Matrix.Translation((pos.x, pos.y, hfun(pos.x, pos.y))) @ M_FACING @ Matrix.Scale(root.scale.x, 4)
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        turn.scale = (face_dir if abs(face_dir) > 0.04 else 0.04, 1, 1)
        turn.keyframe_insert('scale', frame=f)
        # kukla hareketi: zıplama + öne arkaya sallanma (görünüş düzleminde)
        bob.location = (0, 0.035 * abs(math.sin(phase)) * moving, 0)
        bob.rotation_euler = (0, 0, 0.045 * math.sin(phase) * moving)
        bob.keyframe_insert('location', frame=f)
        bob.keyframe_insert('rotation_euler', frame=f)
        head.rotation_euler = (0, 0, -0.1 + 0.08 * math.sin(phase + 1) * moving + (-0.25 + 0.12 * math.sin(f * 0.05 + i)) * (1 - moving))
        head.keyframe_insert('rotation_euler', frame=f)
        for k, leg in enumerate(legs):
            off = 0 if k in (0, 3) else math.pi
            leg.rotation_euler = (0, 0, 0.35 * math.sin(phase + off) * moving)
            leg.keyframe_insert('rotation_euler', frame=f)
print('t anim %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- ışık
world = bpy.data.worlds.new('dunya')
scene.world = world
world.node_tree.nodes['Background'].inputs['Color'].default_value = (1.0, 0.80, 0.58, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.3


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


SUN_AZ = math.radians(193.0)
SUN_EL = math.radians(19.0)
SUN_VEC = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))
light('gunes', 'SUN', 4.6, (1.0, 0.68, 0.40), direction=-SUN_VEC, size=math.radians(4.0))

# ---------------------------------------------------------------- kamera (gerçekçi sürümle aynı vuruşlar)
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
    return (pouch_matrix(f) @ Matrix.Translation(heap[0])).to_translation()


P_END = last_world(N_FRAMES)
_g3 = Vector((GATE_PT.x, GATE_PT.y, hfun(GATE_PT.x, GATE_PT.y) + 0.55))
MID = _g3.lerp(HANG - Vector((0, 0, 0.35)), 0.5)
_row3 = Vector((ROW_CENTER.x, ROW_CENTER.y, hfun(ROW_CENTER.x, ROW_CENTER.y)))
TGT0 = MID.lerp(_row3, 0.3) + RIGHT3 * 0.25 + Vector((0, 0, 0.1))
TGT1 = TGT0 + Vector((-0.08, -0.05, 0.0))
CAM1 = CAM_POS0 + (TGT0 - CAM_POS0).normalized() * 0.35
# son: keseye önden, hafif yukarıdan ve sağdan
CAM_END = P_END + (FACE3 * 0.95 - RIGHT3 * 0.12 + Vector((0, 0, 0.2))).normalized() * 1.05
FOCUS0 = _g3.lerp(HANG - Vector((0, 0, 0.3)), 0.6)
PUSH0, PUSH1 = 212, 296
for f in range(-2, N_FRAMES + 3):
    t0 = max(0.0, min(1.0, (f - 1) / (PUSH0 - 1)))
    cpos = CAM_POS0.lerp(CAM1, t0)
    tpos = TGT0.lerp(TGT1, t0)
    e = smoother((f - PUSH0) / (PUSH1 - PUSH0))
    cpos = cpos.lerp(CAM_END, e)
    tpos = tpos.lerp(P_END + Vector((0, 0, -0.03)), e)
    cpos = cpos + Vector((0.004 * math.sin(f * 0.041), 0.0, 0.003 * math.sin(f * 0.057 + 1)))
    cam.location = cpos
    cam.keyframe_insert('location', frame=f)
    target.location = tpos
    target.keyframe_insert('location', frame=f)
    focus = FOCUS0.lerp(P_END, smoother((f - PUSH0 + 10) / (PUSH1 - PUSH0 - 10)))
    cam_data.dof.focus_distance = (cpos - focus).length
    cam_data.dof.keyframe_insert('focus_distance', frame=f)
    cam_data.dof.aperture_fstop = 1.6 - 0.5 * e          # masa üstü maket hissi: sığ alan derinliği
    cam_data.dof.keyframe_insert('aperture_fstop', frame=f)
    cam_data.lens = 35 + 15 * e
    cam_data.keyframe_insert('lens', frame=f)

# ---------------------------------------------------------------- parıltı: son çakılda küçük, sıcak, yumuşak dört kollu yıldız
glint = light('parilti', 'POINT', 0.0, (1.0, 0.8, 0.5), loc=P_END + FACE3 * 0.2 + Vector((0, 0, 0.15)), size=0.03)
glint.visible_camera = False
for f, en in ((1, 0.0), (258, 0.0), (278, 0.5), (300, 0.4)):
    glint.data.energy = en
    glint.data.keyframe_insert('energy', frame=f)
b2 = bmesh.new()
bmesh.ops.create_icosphere(b2, subdivisions=2, radius=0.0035)
me = bpy.data.meshes.new('parilti_nokta'); b2.to_mesh(me); b2.free()
spark = link(bpy.data.objects.new('parilti_nokta', me))
M_SPARK = emissive('parilti_mat', (1.0, 0.86, 0.6), 0.0)
spark.data.materials.append(M_SPARK)
spark.parent = LAST
spark.location = (0.018, 0.02, 0.016)
for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission'):
    setattr(spark, attr, False)
_sp = M_SPARK.node_tree.nodes['Emission'].inputs['Strength']
for f, v in ((1, 0.0), (262, 0.0), (272, 260.0), (281, 120.0), (290, 210.0), (300, 150.0)):
    _sp.default_value = v
    _sp.keyframe_insert('default_value', frame=f)

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
                print('GPU:', dt, [d.name for d in gpus])
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
C.max_bounces = 6
C.diffuse_bounces = 3
C.glossy_bounces = 1
C.transmission_bounces = 2
C.transparent_max_bounces = 4
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.seed = 7
C.sample_clamp_indirect = 6.0
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = bool(A.bulanik)
R.motion_blur_shutter = 0.35
R.use_persistent_data = True
vs = scene.view_settings
vs.view_transform = 'AgX'
vs.look = 'AgX - High Contrast'
vs.exposure = -0.1

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
for _f in (1, 110, 210):
    scene.frame_set(_f)
    for _nm, _p in (('kapi', _g3), ('kese', HANG), ('dizi_bas', LAND[0].to_3d() + Vector((0, 0, SLAB_TOP))),
                    ('dizi_son', LAND[-1].to_3d() + Vector((0, 0, SLAB_TOP)))):
        _c = world_to_camera_view(scene, cam, _p)
        print('KADRAJ f%d %-8s x=%.2f y(ust)=%.2f' % (_f, _nm, _c.x, 1 - _c.y))
    _c = world_to_camera_view(scene, cam, sheep[0][0].matrix_world.to_translation() + Vector((0, 0, 0.6)))
    print('KADRAJ f%d koyun0   x=%.2f y(ust)=%.2f' % (_f, _c.x, 1 - _c.y))
print('sahne kuruldu: %.1f sn' % (time.time() - T_START), flush=True)
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(A.cikti), 'kagit.blend'))

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
