# Math with Zirek · sahne G (akşam, koyunlar girer, taş çıkar, tek taş kalır) · İKİ TARZ, TEK BETİK
#   suluboya  : suluboya / masal kitabı: yumuşak boya lekeleri, kâğıt greni, kenarda biriken boya, taşan kenarlar
#   resimli3d : fırçayla boyanmış 3B (Arcane benzeri): 3B biçim + fırça darbeli dokular, stilize ışık, sıcak sinematik
# Tarz, betiğin bulunduğu klasörün adından seçilir (suluboya/sahne.py ile resimli3d/sahne.py aynı dosyadır);
# --stil ile de verilebilir. Blender 5.2, Cycles CPU. Tamamen yordamsal: dış varlık yok.
# Yöntem: Cycles yalnız "ham" geçişleri üretir (yüzey rengi, doğrudan+dolaylı ışık, derinlik, sis, ışıma);
# resim, kompozitte bu geçişlerden boyanır: ışık bir renk rampasıyla boya tonlarına çevrilir, sonra Kuwahara
# (boya lekesi filtresi), kâğıt/boya yoğunluğu, kenar koyulaşması, çizgi ve parıltı eklenir.
# Yerleşim, zamanlama ve kamera vuruşları kil sürümüyle (../sahne.py) aynı; kese, çakıl dizisi büyütüldü ve
# yassı bir taşın üstüne alındı (karşılaştırma dersi: geniş planda telefonda okunmalı).
# Kullanım (yalnız bulutta):
#   blender -b -P sahne.py -- --mod kare --kareler 68,180,290 --w 960 --h 540 --ornek 32 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 60 --cikti out            (1920x1080)
import bpy, bmesh, math, random, sys, os, time, argparse
from mathutils import Vector, Matrix, Quaternion, Euler, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--mod', default='kare')          # kare | parca | kur (yalnız kurulum, render yok)
ap.add_argument('--kareler', default='68,180,290')
ap.add_argument('--bas', type=int, default=1)
ap.add_argument('--son', type=int, default=300)
ap.add_argument('--w', type=int, default=1920)
ap.add_argument('--h', type=int, default=1080)
ap.add_argument('--ornek', type=int, default=64)
ap.add_argument('--cikti', default='out')
ap.add_argument('--cihaz', default='cpu')
ap.add_argument('--bulanik', type=int, default=1)
ap.add_argument('--stil', default='')
ap.add_argument('--gecis', action='store_true')    # hata ayıklama: ham geçişleri de yaz
ap.add_argument('--blend', action='store_true')
A = ap.parse_args(argv)
T_START = time.time()


def _script_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


STIL = A.stil or os.path.basename(_script_dir())
if STIL not in ('suluboya', 'resimli3d'):
    STIL = 'suluboya'
SU = STIL == 'suluboya'
print('STIL', STIL, flush=True)

FPS = 30
N_FRAMES = 300
N_SHEEP = 8
T_GATE0 = 40          # ilk koyunun kapıdan geçtiği kare
T_GAP = 22            # koyunlar arası (0,73 sn)
SPEED = 0.95 / FPS    # birim/kare

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


def lin(c):
    """sRGB (0-1) -> doğrusal renk."""
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ---------------------------------------------------------------- arazi
PEN_C = Vector((0.3, 1.2))
PEN_R = 1.4
GATE_ANG = math.radians(228)
GAP_HALF = 0.26


def hfun(x, y):
    d = (Vector((x, y)) - PEN_C).length
    flat = smooth(1.8, 3.6, d)
    h = 0.55 * smooth(3.5, 13.0, y)
    h += flat * (0.07 * math.sin(0.55 * x + 0.3) * math.cos(0.42 * y + 0.8)
                 + 0.03 * math.sin(1.3 * x - 0.7 * y))
    h += 0.012 * noise.noise(Vector((x * 0.9, y * 0.9, 3.1)))
    return h


def link(ob):
    scene.collection.objects.link(ob)
    return ob


def bm_to_obj(name, bm, smooth_shade=True):
    if smooth_shade:
        for f in bm.faces:
            f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    return link(ob)


def add_subsurf(ob, render=2, view=0):
    m = ob.modifiers.new('ss', 'SUBSURF')
    m.levels = view
    m.render_levels = render
    return m


def bake_modifiers(ob):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    ob.data = me


def blob(bm, center, radii, subdiv=3, amp=0.0, nscale=4.0, seed=0, rot=None):
    """bm'ye gürültülü elipsoid ekler."""
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=subdiv, radius=1.0)
    off = Vector((seed * 7.31, seed * 3.17, seed * 5.93))
    R = rot.to_matrix() if rot is not None else Matrix.Identity(3)
    for v in tmp.verts:
        n = v.co.normalized()
        d = 1.0 + amp * noise.noise(n * nscale + off)
        p = Vector((n.x * radii[0], n.y * radii[1], n.z * radii[2])) * d
        v.co = R @ p + Vector(center)
    me = bpy.data.meshes.new('tmp')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


# ---------------------------------------------------------------- malzemeler (yalnız yüzey rengi; ışığı kompozit boyar)
def paint(name, color, var=0.08, patch=3.0, spread=0.10, strokes=None, bump=0.0, coord='Object'):
    """color: sRGB. Yüzey rengi = renk x (nesne başına küçük fark) x (boya lekesi / fırça darbesi deseni).
    suluboya: yumuşak, geniş leke (ıslak üstüne ıslak); resimli3d: yönü parça parça değişen fırça darbeleri."""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    for n in list(N):
        if n.type != 'OUTPUT_MATERIAL':
            N.remove(n)
    out = [n for n in N if n.type == 'OUTPUT_MATERIAL'][0]
    bs = N.new('ShaderNodeBsdfDiffuse')
    L.new(bs.outputs[0], out.inputs['Surface'])
    tc = N.new('ShaderNodeTexCoord')
    oi = N.new('ShaderNodeObjectInfo')
    co = tc.outputs[coord]
    # nesne başına ton farkı
    vr = N.new('ShaderNodeMath'); vr.operation = 'MULTIPLY_ADD'
    vr.inputs[1].default_value = var; vr.inputs[2].default_value = 1.0 - var / 2
    L.new(oi.outputs['Random'], vr.inputs[0])
    base = N.new('ShaderNodeMix'); base.data_type = 'RGBA'; base.blend_type = 'MULTIPLY'
    base.inputs[0].default_value = 1.0
    base.inputs[6].default_value = (*lin(color), 1.0)
    L.new(vr.outputs[0], base.inputs[7])
    col = base.outputs[2]
    if strokes is None:
        # suluboya: geniş, yumuşak leke; soğuk-koyu ile sıcak-açık arası
        nz = N.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = patch
        nz.inputs['Detail'].default_value = 3.0
        nz.inputs['Roughness'].default_value = 0.55
        nz.inputs['Distortion'].default_value = 0.6
        L.new(co, nz.inputs['Vector'])
        rp = N.new('ShaderNodeValToRGB')
        rp.color_ramp.interpolation = 'EASE'
        rp.color_ramp.elements[0].position = 0.3
        rp.color_ramp.elements[0].color = (1 - spread * 1.1, 1 - spread * 0.9, 1 - spread * 0.4, 1)
        rp.color_ramp.elements[1].position = 0.72
        rp.color_ramp.elements[1].color = (1 + spread * 0.5, 1 + spread * 0.3, 1 - spread * 0.1, 1)
        L.new(nz.outputs[0], rp.inputs[0])
        mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'
        mm.inputs[0].default_value = 1.0
        L.new(col, mm.inputs[6]); L.new(rp.outputs[0], mm.inputs[7])
        col = mm.outputs[2]
        height = None
    else:
        # resimli3d: fırça darbeleri. Voronoi hücreleri = darbe öbekleri; her öbekte darbe yönü rastgele;
        # gürültü tek yönde uzatılır (darbe); basamaklı rampa = üç boya tonu (koyu-soğuk, orta, açık-sıcak).
        sc, stretch = strokes
        vo = N.new('ShaderNodeTexVoronoi')
        vo.inputs['Scale'].default_value = sc * 0.35
        vo.inputs['Randomness'].default_value = 1.0
        L.new(co, vo.inputs['Vector'])
        vm = N.new('ShaderNodeVectorMath'); vm.operation = 'SCALE'
        vm.inputs['Scale'].default_value = 6.283
        L.new(vo.outputs['Color'], vm.inputs[0])
        mp = N.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (1.0, stretch, 1.0)
        L.new(co, mp.inputs['Vector'])
        L.new(vm.outputs[0], mp.inputs['Rotation'])
        nz = N.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = sc
        nz.inputs['Detail'].default_value = 2.0
        nz.inputs['Roughness'].default_value = 0.5
        nz.inputs['Distortion'].default_value = 0.35
        L.new(mp.outputs['Vector'], nz.inputs['Vector'])
        # geniş boya alanları (büyük ölçek ton değişimi)
        nb = N.new('ShaderNodeTexNoise')
        nb.inputs['Scale'].default_value = patch
        nb.inputs['Detail'].default_value = 2.0
        L.new(co, nb.inputs['Vector'])
        ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'
        ad.inputs[1].default_value = 0.55
        L.new(nb.outputs[0], ad.inputs[0]); L.new(nz.outputs[0], ad.inputs[2])
        ad2 = N.new('ShaderNodeMath'); ad2.operation = 'SUBTRACT'
        ad2.inputs[1].default_value = 0.27
        L.new(ad.outputs[0], ad2.inputs[0])
        rp = N.new('ShaderNodeValToRGB')
        rp.color_ramp.interpolation = 'CONSTANT'
        e = rp.color_ramp.elements
        e[0].position = 0.0; e[0].color = (1 - spread * 1.3, 1 - spread * 1.0, 1 - spread * 0.35, 1)
        e[1].position = 0.40; e[1].color = (1.0, 1.0, 1.0, 1)
        e3 = e.new(0.62); e3.color = (1 + spread * 0.7, 1 + spread * 0.45, 1 + spread * 0.05, 1)
        e4 = e.new(0.80); e4.color = (1 + spread * 1.2, 1 + spread * 0.9, 1 + spread * 0.3, 1)
        L.new(ad2.outputs[0], rp.inputs[0])
        mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'
        mm.inputs[0].default_value = 1.0
        L.new(col, mm.inputs[6]); L.new(rp.outputs[0], mm.inputs[7])
        col = mm.outputs[2]
        height = ad2.outputs[0]
    L.new(col, bs.inputs['Color'])
    if bump > 0 and height is not None:
        bn = N.new('ShaderNodeBump')
        bn.inputs['Strength'].default_value = bump
        bn.inputs['Distance'].default_value = 0.004
        L.new(height, bn.inputs['Height'])
        L.new(bn.outputs['Normal'], bs.inputs['Normal'])
    return m


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    N = nt.nodes
    for n in list(N):
        if n.type != 'OUTPUT_MATERIAL':
            N.remove(n)
    out = [n for n in N if n.type == 'OUTPUT_MATERIAL'][0]
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1.0)
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def setmat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


# palet (sRGB). Kanal: sıcak krem / aşı / yeşil; soğuk ya da karanlık renk alınmaz.
# Okunaklılık: çakıl sıcak aşı-turuncu, yassı taş serin açık gri-mavi, kese kök boya kırmızısı, duvar nötr gri.
if SU:
    ST = None
    M_GRASS = paint('cim', (0.60, 0.70, 0.34), var=0.0, patch=0.9, spread=0.16)
    M_TUFT = paint('ot', (0.40, 0.56, 0.24), var=0.12, patch=2.0, spread=0.12)
    M_STONE = paint('tas_duvar', (0.70, 0.66, 0.62), var=0.28, patch=5.0, spread=0.16)
    M_WOOL = paint('yun', (0.97, 0.93, 0.84), var=0.05, patch=6.0, spread=0.06)
    M_FACE = paint('yuz', (0.30, 0.25, 0.24), var=0.10, patch=8.0, spread=0.12)
    M_EYE = paint('goz', (0.97, 0.95, 0.90), var=0.0, patch=8.0, spread=0.02)
    M_PUPIL = paint('bebek', (0.10, 0.08, 0.08), var=0.0, spread=0.0)
    M_WOOD = paint('tahta', (0.52, 0.36, 0.22), var=0.15, patch=12.0, spread=0.12)
    M_CLOTH = paint('bez', (0.72, 0.28, 0.20), var=0.0, patch=9.0, spread=0.14)
    M_CORD = paint('ip', (0.90, 0.82, 0.62), var=0.0, spread=0.05)
    M_PEBBLE = paint('cakil', (0.93, 0.62, 0.30), var=0.12, patch=30.0, spread=0.12)
    M_SLAB = paint('yassi_tas', (0.70, 0.74, 0.80), var=0.0, patch=4.0, spread=0.12)
    M_HILL1 = paint('tepe1', (0.56, 0.66, 0.36), var=0.0, patch=0.35, spread=0.18)
    M_HILL2 = paint('tepe2', (0.86, 0.70, 0.42), var=0.0, patch=0.35, spread=0.16)
    M_HILL3 = paint('tepe3', (0.72, 0.76, 0.62), var=0.0, patch=0.3, spread=0.14)
    M_LEAF = paint('yaprak', (0.40, 0.56, 0.26), var=0.1, patch=2.5, spread=0.2)
    M_TRUNK = paint('govde', (0.55, 0.40, 0.28), var=0.1, patch=6.0, spread=0.12)
    M_FLOWER = paint('cicek', (0.99, 0.92, 0.66), var=0.2, spread=0.05)
else:
    M_GRASS = paint('cim', (0.46, 0.60, 0.26), var=0.0, patch=0.8, spread=0.20, strokes=(9.0, 5.0))
    M_TUFT = paint('ot', (0.34, 0.50, 0.20), var=0.14, patch=2.0, spread=0.18, strokes=(40.0, 4.0))
    M_STONE = paint('tas_duvar', (0.62, 0.58, 0.55), var=0.30, patch=5.0, spread=0.18, strokes=(34.0, 3.0), bump=0.25)
    M_WOOL = paint('yun', (0.96, 0.91, 0.80), var=0.05, patch=6.0, spread=0.12, strokes=(38.0, 3.5), bump=0.15)
    M_FACE = paint('yuz', (0.26, 0.20, 0.19), var=0.10, patch=8.0, spread=0.18, strokes=(60.0, 3.0))
    M_EYE = paint('goz', (0.97, 0.95, 0.90), var=0.0, spread=0.02)
    M_PUPIL = paint('bebek', (0.08, 0.06, 0.06), var=0.0, spread=0.0)
    M_WOOD = paint('tahta', (0.55, 0.36, 0.20), var=0.15, patch=12.0, spread=0.18, strokes=(60.0, 6.0))
    M_CLOTH = paint('bez', (0.70, 0.24, 0.17), var=0.0, patch=9.0, spread=0.18, strokes=(55.0, 4.0), bump=0.1)
    M_CORD = paint('ip', (0.90, 0.80, 0.58), var=0.0, spread=0.08)
    M_PEBBLE = paint('cakil', (0.94, 0.60, 0.26), var=0.12, patch=30.0, spread=0.14, strokes=(90.0, 2.5))
    M_SLAB = paint('yassi_tas', (0.62, 0.67, 0.74), var=0.0, patch=4.0, spread=0.16, strokes=(22.0, 4.0))
    M_HILL1 = paint('tepe1', (0.44, 0.58, 0.30), var=0.0, patch=0.35, spread=0.2, strokes=(2.5, 5.0))
    M_HILL2 = paint('tepe2', (0.84, 0.64, 0.34), var=0.0, patch=0.35, spread=0.2, strokes=(2.5, 5.0))
    M_HILL3 = paint('tepe3', (0.66, 0.70, 0.58), var=0.0, patch=0.3, spread=0.16, strokes=(1.8, 5.0))
    M_LEAF = paint('yaprak', (0.34, 0.50, 0.22), var=0.1, patch=2.5, spread=0.22, strokes=(14.0, 3.0))
    M_TRUNK = paint('govde', (0.50, 0.34, 0.22), var=0.1, patch=6.0, spread=0.16, strokes=(30.0, 7.0))
    M_FLOWER = paint('cicek', (0.99, 0.90, 0.60), var=0.2, spread=0.05)
M_LAST = M_PEBBLE
M_SHINE = emissive('goz_isik', (1.0, 0.97, 0.9), 6.0)          # gözdeki küçük ışık noktası


# ---------------------------------------------------------------- zemin
def build_ground():
    bm = bmesh.new()
    x0, x1, y0, y1 = -14.0, 14.0, -7.0, 16.0
    nx, ny = 200, 170
    verts = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            row.append(bm.verts.new((x, y, hfun(x, y))))
        verts.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    ob = bm_to_obj('zemin', bm)
    setmat(ob, M_GRASS)


def ring_pos(a, r=PEN_R):
    return Vector((PEN_C.x + r * math.cos(a), PEN_C.y + r * math.sin(a)))


def ang_dist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def build_tufts(avoid):
    r = rng(11)
    bm = bmesh.new()
    count = 0
    tries = 0
    while count < 340 and tries < 20000:
        tries += 1
        if r.random() < 0.85:
            a = r.uniform(0, 2 * math.pi)
            if ang_dist(a, GATE_ANG) < GAP_HALF + 0.05:
                continue
            rr = PEN_R + (r.uniform(0.07, 0.2) if r.random() < 0.6 else -r.uniform(0.07, 0.14))
            x, y = PEN_C.x + rr * math.cos(a), PEN_C.y + rr * math.sin(a)
        else:
            x = r.uniform(-4.0, 3.5)
            y = r.uniform(-2.8, 3.0)
        if x > 0.6 and y < -0.6 and r.random() < 0.9:       # sağ alt üçte bir sakin
            continue
        if any(f(Vector((x, y))) for f in avoid):
            continue
        count += 1
        z = hfun(x, y)
        big = r.random() < 0.35
        for b in range(r.randint(6, 10) if big else r.randint(3, 5)):
            h = r.uniform(0.045, 0.1) if big else r.uniform(0.03, 0.06)
            tilt = Euler((r.uniform(-0.45, 0.45), r.uniform(-0.45, 0.45), r.uniform(0, 6.28))).to_matrix().to_4x4()
            base = Matrix.Translation((x + r.uniform(-0.02, 0.02), y + r.uniform(-0.02, 0.02), z - 0.004))
            M = base @ tilt @ Matrix.Translation((0, 0, h / 2))
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=5,
                                  radius1=0.011, radius2=0.0015, depth=h, matrix=M)
    ob = bm_to_obj('otlar', bm)
    setmat(ob, M_TUFT)
    bm = bmesh.new()
    k = 0
    while k < 70:
        x = r.uniform(-6, 5); y = r.uniform(-3.5, 7)
        if x > 1.2 and y < -1.0:
            continue
        if (Vector((x, y)) - PEN_C).length < PEN_R + 0.3 or any(f(Vector((x, y))) for f in avoid):
            continue
        k += 1
        blob(bm, (x, y, hfun(x, y) + 0.05), (0.014, 0.014, 0.01), subdiv=2, seed=k)
    ob = bm_to_obj('cicekler', bm)
    setmat(ob, M_FLOWER)


# ---------------------------------------------------------------- ağıl
def stone(name, loc, radii, yaw, seed, tilt=0.12, ss=0):
    r = rng(seed)
    bm = bmesh.new()
    rot = Euler((r.uniform(-tilt, tilt), r.uniform(-tilt, tilt), yaw))
    blob(bm, (0, 0, 0), radii, subdiv=3, amp=0.24, nscale=1.4, seed=seed, rot=rot)
    ob = bm_to_obj(name, bm)
    ob.location = loc
    if ss:
        add_subsurf(ob, ss, 0)
    setmat(ob, M_STONE)
    return ob


def build_pen():
    r = rng(21)
    n = int(2 * math.pi * PEN_R / 0.14)
    sid = 0
    for course in range(5):
        for j in range(n):
            a = (j + 0.5 * course + r.uniform(-0.12, 0.12)) * 2 * math.pi / n
            if ang_dist(a, GATE_ANG) < GAP_HALF + 0.12:
                continue
            p = ring_pos(a, PEN_R + r.uniform(-0.02, 0.02))
            if course == 4 and r.random() < 0.2:
                continue
            sx = r.uniform(0.064, 0.09) * (0.88 if course == 4 else 1.0)
            sy = r.uniform(0.05, 0.066)
            sz = r.uniform(0.036, 0.046)
            z = hfun(p.x, p.y) + 0.035 + course * 0.071 + r.uniform(-0.007, 0.007)
            stone('tas_%03d' % sid, (p.x, p.y, z), (sx, sy, sz), a + math.pi / 2 + r.uniform(-0.15, 0.15), 100 + sid)
            sid += 1
    posts = []
    for side, sgn in (('on', 1), ('arka', -1)):
        a = GATE_ANG + sgn * (GAP_HALF + 0.02)
        p = ring_pos(a)
        posts.append((side, a, p))
        z = hfun(p.x, p.y) + 0.06
        for k in range(7):
            rr = r.uniform(0.11, 0.13) - k * 0.006
            hz = r.uniform(0.045, 0.055)
            stone('direk_%s_%d' % (side, k), (p.x + r.uniform(-0.015, 0.015), p.y + r.uniform(-0.015, 0.015), z),
                  (rr, rr * 0.92, hz), r.uniform(0, 6.28), 500 + k + (0 if sgn > 0 else 50), tilt=0.08, ss=2)
            z += hz * 1.75
    return posts


# ---------------------------------------------------------------- kese
CAM_POS0 = Vector((1.0, -3.9, 1.7))
POUCH_S = 1.35            # kil sürümünden büyük: geniş planda telefonda okunsun


def build_pouch(front_post):
    _, a, p = front_post
    to_cam = (CAM_POS0.xy - p).normalized()
    pegdir = Vector((to_cam.x, to_cam.y, 0.18)).normalized()
    z_top = hfun(p.x, p.y) + 0.06 + 0.05 * 1.75 * 6
    peg_base = Vector((p.x, p.y, z_top - 0.05))
    peg_len = 0.3
    bm = bmesh.new()
    q = Vector((0, 0, 1)).rotation_difference(pegdir)
    blob(bm, (peg_base + pegdir * (peg_len / 2))[:], (0.018, 0.018, peg_len / 2), subdiv=3, amp=0.05, nscale=2.0,
         seed=77, rot=q)
    peg = bm_to_obj('civi', bm)
    add_subsurf(peg, 1, 0)
    setmat(peg, M_WOOD)
    hang = peg_base + pegdir * (peg_len - 0.03) + Vector((0, 0, 0.012))
    prof = [(0.0, 0.0), (0.06, 0.004), (0.095, 0.02), (0.115, 0.05), (0.12, 0.085), (0.112, 0.12),
            (0.09, 0.15), (0.064, 0.171), (0.05, 0.182), (0.054, 0.192), (0.066, 0.205), (0.078, 0.218),
            (0.084, 0.228)]
    DROP = 0.36
    seg = 40
    bm = bmesh.new()
    rings = []
    bottom = bm.verts.new((0, 0, -DROP))
    for (rr, zz) in prof[1:]:
        ring = []
        for s in range(seg):
            th = 2 * math.pi * s / seg
            gather = smooth(0.13, 0.18, zz)
            fold = gather * (0.0025 * math.sin(11 * th + 1.3) + 0.007 * noise.noise(Vector((math.cos(th) * 3.0, math.sin(th) * 3.0, zz * 25))))
            crease = (1 - gather) * smooth(0.06, 0.15, zz) * 0.006 * math.sin(6 * th + 0.4 + 2 * noise.noise(Vector((th, 0.3, 2.2))))
            wob = 0.012 * noise.noise(Vector((math.cos(th) * 2.6, math.sin(th) * 2.6, zz * 12)))
            r2 = rr + fold + crease + wob * (rr / 0.1)
            if zz < 0.1:
                r2 += 0.008 * max(0.0, math.cos(th - 0.3))
            dz = smooth(0.2, 0.228, zz) * (0.002 * math.sin(11 * th + 1.3) + 0.009 * noise.noise(Vector((math.cos(th) * 2.0, math.sin(th) * 2.0, 5.1))))
            ring.append(bm.verts.new((r2 * math.cos(th) * 1.05, r2 * math.sin(th) * 0.95, zz - DROP + dz)))
        rings.append(ring)
    for s in range(seg):
        bm.faces.new((bottom, rings[0][s], rings[0][(s + 1) % seg]))
    for k in range(len(rings) - 1):
        for s in range(seg):
            bm.faces.new((rings[k][s], rings[k + 1][s], rings[k + 1][(s + 1) % seg], rings[k][(s + 1) % seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pouch = bm_to_obj('kese', bm)
    sol = pouch.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.01
    add_subsurf(pouch, 2, 0)
    setmat(pouch, M_CLOTH)
    pouch.location = hang
    pouch.rotation_mode = 'QUATERNION'
    tilt_axis = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    base_q = Quaternion(tilt_axis, math.radians(-22))
    pouch.rotation_quaternion = base_q
    pouch.scale = (POUCH_S, POUCH_S, POUCH_S)

    def curve(name, pts, cyclic=False, bevel=0.005):
        cu = bpy.data.curves.new(name, 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = bevel
        cu.bevel_resolution = 3
        try:
            cu.use_fill_caps = True
        except Exception:
            pass
        sp = cu.splines.new('NURBS')
        sp.points.add(len(pts) - 1)
        for i, pt in enumerate(pts):
            sp.points[i].co = (pt[0], pt[1], pt[2], 1.0)
        sp.use_cyclic_u = cyclic
        sp.use_endpoint_u = not cyclic
        sp.order_u = 3
        ob = bpy.data.objects.new(name, cu)
        link(ob)
        ob.data.materials.append(M_CORD)
        ob.parent = pouch
        return ob
    zt = 0.228 - DROP
    side = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    inv = base_q.inverted()
    sl = inv @ side
    zb = 0.182 - DROP
    back = inv @ Vector((-to_cam.x, -to_cam.y, 0)).normalized()
    curve('ip_aski', [(back * 0.052 + Vector((0, 0, zb)))[:], (back * 0.05 + Vector((0, 0, zb + 0.05)))[:],
                      (back * 0.02 + Vector((0, 0, -0.01)))[:], (0, 0, 0.0)], bevel=0.0055)
    fr = -back
    curve('ip_uc', [(fr * 0.056 + sl * 0.01 + Vector((0, 0, zb)))[:], (fr * 0.066 + sl * 0.02 + Vector((0, 0, zb - 0.03)))[:],
                    (fr * 0.07 + sl * 0.015 + Vector((0, 0, zb - 0.06)))[:]], bevel=0.004)
    curve('ip_bogaz', [(0.056 * math.cos(2 * math.pi * s / 10) * 1.05, 0.056 * math.sin(2 * math.pi * s / 10) * 0.95,
                        zb + 0.004 * math.sin(3 * s)) for s in range(10)], cyclic=True, bevel=0.0065)
    return pouch, base_q, hang, pegdir, zt


PEB_R = (0.05, 0.043, 0.03)     # kil sürümünden ~%15 büyük


def pebble_mesh(name, seed, mat):
    r = rng(seed)
    bm = bmesh.new()
    blob(bm, (0, 0, 0), (PEB_R[0] * r.uniform(0.94, 1.04), PEB_R[1] * r.uniform(0.94, 1.04), PEB_R[2] * r.uniform(0.92, 1.05)),
         subdiv=3, amp=0.12, nscale=1.3, seed=seed)
    ob = bm_to_obj(name, bm)
    add_subsurf(ob, 1, 0)
    setmat(ob, mat)
    ob.rotation_mode = 'QUATERNION'
    return ob


# ---------------------------------------------------------------- koyun
def build_sheep(i):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('koyun_%d' % i, None))
    bob = link(bpy.data.objects.new('koyun_%d_govde' % i, None))
    bob.parent = root
    s = r.uniform(0.82, 0.92)
    root.scale = (s, s, s)
    # yün: çekirdek + iri yüzey topakları (siluet dalgalı, bulut gibi), vokselle birleştirilir
    bm = bmesh.new()
    blob(bm, (0, 0, 0.25), (0.22, 0.135, 0.12), subdiv=3, seed=i)
    for k in range(30):
        u = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
        if u.z < -0.4:
            u.z = -0.4
        pos = Vector((u.x * 0.215, u.y * 0.135, u.z * 0.12 + 0.25))
        rad = r.uniform(0.06, 0.085)
        blob(bm, pos[:], (rad, rad, rad * 0.9), subdiv=2, seed=i * 50 + k)
    blob(bm, (0.2, 0, 0.365), (0.06, 0.055, 0.05), subdiv=2, seed=i + 300)      # başta yün perçem
    blob(bm, (-0.25, 0, 0.29), (0.045, 0.04, 0.04), subdiv=2, seed=i + 400)    # kuyruk
    wool = bm_to_obj('koyun_%d_yun' % i, bm)
    rm = wool.modifiers.new('rm', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = 0.012
    sm = wool.modifiers.new('sm', 'SMOOTH')
    sm.factor = 0.7
    sm.iterations = 5
    bake_modifiers(wool)
    for pl in wool.data.polygons:
        pl.use_smooth = True
    setmat(wool, M_WOOL)
    wool.parent = bob
    # baş: yumuşak, biraz iri (sevimli oran), burun yuvarlak
    bm = bmesh.new()
    blob(bm, (0.055, 0, 0.0), (0.09, 0.07, 0.078), subdiv=3, amp=0.03, seed=i + 500)
    blob(bm, (0.125, 0, -0.035), (0.064, 0.054, 0.05), subdiv=3, amp=0.03, seed=i + 510)
    head = bm_to_obj('koyun_%d_bas' % i, bm)
    add_subsurf(head, 1, 0)
    setmat(head, M_FACE)
    head.parent = bob
    head.location = (0.2, 0, 0.3)
    head.rotation_euler = (0, math.radians(18), 0)
    for sgn in (1, -1):
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.055, 0.022, 0.017), subdiv=2, seed=i + 520 + sgn)
        ear = bm_to_obj('koyun_%d_kulak' % i, bm)
        add_subsurf(ear, 1, 0)
        setmat(ear, M_FACE)
        ear.parent = head
        ear.location = (0.0, sgn * 0.08, 0.035)
        ear.rotation_euler = (sgn * 0.5, 0.25, sgn * 1.25)
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.021, 0.021, 0.021), subdiv=2)
        eye = bm_to_obj('koyun_%d_goz' % i, bm)
        add_subsurf(eye, 1, 0)
        setmat(eye, M_EYE)
        eye.parent = head
        eye.location = (0.1, sgn * 0.04, 0.032)
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.012, 0.012, 0.012), subdiv=2)
        pu = bm_to_obj('koyun_%d_bebek' % i, bm)
        setmat(pu, M_PUPIL)
        pu.parent = eye
        pu.location = (0.013, sgn * 0.006, 0.002)
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.0035, 0.0035, 0.0035), subdiv=1)
        sh = bm_to_obj('koyun_%d_isik' % i, bm)
        setmat(sh, M_SHINE)
        sh.parent = eye
        sh.location = (0.021, sgn * 0.004, 0.008)
        for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy'):
            setattr(sh, attr, False)
    legs = []
    for k, (lx, ly) in enumerate(((0.13, 0.075), (0.13, -0.075), (-0.13, 0.075), (-0.13, -0.075))):
        bm = bmesh.new()
        blob(bm, (0, 0, -0.075), (0.027, 0.027, 0.09), subdiv=3, amp=0.03, seed=i * 10 + k)
        blob(bm, (0.005, 0, -0.152), (0.031, 0.029, 0.018), subdiv=2, seed=i * 10 + k + 5)
        leg = bm_to_obj('koyun_%d_bacak_%d' % (i, k), bm)
        add_subsurf(leg, 1, 0)
        setmat(leg, M_FACE)
        leg.parent = bob
        leg.location = (lx, ly, 0.165)
        legs.append(leg)
    return root, bob, head, legs


# ---------------------------------------------------------------- yol (Catmull-Rom)
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
        self.p = catmull([Vector(q) for q in pts], 30)
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


# ---------------------------------------------------------------- sahneyi kur
build_ground()
posts = build_pen()
front_post = [p for p in posts if p[0] == 'on'][0]
pouch, pouch_q0, HANG, PEGDIR, LIP_Z = build_pouch(front_post)
_, FA, FP = front_post

# çakıl dizisi: kesenin önünde (kameraya doğru), serin açık renk yassı bir taşın üstünde, ekranda sağa doğru
TO_CAM0 = (CAM_POS0.xy - FP).normalized()
RIGHT = Vector((-TO_CAM0.y, TO_CAM0.x))
ROW_GAP = 0.125
ROW_START = HANG.xy + TO_CAM0 * 0.36 - RIGHT * 0.2
ROW_DIR = RIGHT
ROW_CENTER = ROW_START + ROW_DIR * (ROW_GAP * 3.5)
_zc = hfun(ROW_CENTER.x, ROW_CENTER.y)
SLAB_TOP = _zc + 0.04
bm = bmesh.new()
blob(bm, (0, 0, 0), (ROW_GAP * 4.6, 0.19, 0.05), subdiv=4, amp=0.10, nscale=1.6, seed=55,
     rot=Euler((0, 0, math.atan2(ROW_DIR.y, ROW_DIR.x))))
for v in bm.verts:
    if v.co.z > 0.012:
        v.co.z = 0.012 + 0.004 * noise.noise(Vector((v.co.x * 6, v.co.y * 6, 0.4)))
SLAB = bm_to_obj('yassi_tas', bm)
SLAB.location = (ROW_CENTER.x, ROW_CENTER.y, SLAB_TOP - 0.012)
setmat(SLAB, M_SLAB)


def near_slab(p):
    d = p - ROW_CENTER
    u = d.dot(ROW_DIR) / (ROW_GAP * 4.6 + 0.2)
    v = d.dot(TO_CAM0) / 0.42
    return u * u + v * v < 1.0


build_tufts([near_slab,
             lambda p: (p - FP).length < 0.2,
             lambda p: (p - (HANG.xy + TO_CAM0 * 0.1)).length < 0.3])

# arka plan tepeleri ve ağaç
for k, (c, rad, mat) in enumerate((((-7.0, 17.0, -0.3), (9.0, 3.5, 2.2), M_HILL1),
                                   ((7.5, 19.0, -0.5), (10.0, 4.0, 2.6), M_HILL2),
                                   ((0.5, 27.0, -1.0), (16.0, 5.0, 3.6), M_HILL3))):
    bm = bmesh.new()
    blob(bm, c, rad, subdiv=4, amp=0.05, nscale=1.2, seed=900 + k)
    ob = bm_to_obj('tepe_%d' % k, bm)
    setmat(ob, mat)


def tree(name, x, y, sc, seed):
    r = rng(seed)
    z = hfun(x, y)
    bm = bmesh.new()
    blob(bm, (x, y, z + 0.3 * sc), (0.1 * sc, 0.1 * sc, 0.4 * sc), subdiv=3, amp=0.06, seed=seed)
    t = bm_to_obj(name + '_govde', bm)
    setmat(t, M_TRUNK)
    bm = bmesh.new()
    for k in range(7):
        blob(bm, (x + r.uniform(-0.4, 0.4) * sc, y + r.uniform(-0.3, 0.3) * sc, z + (0.85 + r.uniform(-0.1, 0.35)) * sc),
             (r.uniform(0.34, 0.46) * sc,) * 3, subdiv=3, amp=0.08, seed=seed + k)
    lf = bm_to_obj(name + '_yaprak', bm)
    rm = lf.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.03 * sc
    sm = lf.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 6
    bake_modifiers(lf)
    for pl in lf.data.polygons:
        pl.use_smooth = True
    setmat(lf, M_LEAF)


tree('agac1', -2.3, 2.9, 0.62, 1301)
print('t sahne %.1f' % (time.time() - T_START), flush=True)

# koyun yolları (kil sürümüyle aynı)
gu = Vector((math.cos(GATE_ANG), math.sin(GATE_ANG)))
GATE = PEN_C + gu * PEN_R
INSIDE = GATE - gu * 0.42
OUT1 = GATE + gu * 0.75 + Vector((-0.1, 0.05))
spots_rel = [(0.55, 0.45), (0.75, -0.05), (0.1, 0.72), (0.35, 0.08), (0.45, -0.5), (-0.3, 0.55),
             (-0.15, 0.08), (0.02, -0.42)]
SPOTS = [PEN_C + Vector(s) for s in spots_rel]
start_pts = [(-8.2, -1.4), (-3.8, -0.85)]

sheep = [build_sheep(i) for i in range(N_SHEEP)]
paths = []
for i in range(N_SHEEP):
    pts = [Vector(start_pts[0]) + Vector((0, 0.05 * ((i * 7) % 3 - 1))), Vector(start_pts[1]), OUT1, GATE,
           INSIDE, SPOTS[i]]
    paths.append(Path(pts))


def sheep_s(i, f):
    P = paths[i]
    sg = P.closest_s(GATE)
    u = sg + SPEED * (f - (T_GATE0 + T_GAP * i))
    ease = 0.35
    x = (u - (P.total - ease)) / (2 * ease)
    if x <= 0:
        return max(0.0, u)
    if x >= 1:
        return P.total
    return P.total - ease + 2 * ease * (x - x * x / 2)


def key_obj(ob, f, loc=True, rot=True):
    if loc:
        ob.keyframe_insert('location', frame=f)
    if rot:
        ob.keyframe_insert('rotation_quaternion' if ob.rotation_mode == 'QUATERNION' else 'rotation_euler', frame=f)


for i, (root, bob, head, legs) in enumerate(sheep):
    prev_yaw = None
    prev_s = sheep_s(i, 0)
    for f in range(-2, N_FRAMES + 3):
        s = sheep_s(i, f)
        pos, d = paths[i].at(s)
        if d.length < 1e-6:
            pos2, d = paths[i].at(s - 0.02)
        yaw = math.atan2(d.y, d.x)
        if prev_yaw is not None:
            while yaw - prev_yaw > math.pi:
                yaw -= 2 * math.pi
            while yaw - prev_yaw < -math.pi:
                yaw += 2 * math.pi
        prev_yaw = yaw
        moving = min(1.0, max(0.0, (s - prev_s) / SPEED))
        prev_s = s
        phase = s / 0.2 * 2 * math.pi + i
        root.location = (pos.x, pos.y, hfun(pos.x, pos.y))
        root.rotation_euler = (0, 0, yaw)
        key_obj(root, f)
        bob.location = (0, 0, 0.014 * abs(math.sin(phase)) * moving)
        bob.rotation_euler = (0.03 * math.sin(phase) * moving, 0, 0)
        key_obj(bob, f)
        head.rotation_euler = (0.04 * math.sin(f * 0.07 + i), math.radians(18) + 0.07 * math.sin(phase) * moving
                               + 0.05 * math.sin(f * 0.05 + i * 2) * (1 - moving), 0.12 * math.sin(f * 0.03 + i) * (1 - moving))
        key_obj(head, f, loc=False)
        for k, leg in enumerate(legs):
            off = 0 if k in (0, 3) else math.pi
            leg.rotation_euler = (0, 0.5 * math.sin(phase + off) * moving, 0)
            key_obj(leg, f, loc=False)

# ---------------------------------------------------------------- çakıllar
def pouch_quat(f):
    """kese her taş alınışında hafifçe sallanır."""
    to_cam = (CAM_POS0.xy - HANG.xy).normalized()
    ax1 = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    ax2 = Vector((to_cam.x, to_cam.y, 0))
    a1 = a2 = 0.0
    for i in range(N_SHEEP):
        tp = T_GATE0 + T_GAP * i - 3
        if f > tp:
            dt = f - tp
            a1 += 0.05 * math.exp(-dt / 12.0) * math.sin(dt * 0.45)
            a2 += 0.03 * math.exp(-dt / 12.0) * math.sin(dt * 0.38 + 1.0)
    return Quaternion(ax1, a1) @ Quaternion(ax2, a2) @ pouch_q0


def pouch_matrix(f):
    return Matrix.Translation(HANG) @ pouch_quat(f).to_matrix().to_4x4() @ Matrix.Scale(POUCH_S, 4)


# kesenin ağzındaki yığın (kese yerel ekseninde): 0 = son kalan (ortada, ağızda), sonra halka, en üstte üçlü
heap_local = [Vector((0, 0, LIP_Z - 0.004))]
for k in range(5):
    th = 2 * math.pi * k / 5 + 0.3
    heap_local.append(Vector((0.056 * math.cos(th), 0.056 * math.sin(th), LIP_Z + 0.022)))
for k in range(3):
    th = 2 * math.pi * k / 3 + 0.9
    heap_local.append(Vector((0.026 * math.cos(th), 0.026 * math.sin(th), LIP_Z + 0.056)))
take_order = [8, 7, 6, 5, 4, 3, 2, 1]
pebbles = [pebble_mesh('cakil_%d' % k, 3000 + k, M_LAST if k == 0 else M_PEBBLE) for k in range(9)]
LAST = pebbles[0]
LAND = []
rr = rng(4000)
for k in range(N_SHEEP):
    p = ROW_START + ROW_DIR * (ROW_GAP * k) + Vector((rr.uniform(-0.008, 0.008), rr.uniform(-0.008, 0.008)))
    LAND.append(p)
local_rot = [Quaternion((0, 0, 1), rng(5000 + k).uniform(0, 6.28)) @ Quaternion((1, 0, 0), rng(5100 + k).uniform(-0.3, 0.3))
             for k in range(9)]
FLIGHT = 20


def qfix(q, prev):
    if prev is not None and q.dot(prev) < 0:
        return -q
    return q


for idx, peb in enumerate(pebbles):
    order = take_order.index(idx) if idx in take_order else None
    prev_q = None
    t_take = T_GATE0 + T_GAP * order - 3 if order is not None else 10 ** 6
    land_q = Quaternion((0, 0, 1), math.atan2(ROW_DIR.y, ROW_DIR.x) + rng(6000 + idx).uniform(-0.5, 0.5))
    for f in range(-2, N_FRAMES + 3):
        if f <= t_take:
            M = pouch_matrix(f) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            loc, q, _ = M.decompose()
        else:
            M0 = pouch_matrix(t_take) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            p0, q0, _ = M0.decompose()
            L2 = LAND[order]
            p1 = Vector((L2.x, L2.y, SLAB_TOP + PEB_R[2] * 0.9))
            t = min(1.0, (f - t_take) / FLIGHT)
            e = smoother(t)
            if t < 0.3:
                loc = p0 + Vector((0, 0, 0.1 * smoother(t / 0.3)))
            else:
                v = smoother((t - 0.3) / 0.7)
                loc = (p0 + Vector((0, 0, 0.1))).lerp(p1, v) + Vector((0, 0, 0.16 * 4 * v * (1 - v)))
            q = q0.slerp(land_q, e)
            q = Quaternion((1, 0, 0), 2.0 * math.sin(math.pi * e)) @ q if t < 1 else q
            if t >= 1:
                dt = f - t_take - FLIGHT
                loc = p1 + Vector((0, 0, 0.012 * math.exp(-dt / 2.0) * abs(math.sin(dt * 1.3))))
                q = land_q
        q = qfix(q, prev_q)
        prev_q = q
        peb.location = loc
        peb.rotation_quaternion = q
        key_obj(peb, f)

for f in range(-2, N_FRAMES + 3):
    pouch.rotation_quaternion = pouch_quat(f)
    pouch.keyframe_insert('rotation_quaternion', frame=f)
print('t anim %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- ışık
world = bpy.data.worlds.new('dunya')
scene.world = world
WN, WL = world.node_tree.nodes, world.node_tree.links
bg = [n for n in WN if n.type == 'BACKGROUND'][0]
wtc = WN.new('ShaderNodeTexCoord')
sep = WN.new('ShaderNodeSeparateXYZ')
WL.new(wtc.outputs['Generated'], sep.inputs[0])
ramp = WN.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (1.0, 0.72, 0.48, 1)
ramp.color_ramp.elements[1].position = 0.35
ramp.color_ramp.elements[1].color = (0.80, 0.84, 0.92, 1) if not SU else (0.92, 0.88, 0.80, 1)
WL.new(sep.outputs['Z'], ramp.inputs[0])
WL.new(ramp.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.6
world.mist_settings.start = 3.0
world.mist_settings.depth = 22.0
world.mist_settings.falloff = 'LINEAR'


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


# alçak akşam güneşi: soldan ve hafif önden (koyunların kameraya bakan yanı aydınlık, gölgeler sağ arkaya)
SUN_AZ, SUN_EL = math.radians(203.0), math.radians(21.0)
TO_SUN = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))
light('gunes', 'SUN', 3.2, (1.0, 0.82, 0.62), direction=-TO_SUN, size=math.radians(3.5 if SU else 1.5))
if not SU:
    # resimli3d: arkadan serin kenar ışığı (siluetleri ayırır), sıcak ana ışığa karşı
    RIM = Vector((0.55, 0.95, 0.45)).normalized()
    light('kenar', 'SUN', 2.2, (0.62, 0.78, 1.0), direction=-RIM, size=math.radians(2.0))

# ---------------------------------------------------------------- kamera (kil sürümüyle aynı vuruşlar)
cam_data = bpy.data.cameras.new('kamera')
cam_data.lens = 50
cam_data.sensor_width = 36
cam = link(bpy.data.objects.new('kamera', cam_data))
scene.camera = cam
target = link(bpy.data.objects.new('hedef', None))
tr = cam.constraints.new('TRACK_TO')
tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'
tr.up_axis = 'UP_Y'
cam_data.dof.use_dof = True
cam_data.dof.aperture_blades = 0


def last_world(f):
    return (pouch_matrix(f) @ Matrix.Translation(heap_local[0])).to_translation()


P_END = last_world(N_FRAMES)
TGT0 = Vector((-0.05, 0.45, 0.22))
TGT1 = Vector((-0.12, 0.40, 0.24))
CAM1 = Vector((0.85, -3.65, 1.62))
v_end = (CAM1 - P_END)
v_end.z = 0
v_end = Matrix.Rotation(math.radians(-32), 3, 'Z') @ v_end.normalized()
CAM_END = P_END + (v_end * 0.75 + Vector((0, 0, 0.95))).normalized() * 1.15
FOCUS0 = (GATE.to_3d() + Vector((0, 0, 0.3))).lerp(Vector((HANG.x, HANG.y, HANG.z - 0.25)), 0.8)
F0, F1 = (3.2, 4.0) if SU else (1.6, 2.4)
PUSH0, PUSH1 = 212, 296
for f in range(-2, N_FRAMES + 3):
    t0 = max(0.0, min(1.0, (f - 1) / (PUSH0 - 1)))
    cpos = CAM_POS0.lerp(CAM1, t0)
    tpos = TGT0.lerp(TGT1, t0)
    e = smoother((f - PUSH0) / (PUSH1 - PUSH0))
    cpos = cpos.lerp(CAM_END, e)
    tpos = tpos.lerp(P_END + Vector((0, 0, -0.035)), e)
    cpos = cpos + Vector((0.004 * math.sin(f * 0.041), 0.0, 0.003 * math.sin(f * 0.057 + 1)))
    cam.location = cpos
    cam.keyframe_insert('location', frame=f)
    target.location = tpos
    target.keyframe_insert('location', frame=f)
    focus = FOCUS0.lerp(P_END, smoother((f - PUSH0 + 10) / (PUSH1 - PUSH0 - 10)))
    cam_data.dof.focus_distance = (cpos - focus).length
    cam_data.dof.keyframe_insert('focus_distance', frame=f)
    cam_data.dof.aperture_fstop = F0 + (F1 - F0) * e
    cam_data.dof.keyframe_insert('aperture_fstop', frame=f)

# ---------------------------------------------------------------- son taşın parıltısı (küçük, sıcak, yumuşak dört kollu yıldız)
cam_dir_end = (CAM_END - P_END).normalized()
b2 = bmesh.new()
blob(b2, (0, 0, 0), (0.004, 0.004, 0.004), subdiv=2)
spark = bm_to_obj('parilti_nokta', b2)
M_SPARK = emissive('parilti_mat', (1.0, 0.86, 0.58), 0.0)
setmat(spark, M_SPARK)
spark.parent = LAST
_top = (cam_dir_end * 0.35 + Vector((0, 0, 1))).normalized()
_M300 = pouch_matrix(N_FRAMES) @ Matrix.Translation(heap_local[0]) @ local_rot[0].to_matrix().to_4x4()
_l3, _q3, _s3 = _M300.decompose()
spark.location = (Matrix.Translation(_l3) @ _q3.to_matrix().to_4x4()).inverted() @ (P_END + _top * (PEB_R[2] + 0.004))
for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission'):
    setattr(spark, attr, False)
_sp = M_SPARK.node_tree.nodes['Emission'].inputs['Strength']
for f, v in ((1, 0.0), (262, 0.0), (272, 320.0), (281, 150.0), (290, 260.0), (300, 180.0)):
    _sp.default_value = v
    _sp.keyframe_insert('default_value', frame=f)
# son taşa sıcak bir dokunuş: çakılın çevresinde hafif ışık (yalnız parıltı anında)
glint = light('parilti', 'POINT', 0.0, (1.0, 0.8, 0.5), loc=P_END + (cam_dir_end * 0.6 + Vector((0, 0, 0.8))).normalized() * 0.35, size=0.02)
glint.visible_camera = False
for f, en in ((1, 0.0), (258, 0.0), (278, 0.35), (300, 0.3)):
    glint.data.energy = en
    glint.data.keyframe_insert('energy', frame=f)

# resimli3d: havada süzülen, ışık alan toz (Arcane'deki parçacık havası); sağ alt ve orta boş
from bpy_extras.object_utils import world_to_camera_view
scene.frame_set(1)
bpy.context.view_layer.update()
if not SU:
    M_MOTE = emissive('toz', (1.0, 0.8, 0.5), 2.2)
    rm_ = rng(8000)
    motes, tries = 0, 0
    while motes < 16 and tries < 3000:
        tries += 1
        d = rm_.uniform(1.3, 2.6) if rm_.random() < 0.6 else rm_.uniform(6.0, 10.0)
        base = CAM_POS0 + (TGT0 - CAM_POS0).normalized() * d
        p = base + Vector((rm_.uniform(-1.0, 1.0) * d * 0.33, 0, rm_.uniform(-0.55, 0.55) * d * 0.2))
        sc = world_to_camera_view(scene, cam, p)
        if not (0.02 < sc.x < 0.98 and 0.05 < sc.y < 0.98):
            continue
        if (sc.x > 0.62 and sc.y < 0.42) or (0.22 < sc.x < 0.6 and 0.08 < sc.y < 0.65):
            continue
        if p.z < hfun(p.x, p.y) + 0.1:
            continue
        b2 = bmesh.new()
        blob(b2, (0, 0, 0), (0.004 if d < 5 else 0.018,) * 3, subdiv=1)
        mo = bm_to_obj('toz_%d' % motes, b2)
        setmat(mo, M_MOTE)
        ph = rm_.uniform(0, 6.28)
        for f in range(-2, N_FRAMES + 3, 3):
            mo.location = p + Vector((0.03 * math.sin(f * 0.02 + ph), 0.02 * math.cos(f * 0.017 + ph), 0.0012 * f))
            mo.keyframe_insert('location', frame=f)
        for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy'):
            setattr(mo, attr, False)
        motes += 1

# ---------------------------------------------------------------- render ayarları
R = scene.render
R.engine = 'CYCLES'
C = scene.cycles
C.device = 'CPU'
C.samples = A.ornek
C.use_adaptive_sampling = True
C.adaptive_threshold = 0.03
C.use_denoising = False           # gürültü kompozitte, ışık geçişinde giderilir
C.max_bounces = 3
C.diffuse_bounces = 2
C.glossy_bounces = 0
C.transmission_bounces = 0
C.transparent_max_bounces = 2
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.seed = 7
C.use_animated_seed = False
C.sample_clamp_indirect = 5.0
C.use_light_tree = False
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = bool(A.bulanik)
R.motion_blur_shutter = 0.3
R.use_persistent_data = True
R.film_transparent = True         # gökyüzünü kompozit boyar
vs = scene.view_settings
vs.view_transform = 'Standard'
vs.look = 'None'
vs.exposure = 0.0
vl = scene.view_layers[0]
for p in ('use_pass_diffuse_direct', 'use_pass_diffuse_indirect', 'use_pass_diffuse_color', 'use_pass_emit',
          'use_pass_normal', 'use_pass_mist', 'use_pass_z'):
    setattr(vl, p, True)

# ---------------------------------------------------------------- kompozit: geçişlerden resmi boya
ng = bpy.data.node_groups.new('kompozit', 'CompositorNodeTree')
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
scene.compositing_node_group = ng
NN, LL = ng.nodes, ng.links
PX = A.w / 1920.0                 # piksel ölçülü ayarlar önizlemede de aynı görünsün


def put(sock, v):
    if isinstance(v, bpy.types.NodeSocket):
        LL.new(v, sock)
    elif isinstance(v, (tuple, list)):
        vv = tuple(v)
        n = len(sock.default_value)
        if len(vv) < n:
            vv = vv + (1.0,) * (n - len(vv))
        sock.default_value = vv[:n]
    else:
        sock.default_value = v


def isock(n, name, k=0):
    return [s for s in n.inputs if s.name == name and s.enabled][k]


def osock(n, name=None, k=0):
    ss = [s for s in n.outputs if s.enabled and (name is None or s.name == name)]
    return ss[k]


def mix(a, b, blend='MIX', fac=1.0, clamp=False):
    n = NN.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = blend; n.clamp_result = clamp
    put(n.inputs[0], fac); put(n.inputs[6], a); put(n.inputs[7], b)
    return n.outputs[2]


def math_(op, a, b=0.0, c=0.0, clamp=False):
    n = NN.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
    put(n.inputs[0], a); put(n.inputs[1], b); put(n.inputs[2], c)
    return n.outputs[0]


def cramp(fac, stops, interp='LINEAR'):
    n = NN.new('ShaderNodeValToRGB')
    cr = n.color_ramp
    cr.interpolation = interp
    el = cr.elements
    el[0].position = stops[0][0]; el[0].color = (*stops[0][1], 1.0)
    el[1].position = stops[-1][0]; el[1].color = (*stops[-1][1], 1.0)
    for pos, c in stops[1:-1]:
        e = el.new(pos); e.color = (*c, 1.0)
    put(n.inputs[0], fac)
    return n.outputs[0]


def bw(img):
    n = NN.new('CompositorNodeRGBToBW'); put(n.inputs[0], img)
    return n.outputs[0]


def tnoise(vec, scale, detail=2.0, rough=0.5, dist=0.0, w=0.0):
    n = NN.new('ShaderNodeTexNoise'); n.noise_dimensions = '4D'
    put(n.inputs['Vector'], vec); n.inputs['W'].default_value = w
    n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough; n.inputs['Distortion'].default_value = dist
    return n.outputs[0], n.outputs[1]


def blur(img, px):
    n = NN.new('CompositorNodeBlur'); put(n.inputs['Image'], img)
    n.inputs['Size'].default_value = (px * PX, px * PX)
    try:
        n.inputs['Type'].default_value = 'Fast Gaussian'
    except Exception:
        pass
    return n.outputs[0]


def menu(n, name, val):
    try:
        n.inputs[name].default_value = val
    except Exception as ex:
        print('menü', name, val, ex)


rl = NN.new('CompositorNodeRLayers')
gout = NN.new('NodeGroupOutput')
P_A = osock(rl, 'Diffuse Color'); P_LD = osock(rl, 'Diffuse Direct'); P_LI = osock(rl, 'Diffuse Indirect')
P_E = osock(rl, 'Emission'); P_N = osock(rl, 'Normal'); P_MI = osock(rl, 'Mist'); P_AL = osock(rl, 'Alpha')
P_Z = osock(rl, 'Depth')
ic = NN.new('CompositorNodeImageCoordinates'); put(ic.inputs[0], osock(rl, 'Image'))
UV = osock(ic, 'Uniform')
sepn = NN.new('ShaderNodeSeparateXYZ'); put(sepn.inputs[0], osock(ic, 'Normalized'))
NY = sepn.outputs['Y']

# 1) ışık: doğrudan + dolaylı, gürültüsü giderilir (düşük örnekle temiz ışık)
Lraw = mix(P_LD, P_LI, 'ADD')
dn = NN.new('CompositorNodeDenoise')
put(dn.inputs['Image'], Lraw); put(dn.inputs['Normal'], P_N)
menu(dn, 'Quality', 'High')
LIGHT = dn.outputs[0]
lum = bw(LIGHT)

# 2) ışığı boya tonlarına çevir
if SU:
    # suluboya: üç yumuşak değer (gölge, orta, ışık); gölge serin-mor saydam boya, ışık sıcak krem
    K = 1.0
    shade = cramp(math_('MULTIPLY', lum, K), [
        (0.00, lin((0.52, 0.50, 0.66))),
        (0.30, lin((0.66, 0.62, 0.74))),
        (0.48, lin((0.88, 0.80, 0.78))),
        (0.70, lin((1.00, 0.94, 0.84))),
        (1.30, lin((1.00, 0.97, 0.90)))], 'EASE')
    base = mix(P_A, shade, 'MULTIPLY')
else:
    # resimli3d: ışığın rengi korunur, değeri basamaklanır (sert ama boyanmış geçiş), terminatörde sıcak bant
    K = 1.0
    gval = cramp(math_('MULTIPLY', lum, K), [
        (0.00, (0.30, 0.30, 0.30)),
        (0.28, (0.36, 0.36, 0.36)),
        (0.40, (0.80, 0.80, 0.80)),
        (0.95, (1.00, 1.00, 1.00)),
        (2.00, (1.25, 1.25, 1.25))], 'EASE')
    ratio = math_('DIVIDE', bw(gval), math_('MAXIMUM', lum, 0.03))
    lit = mix(LIGHT, ratio, 'MULTIPLY')
    tint = cramp(math_('MULTIPLY', lum, K), [
        (0.00, lin((0.80, 0.86, 1.00))),
        (0.30, lin((0.86, 0.88, 1.00))),
        (0.38, lin((1.00, 0.80, 0.70))),
        (0.50, (1.0, 1.0, 1.0)),
        (1.00, (1.0, 1.0, 1.0))], 'LINEAR')
    shade = mix(lit, tint, 'MULTIPLY')
    base = mix(P_A, shade, 'MULTIPLY')

# 3) hava perspektifi: uzak yerler açık, sıcak pus
HAZE = lin((0.96, 0.88, 0.74)) if SU else lin((0.98, 0.80, 0.60))
hz = mix(base, HAZE, 'MIX', fac=math_('MULTIPLY', P_MI, 0.55 if SU else 0.45, clamp=True))

# 4) gökyüzü: boyanmış yıkama (üst krem, ufukta şeftali), birkaç yumuşak bulut lekesi
sky = cramp(NY, [(0.3, lin((0.99, 0.80, 0.60))), (0.75, lin((0.98, 0.90, 0.76))), (1.0, lin((0.96, 0.93, 0.84)))], 'EASE')
cl, _ = tnoise(UV, 1.6, 3.0, 0.5, 0.5, w=3.0)
clm = cramp(cl, [(0.55, (0, 0, 0)), (0.72, (1, 1, 1))], 'EASE')
sky = mix(sky, lin((1.0, 0.95, 0.88)), 'MIX', fac=math_('MULTIPLY', bw(clm), 0.6))
img = mix(sky, hz, 'MIX', fac=P_AL)

# 5) boya: Kuwahara (fırça/leke), ardından tarza göre
kw = NN.new('CompositorNodeKuwahara'); put(kw.inputs['Image'], img)
menu(kw, 'Type', 'Anisotropic')
kw.inputs['Size'].default_value = (5.0 if SU else 4.0) * PX
kw.inputs['Uniformity'].default_value = 4
kw.inputs['Sharpness'].default_value = 0.35 if SU else 0.7
kw.inputs['Eccentricity'].default_value = 1.0
PAINT = kw.outputs[0]

# çizgi: derinlikteki göreli sıçrama (siluet) -> ince koyu kontur
sob = NN.new('CompositorNodeFilter'); put(sob.inputs['Image'], P_Z); menu(sob, 'Type', 'Sobel')
edge_rel = math_('DIVIDE', bw(sob.outputs[0]), math_('MAXIMUM', P_Z, 0.1))
LINE = math_('MULTIPLY', math_('SUBTRACT', edge_rel, 0.04), 8.0, clamp=True)

if SU:
    # taşan kenar: resim, yavaş değişen gürültüyle 2-3 piksel itilir
    dcol = tnoise(UV, 9.0, 3.0, 0.6, 0.0, w=1.0)[1]
    dvec = mix(mix(dcol, (0.5, 0.5, 0.5), 'SUBTRACT'), (5.0 * PX, 5.0 * PX, 0.0), 'MULTIPLY')
    dsp = NN.new('CompositorNodeDisplace'); put(dsp.inputs['Image'], PAINT); put(dsp.inputs['Displacement'], dvec)
    menu(dsp, 'Extension X', 'Extend'); menu(dsp, 'Extension Y', 'Extend')
    c01 = mix(dsp.outputs[0], (0, 0, 0), 'ADD', clamp=True)
    # kurşun kalem çizgisi: çok hafif, sıcak kahve (masal kitabı)
    c01 = mix(c01, lin((0.36, 0.26, 0.22)), 'MIX', fac=math_('MULTIPLY', LINE, 0.35))
    # boya yoğunluğu modeli: pigment = 1 - renk; kenar birikmesi + kâğıt greni + ıslak leke ile çarpılır
    pig = mix((1, 1, 1), c01, 'SUBTRACT')
    bl = blur(c01, 7.0)
    edge = bw(mix(c01, bl, 'DIFFERENCE'))
    g1, _ = tnoise(UV, 420.0, 4.0, 0.65, 0.0, w=5.0)           # kâğıt greni
    g2, _ = tnoise(UV, 60.0, 5.0, 0.6, 0.2, w=7.0)             # granülasyon (boya çökmesi)
    wm, _ = tnoise(UV, 2.4, 3.0, 0.55, 0.3, w=9.0)             # ıslak leke
    dens = math_('MULTIPLY_ADD', edge, 2.6, 1.0)
    dens = math_('MULTIPLY_ADD', math_('SUBTRACT', g1, 0.5), 0.55, dens)
    dens = math_('MULTIPLY_ADD', math_('SUBTRACT', g2, 0.5), 0.45, dens)
    dens = math_('MULTIPLY_ADD', math_('SUBTRACT', wm, 0.5), 0.5, dens)
    pig2 = mix(pig, dens, 'MULTIPLY')
    col = mix((1, 1, 1), pig2, 'SUBTRACT', clamp=True)
    PAPER = lin((0.975, 0.955, 0.905))
    col = mix(col, PAPER, 'MULTIPLY')
    # kâğıt dokusu (hafif kabartı gölgesi)
    pb, _ = tnoise(UV, 140.0, 6.0, 0.7, 0.0, w=11.0)
    col = mix(col, math_('MULTIPLY_ADD', pb, 0.06, 0.97), 'MULTIPLY')
    # kenarlarda boyanmamış kâğıda yumuşak geçiş (masal kitabı sayfası)
    vn, _ = tnoise(UV, 3.0, 3.0, 0.6, 0.0, w=13.0)
    cen = NN.new('ShaderNodeVectorMath'); cen.operation = 'SUBTRACT'
    put(cen.inputs[0], osock(ic, 'Normalized')); cen.inputs[1].default_value = (0.5, 0.5, 0.0)
    scl = NN.new('ShaderNodeVectorMath'); scl.operation = 'MULTIPLY'
    put(scl.inputs[0], cen.outputs[0]); scl.inputs[1].default_value = (1.0, 0.72, 1.0)
    ln = NN.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; put(ln.inputs[0], scl.outputs[0])
    vv = math_('MULTIPLY_ADD', vn, 0.10, osock(ln, 'Value'))
    vig = math_('MULTIPLY', math_('SUBTRACT', vv, 0.52), 4.0, clamp=True)
    col = mix(col, PAPER, 'MIX', fac=math_('MULTIPLY', vig, 0.85))
    OUTC = col
else:
    # resimli3d: hafif keskinleştirme (boya kenarı) + koyu sıcak kontur
    shp = NN.new('CompositorNodeFilter'); put(shp.inputs['Image'], PAINT); menu(shp, 'Type', 'Box Sharpen')
    shp.inputs['Factor'].default_value = 0.12
    col = mix(shp.outputs[0], (0, 0, 0), 'ADD', clamp=False)
    col = mix(col, lin((0.16, 0.10, 0.10)), 'MIX', fac=math_('MULTIPLY', LINE, 0.55))
    # boyalı gren (ekrana sabit ince tuval dokusu, çok hafif)
    g1, _ = tnoise(UV, 300.0, 4.0, 0.6, 0.0, w=5.0)
    col = mix(col, math_('MULTIPLY_ADD', g1, 0.07, 0.965), 'MULTIPLY')
    OUTC = col

# 6) ışıma (gözdeki ışık, parıltı, toz) boyadan sonra eklenir: net kalır
OUTC = mix(OUTC, P_E, 'ADD')
fg = NN.new('CompositorNodeGlare')
for nm, val in (('Type', 'Fog Glow'), ('Quality', 'High'), ('Threshold', 0.9 if not SU else 3.0), ('Strength', 0.22 if not SU else 0.25),
                ('Size', 0.5), ('Tint', (1.0, 0.82, 0.6, 1.0))):
    if nm in fg.inputs:
        try:
            fg.inputs[nm].default_value = val
        except Exception as ex:
            print('fog', nm, ex)
put(fg.inputs['Image'], OUTC)
gl = NN.new('CompositorNodeGlare')
for nm, val in (('Type', 'Streaks'), ('Quality', 'High'), ('Threshold', 30.0), ('Strength', 0.3), ('Streaks', 4),
                ('Streaks Angle', 0.0), ('Fade', 0.75), ('Size', 0.25), ('Saturation', 0.9), ('Tint', (1.0, 0.82, 0.55, 1.0))):
    if nm in gl.inputs:
        try:
            gl.inputs[nm].default_value = val
        except Exception as ex:
            print('glare', nm, ex)
put(gl.inputs['Image'], fg.outputs[0])
FINAL = gl.outputs[0]
if not SU:
    cb = NN.new('CompositorNodeColorBalance'); put(cb.inputs['Image'], FINAL)
    menu(cb, 'Type', 'Lift/Gamma/Gain')
    try:
        isock(cb, 'Lift', 1).default_value = (0.99, 1.0, 1.03, 1)
        isock(cb, 'Gain', 1).default_value = (1.04, 1.0, 0.95, 1)
    except Exception as ex:
        print('renk dengesi', ex)
    FINAL = cb.outputs[0]
put(gout.inputs[0], FINAL)

# hata ayıklama: ham geçişler dosyaya
if A.gecis:
    fo = NN.new('CompositorNodeOutputFile')
    try:
        fo.base_path = os.path.join(os.path.abspath(A.cikti), 'gecis_')
    except Exception:
        fo.directory = os.path.abspath(A.cikti)
    try:
        fo.file_slots.clear()
        for nm in ('isik', 'renk', 'boya'):
            fo.file_slots.new(nm)
        LL.new(LIGHT, fo.inputs[0]); LL.new(P_A, fo.inputs[1]); LL.new(PAINT, fo.inputs[2])
    except Exception as ex:
        print('gecis çıktısı kurulamadı', ex)

for _f in (1, 68, 180, 290):
    scene.frame_set(_f)
    for _nm, _p in (('kapi', GATE.to_3d() + Vector((0, 0, 0.2))), ('kese', HANG - Vector((0, 0, 0.25))),
                    ('dizi_bas', LAND[0].to_3d() + Vector((0, 0, SLAB_TOP))),
                    ('dizi_son', LAND[-1].to_3d() + Vector((0, 0, SLAB_TOP)))):
        _c = world_to_camera_view(scene, cam, _p)
        print('KADRAJ f%d %-8s x=%.2f y(ust)=%.2f' % (_f, _nm, _c.x, 1 - _c.y))
print('sahne kuruldu: %.1f sn' % (time.time() - T_START), flush=True)
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(A.cikti), STIL + '.blend'))

_t = {}
bpy.app.handlers.render_pre.append(lambda sc, *a: _t.__setitem__('t', time.time()))
bpy.app.handlers.render_post.append(lambda sc, *a: print('KARE %d: %.1f sn' % (sc.frame_current, time.time() - _t.get('t', time.time())), flush=True))

R.image_settings.file_format = 'PNG'
R.image_settings.color_mode = 'RGB'
R.image_settings.color_depth = '8'
if A.mod == 'kur':
    print('yalnız kurulum (render yok)')
elif A.mod == 'kare':
    for f in [int(x) for x in A.kareler.split(',') if x.strip()]:
        scene.frame_set(f)
        R.filepath = os.path.join(os.path.abspath(A.cikti), 'kare_%04d.png' % f)
        bpy.ops.render.render(write_still=True)
else:
    scene.frame_start = A.bas
    scene.frame_end = A.son
    R.filepath = os.path.join(os.path.abspath(A.cikti), 'k_')
    bpy.ops.render.render(animation=True)
print('BITTI toplam %.1f sn' % (time.time() - T_START))
