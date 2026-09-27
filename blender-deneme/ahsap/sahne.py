# Math with Zirek · sahne G, BOYALI AHŞAP OYUNCAK sürüm (akşam, koyunlar girer, taş çıkar, tek taş kalır)
# Blender 5.2, Cycles CPU. Tamamen yordamsal, dış varlık yok. Sabit tohumlar.
# Görünüm: masa üstü minyatür diorama, tilt-shift (çok sığ alan derinliği, yukarıdan bakış). Tornada çekilmiş,
# boyanmış tahta koyunlar; duvar tahta bloklar; boyanın altından tahta damarı görünür, kenarlarda hafif boya
# kopukları (çıplak tahta); boyalı tahta tepeler ve tornalanmış ağaçlar; oyma, boyalı tahta kese; tahta boncuk çakıllar.
# Yerleşim, zamanlama ve kamera vuruşları kil sürümüyle (../sahne.py) ve keçe sürümüyle aynı.
# Kullanım (yalnız bulutta):
#   blender -b -P sahne.py -- --mod kare --kareler 68,210,290 --w 960 --h 540 --ornek 32 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 60 --cikti out       (1920x1080)
import bpy, bmesh, math, random, sys, os, time, argparse
from mathutils import Vector, Matrix, Quaternion, Euler, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--mod', default='kare')
ap.add_argument('--kareler', default='68,210,290')
ap.add_argument('--bas', type=int, default=1)
ap.add_argument('--son', type=int, default=300)
ap.add_argument('--w', type=int, default=1920)
ap.add_argument('--h', type=int, default=1080)
ap.add_argument('--ornek', type=int, default=64)
ap.add_argument('--cikti', default='out')
ap.add_argument('--cihaz', default='cpu')
ap.add_argument('--blend', action='store_true')
A = ap.parse_args(argv)
T_START = time.time()

FPS = 30
N_FRAMES = 300
N_SHEEP = 8
T_GATE0 = 40
T_GAP = 22
SPEED = 0.95 / FPS

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


def bm_to_obj(name, bm, smooth_shade=True):
    for f in bm.faces:
        f.smooth = smooth_shade
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def add_subsurf(ob, render=2, view=0):
    m = ob.modifiers.new('ss', 'SUBSURF')
    m.levels = view
    m.render_levels = render
    return m


def blob(bm, center, radii, subdiv=3, amp=0.0, nscale=4.0, seed=0, rot=None):
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


def merge_bm(bm, tmp, M=None):
    if M is not None:
        tmp.transform(M)
    me = bpy.data.meshes.new('tmp')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def rbox(bm, center, size, yaw=0.0, bev=0.008, pitch=0.0, roll=0.0):
    """pahlı (kenarı yuvarlatılmış) tahta blok."""
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=1.0)
    for v in tmp.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=bev, segments=3, profile=0.5, affect='EDGES', clamp_overlap=True)
    M = Matrix.Translation(center) @ Euler((roll, pitch, yaw)).to_matrix().to_4x4()
    merge_bm(bm, tmp, M)


def lathe(bm, prof, seg=40, M=None, axis='Z', wobble=0.0, seed=0):
    """tornada çekilmiş parça: prof = [(yarıçap, eksen boyu)], uçlarda yarıçap 0 ise kapalı."""
    tmp = bmesh.new()
    rings = []
    for (r, t) in prof:
        if r <= 1e-6:
            rings.append([tmp.verts.new((0, 0, t))])
            continue
        ring = []
        for s in range(seg):
            th = 2 * math.pi * s / seg
            rr = r * (1 + wobble * noise.noise(Vector((math.cos(th) * 2, math.sin(th) * 2, t * 8 + seed))))
            ring.append(tmp.verts.new((rr * math.cos(th), rr * math.sin(th), t)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for s in range(seg):
                tmp.faces.new((a[0], b[s], b[(s + 1) % seg]))
        elif len(b) == 1:
            for s in range(seg):
                tmp.faces.new((a[s], b[0], a[(s + 1) % seg]))
        else:
            for s in range(seg):
                tmp.faces.new((a[s], b[s], b[(s + 1) % seg], a[(s + 1) % seg]))
    if len(rings[0]) > 1:
        tmp.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        tmp.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    if axis == 'X':
        tmp.transform(Matrix.Rotation(math.pi / 2, 4, 'Y'))
    merge_bm(bm, tmp, M)


def setmat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


def _inp(node, names, value):
    for n in names:
        if n in node.inputs:
            try:
                node.inputs[n].default_value = value
                return node.inputs[n]
            except Exception:
                pass
    return None


class NB:
    def __init__(self, nt):
        self.N, self.L = nt.nodes, nt.links

    def m(self, op, a, b=None, c=None):
        n = self.N.new('ShaderNodeMath')
        n.operation = op
        for k, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[k].default_value = v
            else:
                self.L.new(v, n.inputs[k])
        return n.outputs[0]

    def noise(self, vec, scale, detail=4.0, rough=0.55, dist=0.0):
        n = self.N.new('ShaderNodeTexNoise')
        n.inputs['Scale'].default_value = scale
        _inp(n, ['Detail'], detail)
        _inp(n, ['Roughness'], rough)
        _inp(n, ['Distortion'], dist)
        self.L.new(vec, n.inputs['Vector'])
        return n.outputs['Fac']

    def mapping(self, vec, scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0)):
        n = self.N.new('ShaderNodeMapping')
        n.inputs['Scale'].default_value = scale
        n.inputs['Rotation'].default_value = rot
        n.inputs['Location'].default_value = loc
        self.L.new(vec, n.inputs['Vector'])
        return n.outputs['Vector']

    def mix(self, fac, a, b):
        n = self.N.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.blend_type = 'MIX'
        if isinstance(fac, (int, float)):
            n.inputs['Factor'].default_value = fac
        else:
            self.L.new(fac, n.inputs['Factor'])
        ca = [s for s in n.inputs if s.type == 'RGBA']
        for sock, v in ((ca[0], a), (ca[1], b)):
            if isinstance(v, tuple):
                sock.default_value = (*v[:3], 1)
            else:
                self.L.new(v, sock)
        return [s for s in n.outputs if s.type == 'RGBA'][0]


AXIS_SCALE = {'X': (0.07, 1.0, 1.0), 'Y': (1.0, 0.07, 1.0), 'Z': (1.0, 1.0, 0.07)}


def paint(name, color=None, palette=None, rough=0.4, axis='X', gscale=1.0, chip=1.0, wear=0.0, var=0.06,
          wood_col=(0.74, 0.54, 0.33), grain_show=0.1, bevel_r=0.01, planks=0.0, emission=None, sat=1.0, coat=0.12,
          spec=0.45, bev_samples=6):
    """Boyalı tahta: tahta damarı (halka dokusu, bir eksende uzamış), üstünde ipeksi boya; damar boyanın
    altından hem renkte hem kabartmada okunur; kenarlarda (Bevel düğümü ile bulunan) boya kopukları."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nb = NB(nt)
    N, L = nb.N, nb.L
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    oi = N.new('ShaderNodeObjectInfo')
    gv = nb.mapping(tc.outputs['Object'], AXIS_SCALE[axis], loc=(0.31, 0.17, 0.53))
    rofs = N.new('ShaderNodeVectorMath'); rofs.operation = 'MULTIPLY_ADD'
    L.new(gv, rofs.inputs[0])
    rofs.inputs[1].default_value = (1, 1, 1)
    L.new(oi.outputs['Random'], rofs.inputs[2])
    wv = N.new('ShaderNodeTexWave')
    wv.wave_type = 'RINGS'
    wv.inputs['Scale'].default_value = 16.0 * gscale
    wv.inputs['Distortion'].default_value = 7.0
    _inp(wv, ['Detail'], 4.0)
    _inp(wv, ['Detail Scale'], 1.5)
    L.new(rofs.outputs[0], wv.inputs['Vector'])
    g = wv.outputs['Fac']
    fine = nb.noise(gv, 260 * gscale, 3.0)
    gg = nb.m('MULTIPLY_ADD', fine, 0.25, nb.m('MULTIPLY', g, 0.75))
    # çıplak tahta rengi
    whs = N.new('ShaderNodeHueSaturation')
    whs.inputs['Color'].default_value = (*wood_col, 1)
    L.new(nb.m('MULTIPLY_ADD', gg, 0.45, 0.72), whs.inputs['Value'])
    # boya rengi
    phs = N.new('ShaderNodeHueSaturation')
    if palette:
        rp = N.new('ShaderNodeValToRGB')
        rp.color_ramp.interpolation = 'CONSTANT'
        els = rp.color_ramp.elements
        while len(els) < len(palette):
            els.new(0.5)
        for k, c in enumerate(palette):
            els[k].position = k / len(palette)
            els[k].color = (*c, 1)
        L.new(oi.outputs['Random'], rp.inputs['Fac'])
        L.new(rp.outputs['Color'], phs.inputs['Color'])
    else:
        phs.inputs['Color'].default_value = (*color, 1)
    phs.inputs['Saturation'].default_value = sat
    vr = nb.m('MULTIPLY_ADD', oi.outputs['Random'], var, 1.0 - var / 2)
    L.new(nb.m('MULTIPLY', vr, nb.m('MULTIPLY_ADD', gg, grain_show, 1.0 - grain_show * 0.6)), phs.inputs['Value'])
    mask = None
    if chip > 0:
        bev = N.new('ShaderNodeBevel')
        bev.samples = bev_samples
        bev.inputs['Radius'].default_value = bevel_r
        geo = N.new('ShaderNodeNewGeometry')
        dt = N.new('ShaderNodeVectorMath'); dt.operation = 'DOT_PRODUCT'
        L.new(bev.outputs['Normal'], dt.inputs[0])
        L.new(geo.outputs['Normal'], dt.inputs[1])
        edge = nb.m('SUBTRACT', 1.0, dt.outputs['Value'])
        cn = nb.noise(tc.outputs['Object'], 38.0, 5.0, 0.7)
        cm = nb.m('MULTIPLY', nb.m('MULTIPLY', edge, 30.0 * chip), nb.m('SUBTRACT', cn, 0.38))
        mr = N.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 0.25
        mr.inputs['From Max'].default_value = 0.4
        L.new(cm, mr.inputs['Value'])
        mask = mr.outputs['Result']
        L.new(bev.outputs['Normal'], b.inputs['Normal'])
    if wear > 0:
        wn = nb.noise(tc.outputs['Object'], 9.0, 6.0, 0.7)
        wmr = N.new('ShaderNodeMapRange')
        wmr.inputs['From Min'].default_value = 1.0 - wear * 0.36
        wmr.inputs['From Max'].default_value = 1.0 - wear * 0.34
        L.new(wn, wmr.inputs['Value'])
        mask = wmr.outputs['Result'] if mask is None else nb.m('MAXIMUM', mask, wmr.outputs['Result'])
    col = phs.outputs['Color']
    if mask is not None:
        col = nb.mix(mask, col, whs.outputs['Color'])
        L.new(nb.m('MULTIPLY_ADD', mask, 0.72 - rough, rough), b.inputs['Roughness'])
    else:
        b.inputs['Roughness'].default_value = rough
    height = nb.m('MULTIPLY', gg, 0.35)
    if planks > 0:
        pw = N.new('ShaderNodeTexWave')
        pw.wave_type = 'BANDS'
        pw.bands_direction = 'Y'
        try:
            pw.wave_profile = 'SAW'
        except Exception:
            pass
        pw.inputs['Scale'].default_value = planks
        pw.inputs['Distortion'].default_value = 0.0
        L.new(tc.outputs['Object'], pw.inputs['Vector'])
        pr = N.new('ShaderNodeMapRange')
        pr.inputs['From Min'].default_value = 0.985
        pr.inputs['From Max'].default_value = 1.0
        L.new(pw.outputs['Fac'], pr.inputs['Value'])
        col = nb.mix(nb.m('MULTIPLY', pr.outputs['Result'], 0.55), col, (0.08, 0.06, 0.03))
        height = nb.m('SUBTRACT', height, nb.m('MULTIPLY', pr.outputs['Result'], 0.8))
    if mask is not None:
        height = nb.m('SUBTRACT', height, nb.m('MULTIPLY', mask, 0.5))
    L.new(col, b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.22
    bp.inputs['Distance'].default_value = 0.002
    L.new(height, bp.inputs['Height'])
    if chip > 0:
        L.new(bev.outputs['Normal'], bp.inputs['Normal'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])
    _inp(b, ['Specular IOR Level'], spec)
    _inp(b, ['Coat Weight'], coat)
    _inp(b, ['Coat Roughness'], 0.3)
    if emission is not None:
        _inp(b, ['Emission Color'], (*emission, 1))
        _inp(b, ['Emission Strength'], 0.0)
    return m


def cord(name, color):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nb = NB(nt)
    N, L = nb.N, nb.L
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    wv = N.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'DIAGONAL'
    wv.inputs['Scale'].default_value = 150.0
    L.new(tc.outputs['Object'], wv.inputs['Vector'])
    hs = N.new('ShaderNodeHueSaturation')
    hs.inputs['Color'].default_value = (*color, 1)
    L.new(nb.m('MULTIPLY_ADD', wv.outputs['Fac'], 0.3, 0.75), hs.inputs['Value'])
    L.new(hs.outputs['Color'], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.6
    L.new(wv.outputs['Fac'], bp.inputs['Height'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.8
    _inp(b, ['Sheen Weight'], 0.5)
    return m


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    N = m.node_tree.nodes
    N.remove(N['Principled BSDF'])
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1.0)
    em.inputs['Strength'].default_value = strength
    m.node_tree.links.new(em.outputs[0], N['Material Output'].inputs['Surface'])
    return m


# renk: kanalın sıcak krem / aşı / yeşil paleti; çakıl safran-aşı, kese kök boya kırmızısı, çakıl tahtası arduvaz gri
M_BOARD = paint('zemin_boya', (0.17, 0.31, 0.08), rough=0.66, axis='X', gscale=0.35, chip=0.0, wear=0.25, var=0.0,
                grain_show=0.2, planks=2.4, coat=0.0, spec=0.3)
M_BLOCK = paint('blok', palette=[(0.50, 0.49, 0.46), (0.38, 0.39, 0.40), (0.58, 0.56, 0.50), (0.44, 0.44, 0.42),
                                 (0.33, 0.34, 0.36), (0.62, 0.47, 0.30)], rough=0.45, axis='X', gscale=1.6, chip=1.0,
                grain_show=0.14, bevel_r=0.012)
M_POST = paint('direk', palette=[(0.40, 0.41, 0.43), (0.50, 0.49, 0.46), (0.35, 0.36, 0.38)], rough=0.45, axis='X',
               gscale=1.4, chip=1.1, grain_show=0.14, bevel_r=0.014)
M_WOOL = paint('yun_boya', (0.93, 0.89, 0.79), rough=0.38, axis='X', gscale=2.0, chip=0.0, wear=0.35, var=0.04,
               grain_show=0.12)
M_HEAD = paint('bas_boya', (0.075, 0.065, 0.06), rough=0.35, axis='X', gscale=2.5, chip=1.0, wear=0.2, var=0.05,
               grain_show=0.25, bevel_r=0.008)
M_EAR = paint('kulak_boya', (0.075, 0.065, 0.06), rough=0.35, axis='X', gscale=3.0, chip=1.2, var=0.05, grain_show=0.25,
              bevel_r=0.006)
M_EYE_W = paint('goz_ak', (0.95, 0.93, 0.87), rough=0.3, chip=0.0, var=0.0, grain_show=0.03)
M_EYE_B = paint('goz_bebek', (0.02, 0.02, 0.02), rough=0.25, chip=0.0, var=0.0, grain_show=0.0)
M_LEG = paint('bacak', (0.22, 0.14, 0.09), rough=0.45, axis='Z', gscale=3.0, chip=0.8, var=0.05, grain_show=0.3,
              bevel_r=0.006)
M_POUCH = paint('kese_boya', (0.56, 0.12, 0.08), rough=0.5, axis='Z', gscale=1.8, chip=1.4, wear=0.6, var=0.0,
                grain_show=0.4, bevel_r=0.012, coat=0.05)
M_CORD = cord('kese_ipi', (0.88, 0.80, 0.62))
M_PEG = paint('civi', (0.70, 0.52, 0.32), rough=0.55, axis='Z', gscale=2.0, chip=0.0, var=0.0, grain_show=1.0,
              wood_col=(0.70, 0.52, 0.32))
M_PEBBLE = paint('cakil_boya', (0.90, 0.58, 0.16), rough=0.5, axis='X', gscale=3.0, chip=0.0, wear=0.2, var=0.1,
                 grain_show=0.14)
M_LAST = paint('son_cakil', (0.90, 0.58, 0.16), rough=0.5, axis='X', gscale=3.0, chip=0.0, wear=0.2, var=0.0,
               grain_show=0.14, emission=(1.0, 0.72, 0.38))
M_SLAB = paint('cakil_tahtasi', (0.36, 0.40, 0.44), rough=0.45, axis='X', gscale=1.0, chip=1.0, var=0.0, grain_show=0.16,
               bevel_r=0.012)
M_HILL = [paint('tepe1', (0.26, 0.42, 0.12), rough=0.6, axis='X', gscale=0.25, chip=0.0, var=0.0, grain_show=0.2, coat=0.0, spec=0.3),
          paint('tepe2', (0.72, 0.50, 0.16), rough=0.6, axis='X', gscale=0.25, chip=0.0, var=0.0, grain_show=0.2, coat=0.0, spec=0.3),
          paint('tepe3', (0.50, 0.56, 0.30), rough=0.6, axis='X', gscale=0.2, chip=0.0, var=0.0, grain_show=0.2, coat=0.0, spec=0.3),
          paint('tepe4', (0.36, 0.50, 0.15), rough=0.6, axis='X', gscale=0.25, chip=0.0, var=0.0, grain_show=0.2, coat=0.0, spec=0.3)]
M_TREE = paint('agac_boya', palette=[(0.16, 0.36, 0.14), (0.24, 0.43, 0.13), (0.12, 0.30, 0.16)], rough=0.4, axis='Z',
               gscale=1.2, chip=1.0, grain_show=0.16, bevel_r=0.01)
M_TRUNK = paint('govde', (0.70, 0.52, 0.32), rough=0.55, axis='Z', gscale=2.0, chip=0.0, var=0.0, grain_show=1.0,
                wood_col=(0.66, 0.47, 0.28))
M_BEAD = paint('boncuk', palette=[(0.96, 0.82, 0.30), (0.96, 0.93, 0.86), (0.92, 0.55, 0.45)], rough=0.35, chip=0.0,
               grain_show=0.05)
M_HURDLE = paint('kapi_kanadi', (0.66, 0.49, 0.30), rough=0.55, axis='X', gscale=2.0, chip=0.0, var=0.0, grain_show=1.0,
                 wood_col=(0.66, 0.49, 0.30))

# ---------------------------------------------------------------- yerleşim (kil ve keçe sürümüyle aynı düzen)
PEN_C = Vector((0.3, 1.3))
PEN_R = 1.35
GATE_ANG = math.radians(228)
GAP_HALF = 0.26
CAM_POS0 = Vector((1.05, -3.35, 2.45))          # tilt-shift: daha yukarıdan bakış
LOOK0 = Vector((-0.05, 0.55))
FWD0 = (LOOK0 - CAM_POS0.xy).normalized()
RIGHT = Vector((FWD0.y, -FWD0.x))
RIGHT3 = RIGHT.to_3d()


def ang_dist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def ring_pos(a, r=PEN_R):
    return Vector((PEN_C.x + r * math.cos(a), PEN_C.y + r * math.sin(a)))


def hfun(x, y):
    d = (Vector((x, y)) - PEN_C).length
    flat = smooth(1.9, 3.6, d)
    h = 0.45 * smooth(3.6, 13.0, y)
    h += flat * (0.05 * math.sin(0.55 * x + 0.3) * math.cos(0.42 * y + 0.8) + 0.02 * math.sin(1.3 * x - 0.7 * y))
    return h


gu = Vector((math.cos(GATE_ANG), math.sin(GATE_ANG)))
GATE = PEN_C + gu * PEN_R
FRONT_A = GATE_ANG + GAP_HALF + 0.02
BACK_A = GATE_ANG - GAP_HALF - 0.02
FP = ring_pos(FRONT_A)
BP = ring_pos(BACK_A)
TO_CAM = (CAM_POS0.xy - FP).normalized()
TO_CAM3 = TO_CAM.to_3d()
PEB_SP = 0.128
ROW_CENTER = FP + TO_CAM * 0.62 + RIGHT * 0.14
LAND = [ROW_CENTER + RIGHT * PEB_SP * (k - 3.5) for k in range(N_SHEEP)]
_rr = rng(4000)
LAND = [p + Vector((_rr.uniform(-0.006, 0.006), _rr.uniform(-0.006, 0.006))) for p in LAND]

INSIDE = GATE - gu * 0.45
OUT1 = GATE + gu * 0.62 - RIGHT * 0.25
START1 = OUT1 - RIGHT * 2.3 + FWD0 * 0.15
START0 = OUT1 - RIGHT * 9.0 + FWD0 * 0.5
SPOTS = []
_rs = rng(77)
while len(SPOTS) < N_SHEEP:
    a = _rs.uniform(0, 2 * math.pi)
    rr = _rs.uniform(0.25, PEN_R - 0.38)
    q = PEN_C + Vector((rr * math.cos(a), rr * math.sin(a)))
    if (q - INSIDE).length < 0.45:
        continue
    if all((q - o).length > 0.5 for o in SPOTS):
        SPOTS.append(q)
SPOTS.sort(key=lambda q: -(q - INSIDE).length)


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


paths = []
for i in range(N_SHEEP):
    jit = FWD0 * (0.06 * ((i * 7) % 3 - 1))
    paths.append(Path([START0 + jit, START1 + jit, OUT1, GATE, INSIDE, SPOTS[i]]))
_dmin = min((q - l).length for P in paths for q in P.p for l in LAND)
print('YOL-DIZI en yakın mesafe: %.2f' % _dmin)


def near_path(p, d=0.3):
    return min((q - p).length for q in paths[0].p[::4]) < d


def calm_right(p, margin=0.0):
    rel = p - CAM_POS0.xy
    return rel.dot(RIGHT) > 0.35 * rel.dot(FWD0) - 0.4 - margin and rel.dot(FWD0) < 4.3


# ---------------------------------------------------------------- zemin: boyalı tahta levha (tahta şeritler)
def build_ground():
    bm = bmesh.new()
    x0, x1, y0, y1 = -9.0, 9.0, -6.0, 14.0
    nx, ny = 160, 150
    verts = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * (j / ny) ** 1.25
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            row.append(bm.verts.new((x, y, hfun(x, y))))
        verts.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    ob = bm_to_obj('zemin', bm)
    setmat(ob, M_BOARD)
    return ob


build_ground()


# ---------------------------------------------------------------- ağıl: tahta bloklar
def build_pen():
    L_B, D_B, H_B = 0.17, 0.095, 0.082
    n = int(2 * math.pi * PEN_R / (L_B + 0.006))
    k = 0
    for course in range(4):
        for j in range(n):
            a = (j + 0.5 * course) * 2 * math.pi / n
            if ang_dist(a, GATE_ANG) < GAP_HALF + 0.13:
                continue
            r = rng(3000 + course * 131 + j)
            if course == 3 and r.random() < 0.12:
                continue
            p = ring_pos(a, PEN_R + r.uniform(-0.008, 0.008))
            z = hfun(p.x, p.y) + H_B / 2 + course * (H_B + 0.002)
            bm = bmesh.new()
            rbox(bm, (p.x, p.y, z), (L_B * r.uniform(0.94, 1.0), D_B, H_B), yaw=a + math.pi / 2 + r.uniform(-0.04, 0.04),
                 bev=0.009, roll=r.uniform(-0.02, 0.02))
            ob = bm_to_obj('blok_%03d' % k, bm, smooth_shade=True)
            setmat(ob, M_BLOCK)
            k += 1
    top = 0.0
    for side, a in (('on', FRONT_A), ('arka', BACK_A)):
        p = ring_pos(a)
        z = hfun(p.x, p.y)
        r = rng(700 + (0 if side == 'on' else 50))
        for kk in range(6):
            h = 0.105
            bm = bmesh.new()
            rbox(bm, (p.x + r.uniform(-0.006, 0.006), p.y + r.uniform(-0.006, 0.006), z + h / 2), (0.22, 0.22, h),
                 yaw=a + (0.12 if kk % 2 else -0.05) + r.uniform(-0.05, 0.05), bev=0.012)
            ob = bm_to_obj('direk_%s_%d' % (side, kk), bm)
            setmat(ob, M_POST)
            z += h + 0.003
        # tepesinde tornalanmış tahta topuz
        bm = bmesh.new()
        lathe(bm, [(0.0, 0.0), (0.07, 0.0), (0.075, 0.012), (0.05, 0.03), (0.035, 0.045), (0.06, 0.075), (0.066, 0.1),
                   (0.055, 0.125), (0.03, 0.14), (0.0, 0.145)], seg=40, M=Matrix.Translation((p.x, p.y, z)))
        ob = bm_to_obj('direk_topuz_%s' % side, bm)
        setmat(ob, M_POST)
        top = z
    return top


POST_TOP = build_pen()
print('t duvar %.1f' % (time.time() - T_START), flush=True)


def build_hurdle():
    p = BP
    t = Vector((math.sin(BACK_A), -math.cos(BACK_A)))
    inward = (PEN_C - p).normalized()
    start = p + inward * 0.22 + t * 0.14
    d = (t * 0.85 + inward * 0.15).normalized()
    yaw = math.atan2(d.y, d.x)
    Lh = 0.6
    z0 = hfun(start.x, start.y)
    bm = bmesh.new()
    for k, zz in enumerate((0.1, 0.2, 0.3)):
        c = start + d * (Lh / 2)
        rbox(bm, (c.x, c.y, z0 + zz), (Lh, 0.022, 0.04), yaw=yaw, bev=0.006)
    for k, s in enumerate((0.03, Lh / 2, Lh - 0.03)):
        c = start + d * s
        rbox(bm, (c.x, c.y, z0 + 0.18), (0.035, 0.035, 0.36), yaw=yaw, bev=0.006)
    ob = bm_to_obj('kapi_kanadi', bm)
    setmat(ob, M_HURDLE)



# ---------------------------------------------------------------- çakıl tahtası (dizinin yeri)
SLAB_T = 0.03


def build_slab():
    bm = bmesh.new()
    Ls, Ws = 1.2, 0.2
    tmp = bmesh.new()
    # yuvarlak uçlu yassı tahta: iki uç yarım daire
    pts = []
    for k in range(21):
        a = -math.pi / 2 + math.pi * k / 20
        pts.append(Vector((Ls / 2 - Ws / 2 + Ws / 2 * math.cos(a), Ws / 2 * math.sin(a))))
    for k in range(21):
        a = math.pi / 2 + math.pi * k / 20
        pts.append(Vector((-Ls / 2 + Ws / 2 + Ws / 2 * math.cos(a), Ws / 2 * math.sin(a))))
    vs = [tmp.verts.new((p.x, p.y, 0.0)) for p in pts]
    f = tmp.faces.new(vs)
    ex = bmesh.ops.extrude_face_region(tmp, geom=[f])
    bmesh.ops.translate(tmp, verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, SLAB_T))
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    bmesh.ops.bevel(tmp, geom=[e for e in tmp.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6],
                    offset=0.008, segments=3, profile=0.5, affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(tmp, faces=[fc for fc in tmp.faces if len(fc.verts) > 8])
    c = ROW_CENTER
    M = Matrix.Translation((c.x, c.y, hfun(c.x, c.y) - 0.004)) @ Matrix.Rotation(math.atan2(RIGHT.y, RIGHT.x), 4, 'Z')
    merge_bm(bm, tmp, M)
    ob = bm_to_obj('cakil_tahtasi', bm, smooth_shade=False)
    setmat(ob, M_SLAB)


build_slab()
SLAB_TOP = SLAB_T - 0.004


def slab_z(p):
    return hfun(ROW_CENTER.x, ROW_CENTER.y) + SLAB_TOP


# ---------------------------------------------------------------- arka plan: boyalı tahta tepeler, tornalanmış ağaçlar
for k, (c, rad, mat) in enumerate((((-6.5, 16.0, -0.4), (8.5, 3.4, 2.1), M_HILL[0]),
                                   ((7.0, 18.0, -0.6), (9.5, 3.8, 2.5), M_HILL[1]),
                                   ((0.5, 26.0, -1.0), (15.0, 5.0, 3.6), M_HILL[2]),
                                   ((-1.5, 13.5, -0.5), (5.0, 2.2, 1.35), M_HILL[3]))):
    bm = bmesh.new()
    blob(bm, c, rad, subdiv=5, amp=0.02, nscale=1.2, seed=900 + k)
    ob = bm_to_obj('tepe_%d' % k, bm)
    setmat(ob, mat)


for k, (c, rad, mat) in enumerate((((-2.8, 7.6, -0.35), (3.0, 1.5, 1.0), M_HILL[2]),
                                   ((1.6, 8.6, -0.45), (3.6, 1.7, 1.2), M_HILL[1]),
                                   ((5.0, 7.2, -0.35), (2.6, 1.3, 0.85), M_HILL[0]))):
    c = (c[0], c[1], c[2] + hfun(c[0], c[1]))
    bm = bmesh.new()
    blob(bm, c, rad, subdiv=5, amp=0.03, nscale=1.4, seed=950 + k)
    ob = bm_to_obj('yakin_tepe_%d' % k, bm)
    setmat(ob, mat)


def cone_tree(name, x, y, sc, seed):
    """Erzgebirge usulü tornalanmış çam: basamaklı koni + tahta gövde."""
    z = hfun(x, y)
    bm = bmesh.new()
    lathe(bm, [(0.0, 0.0), (0.05, 0.0), (0.05, 0.22), (0.0, 0.22)], seg=24,
          M=Matrix.Translation((x, y, z)) @ Matrix.Scale(sc, 4))
    t = bm_to_obj(name + '_govde', bm)
    setmat(t, M_TRUNK)
    prof = [(0.0, 0.18)]
    for k in range(4):
        z0 = 0.18 + k * 0.2
        r0 = 0.36 - k * 0.075
        prof += [(r0 * 0.75, z0), (r0, z0 + 0.02), (r0 * 0.95, z0 + 0.04), (r0 * 0.55, z0 + 0.22)]
    prof += [(0.05, 1.0), (0.0, 1.04)]
    bm = bmesh.new()
    lathe(bm, prof, seg=48, M=Matrix.Translation((x, y, z)) @ Matrix.Scale(sc, 4))
    c = bm_to_obj(name + '_tac', bm)
    setmat(c, M_TREE)


def ball_tree(name, x, y, sc, seed):
    z = hfun(x, y)
    bm = bmesh.new()
    lathe(bm, [(0.0, 0.0), (0.06, 0.0), (0.05, 0.55), (0.0, 0.55)], seg=24,
          M=Matrix.Translation((x, y, z)) @ Matrix.Scale(sc, 4))
    t = bm_to_obj(name + '_govde', bm)
    setmat(t, M_TRUNK)
    bm = bmesh.new()
    blob(bm, (x, y, z + 0.78 * sc), (0.34 * sc, 0.34 * sc, 0.36 * sc), subdiv=4, seed=seed)
    c = bm_to_obj(name + '_tac', bm)
    setmat(c, M_TREE)


ball_tree('agac1', -2.4, 3.0, 0.7, 1301)
cone_tree('agac2', -1.6, 3.9, 0.75, 1302)
cone_tree('agac3', 2.9, 5.2, 0.6, 1311)
ball_tree('agac4', 3.6, 6.2, 0.6, 1312)
cone_tree('agac5', -3.7, 2.2, 0.55, 1313)
cone_tree('agac6', -0.6, 6.0, 0.6, 1314)
cone_tree('agac7', 1.2, 5.3, 0.5, 1315)
ball_tree('agac8', 4.4, 4.6, 0.5, 1316)


def bushes_and_beads():
    r = rng(1400)
    bmb = bmesh.new()
    bmf = bmesh.new()
    k = 0
    while k < 12:
        a = r.uniform(0, 2 * math.pi)
        if ang_dist(a, GATE_ANG) < GAP_HALF + 0.3:
            continue
        p = ring_pos(a, PEN_R + 0.17)
        if calm_right(p, 0.3) or (p - ROW_CENTER).length < 0.8 or (p - FP).length < 0.4:
            continue
        k += 1
        s = r.uniform(0.045, 0.07)
        blob(bmb, (p.x, p.y, hfun(p.x, p.y) + s * 0.8), (s, s, s * 0.9), subdiv=3, seed=k)
    k = 0
    while k < 40:
        x = r.uniform(-4.5, 4.0); y = r.uniform(-2.2, 5.5)
        p = Vector((x, y))
        if calm_right(p, 0.6):
            continue
        if (p - PEN_C).length < PEN_R + 0.3 or near_path(p, 0.45) or (p - ROW_CENTER).length < 0.9:
            continue
        k += 1
        s = r.uniform(0.012, 0.018)
        blob(bmf, (x, y, hfun(x, y) + s * 0.7), (s, s, s * 0.8), subdiv=2, seed=k)
    ob = bm_to_obj('calilar', bmb)
    setmat(ob, M_TREE)
    # boncukları renk renk ayrı nesneye bölmek yerine tek nesne: renk için birkaç nesne
    ob = bm_to_obj('boncuk_cicekler', bmf)
    setmat(ob, M_BEAD)


bushes_and_beads()

# ---------------------------------------------------------------- kese: oyma, boyalı tahta; ip
POUCH_S = 1.45
PEG_Z = POST_TOP - 0.16
_pd = (TO_CAM * 0.55 + RIGHT * 0.8).normalized()
_pegdir = Vector((_pd.x, _pd.y, 0.16)).normalized()
PEG_BASE = Vector((FP.x, FP.y, PEG_Z))
PEG_LEN = 0.3
bm = bmesh.new()
lathe(bm, [(0.0, 0.0), (0.018, 0.0), (0.018, PEG_LEN - 0.012), (0.014, PEG_LEN - 0.003), (0.0, PEG_LEN)], seg=24,
      M=Matrix.Translation(PEG_BASE) @ Vector((0, 0, 1)).rotation_difference(_pegdir).to_matrix().to_4x4())
peg = bm_to_obj('civi', bm)
setmat(peg, M_PEG)
HANG = PEG_BASE + _pegdir * (PEG_LEN - 0.05) + Vector((0, 0, 0.016))
PROF = [(0.0, 0.0), (0.06, 0.004), (0.095, 0.02), (0.115, 0.05), (0.12, 0.085), (0.112, 0.12),
        (0.09, 0.15), (0.064, 0.171), (0.05, 0.182), (0.054, 0.192), (0.066, 0.205), (0.078, 0.218), (0.084, 0.228)]
DROP = 0.37
LIP_Z = 0.228 - DROP
NECK_Z = 0.182 - DROP


def build_pouch():
    seg = 56
    bm = bmesh.new()
    # dış yüz + dudak + iç oyuk (ağızdan aşağı 5 cm) — tek parça oyma
    prof = [(r, z) for (r, z) in PROF]
    prof += [(0.084, 0.232), (0.079, 0.235), (0.072, 0.232), (0.066, 0.22), (0.055, 0.2), (0.045, 0.19), (0.0, 0.185)]
    rings = []
    for (rr, zz) in prof:
        if rr <= 0:
            rings.append([bm.verts.new((0, 0, zz - DROP))])
            continue
        ring = []
        for s in range(seg):
            th = 2 * math.pi * s / seg
            # oyma kırışıklar: boğazda büzgü, gövdede aşağı inen yumuşak oluklar (yontma izi)
            gather = smooth(0.13, 0.18, zz) * (1 - smooth(0.2, 0.23, zz))
            fold = gather * 0.006 * math.sin(10 * th + 1.3)
            crease = (1 - gather) * smooth(0.04, 0.15, zz) * 0.005 * math.sin(6 * th + 0.4)
            facet = 0.0045 * abs(math.sin(9 * th + zz * 30 + 2.0 * math.sin(3 * th)))
            r2 = rr + fold + crease + facet * (rr / 0.12)
            ring.append(bm.verts.new((r2 * math.cos(th) * 1.04, r2 * math.sin(th) * 0.96, zz - DROP)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        if len(a) == 1:
            for s in range(seg):
                bm.faces.new((a[0], b[s], b[(s + 1) % seg]))
        elif len(b) == 1:
            for s in range(seg):
                bm.faces.new((a[s], b[0], a[(s + 1) % seg]))
        else:
            for s in range(seg):
                bm.faces.new((a[s], b[s], b[(s + 1) % seg], a[(s + 1) % seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pouch = bm_to_obj('kese', bm)
    add_subsurf(pouch, 1, 0)
    setmat(pouch, M_POUCH)
    pouch.location = HANG
    pouch.rotation_mode = 'QUATERNION'
    tilt_axis = Vector((-TO_CAM.y, TO_CAM.x, 0)).normalized()
    q0 = Quaternion(tilt_axis, math.radians(-20))
    pouch.rotation_quaternion = q0
    pouch.scale = (POUCH_S,) * 3
    inv = q0.inverted()

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
        ob = link(bpy.data.objects.new(name, cu))
        ob.data.materials.append(M_CORD)
        ob.parent = pouch
        return ob
    back = inv @ Vector((-TO_CAM.x, -TO_CAM.y, 0)).normalized()
    side = inv @ Vector((-TO_CAM.y, TO_CAM.x, 0)).normalized()
    zb = NECK_Z
    curve('ip_aski', [(back * 0.054 + Vector((0, 0, zb)))[:], (back * 0.05 + Vector((0, 0, zb + 0.05)))[:],
                      (back * 0.02 + Vector((0, 0, -0.01)))[:], (0, 0, 0.0)], bevel=0.0055)
    curve('ip_bogaz', [(0.057 * math.cos(2 * math.pi * s / 12) * 1.04, 0.057 * math.sin(2 * math.pi * s / 12) * 0.96,
                        zb + 0.003 * math.sin(3 * s)) for s in range(12)], cyclic=True, bevel=0.0065)
    fr = -back
    for k, (dx, ln) in enumerate(((0.012, 0.08), (-0.004, 0.065))):
        curve('ip_uc_%d' % k, [(fr * 0.059 + side * dx + Vector((0, 0, zb)))[:],
                               (fr * 0.068 + side * (dx + 0.01) + Vector((0, 0, zb - ln * 0.5)))[:],
                               (fr * 0.07 + side * (dx + 0.006) + Vector((0, 0, zb - ln)))[:]], bevel=0.0045)
        bm2 = bmesh.new()
        lathe(bm2, [(0.0, 0.0), (0.009, 0.002), (0.011, 0.012), (0.008, 0.02), (0.0, 0.022)], seg=20,
              M=Matrix.Translation(fr * 0.07 + side * (dx + 0.006) + Vector((0, 0, zb - ln - 0.02))))
        bd = bm_to_obj('ip_boncuk_%d' % k, bm2)
        setmat(bd, M_PEG)
        bd.parent = pouch
    return pouch, q0


pouch, POUCH_Q0 = build_pouch()


def pouch_quat(f):
    to_cam = TO_CAM
    ax1 = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    ax2 = Vector((to_cam.x, to_cam.y, 0))
    a1 = a2 = 0.0
    for i in range(N_SHEEP):
        tp = T_GATE0 + T_GAP * i - 3
        if f > tp:
            dt = f - tp
            a1 += 0.04 * math.exp(-dt / 12.0) * math.sin(dt * 0.45)
            a2 += 0.02 * math.exp(-dt / 12.0) * math.sin(dt * 0.38 + 1.0)
    return Quaternion(ax1, a1) @ Quaternion(ax2, a2) @ POUCH_Q0


def pouch_matrix(f):
    return Matrix.Translation(HANG) @ pouch_quat(f).to_matrix().to_4x4() @ Matrix.Scale(POUCH_S, 4)


for f in range(-2, N_FRAMES + 3):
    pouch.rotation_quaternion = pouch_quat(f)
    pouch.keyframe_insert('rotation_quaternion', frame=f)
print('t kese %.1f' % (time.time() - T_START), flush=True)


# ---------------------------------------------------------------- çakıllar: boyalı tahta boncuk (yassı, düzgün)
def pebble_mesh(name, seed, mat):
    r = rng(seed)
    bm = bmesh.new()
    rx, ry = r.uniform(0.049, 0.053), r.uniform(0.039, 0.042)
    prof = []
    for k in range(13):
        a = -math.pi / 2 + math.pi * k / 12
        prof.append((math.cos(a), math.sin(a) * 0.029))
    lathe(bm, [(max(0.0, c), z) for (c, z) in prof], seg=40)
    for v in bm.verts:
        v.co.x *= rx
        v.co.y *= ry
    ob = bm_to_obj(name, bm)
    setmat(ob, mat)
    ob.rotation_mode = 'QUATERNION'
    return ob


heap_local = [Vector((0, 0, LIP_Z - 0.012))]
for k in range(5):
    th = 2 * math.pi * k / 5 + 0.3
    heap_local.append(Vector((0.05 * math.cos(th), 0.05 * math.sin(th), LIP_Z + 0.012)))
for k in range(3):
    th = 2 * math.pi * k / 3 + 0.9
    heap_local.append(Vector((0.022 * math.cos(th), 0.022 * math.sin(th), LIP_Z + 0.036)))
take_order = [8, 7, 6, 5, 4, 3, 2, 1]
pebbles = [pebble_mesh('cakil_%d' % k, 3000 + k, M_LAST if k == 0 else M_PEBBLE) for k in range(9)]
LAST = pebbles[0]
local_rot = [Quaternion((0, 0, 1), rng(5000 + k).uniform(0, 6.28)) @ Quaternion((1, 0, 0), rng(5100 + k).uniform(-0.25, 0.25))
             for k in range(9)]
FLIGHT = 20


def qfix(q, prev):
    return -q if (prev is not None and q.dot(prev) < 0) else q


for idx, peb in enumerate(pebbles):
    order = take_order.index(idx) if idx in take_order else None
    prev_q = None
    t_take = T_GATE0 + T_GAP * order - 3 if order is not None else 10 ** 6
    land_q = Quaternion((0, 0, 1), math.atan2(RIGHT.y, RIGHT.x) + rng(6000 + idx).uniform(-0.3, 0.3))
    for f in range(-2, N_FRAMES + 3):
        if f <= t_take:
            M = pouch_matrix(f) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            loc, q, _ = M.decompose()
        else:
            M0 = pouch_matrix(t_take) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            p0, q0, _ = M0.decompose()
            L2 = LAND[order]
            p1 = Vector((L2.x, L2.y, slab_z(L2) + 0.029))
            t = min(1.0, (f - t_take) / FLIGHT)
            e = smoother(t)
            if t < 0.3:
                loc = p0 + Vector((0, 0, 0.1 * smoother(t / 0.3)))
            else:
                v = smoother((t - 0.3) / 0.7)
                loc = (p0 + Vector((0, 0, 0.1))).lerp(p1, v) + Vector((0, 0, 0.16 * 4 * v * (1 - v)))
            q = q0.slerp(land_q, e)
            q = Quaternion((1, 0, 0), 2.0 * math.sin(math.pi * e)) @ q if t < 1 else land_q
            if t >= 1:
                dt = f - t_take - FLIGHT
                loc = p1 + Vector((0, 0, 0.012 * math.exp(-dt / 2.0) * abs(math.sin(dt * 1.3))))
        q = qfix(q, prev_q)
        prev_q = q
        peb.location = loc
        peb.rotation_quaternion = q
        peb.keyframe_insert('location', frame=f)
        peb.keyframe_insert('rotation_quaternion', frame=f)
print('t cakil %.1f' % (time.time() - T_START), flush=True)


# ---------------------------------------------------------------- koyun: tornada çekilmiş, boyalı tahta oyuncak
def flat_piece(bm, outline, thick, M):
    tmp = bmesh.new()
    vs = [tmp.verts.new((x, y, -thick / 2)) for (x, y) in outline]
    f = tmp.faces.new(vs)
    ex = bmesh.ops.extrude_face_region(tmp, geom=[f])
    bmesh.ops.translate(tmp, verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, thick))
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    bmesh.ops.bevel(tmp, geom=[e for e in tmp.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6],
                    offset=thick * 0.3, segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(tmp, faces=[fc for fc in tmp.faces if len(fc.verts) > 6])
    merge_bm(bm, tmp, M)


BODY_PROF = [(0.0, -0.215), (0.045, -0.212), (0.08, -0.198), (0.106, -0.172), (0.123, -0.135), (0.132, -0.09),
             (0.136, -0.04), (0.136, 0.02), (0.132, 0.07), (0.122, 0.115), (0.104, 0.152), (0.078, 0.18),
             (0.045, 0.197), (0.0, 0.202)]


def build_sheep(i):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('koyun_%d' % i, None))
    bob = link(bpy.data.objects.new('koyun_%d_govde' % i, None))
    bob.parent = root
    s = r.uniform(0.86, 0.94)
    root.scale = (s, s, s)
    # gövde: tornalanmış yumurta, krem boya; ortasında torna halkası (iki oluk)
    bm = bmesh.new()
    prof = []
    for (rr, t) in BODY_PROF:
        groove = 0.0
        for gc in (-0.03, 0.03):
            groove -= 0.004 * math.exp(-((t - gc) / 0.006) ** 2)
        prof.append((rr + (groove if rr > 0.1 else 0.0), t))
    lathe(bm, prof, seg=64, axis='X', M=Matrix.Translation((0, 0, 0.26)))
    body = bm_to_obj('koyun_%d_yun' % i, bm)
    setmat(body, M_WOOL)
    body.parent = bob
    # kuyruk: küçük krem topuz
    bm = bmesh.new()
    blob(bm, (-0.215, 0, 0.3), (0.028, 0.026, 0.03), subdiv=3)
    tl = bm_to_obj('koyun_%d_kuyruk' % i, bm)
    setmat(tl, M_WOOL)
    tl.parent = bob
    # baş: tornalanmış (top + burun), koyu boya
    head = link(bpy.data.objects.new('koyun_%d_bas' % i, None))
    head.parent = bob
    head.location = (0.19, 0, 0.35)
    head.rotation_euler = (0, math.radians(18), 0)
    bm = bmesh.new()
    lathe(bm, [(0.0, -0.075), (0.04, -0.066), (0.066, -0.04), (0.076, 0.0), (0.072, 0.03), (0.064, 0.055),
               (0.057, 0.085), (0.054, 0.11), (0.046, 0.128), (0.026, 0.138), (0.0, 0.14)], seg=48, axis='X')
    hd = bm_to_obj('koyun_%d_yuz' % i, bm)
    setmat(hd, M_HEAD)
    hd.parent = head
    # başın üstünde krem boyalı perçem (küçük tornalanmış topuz)
    bm = bmesh.new()
    lathe(bm, [(0.0, 0.0), (0.04, 0.0), (0.045, 0.015), (0.035, 0.03), (0.0, 0.034)], seg=32,
          M=Matrix.Translation((-0.005, 0, 0.058)))
    tf = bm_to_obj('koyun_%d_percem' % i, bm)
    setmat(tf, M_WOOL)
    tf.parent = head
    ear_ol = [(0.0, 0.0), (0.03, 0.02), (0.075, 0.018), (0.1, 0.0), (0.075, -0.018), (0.03, -0.02)]
    for sgn in (1, -1):
        bm = bmesh.new()
        flat_piece(bm, ear_ol, 0.012, Matrix.Identity(4))
        ear = bm_to_obj('koyun_%d_kulak' % i, bm)
        setmat(ear, M_EAR)
        ear.parent = head
        ear.location = (-0.02, sgn * 0.058, 0.035)
        ear.rotation_euler = (math.radians(90) * sgn + sgn * 0.3, -0.35, sgn * math.radians(95))
        # boyalı göz: beyaz daire + siyah bebek (hafif kabarık boya)
        for nm, rad, th, mat, dz in (('goz', 0.026, 0.004, M_EYE_W, 0.0), ('bebek', 0.0135, 0.0056, M_EYE_B, 0.004)):
            bm = bmesh.new()
            lathe(bm, [(0.0, 0.0), (rad, 0.0), (rad, th * 0.6), (rad * 0.7, th), (0.0, th)], seg=24)
            e = bm_to_obj('koyun_%d_%s' % (i, nm), bm)
            setmat(e, mat)
            e.parent = head
            nrm = Vector((0.55, sgn * 0.8, 0.25)).normalized()
            base = Vector((0.058, sgn * 0.054, 0.03)) + nrm * (dz * 0.3)
            e.location = base + Vector((0.004, 0, 0.001)) * (1 if nm == 'bebek' else 0)
            e.rotation_mode = 'QUATERNION'
            e.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(nrm)
    # bacaklar: sabit tahta çubuklar (oyuncak), koyu boya
    for k, (lx, ly) in enumerate(((0.11, 0.07), (0.11, -0.07), (-0.11, 0.07), (-0.11, -0.07))):
        bm = bmesh.new()
        lathe(bm, [(0.0, 0.0), (0.026, 0.0), (0.031, 0.006), (0.031, 0.022), (0.027, 0.032), (0.026, 0.19), (0.0, 0.19)],
              seg=28, M=Matrix.Translation((lx, ly, 0.0)))
        leg = bm_to_obj('koyun_%d_bacak_%d' % (i, k), bm)
        setmat(leg, M_LEG)
        leg.parent = bob
    return root, bob, head


sheep = [build_sheep(i) for i in range(N_SHEEP)]
print('t koyun %.1f' % (time.time() - T_START), flush=True)


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


for i, (root, bob, head) in enumerate(sheep):
    prev_yaw = None
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
        moving = min(1.0, max(0.0, (sheep_s(i, f) - sheep_s(i, f - 1)) / SPEED))
        phase = s / 0.24 * math.pi + i
        root.location = (pos.x, pos.y, hfun(pos.x, pos.y))
        root.rotation_euler = (0, 0, yaw)
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        # oyuncak, görünmez bir elle yürütülür: sekme + yan yana yalpalama (bacaklar sabit)
        hop = abs(math.sin(phase))
        bob.location = (0, 0, 0.028 * hop * moving)
        bob.rotation_euler = (0.09 * math.sin(phase) * moving, -0.06 * math.cos(2 * phase) * moving * 0.5, 0)
        bob.keyframe_insert('location', frame=f)
        bob.keyframe_insert('rotation_euler', frame=f)
        head.rotation_euler = (0.04 * math.sin(f * 0.07 + i), math.radians(18) + 0.05 * math.sin(phase * 2) * moving
                               + 0.08 * math.sin(f * 0.05 + i * 2) * (1 - moving), 0.16 * math.sin(f * 0.03 + i) * (1 - moving))
        head.keyframe_insert('rotation_euler', frame=f)
print('t anim %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- ışık: sıcak akşam güneşi, net gölge (minyatür)
world = bpy.data.worlds.new('dunya')
scene.world = world
WN, WL = world.node_tree.nodes, world.node_tree.links
bg = WN['Background']
wtc = WN.new('ShaderNodeTexCoord')
sep = WN.new('ShaderNodeSeparateXYZ')
WL.new(wtc.outputs['Generated'], sep.inputs[0])
ramp = WN.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (1.0, 0.70, 0.45, 1)
ramp.color_ramp.elements[1].position = 0.35
ramp.color_ramp.elements[1].color = (0.92, 0.88, 0.78, 1)
WL.new(sep.outputs['Z'], ramp.inputs['Fac'])
WL.new(ramp.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.55


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


sun_dir = Vector((0.55, -0.78, -0.36)).normalized()
light('gunes', 'SUN', 4.4, (1.0, 0.70, 0.42), direction=sun_dir, size=math.radians(3.0))
light('dolgu', 'AREA', 90.0, (1.0, 0.91, 0.80), loc=(3.5, -4.5, 3.6),
      direction=(Vector((-0.4, 0.4, 0.3)) - Vector((3.5, -4.5, 3.6))), size=4.5)
light('arka_dolgu', 'AREA', 30.0, (1.0, 0.8, 0.6), loc=(-3.0, 4.0, 2.5),
      direction=(Vector((0, 1, 0.3)) - Vector((-3.0, 4.0, 2.5))), size=3.0)

# ---------------------------------------------------------------- kamera: aynı vuruşlar, tilt-shift alan derinliği
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
cam_data.dof.aperture_blades = 7
cam_data.dof.aperture_rotation = 0.3


def last_world(f):
    return (pouch_matrix(f) @ Matrix.Translation(heap_local[0])).to_translation()


P_END = last_world(N_FRAMES)
ROW3 = Vector((ROW_CENTER.x, ROW_CENTER.y, slab_z(ROW_CENTER)))
GATE3 = Vector((GATE.x, GATE.y, hfun(GATE.x, GATE.y) + 0.25))
TGT0 = GATE3.lerp(ROW3, 0.45) + Vector((0, 0, 0.0)) + RIGHT3 * 0.3 + FWD0.to_3d() * 0.35
TGT1 = TGT0 + Vector((-0.05, -0.05, 0.0))
CAM1 = CAM_POS0 + (TGT0 - CAM_POS0).normalized() * 0.3
CAM_END = P_END + (TO_CAM3 * 0.8 + RIGHT3 * 0.22 + Vector((0, 0, 0.62))).normalized() * 0.98
FOCUS0 = Vector((HANG.x, HANG.y, HANG.z - 0.2)).lerp(ROW3, 0.45)
PUSH0, PUSH1 = 212, 296
for f in range(-2, N_FRAMES + 3):
    t0 = max(0.0, min(1.0, (f - 1) / (PUSH0 - 1)))
    cpos = CAM_POS0.lerp(CAM1, t0)
    tpos = TGT0.lerp(TGT1, t0)
    e = smoother((f - PUSH0) / (PUSH1 - PUSH0))
    cpos = cpos.lerp(CAM_END, e)
    tpos = tpos.lerp(P_END + Vector((0, 0, -0.05)), e)
    cpos = cpos + Vector((0.003 * math.sin(f * 0.041), 0.0, 0.002 * math.sin(f * 0.057 + 1)))
    cam.location = cpos
    cam.keyframe_insert('location', frame=f)
    target.location = tpos
    target.keyframe_insert('location', frame=f)
    focus = FOCUS0.lerp(P_END, smoother((f - PUSH0 + 10) / (PUSH1 - PUSH0 - 10)))
    cam_data.dof.focus_distance = (cpos - focus).length
    cam_data.dof.keyframe_insert('focus_distance', frame=f)
    cam_data.dof.aperture_fstop = 0.55 + 0.5 * e
    cam_data.dof.keyframe_insert('aperture_fstop', frame=f)

# ---------------------------------------------------------------- son çakılın parıltısı
cam_dir_end = (CAM_END - P_END).normalized()
glint = light('parilti', 'POINT', 0.0, (1.0, 0.8, 0.5), loc=P_END + cam_dir_end * 0.35 + Vector((0, 0, 0.2)), size=0.02)
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
_top = (cam_dir_end * 0.35 + Vector((0, 0, 1))).normalized()
_M300 = pouch_matrix(N_FRAMES) @ Matrix.Translation(heap_local[0]) @ local_rot[0].to_matrix().to_4x4()
_l3, _q3, _s3 = _M300.decompose()
spark.location = (Matrix.Translation(_l3) @ _q3.to_matrix().to_4x4()).inverted() @ (P_END + _top * 0.031)
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
C.device = 'CPU'
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
C.max_bounces = 5
C.diffuse_bounces = 3
C.glossy_bounces = 2
C.transmission_bounces = 1
C.transparent_max_bounces = 2
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.seed = 7
C.sample_clamp_indirect = 6.0
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = True
R.motion_blur_shutter = 0.35
R.use_persistent_data = True
vs = scene.view_settings
vs.view_transform = 'AgX'
try:
    vs.look = 'AgX - Punchy'
except Exception:
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
for _f in (1, 68, 210, 296):
    scene.frame_set(_f)
    for _nm, _p in (('kapi', GATE3), ('kese', HANG), ('kese_alt', HANG + Vector((0, 0, -DROP * POUCH_S))),
                    ('dizi_bas', LAND[0].to_3d() + Vector((0, 0, slab_z(LAND[0])))),
                    ('dizi_son', LAND[-1].to_3d() + Vector((0, 0, slab_z(LAND[-1])))),
                    ('agil_sag', ring_pos(math.radians(330)).to_3d()), ('agil_arka', ring_pos(math.radians(80)).to_3d()),
                    ('son_cakil', P_END)):
        _c = world_to_camera_view(scene, cam, _p)
        print('KADRAJ f%d %-9s x=%.2f y(ust)=%.2f' % (_f, _nm, _c.x, 1 - _c.y))
    _c = world_to_camera_view(scene, cam, sheep[0][0].matrix_world.to_translation() + Vector((0, 0, 0.3)))
    print('KADRAJ f%d koyun0    x=%.2f y(ust)=%.2f' % (_f, _c.x, 1 - _c.y))
print('sahne kuruldu: %.1f sn' % (time.time() - T_START), flush=True)
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(A.cikti), 'ahsap.blend'))

_t = {}
bpy.app.handlers.render_pre.append(lambda sc, *a: _t.__setitem__('t', time.time()))
bpy.app.handlers.render_post.append(lambda sc, *a: print('KARE %d: %.1f sn' % (sc.frame_current, time.time() - _t.get('t', time.time())), flush=True))

R.image_settings.file_format = 'PNG'
R.image_settings.color_mode = 'RGB'
R.image_settings.color_depth = '8'
outdir = os.path.abspath(A.cikti)
if A.mod == 'kare':
    for f in [int(x) for x in A.kareler.split(',') if x.strip()]:
        scene.frame_set(f)
        R.filepath = os.path.join(outdir, 'kare_%04d.png' % f)
        bpy.ops.render.render(write_still=True)
elif A.mod == 'parca':
    scene.frame_start = A.bas
    scene.frame_end = A.son
    R.filepath = os.path.join(outdir, 'k_')
    bpy.ops.render.render(animation=True)
print('BITTI toplam %.1f sn' % (time.time() - T_START))
