# Math with Zirek · sahne G, MİNYATÜR sürüm (akşam, koyunlar girer, taş çıkar, tek taş kalır)
# Blender 5.2, Cycles + Freestyle. Tamamen yordamsal, dış varlık yok.
# Minyatür resim ruhunda (belirli bir esere dayanmaz): dik açıdan ortografik (derinliği düzleşmiş, üst üste
# dizilmiş) kamera; ışık yok, her yüzey "boyalı" (düz renk + yumuşak iki ton + pigment lekelenmesi + kâğıt greni);
# ince sepya kontur (Freestyle, kalem gibi kalınlığı değişen çizgi); maden renkleri (lacivert/lapis, zencefre
# kırmızısı, malakit yeşili, aşı); altın gök ve altın süslemeli ince pervaz. Yazı, hat, dinî motif yok.
# Hikâye, zamanlama ve kamera vuruşları öteki sürümlerle aynı (8 koyun, 0,73 sn, son 3 sn yaklaşma, tek taş parıltısı).
# Kullanım:
#   blender -b -P sahne.py -- --mod kare --kareler 68,180,290 --w 960 --h 540 --ornek 16 --cikti out
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
ap.add_argument('--ornek', type=int, default=32)
ap.add_argument('--cikti', default='out')
ap.add_argument('--cihaz', default='auto')
ap.add_argument('--bulanik', type=int, default=0)
ap.add_argument('--cizgi', type=int, default=1)
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
NOLINE = bpy.data.collections.new('cizgisiz')      # konturu çizilmeyenler (ot, çiçek, gök, pervaz)
scene.collection.children.link(NOLINE)


def rng(seed):
    return random.Random(seed)


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def smoother(t):
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def link(ob, noline=False):
    (NOLINE if noline else scene.collection).objects.link(ob)
    return ob


def s2l(c):
    """sRGB (0-1) -> doğrusal renk. Palet ekranda görünen değerlerle yazılır."""
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def bm_obj(name, bm, mats, smooth_shade=True, noline=False, subsurf=0):
    for f in bm.faces:
        f.smooth = smooth_shade
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = link(bpy.data.objects.new(name, me), noline)
    if subsurf:
        ss = ob.modifiers.new('ss', 'SUBSURF'); ss.levels = subsurf; ss.render_levels = subsurf
    return ob


def blob(bm, center, radii, subdiv=3, amp=0.0, seed=0, rot=None, mi=0, nscale=1.7, curls=0.0, curl_scale=6.0):
    """Yumuşak topak. curls>0: yüzeyde yuvarlak kabarcıklar (minyatürde yün kıvırcığı / süngerimsi kaya)."""
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=subdiv, radius=1.0)
    o = Vector((seed * 3.1, seed * 1.7, seed * 0.9))
    for v in tmp.verts:
        n = v.co.normalized()
        d = 1.0 + amp * noise.noise(n * nscale + o)
        if curls:
            dist, _ = noise.voronoi(n * curl_scale + o)
            d += curls * max(0.0, 1.0 - dist[0] / 0.62) ** 0.6
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


def tube(bm, p0, p1, r0, r1, seg=10, mi=0):
    d = (p1 - p0)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=d.length,
                          matrix=Matrix.Translation(p0 + d / 2) @ q.to_matrix().to_4x4())
    for f in tmp.faces:
        f.material_index = mi
    me = bpy.data.meshes.new('_t')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


# ---------------------------------------------------------------- yerleşim (öteki sürümlerle aynı düzen, ağıl biraz küçük)
PEN_C = Vector((0.0, 6.0))
PEN_R = 3.3
GATE_ANG = math.radians(228)
GAP_HALF = 0.27
WALL_H = 0.8
POST_R = 0.3
POST_H = 1.3
EL = math.radians(33.0)          # kamera yükselme açısı: zemin ekranda yukarı doğru "dizilir"

gu = Vector((math.cos(GATE_ANG), math.sin(GATE_ANG)))
GATE_PT = PEN_C + gu * PEN_R
CAM_AZ = GATE_ANG + math.radians(40)
_FC = Vector((math.cos(CAM_AZ), math.sin(CAM_AZ)))   # yerde: kapıdan kameraya
_RT = Vector((-_FC.y, _FC.x))
_f = -_FC
RIGHT = Vector((_f.y, -_f.x)).normalized()           # ekranda sağ
RIGHT3 = RIGHT.to_3d()
FWD3 = (-_FC).to_3d()                                # kameradan uzağa (yerde)
VIEW = Vector((-_FC.x * math.cos(EL), -_FC.y * math.cos(EL), -math.sin(EL)))   # bakış yönü
LDIR = (-RIGHT3 * 0.55 + _FC.to_3d() * 0.35 + Vector((0, 0, 0.75))).normalized()  # boyadaki ışık: sol üst önden


def hfun(x, y):
    """Ağıl düzlükte; arkada tepe katmanları yükselir (minyatürde üst üste dizilen zemin)."""
    p = Vector((x, y))
    depth = (p - GATE_PT).dot(-_FC)          # kameradan uzaklaştıkça
    h = 0.0
    h += 1.6 * smooth(PEN_R * 2 + 0.8, PEN_R * 2 + 5.5, depth)
    h += 1.4 * smooth(PEN_R * 2 + 6.0, PEN_R * 2 + 10.0, depth)
    h += 0.35 * smooth(PEN_R * 2 + 1.0, PEN_R * 2 + 9.0, depth) * math.sin((p.dot(RIGHT)) * 0.45 + 0.7)
    h += 0.05 * noise.noise(Vector((x * 0.3, y * 0.3, 0.3)))
    return h


def ring_pos(a, r=PEN_R):
    return Vector((PEN_C.x + r * math.cos(a), PEN_C.y + r * math.sin(a)))


# ---------------------------------------------------------------- boya malzemesi
def _paper_grain(N, L):
    """Ekran uzayında kâğıt: ince lif greni + geniş, çok hafif sulu boya lekesi. Çarpan (0,9-1,03) döner."""
    tc = N.new('ShaderNodeTexCoord')
    sc = N.new('ShaderNodeVectorMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = (16.0, 9.0, 1.0)
    L.new(tc.outputs['Window'], sc.inputs[0])
    fine = N.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 34.0; fine.inputs['Detail'].default_value = 8.0
    fine.inputs['Roughness'].default_value = 0.7
    L.new(sc.outputs[0], fine.inputs['Vector'])
    wash = N.new('ShaderNodeTexNoise'); wash.inputs['Scale'].default_value = 0.35; wash.inputs['Detail'].default_value = 3.0
    L.new(sc.outputs[0], wash.inputs['Vector'])
    a = N.new('ShaderNodeMath'); a.operation = 'MULTIPLY_ADD'; a.inputs[1].default_value = 0.08; a.inputs[2].default_value = 0.96
    L.new(fine.outputs['Fac'], a.inputs[0])
    b = N.new('ShaderNodeMath'); b.operation = 'MULTIPLY_ADD'; b.inputs[1].default_value = 0.07
    L.new(wash.outputs['Fac'], b.inputs[0]); L.new(a.outputs[0], b.inputs[2])
    c = N.new('ShaderNodeMath'); c.operation = 'SUBTRACT'; c.inputs[1].default_value = 0.035
    L.new(b.outputs[0], c.inputs[0])
    return c.outputs[0]


def paint(name, color, shade=(0.80, 0.78, 0.88), mottle=0.06, pattern=None, pcol=None, pscale=5.0, pwidth=0.05,
          gold=False, grad=None, soft=0.22):
    """Boyalı yüzey (ışıksız): düz renk, sol üstten yumuşak iki ton, pigment lekesi, kâğıt greni.
    pattern: 'yun' (kıvırcık kontur ağı), 'tas' (düzensiz taş örgüsü), 'benek' (seyrek nokta), 'sunger' (kaya delikleri)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    for n in list(N):
        if n.type == 'BSDF_PRINCIPLED':
            N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    base = N.new('ShaderNodeRGB'); base.outputs[0].default_value = (*s2l(color), 1)
    col = base.outputs[0]
    tc = N.new('ShaderNodeTexCoord')
    if grad is not None:
        # nesne ekseninde renk geçişi (kaya: koyu dip, açık tepe; gök: ufukta açık)
        c2, axis, lo, hi = grad
        sp = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sp.inputs[0])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = lo; mr.inputs['From Max'].default_value = hi
        L.new(sp.outputs[axis], mr.inputs['Value'])
        cc = N.new('ShaderNodeRGB'); cc.outputs[0].default_value = (*s2l(c2), 1)
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L.new(mr.outputs[0], mx.inputs['Factor']); L.new(col, mx.inputs['A']); L.new(cc.outputs[0], mx.inputs['B'])
        col = mx.outputs['Result']
    if pattern is not None:
        pc = N.new('ShaderNodeRGB'); pc.outputs[0].default_value = (*s2l(pcol or (0.35, 0.22, 0.14)), 1)
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (pscale, pscale, pscale * (1.5 if pattern == 'tas' else 1.0))
        L.new(tc.outputs['Object'], mp.inputs['Vector'])
        if pattern in ('yun', 'tas'):
            vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'
            vo.inputs['Randomness'].default_value = 0.85
            L.new(mp.outputs[0], vo.inputs['Vector'])
            rp = N.new('ShaderNodeMapRange'); rp.inputs['From Min'].default_value = pwidth
            rp.inputs['From Max'].default_value = pwidth * 0.35
            rp.inputs['To Max'].default_value = 0.8 if pattern == 'yun' else 1.0
            L.new(vo.outputs['Distance'], rp.inputs['Value'])
            fac = rp.outputs[0]
            if pattern == 'tas':
                # taş başına ton farkı
                vc = N.new('ShaderNodeTexVoronoi'); vc.inputs['Randomness'].default_value = 0.85
                L.new(mp.outputs[0], vc.inputs['Vector'])
                hs = N.new('ShaderNodeHueSaturation')
                vm = N.new('ShaderNodeMath'); vm.operation = 'MULTIPLY_ADD'; vm.inputs[1].default_value = 0.16; vm.inputs[2].default_value = 0.9
                sep = N.new('ShaderNodeSeparateColor'); L.new(vc.outputs['Color'], sep.inputs[0])
                L.new(sep.outputs[0], vm.inputs[0])
                L.new(col, hs.inputs['Color']); L.new(vm.outputs[0], hs.inputs['Value'])
                col = hs.outputs['Color']
            else:
                # kıvırcık: her hücrede küçük iç halka (yarım kıvrım)
                v2 = N.new('ShaderNodeTexVoronoi'); v2.inputs['Randomness'].default_value = 0.85
                L.new(mp.outputs[0], v2.inputs['Vector'])
                rg = N.new('ShaderNodeMapRange'); rg.interpolation_type = 'SMOOTHSTEP'
                ring = N.new('ShaderNodeMath'); ring.operation = 'PINGPONG'; ring.inputs[1].default_value = 0.5
                ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'
                sub = N.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = 0.2
                L.new(v2.outputs['Distance'], sub.inputs[0]); L.new(sub.outputs[0], ab.inputs[0])
                rg.inputs['From Min'].default_value = 0.035; rg.inputs['From Max'].default_value = 0.012
                rg.inputs['To Max'].default_value = 0.45
                L.new(ab.outputs[0], rg.inputs['Value'])
                mxf = N.new('ShaderNodeMath'); mxf.operation = 'MAXIMUM'
                L.new(fac, mxf.inputs[0]); L.new(rg.outputs[0], mxf.inputs[1])
                fac = mxf.outputs[0]
        else:
            vo = N.new('ShaderNodeTexVoronoi')
            vo.inputs['Randomness'].default_value = 1.0
            L.new(mp.outputs[0], vo.inputs['Vector'])
            rp = N.new('ShaderNodeMapRange'); rp.interpolation_type = 'SMOOTHSTEP'
            rp.inputs['From Min'].default_value = pwidth
            rp.inputs['From Max'].default_value = pwidth * 0.7
            L.new(vo.outputs['Distance'], rp.inputs['Value'])
            fac = rp.outputs[0]
            if pattern == 'benek':
                # seyrek: yalnız bazı hücrelerde nokta
                sep = N.new('ShaderNodeSeparateColor'); L.new(vo.outputs['Color'], sep.inputs[0])
                gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.55
                L.new(sep.outputs[0], gt.inputs[0])
                ml = N.new('ShaderNodeMath'); ml.operation = 'MULTIPLY'
                L.new(fac, ml.inputs[0]); L.new(gt.outputs[0], ml.inputs[1])
                fac = ml.outputs[0]
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L.new(fac, mx.inputs['Factor']); L.new(col, mx.inputs['A']); L.new(pc.outputs[0], mx.inputs['B'])
        col = mx.outputs['Result']
    # iki ton: n·ışık
    gm = N.new('ShaderNodeNewGeometry')
    dp = N.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'; dp.inputs[1].default_value = LDIR
    L.new(gm.outputs['Normal'], dp.inputs[0])
    tr = N.new('ShaderNodeMapRange'); tr.interpolation_type = 'SMOOTHSTEP'
    tr.inputs['From Min'].default_value = 0.12 - soft / 2; tr.inputs['From Max'].default_value = 0.12 + soft / 2
    L.new(dp.outputs['Value'], tr.inputs['Value'])
    sh = N.new('ShaderNodeMix'); sh.data_type = 'RGBA'; sh.blend_type = 'MULTIPLY'
    sh.inputs['B'].default_value = (*shade, 1)
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(tr.outputs[0], inv.inputs[1])
    L.new(inv.outputs[0], sh.inputs['Factor']); L.new(col, sh.inputs['A'])
    col = sh.outputs['Result']
    # pigment lekesi (nesne uzayı) + kâğıt (ekran uzayı)
    mt = N.new('ShaderNodeTexNoise'); mt.inputs['Scale'].default_value = 2.5; mt.inputs['Detail'].default_value = 3.0
    L.new(tc.outputs['Object'], mt.inputs['Vector'])
    mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY_ADD'; mm.inputs[1].default_value = mottle * 2
    mm.inputs[2].default_value = 1.0 - mottle
    L.new(mt.outputs['Fac'], mm.inputs[0])
    pg = _paper_grain(N, L)
    tot = N.new('ShaderNodeMath'); tot.operation = 'MULTIPLY'
    L.new(mm.outputs[0], tot.inputs[0]); L.new(pg, tot.inputs[1])
    hs = N.new('ShaderNodeHueSaturation'); L.new(col, hs.inputs['Color']); L.new(tot.outputs[0], hs.inputs['Value'])
    col = hs.outputs['Color']
    if gold:
        # altın varak: ince parlak benekler + hafif pırıltı
        gn = N.new('ShaderNodeTexNoise'); gn.inputs['Scale'].default_value = 60.0; gn.inputs['Detail'].default_value = 6.0
        L.new(tc.outputs['Object'], gn.inputs['Vector'])
        gr = N.new('ShaderNodeValToRGB')
        gr.color_ramp.elements[0].position = 0.45; gr.color_ramp.elements[0].color = (0, 0, 0, 1)
        gr.color_ramp.elements[1].position = 0.75; gr.color_ramp.elements[1].color = (1, 1, 1, 1)
        L.new(gn.outputs['Fac'], gr.inputs['Fac'])
        gm2 = N.new('ShaderNodeMix'); gm2.data_type = 'RGBA'; gm2.blend_type = 'SCREEN'
        gm2.inputs['B'].default_value = (*s2l((0.55, 0.45, 0.22)), 1)
        sepg = N.new('ShaderNodeSeparateColor'); L.new(gr.outputs['Color'], sepg.inputs[0])
        L.new(sepg.outputs[0], gm2.inputs['Factor']); L.new(col, gm2.inputs['A'])
        col = gm2.outputs['Result']
    em = N.new('ShaderNodeEmission')
    L.new(col, em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.0
    L.new(em.outputs[0], out.inputs['Surface'])
    return m


def flat_emit(name, color, strength=1.0, paper=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    for n in list(N):
        if n.type == 'BSDF_PRINCIPLED':
            N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    em = N.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = strength
    if paper:
        base = N.new('ShaderNodeRGB'); base.outputs[0].default_value = (*s2l(color), 1)
        hs = N.new('ShaderNodeHueSaturation'); L.new(base.outputs[0], hs.inputs['Color'])
        L.new(_paper_grain(N, L), hs.inputs['Value'])
        L.new(hs.outputs['Color'], em.inputs['Color'])
    else:
        em.inputs['Color'].default_value = (*s2l(color), 1)
    L.new(em.outputs[0], out.inputs['Surface'])
    return m


# ---------------------------------------------------------------- palet (maden renkleri, sıcak akşam)
SEPIA = (0.30, 0.18, 0.10)
M_GROUND = paint('zemin', (0.66, 0.70, 0.42), mottle=0.05, pattern='benek', pcol=(0.93, 0.86, 0.66), pscale=2.2, pwidth=0.075,
                 grad=((0.80, 0.72, 0.44), 'Z', 0.0, 3.2), soft=0.5, shade=(0.88, 0.88, 0.92))
M_HILLROCK = paint('kaya', (0.62, 0.50, 0.66), mottle=0.06, pattern='sunger', pcol=(0.46, 0.34, 0.50), pscale=7.0, pwidth=0.12,
                   grad=((0.94, 0.80, 0.78), 'Z', -0.3, 1.1), soft=0.3)
M_HILLROCK2 = paint('kaya2', (0.80, 0.56, 0.40), mottle=0.06, pattern='sunger', pcol=(0.62, 0.40, 0.28), pscale=7.0, pwidth=0.12,
                    grad=((0.97, 0.84, 0.66), 'Z', -0.3, 1.1), soft=0.3)
M_WALL = paint('duvar', (0.88, 0.78, 0.64), pattern='tas', pcol=(0.42, 0.28, 0.18), pscale=3.1, pwidth=0.055, soft=0.25,
               shade=(0.80, 0.76, 0.84))
M_CAP = paint('duvar_kapak', (0.93, 0.86, 0.74), pattern='tas', pcol=(0.42, 0.28, 0.18), pscale=2.2, pwidth=0.05, soft=0.25)
WOOL_COLS = [(0.97, 0.94, 0.86), (0.96, 0.92, 0.84), (0.84, 0.68, 0.48), (0.97, 0.93, 0.85), (0.40, 0.31, 0.28),
             (0.95, 0.91, 0.82), (0.90, 0.88, 0.84), (0.86, 0.72, 0.52)]
M_WOOLS = [paint('yun_%d' % k, c, pattern='yun', pcol=((0.62, 0.52, 0.42) if sum(c) > 1.2 else (0.70, 0.60, 0.52)),
                 pscale=11.0, pwidth=0.05, soft=0.3, shade=(0.84, 0.82, 0.90)) for k, c in enumerate(WOOL_COLS)]
M_FACES = [paint('yuz_%d' % k, ((0.93, 0.84, 0.74) if sum(c) > 1.2 else (0.36, 0.28, 0.25)), soft=0.3) for k, c in enumerate(WOOL_COLS)]
M_EAR_IN = paint('kulak_ic', (0.90, 0.58, 0.52), soft=0.3)
M_LEG = paint('bacak', (0.34, 0.24, 0.18), soft=0.3)
M_EYE = flat_emit('goz', (0.10, 0.06, 0.04), paper=False)
M_POUCH = paint('kese', (0.14, 0.27, 0.62), pattern='benek', pcol=(0.86, 0.68, 0.30), pscale=9.0, pwidth=0.11, soft=0.3,
                shade=(0.78, 0.78, 0.9))
M_POUCH_IN = paint('kese_ic', (0.07, 0.11, 0.30), soft=0.3)
M_GOLD = paint('altin', (0.84, 0.65, 0.28), gold=True, soft=0.35, shade=(0.82, 0.78, 0.74))
M_CORD = paint('ip', (0.80, 0.26, 0.14), soft=0.3)
M_WOOD = paint('civi', (0.52, 0.34, 0.20), soft=0.3)
M_PEBBLE = paint('cakil', (0.86, 0.38, 0.16), mottle=0.05, soft=0.3, shade=(0.80, 0.76, 0.86))
M_SLAB = paint('yassi_tas', (0.95, 0.91, 0.80), mottle=0.04, soft=0.4)
M_CYPRESS = paint('servi', (0.17, 0.38, 0.28), pattern='tas', pcol=(0.10, 0.25, 0.18), pscale=9.0, pwidth=0.06, soft=0.3)
M_TREE = paint('agac', (0.30, 0.52, 0.34), pattern='benek', pcol=(0.97, 0.88, 0.86), pscale=8.0, pwidth=0.12, soft=0.3)
M_TRUNK = paint('govde', (0.46, 0.30, 0.20), soft=0.3)
M_GRASS = flat_emit('ot', (0.22, 0.42, 0.26))
M_GRASS2 = flat_emit('ot2', (0.36, 0.52, 0.28))
M_FLOWER = [flat_emit('cicek_k', (0.84, 0.24, 0.14)), flat_emit('cicek_b', (0.98, 0.95, 0.86)),
            flat_emit('cicek_l', (0.20, 0.34, 0.70))]
M_SKY = paint('gok', (0.86, 0.66, 0.30), gold=True, grad=((0.98, 0.85, 0.58), 'Z', 3.0, -2.0), soft=0.0, mottle=0.03)
M_CLOUD = paint('bulut', (0.97, 0.93, 0.88), grad=((0.80, 0.76, 0.90), 'Z', 0.2, -0.3), soft=0.4)
M_CREAM = flat_emit('pervaz_kagit', (0.94, 0.89, 0.77))
M_LAPIS = flat_emit('pervaz_lacivert', (0.13, 0.24, 0.56))
M_VERM = flat_emit('pervaz_kirmizi', (0.78, 0.24, 0.12))
M_BGOLD = paint('pervaz_altin', (0.85, 0.67, 0.30), gold=True, soft=0.0, mottle=0.03)


# ---------------------------------------------------------------- zemin
def build_ground():
    bm = bmesh.new()
    X0, X1, Y0, Y1, n = -22.0, 22.0, -10.0, 34.0, 110
    ny = int(n * (Y1 - Y0) / (X1 - X0))
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(n + 1):
            x = X0 + (X1 - X0) * i / n
            y = Y0 + (Y1 - Y0) * j / ny
            row.append(bm.verts.new((x, y, hfun(x, y))))
        grid.append(row)
    for j in range(ny):
        for i in range(n):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    ob = bm_obj('zemin', bm, [M_GROUND])
    return ob


def build_sky():
    """Altın gök: arkada kameraya bakan büyük düzlem + iki stilize bulut kuşağı."""
    c = GATE_PT.to_3d() + FWD3 * 30.0
    c.z = 6.0
    up = Vector((0, 0, 1))
    n_ = -VIEW
    x_ = RIGHT3
    y_ = n_.cross(x_).normalized()
    bm = bmesh.new()
    vs = [bm.verts.new(c + x_ * sx * 60 + y_ * sy * 30) for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(vs)
    sky = bm_obj('gok', bm, [M_SKY], noline=True)
    # gök geçişi nesne Z'sine göre: düzlemin yerel Z = dünya Z
    r = rng(17)
    for k, (u, h, w) in enumerate(((-4.5, 4.4, 3.2), (3.8, 4.9, 2.6), (8.5, 4.2, 2.0))):
        bm = bmesh.new()
        pts = []
        nlob = 7
        for s in range(64):
            t = 2 * math.pi * s / 64
            rr = 1.0 + 0.22 * abs(math.sin(nlob * t / 2 + k))
            pts.append((math.cos(t) * w * rr, math.sin(t) * w * 0.22 * rr))
        vs = [bm.verts.new((px, 0, pz)) for (px, pz) in pts]
        f = bm.faces.new(vs)
        ex = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm, verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0.05, 0))
        cl = bm_obj('bulut_%d' % k, bm, [M_CLOUD], smooth_shade=False)
        pos = GATE_PT.to_3d() + FWD3 * 22.0 + RIGHT3 * u
        pos.z = h + 3.0
        cl.matrix_world = Matrix.Translation(pos) @ Matrix((x_, -n_, y_)).transposed().to_4x4()
    return sky


def build_backdrop():
    """Tepede süngerimsi pastel kayalar, servi ve çiçekli ağaç (sol ve orta arkada; sağ alt boş)."""
    fwd = FWD3
    # kaya kümeleri: (sağ kayma, derinlik, ölçek, malzeme)
    for k, (u, dep, s, m) in enumerate(((-6.8, 11.5, 1.2, M_HILLROCK), (-4.6, 13.8, 0.8, M_HILLROCK2), (6.4, 14.5, 1.0, M_HILLROCK),
                                        (9.2, 12.2, 0.75, M_HILLROCK2), (1.5, 16.5, 0.9, M_HILLROCK2))):
        p = GATE_PT.to_3d() + fwd * dep + RIGHT3 * u
        z = hfun(p.x, p.y)
        bm = bmesh.new()
        r = rng(400 + k)
        for j in range(6):
            off = Vector((r.uniform(-0.9, 0.9) * s, r.uniform(-0.4, 0.4) * s, 0))
            hh = r.uniform(0.5, 1.2) * s * (1.3 if j < 2 else 1.0)
            blob(bm, Vector((p.x, p.y, z)) + off + Vector((0, 0, hh * 0.35)), (0.5 * s, 0.45 * s, hh), subdiv=3, amp=0.12,
                 seed=400 + k * 10 + j, curls=0.1, curl_scale=4.0)
        bm_obj('kaya_%d' % k, bm, [m])
    # serviler
    for k, (u, dep, s) in enumerate(((-3.2, 12.2, 1.0), (-2.5, 12.8, 0.8), (4.2, 11.6, 0.9))):
        p = GATE_PT.to_3d() + fwd * dep + RIGHT3 * u
        z = hfun(p.x, p.y)
        bm = bmesh.new()
        tube(bm, Vector((p.x, p.y, z - 0.1)), Vector((p.x, p.y, z + 0.5 * s)), 0.07 * s, 0.06 * s, seg=8)
        bm_obj('servi_govde_%d' % k, bm, [M_TRUNK])
        bm = bmesh.new()
        prof = [(0.0, 0.25), (0.28, 0.45), (0.36, 1.0), (0.32, 1.8), (0.2, 2.6), (0.0, 3.1)]
        seg = 16
        rings = []
        for (rr, zz) in prof[1:-1]:
            rings.append([bm.verts.new((p.x + rr * s * math.cos(2 * math.pi * t / seg), p.y + rr * s * math.sin(2 * math.pi * t / seg),
                                        z + zz * s)) for t in range(seg)])
        b0 = bm.verts.new((p.x, p.y, z + prof[0][1] * s)); b1 = bm.verts.new((p.x, p.y, z + prof[-1][1] * s))
        for t in range(seg):
            bm.faces.new((b0, rings[0][(t + 1) % seg], rings[0][t]))
            bm.faces.new((b1, rings[-1][t], rings[-1][(t + 1) % seg]))
        for j in range(len(rings) - 1):
            for t in range(seg):
                bm.faces.new((rings[j][t], rings[j][(t + 1) % seg], rings[j + 1][(t + 1) % seg], rings[j + 1][t]))
        bm_obj('servi_%d' % k, bm, [M_CYPRESS], subsurf=1)
    # çiçekli ağaç
    for k, (u, dep, s) in enumerate(((-8.8, 9.6, 1.0), (7.6, 12.8, 0.85))):
        p = GATE_PT.to_3d() + fwd * dep + RIGHT3 * u
        z = hfun(p.x, p.y)
        bm = bmesh.new()
        tube(bm, Vector((p.x, p.y, z - 0.1)), Vector((p.x + 0.1, p.y, z + 1.2 * s)), 0.1 * s, 0.06 * s, seg=8)
        tube(bm, Vector((p.x + 0.05, p.y, z + 0.8 * s)), Vector((p.x - 0.35 * s, p.y, z + 1.4 * s)), 0.05 * s, 0.03 * s, seg=6)
        bm_obj('agac_govde_%d' % k, bm, [M_TRUNK])
        bm = bmesh.new()
        r = rng(500 + k)
        for j in range(5):
            blob(bm, Vector((p.x + r.uniform(-0.5, 0.5) * s, p.y + r.uniform(-0.3, 0.3) * s, z + (1.5 + r.uniform(-0.2, 0.4)) * s)),
                 (0.55 * s, 0.5 * s, 0.45 * s), subdiv=3, amp=0.1, seed=500 + j, curls=0.08, curl_scale=5.0)
        bm_obj('agac_tac_%d' % k, bm, [M_TREE])


# ---------------------------------------------------------------- ağıl
def sweep_ring(name, a0, a1, prof, radius, center, m, step=0.05):
    bm = bmesh.new()
    n = max(2, int(abs(a1 - a0) * radius / step))
    rows = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        c, s = math.cos(a), math.sin(a)
        wob = 0.03 * noise.noise(Vector((c * 3, s * 3, 0.5)))
        row = []
        for (dr, zz) in prof:
            x, y = center.x + (radius + dr) * c, center.y + (radius + dr) * s
            row.append(bm.verts.new((x, y, hfun(x, y) + zz + (wob if zz > 0.1 else 0))))
        rows.append(row)
    k = len(prof)
    for i in range(n):
        for j in range(k - 1):
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    if abs(a1 - a0) < 2 * math.pi - 1e-3:
        for row in (rows[0], list(reversed(rows[-1]))):
            bm.faces.new(row)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm_obj(name, bm, [m])


WALL_PROF = [(0.24, -0.1), (0.23, 0.0), (0.2, WALL_H * 0.6), (0.17, WALL_H - 0.02), (0.1, WALL_H + 0.05), (0.0, WALL_H + 0.08),
             (-0.1, WALL_H + 0.05), (-0.17, WALL_H - 0.02), (-0.2, WALL_H * 0.6), (-0.23, 0.0), (-0.24, -0.1)]


def build_pen():
    a0 = GATE_ANG + GAP_HALF
    a1 = GATE_ANG - GAP_HALF + 2 * math.pi
    w = sweep_ring('duvar', a0, a1, WALL_PROF, PEN_R, PEN_C, M_WALL)
    posts = []
    for side, sgn in (('on', 1), ('arka', -1)):
        a = GATE_ANG + sgn * GAP_HALF
        p = ring_pos(a)
        z = hfun(p.x, p.y)
        bm = bmesh.new()
        tube(bm, Vector((p.x, p.y, z - 0.1)), Vector((p.x, p.y, z + POST_H)), POST_R, POST_R * 0.92, seg=24)
        ob = bm_obj('direk_' + side, bm, [M_WALL])
        bm = bmesh.new()
        blob(bm, Vector((p.x, p.y, z + POST_H + 0.05)), (POST_R * 1.25, POST_R * 1.2, 0.12), subdiv=3, amp=0.08, seed=30 + sgn)
        bm_obj('direk_kapak_' + side, bm, [M_CAP])
        posts.append((side, a, p))
    return posts


# ---------------------------------------------------------------- ot tutamları, çiçekler (düzenli aralıklı, minyatürdeki gibi)
def grass_tufts(avoid):
    r = rng(123)
    bm1, bm2 = bmesh.new(), bmesh.new()
    bf = [bmesh.new() for _ in M_FLOWER]
    k = 0
    # düzenli ızgara + küçük sapma
    step = 0.75
    for gx in range(-40, 41):
        for gy in range(-30, 60):
            p = GATE_PT + RIGHT * (gx * step + (gy % 2) * step * 0.5) + (-_FC) * (gy * step * 0.8)
            p += Vector((r.uniform(-0.2, 0.2), r.uniform(-0.2, 0.2)))
            if abs(p.dot(RIGHT) - GATE_PT.dot(RIGHT)) > 14 or (p - GATE_PT).dot(-_FC) > 14 or (p - GATE_PT).dot(-_FC) < -6:
                continue
            if any(f(p) for f in avoid):
                continue
            if r.random() < 0.3:
                continue
            z = hfun(p.x, p.y)
            s = r.uniform(0.8, 1.15)
            bm = bm1 if r.random() < 0.55 else bm2
            nb = 5
            for b in range(nb):
                ang = -0.9 + 1.8 * b / (nb - 1) + r.uniform(-0.1, 0.1)
                tip = Vector((p.x, p.y, z)) + RIGHT3 * math.sin(ang) * 0.13 * s + Vector((0, 0, math.cos(ang) * 0.2 * s))
                base = Vector((p.x, p.y, z - 0.01))
                side = RIGHT3 * 0.018 * s
                v0 = bm.verts.new(base - side); v1 = bm.verts.new(base + side); v2 = bm.verts.new(tip)
                bm.faces.new((v0, v1, v2))
            if r.random() < 0.35:
                fb = bf[r.randrange(len(bf))]
                c = Vector((p.x, p.y, z + 0.2 * s)) + RIGHT3 * r.uniform(-0.05, 0.05)
                n_ = -VIEW
                x_ = RIGHT3; y_ = n_.cross(x_).normalized()
                ring = [fb.verts.new(c + (x_ * math.cos(2 * math.pi * t / 6) + y_ * math.sin(2 * math.pi * t / 6)) * 0.035) for t in range(6)]
                fb.faces.new(ring)
            k += 1
    bm_obj('ot1', bm1, [M_GRASS], smooth_shade=False, noline=True)
    bm_obj('ot2', bm2, [M_GRASS2], smooth_shade=False, noline=True)
    for j, fb in enumerate(bf):
        bm_obj('cicek_%d' % j, fb, [M_FLOWER[j]], smooth_shade=False, noline=True)


# ---------------------------------------------------------------- koyun (süslemeli minyatür koyunu: kıvırcık yün, ince bacak)
def build_sheep(i):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('koyun_%d' % i, None))
    s = r.uniform(0.95, 1.05)
    bob = link(bpy.data.objects.new('koyun_%d_govde' % i, None))
    bob.parent = root
    bob.scale = (s, s, s)
    bm = bmesh.new()
    blob(bm, Vector((0, 0, 0.6)), (0.48, 0.27, 0.27), subdiv=5, amp=0.03, seed=i * 7, curls=0.05, curl_scale=5.0)
    blob(bm, Vector((-0.46, 0, 0.66)), (0.08, 0.06, 0.09), subdiv=3, amp=0.05, seed=i * 7 + 1, curls=0.1, curl_scale=5.0)
    body = bm_obj('koyun_%d_yun' % i, bm, [M_WOOLS[i]])
    body.parent = bob
    head = link(bpy.data.objects.new('koyun_%d_bas' % i, None))
    head.parent = bob
    head.location = (0.42, 0, 0.74)
    bm = bmesh.new()
    rot = Quaternion((0, 1, 0), math.radians(28))
    blob(bm, Vector((0.12, 0, -0.03)), (0.16, 0.085, 0.095), subdiv=3, amp=0.0, seed=1, rot=rot, mi=0)
    for sy in (-1, 1):
        blob(bm, Vector((0.03, sy * 0.1, 0.03)), (0.075, 0.03, 0.022), subdiv=2, amp=0.0, seed=2,
             rot=Quaternion((0, 0, 1), sy * 0.9) @ Quaternion((1, 0, 0), sy * 0.4), mi=2)
        blob(bm, Vector((0.14, sy * 0.066, 0.02)), (0.017, 0.012, 0.019), subdiv=2, amp=0.0, seed=3, mi=1)
    blob(bm, Vector((0.04, 0, 0.06)), (0.09, 0.08, 0.06), subdiv=3, amp=0.05, seed=i + 77, mi=3, curls=0.12, curl_scale=6.0)
    hd = bm_obj('koyun_%d_yuz' % i, bm, [M_FACES[i], M_EYE, M_EAR_IN, M_WOOLS[i]])
    hd.parent = head
    legs = []
    for k, (lx, ly) in enumerate(((0.25, 0.12), (0.25, -0.12), (-0.25, 0.12), (-0.25, -0.12))):
        leg = link(bpy.data.objects.new('koyun_%d_bacak_%d' % (i, k), None))
        leg.parent = bob
        leg.location = (lx, ly, 0.44)
        bm = bmesh.new()
        tube(bm, Vector((0, 0, 0.03)), Vector((0, 0, -0.4)), 0.032, 0.024, seg=8)
        blob(bm, Vector((0.008, 0, -0.415)), (0.034, 0.028, 0.028), subdiv=2, amp=0.0, seed=4)
        g = bm_obj('koyun_%d_bacak_%d_m' % (i, k), bm, [M_LEG])
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


INSIDE = GATE_PT - gu * 1.1
OUT1 = GATE_PT - _RT * 0.8 + _FC * 1.3
SPOTS = []
_rs = rng(77)
_tries = 0
while len(SPOTS) < N_SHEEP:
    _tries += 1
    a = _rs.uniform(0, 2 * math.pi)
    rr = _rs.uniform(0.3, PEN_R - 0.85)
    q = PEN_C + Vector((rr * math.cos(a), rr * math.sin(a)))
    if (q - INSIDE).length < 0.9:
        continue
    if all((q - o).length > (1.15 if _tries < 5000 else 0.95) for o in SPOTS):
        SPOTS.append(q)
SPOTS.sort(key=lambda q: -(q - INSIDE).length)
START = [GATE_PT - _RT * 11.0 + _FC * 2.6, GATE_PT - _RT * 3.2 + _FC * 2.2]
paths = []
for i in range(N_SHEEP):
    jit = _FC * (0.14 * ((i * 7) % 3 - 1))
    paths.append(Path([START[0] + jit, START[1] + jit * 0.7, OUT1, GATE_PT, INSIDE, SPOTS[i]]))

# ---------------------------------------------------------------- sahneyi kur
build_ground()
build_sky()
build_backdrop()
posts = build_pen()
front_post = [p for p in posts if p[0] == 'on'][0]
_, FA, FP = front_post
TO_CAM0 = _FC
PEB_R = 0.085
ROW_GAP = 0.21
ROW_START = FP + TO_CAM0 * (POST_R + 0.85) - RIGHT * 0.05
ROW_DIR = RIGHT
ROW_CENTER = ROW_START + ROW_DIR * (ROW_GAP * 3.5)


def near_path(p):
    return min((q - p).length for q in paths[0].p[::3]) < 0.6


grass_tufts([lambda p: abs((p - PEN_C).length - PEN_R) < 0.4,
             lambda p: (p - ROW_CENTER).length < 1.25,
             near_path,
             lambda p: (p - FP).length < POST_R + 0.35,
             lambda p: (p - ring_pos(GATE_ANG - GAP_HALF)).length < POST_R + 0.35,
             lambda p: (p - PEN_C).length < PEN_R - 0.3])

slab_c = ROW_CENTER
bm = bmesh.new()
blob(bm, Vector((0, 0, 0)), (ROW_GAP * 4 + 0.24, 0.32, 0.07), subdiv=3, amp=0.05, seed=55, nscale=1.3)
SLAB = bm_obj('yassi_tas', bm, [M_SLAB])
SLAB.location = (slab_c.x, slab_c.y, hfun(slab_c.x, slab_c.y) + 0.0)
SLAB.rotation_euler = (0, 0, math.atan2(ROW_DIR.y, ROW_DIR.x))
SLAB_TOP = hfun(slab_c.x, slab_c.y) + 0.068
print('t sahne %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- çivi, kese (lacivert, altın bantlı)
PEG_Z = 1.0
_out = Vector((math.cos(FA), math.sin(FA)))
pegdir2 = (TO_CAM0 * 0.8 + _out * 0.2).normalized()
pegdir = Vector((pegdir2.x, pegdir2.y, 0.18)).normalized()
z_post = hfun(FP.x, FP.y)
peg_base = Vector((FP.x, FP.y, z_post + PEG_Z)) + pegdir2.to_3d() * (POST_R - 0.08)
PEG_LEN = 0.3
bm = bmesh.new()
tube(bm, peg_base, peg_base + pegdir * PEG_LEN, 0.03, 0.026, seg=10)
blob(bm, peg_base + pegdir * PEG_LEN, (0.03, 0.03, 0.03), subdiv=2)
bm_obj('civi', bm, [M_WOOD])
HANG = peg_base + pegdir * (PEG_LEN - 0.07) + Vector((0, 0, 0.02))

DROP = 0.54
PROF = [(0.0, 0.0), (0.13, 0.012), (0.2, 0.06), (0.225, 0.13), (0.215, 0.21), (0.18, 0.27), (0.13, 0.31),
        (0.112, 0.335), (0.13, 0.36), (0.165, 0.395), (0.185, 0.42)]
LIP_Z = 0.42 - DROP
NECK_Z = 0.33 - DROP


def build_pouch():
    seg = 32
    bm = bmesh.new()
    bottom = bm.verts.new((0, 0, -DROP))
    rings = []
    for k, (r_, z) in enumerate(PROF[1:]):
        ring = []
        for s in range(seg):
            th = 2 * math.pi * s / seg
            dz = 0.0
            rr = r_
            if k >= len(PROF) - 3:
                dz = 0.018 * math.sin(6 * th) * (k - (len(PROF) - 4)) / 2      # ağız: dalgalı kumaş
            if 2 <= k <= 5:
                rr += 0.006 * math.sin(9 * th)                                     # gövdede yumuşak kırışık
            ring.append(bm.verts.new((rr * math.cos(th), rr * math.sin(th) * 0.92, z - DROP + dz)))
        rings.append(ring)
    for s in range(seg):
        bm.faces.new((bottom, rings[0][s], rings[0][(s + 1) % seg]))
    for k in range(len(rings) - 1):
        for s in range(seg):
            bm.faces.new((rings[k][s], rings[k + 1][s], rings[k + 1][(s + 1) % seg], rings[k][(s + 1) % seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = bm_obj('kese', bm, [M_POUCH])
    sol = ob.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.014; sol.material_offset = 1
    ob.data.materials.append(M_POUCH_IN)
    ss = ob.modifiers.new('ss', 'SUBSURF'); ss.levels = 1; ss.render_levels = 1
    bm = bmesh.new()
    blob(bm, Vector((0, 0, NECK_Z + 0.012)), (0.105, 0.095, 0.012), subdiv=2)
    inn = bm_obj('kese_ic', bm, [M_POUCH_IN], noline=True)
    inn.parent = ob
    # altın bantlar: boğazda ve gövdenin ortasında
    gb = bmesh.new()
    for (zc, rad, th_) in ((NECK_Z + 0.004, 0.118, 0.012), (0.15 - DROP, 0.228, 0.01)):
        n = 40
        for s in range(n):
            a0_, a1_ = 2 * math.pi * s / n, 2 * math.pi * (s + 1) / n
            p0 = Vector((rad * math.cos(a0_), rad * math.sin(a0_) * 0.92, zc))
            p1 = Vector((rad * math.cos(a1_), rad * math.sin(a1_) * 0.92, zc))
            tube(gb, p0, p1, th_, th_, seg=6)
    return ob, gb


pouch, gold_bm = build_pouch()
pouch.location = HANG
pouch.rotation_mode = 'QUATERNION'
_tilt_axis = Vector((-TO_CAM0.y, TO_CAM0.x, 0)).normalized()
POUCH_Q0 = Quaternion(_tilt_axis, math.radians(-10))
pouch.rotation_quaternion = POUCH_Q0
_back = POUCH_Q0.inverted() @ (-TO_CAM0.to_3d()); _back.z = 0; _back.normalize()
POUCH_OFF = -_back * 0.17
pouch.data.transform(Matrix.Translation(POUCH_OFF))
for ch in pouch.children:
    ch.location = POUCH_OFF
gold_bm.transform(Matrix.Translation(POUCH_OFF))
gband = bm_obj('kese_altin', gold_bm, [M_GOLD])
gband.parent = pouch
_front = -_back
_side = Vector((-_front.y, _front.x, 0))
cord_bm = bmesh.new()
_kn = POUCH_OFF + _front * 0.12 + Vector((0, 0, NECK_Z + 0.006))
tube(cord_bm, _kn, _kn + _front * 0.03 + _side * 0.06 + Vector((0, 0, -0.1)), 0.011, 0.009, seg=6)
tube(cord_bm, _kn, _kn + _front * 0.03 - _side * 0.04 + Vector((0, 0, -0.12)), 0.011, 0.009, seg=6)
blob(cord_bm, _kn + _front * 0.012, (0.022, 0.022, 0.02), subdiv=2)
for sgn in (1, -1):         # püskül
    blob(cord_bm, _kn + _front * 0.03 + _side * (0.06 if sgn > 0 else -0.04) + Vector((0, 0, -0.1 if sgn > 0 else -0.12)),
         (0.018, 0.018, 0.03), subdiv=2)
_bk = POUCH_OFF + _back * 0.115 + Vector((0, 0, NECK_Z + 0.006))
tube(cord_bm, _bk, Vector((0, 0, 0.0)), 0.01, 0.01, seg=6)
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


# ---------------------------------------------------------------- çakıllar (zencefre-aşı rengi, konturlu)
def pebble_mesh(name, seed):
    r = rng(seed)
    bm = bmesh.new()
    blob(bm, Vector((0, 0, 0)), (PEB_R * r.uniform(0.95, 1.06), PEB_R * r.uniform(0.78, 0.86), PEB_R * r.uniform(0.55, 0.62)),
         subdiv=3, amp=0.07, seed=seed, nscale=1.2)
    ob = bm_obj(name, bm, [M_PEBBLE])
    ob.rotation_mode = 'QUATERNION'
    return ob


heap_local = [POUCH_OFF + Vector((0.0, 0.0, LIP_Z - 0.035))]
for k in range(5):
    th = 2 * math.pi * k / 5 + 0.3
    heap_local.append(POUCH_OFF + Vector((0.095 * math.cos(th), 0.085 * math.sin(th), LIP_Z - 0.07)))
for k in range(3):
    th = 2 * math.pi * k / 3 + 0.9
    heap_local.append(POUCH_OFF + Vector((0.05 * math.cos(th), 0.05 * math.sin(th), LIP_Z - 0.012)))
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
                loc = p0 + Vector((0, 0, 0.22 * smoother(t / 0.28)))
            else:
                v = smoother((t - 0.28) / 0.72)
                loc = (p0 + Vector((0, 0, 0.22))).lerp(p1, v) + Vector((0, 0, 0.28 * 4 * v * (1 - v)))
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
    ease = 1.0
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
        bob.rotation_euler = (0.02 * math.sin(phase) * moving, 0.02 * math.sin(2 * phase) * moving, 0)
        bob.keyframe_insert('location', frame=f)
        bob.keyframe_insert('rotation_euler', frame=f)
        head.rotation_euler = (0.05 * math.sin(f * 0.07 + i),
                               0.06 * math.sin(phase) * moving + (0.4 + 0.2 * math.sin(f * 0.05 + i * 2)) * (1 - moving),
                               0.2 * math.sin(f * 0.03 + i) * (1 - moving))
        head.keyframe_insert('rotation_euler', frame=f)
        for k, leg in enumerate(legs):
            off = 0 if k in (0, 3) else math.pi
            leg.rotation_euler = (0, 0.4 * math.sin(phase + off) * moving, 0)
            leg.keyframe_insert('rotation_euler', frame=f)
print('t anim %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- dünya (ışık yok: her şey boyalı yüzey)
world = bpy.data.worlds.new('dunya')
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs['Color'].default_value = (*s2l((0.86, 0.68, 0.34)), 1)
bg.inputs['Strength'].default_value = 1.0

# ---------------------------------------------------------------- kamera: ortografik, dik açı (derinlik düzleşir)
cam_data = bpy.data.cameras.new('kamera')
cam_data.type = 'ORTHO'
cam_data.clip_start = 0.05
cam_data.clip_end = 200.0
cam = link(bpy.data.objects.new('kamera', cam_data))
scene.camera = cam
cam.rotation_mode = 'QUATERNION'
CAM_Q = (-VIEW).to_track_quat('Z', 'Y')           # kameranın -Z'si bakış yönü


def last_world(f):
    return (pouch_matrix(f) @ Matrix.Translation(heap_local[0])).to_translation()


P_END = last_world(N_FRAMES)
_g3 = Vector((GATE_PT.x, GATE_PT.y, hfun(GATE_PT.x, GATE_PT.y) + 0.5))
_row3 = Vector((ROW_CENTER.x, ROW_CENTER.y, SLAB_TOP))
S0 = 10.0              # geniş plan: kadraj genişliği (m)
S1 = 9.4
S_END = 1.35           # yakın plan
TGT0 = _g3.lerp(_row3, 0.35) + RIGHT3 * 1.5 + FWD3 * 1.2 + Vector((0, 0, 0.3))
TGT1 = TGT0 - RIGHT3 * 0.15
TGT_END = P_END + Vector((0, 0, -0.06)) - RIGHT3 * 0.04
PUSH0, PUSH1 = 212, 296
CAM_DIST = 40.0
ORTHO = []
for f in range(-2, N_FRAMES + 3):
    t0 = max(0.0, min(1.0, (f - 1) / (PUSH0 - 1)))
    t0 = t0 * t0 * (3 - 2 * t0) * 0.5 + t0 * 0.5
    tpos = TGT0.lerp(TGT1, t0)
    sc = S0 + (S1 - S0) * t0
    e = smoother((f - PUSH0) / (PUSH1 - PUSH0))
    # yakınlaşma: ölçek logaritmik (hız algısı düzgün), hedef ona göre
    sc = math.exp(math.log(sc) * (1 - e) + math.log(S_END) * e)
    w_ = (S0 - sc) / (S0 - S_END) if e > 0 else 0.0
    tpos = tpos.lerp(TGT_END, smoother(min(1.0, w_ * 1.08)))
    cam.location = tpos - VIEW * CAM_DIST
    cam.rotation_quaternion = CAM_Q
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_quaternion', frame=f)
    cam_data.ortho_scale = sc
    cam_data.keyframe_insert('ortho_scale', frame=f)
    ORTHO.append((f, sc))


# ---------------------------------------------------------------- pervaz: kâğıt kenar, altın cetvel, altın süslü lacivert şerit
def frame_band(bm, x0, y0, t, mi=0):
    """Dikdörtgen çerçeve şeridi: dış yarı ölçü (x0, y0), kalınlık t (kadraj genişliği birimiyle)."""
    xi, yi = x0 - t, y0 - t
    o = [bm.verts.new(v) for v in ((-x0, -y0, 0), (x0, -y0, 0), (x0, y0, 0), (-x0, y0, 0))]
    n = [bm.verts.new(v) for v in ((-xi, -yi, 0), (xi, -yi, 0), (xi, yi, 0), (-xi, yi, 0))]
    for k in range(4):
        f = bm.faces.new((o[k], o[(k + 1) % 4], n[(k + 1) % 4], n[k]))
        f.material_index = mi


border = link(bpy.data.objects.new('pervaz', None), noline=True)
border.parent = cam
border.location = (0, 0, -0.5)
HX, HY = 0.5, 0.5 * A.h / A.w
bm = bmesh.new()
lay = [(0.03, 0.008, 0), (0.008 + 0.0, 0.0025, 1), (0.0105, 0.0125, 2), (0.023, 0.0022, 1), (0.0252, 0.0012, 3)]
# (içe doğru başlangıç, kalınlık, malzeme): kâğıt, altın, lacivert, altın, kırmızı
frame_band(bm, HX + 0.02, HY + 0.02, 0.028, 0)
for (ins, th, mi) in lay[1:]:
    frame_band(bm, HX - ins, HY - ins, th, mi)
# süs: lacivert şeritte altın noktalar ve üçlü nokta kümeleri (geometrik, dinî değil)
mid = 0.0105 + 0.0125 / 2
step = 0.022
k = 0
for side in range(4):
    if side in (0, 1):
        L_ = 2 * (HX - mid)
    else:
        L_ = 2 * (HY - mid)
    nn = int(L_ / step)
    for j in range(nn + 1):
        u = -L_ / 2 + L_ * j / max(1, nn)
        if side == 0:
            c = Vector((u, -(HY - mid), 0))
        elif side == 1:
            c = Vector((u, HY - mid, 0))
        elif side == 2:
            c = Vector((-(HX - mid), u, 0))
        else:
            c = Vector((HX - mid, u, 0))
        rad = 0.0026 if (j % 2 == 0) else 0.0014
        pts = [(0, 0)] if j % 2 == 0 else [(-0.0022, 0), (0.0022, 0), (0, 0.0022)]
        for (dx, dy) in pts:
            if side >= 2:
                dx, dy = dy, dx
            ring = [bm.verts.new(c + Vector((dx + rad * math.cos(2 * math.pi * t / 10), dy + rad * math.sin(2 * math.pi * t / 10), 0.0002)))
                    for t in range(10)]
            f = bm.faces.new(ring)
            f.material_index = 1
        k += 1
me = bpy.data.meshes.new('pervaz_m')
bm.to_mesh(me); bm.free()
for m in (M_CREAM, M_BGOLD, M_LAPIS, M_VERM):
    me.materials.append(m)
bord = link(bpy.data.objects.new('pervaz_m', me), noline=True)
bord.parent = border
for f, sc in ORTHO:
    border.scale = (sc, sc, sc)
    border.keyframe_insert('scale', frame=f)

# ---------------------------------------------------------------- parıltı: son çakılda küçük, sıcak, yumuşak dört kollu yıldız
b2 = bmesh.new()
bmesh.ops.create_icosphere(b2, subdivisions=2, radius=0.0045)
me = bpy.data.meshes.new('parilti_nokta'); b2.to_mesh(me); b2.free()
spark = link(bpy.data.objects.new('parilti_nokta', me), noline=True)
M_SPARK = flat_emit('parilti_mat', (1.0, 0.9, 0.7), 0.0, paper=False)
spark.data.materials.append(M_SPARK)
spark.parent = LAST
_M300 = pouch_matrix(N_FRAMES) @ Matrix.Translation(heap_local[0]) @ local_rot[0].to_matrix().to_4x4()
_l3, _q3, _s3 = _M300.decompose()
_top = (-VIEW * 0.6 + Vector((0, 0, 0.8))).normalized()
spark.location = (Matrix.Translation(_l3) @ _q3.to_matrix().to_4x4()).inverted() @ (P_END + _top * PEB_R * 0.6 - RIGHT3 * PEB_R * 0.25)
_sp = next(n for n in M_SPARK.node_tree.nodes if n.type == 'EMISSION').inputs['Strength']
for f, v in ((1, 0.0), (262, 0.0), (272, 240.0), (281, 110.0), (290, 190.0), (300, 140.0)):
    _sp.default_value = v
    _sp.keyframe_insert('default_value', frame=f)
# son taşa sıcak hale (boyalı dünyada ışık yerine: taşın rengi hafifçe aydınlanır)
_peb_em = next(n for n in M_PEBBLE.node_tree.nodes if n.type == 'EMISSION').inputs['Strength']
M_LAST = M_PEBBLE.copy(); M_LAST.name = 'son_cakil'
LAST.data.materials[0] = M_LAST
_le = next(n for n in M_LAST.node_tree.nodes if n.type == 'EMISSION').inputs['Strength']
for f, v in ((1, 1.0), (262, 1.0), (276, 1.22), (300, 1.16)):
    _le.default_value = v
    _le.keyframe_insert('default_value', frame=f)

# ---------------------------------------------------------------- render ayarları
R = scene.render
R.engine = 'CYCLES'
C = scene.cycles
C.device = 'CPU'
C.samples = A.ornek
C.use_adaptive_sampling = True
C.adaptive_threshold = 0.01
C.use_denoising = False                  # boyalı dünyada gürültü yok (yalnız kenar yumuşatma için örnek)
C.max_bounces = 1
C.diffuse_bounces = 0
C.glossy_bounces = 0
C.transmission_bounces = 0
C.transparent_max_bounces = 2
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.seed = 7
C.pixel_filter_type = 'BLACKMAN_HARRIS'
C.filter_width = 1.4
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = bool(A.bulanik)
R.use_persistent_data = True
vs = scene.view_settings
vs.view_transform = 'Standard'
vs.look = 'None'
vs.exposure = 0.0
vs.gamma = 1.0

# Freestyle: ince sepya kontur, kalem gibi kalınlığı değişen
if A.cizgi:
    R.use_freestyle = True
    R.line_thickness_mode = 'ABSOLUTE'
    R.line_thickness = 1.0
    vl = scene.view_layers[0]
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(120)
    fs.use_culling = True
    ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('kontur')
    ls.select_by_visibility = True
    ls.visibility = 'VISIBLE'
    ls.select_by_edge_types = True
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.select_external_contour = True
    ls.select_by_collection = True
    ls.collection = NOLINE
    ls.collection_negation = 'EXCLUSIVE'
    if ls.linestyle is None:
        ls.linestyle = bpy.data.linestyles.new('kontur_stil')
    st = ls.linestyle
    st.color = s2l(SEPIA)
    base_t = max(1.1, 1.9 * A.h / 1080)
    st.thickness = base_t
    st.thickness_position = 'CENTER'
    st.caps = 'ROUND'
    cal = st.thickness_modifiers.new('kalem', 'CALLIGRAPHY')
    cal.orientation = math.radians(50)
    cal.thickness_min = base_t * 0.55
    cal.thickness_max = base_t * 1.25
    cal.blend = 'MIX'
    st.geometry_modifiers.new('ornek', 'SAMPLING').sampling = 2.0

ng = bpy.data.node_groups.new('kompozit', 'CompositorNodeTree')
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
scene.compositing_node_group = ng
rl = ng.nodes.new('CompositorNodeRLayers')
out = ng.nodes.new('NodeGroupOutput')
gl = ng.nodes.new('CompositorNodeGlare')
for nm, val in (('Type', 'Streaks'), ('Quality', 'High'), ('Threshold', 20.0), ('Strength', 0.3), ('Streaks', 4),
                ('Streaks Angle', 0.0), ('Fade', 0.72), ('Size', 0.22), ('Saturation', 0.9), ('Tint', (1.0, 0.82, 0.55, 1.0))):
    if nm in gl.inputs:
        try:
            gl.inputs[nm].default_value = val
        except Exception as ex:
            print('glare', nm, ex)
fg = ng.nodes.new('CompositorNodeGlare')
for nm, val in (('Type', 'Fog Glow'), ('Quality', 'High'), ('Threshold', 20.0), ('Strength', 0.3), ('Size', 0.35),
                ('Tint', (1.0, 0.8, 0.5, 1.0))):
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
                    ('dizi_son', LAND[-1].to_3d() + Vector((0, 0, SLAB_TOP))), ('son_tas', P_END),
                    ('agil_arka', (PEN_C - gu * PEN_R).to_3d())):
        _c = world_to_camera_view(scene, cam, _p)
        print('KADRAJ f%d %-9s x=%.2f y(ust)=%.2f' % (_f, _nm, _c.x, 1 - _c.y))
    for _i in (0, 7):
        _c = world_to_camera_view(scene, cam, sheep[_i][0].matrix_world.to_translation() + Vector((0, 0, 0.6)))
        print('KADRAJ f%d koyun%d    x=%.2f y(ust)=%.2f' % (_f, _i, _c.x, 1 - _c.y))
print('sahne kuruldu: %.1f sn' % (time.time() - T_START), flush=True)
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(A.cikti), 'minyatur.blend'))

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
