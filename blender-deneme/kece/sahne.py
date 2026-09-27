# Math with Zirek · sahne G, KEÇE / ÖRGÜ sürüm (akşam, koyunlar girer, taş çıkar, tek taş kalır)
# Blender 5.2, Cycles CPU. Tamamen yordamsal, dış varlık yok. Sabit tohumlar.
# Görünüm: iğne keçesi koyunlar (tüylenmiş yün lifleri), keçe tepeler, dikiş izleri, örgü kese, keçe çakıllar;
# yumuşak sıcak akşam ışığı; el yapımı stop-motion hissi: her poz iki kare durur ("ikişerli", 15 poz/sn).
# Yerleşim, zamanlama ve kamera vuruşları kil sürümüyle (../sahne.py) aynı; çakıl dizisi ve kese büyütüldü.
# Kullanım (yalnız bulutta):
#   blender -b -P sahne.py -- --mod kare --kareler 68,210,290 --w 960 --h 540 --ornek 32 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 60 --cikti out       (1920x1080; çift kareler kopya)
import bpy, bmesh, math, random, sys, os, time, argparse, shutil
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
ap.add_argument('--tuy', type=int, default=1)          # yün lifleri (geometri düğümleri)
ap.add_argument('--blend', action='store_true')
A = ap.parse_args(argv)
T_START = time.time()

FPS = 30
N_FRAMES = 300
N_SHEEP = 8
T_GATE0 = 40          # ilk koyunun kapıdan geçtiği kare
T_GAP = 22            # koyunlar arası (0,73 sn)
SPEED = 0.95 / FPS


def fe(f):
    """stop-motion: her poz iki kare (1-2, 3-4, ...)."""
    return f - ((f - 1) % 2)


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
    if smooth_shade:
        for f in bm.faces:
            f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


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


def remeshed(name, bm, voxel, smooth_it=5, factor=0.7):
    ob = bm_to_obj(name, bm)
    rm = ob.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = voxel
    sm = ob.modifiers.new('sm', 'SMOOTH'); sm.factor = factor; sm.iterations = smooth_it
    bake_modifiers(ob)
    for pl in ob.data.polygons:
        pl.use_smooth = True
    return ob


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


# ---------------------------------------------------------------- düğüm yardımcıları
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


def fibre_height(nb, vec, scale):
    """Keçe lifleri: iki yöne uzatılmış ince gürültü + çok ince gren."""
    v1 = nb.mapping(vec, (1.0, 1.0, 7.0), (0.7, 0.3, 1.1))
    v2 = nb.mapping(vec, (7.0, 1.0, 1.0), (0.2, 1.3, 0.4))
    n1 = nb.noise(v1, 160 * scale, 6.0, 0.62, 1.2)
    n2 = nb.noise(v2, 210 * scale, 6.0, 0.62, 1.2)
    n3 = nb.noise(vec, 900 * scale, 2.0, 0.5)
    return nb.m('MULTIPLY_ADD', nb.m('ADD', n1, n2), 0.5, nb.m('MULTIPLY', n3, 0.35))


def felt(name, color, palette=None, var=0.08, hue_var=0.012, sheen=0.9, rough=0.93, bump=0.35, sss=0.05,
         mottle=0.10, fscale=1.0, fcontrast=0.14, emission=None, heather=0.0, dimple=0.0):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nb = NB(nt)
    N, L = nb.N, nb.L
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    oi = N.new('ShaderNodeObjectInfo')
    hs = N.new('ShaderNodeHueSaturation')
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
        L.new(rp.outputs['Color'], hs.inputs['Color'])
    else:
        hs.inputs['Color'].default_value = (*color, 1)
    L.new(nb.m('MULTIPLY_ADD', oi.outputs['Random'], hue_var * 2, 0.5 - hue_var), hs.inputs['Hue'])
    vr = nb.m('MULTIPLY_ADD', oi.outputs['Random'], var, 1.0 - var / 2)
    mt = nb.noise(tc.outputs['Object'], 3.0 / fscale, 3.0)
    mm = nb.m('MULTIPLY_ADD', mt, mottle * 2, 1.0 - mottle)
    fh = fibre_height(nb, tc.outputs['Object'], fscale)
    fc = nb.m('MULTIPLY_ADD', fh, fcontrast * 2, 1.0 - fcontrast * 0.9)
    val = nb.m('MULTIPLY', nb.m('MULTIPLY', vr, mm), fc)
    if heather > 0:
        # karışık yün: seyrek açık ve koyu lifler (benekli yün)
        hv = nb.mapping(tc.outputs['Object'], (1.0, 1.0, 5.0), (0.4, 0.9, 0.2))
        hn = nb.noise(hv, 120 * fscale, 3.0, 0.5, 2.0)
        hi = N.new('ShaderNodeMapRange'); hi.inputs['From Min'].default_value = 0.66; hi.inputs['From Max'].default_value = 0.7
        L.new(hn, hi.inputs['Value'])
        lo = N.new('ShaderNodeMapRange'); lo.inputs['From Min'].default_value = 0.34; lo.inputs['From Max'].default_value = 0.3
        L.new(hn, lo.inputs['Value'])
        val = nb.m('MULTIPLY', val, nb.m('MULTIPLY_ADD', hi.outputs['Result'], heather * 0.35,
                                         nb.m('MULTIPLY_ADD', lo.outputs['Result'], -heather * 0.45, 1.0)))
    L.new(val, hs.inputs['Value'])
    L.new(hs.outputs['Color'], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = bump
    bp.inputs['Distance'].default_value = 0.005
    height = fh
    if dimple > 0:
        # iğne izleri: küçük çukurlar
        vo = N.new('ShaderNodeTexVoronoi')
        vo.feature = 'F1'
        vo.inputs['Scale'].default_value = 140.0 * fscale
        L.new(tc.outputs['Object'], vo.inputs['Vector'])
        dm = N.new('ShaderNodeMapRange'); dm.inputs['From Min'].default_value = 0.0; dm.inputs['From Max'].default_value = 0.22
        L.new(vo.outputs['Distance'], dm.inputs['Value'])
        height = nb.m('MULTIPLY_ADD', dm.outputs['Result'], dimple, fh)
    L.new(height, bp.inputs['Height'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = rough
    _inp(b, ['Specular IOR Level'], 0.2)
    _inp(b, ['Sheen Weight'], sheen)
    _inp(b, ['Sheen Roughness'], 0.4)
    _inp(b, ['Sheen Tint'], (1.0, 0.97, 0.92, 1))
    if sss > 0:
        _inp(b, ['Subsurface Weight'], sss)
        _inp(b, ['Subsurface Radius'], (1.0, 0.6, 0.4))
        _inp(b, ['Subsurface Scale'], 0.008)
    if emission is not None:
        _inp(b, ['Emission Color'], (*emission, 1))
        _inp(b, ['Emission Strength'], 0.0)
    return m


def knit(name, color, cols=40.0, rows=24.0):
    """Örgü (düz örgü 'V' ilmekleri): UV üstünde yordamsal ilmek kabartması + lif."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nb = NB(nt)
    N, L = nb.N, nb.L
    b = N['Principled BSDF']
    uv = N.new('ShaderNodeUVMap')
    tc = N.new('ShaderNodeTexCoord')
    sp = N.new('ShaderNodeSeparateXYZ')
    L.new(uv.outputs['UV'], sp.inputs[0])
    x = nb.m('MULTIPLY', sp.outputs['X'], cols)
    y = nb.m('MULTIPLY', sp.outputs['Y'], rows)
    cx = nb.m('SUBTRACT', nb.m('FRACT', x), 0.5)
    cy = nb.m('SUBTRACT', nb.m('FRACT', y), 0.5)
    legs = []
    ca, sa = math.cos(0.5), math.sin(0.5)
    for s in (1, -1):
        px = nb.m('SUBTRACT', cx, s * 0.24)
        rx = nb.m('MULTIPLY_ADD', cy, s * sa, nb.m('MULTIPLY', px, ca))
        ry = nb.m('MULTIPLY_ADD', px, -s * sa, nb.m('MULTIPLY', cy, ca))
        d2 = nb.m('ADD', nb.m('POWER', nb.m('DIVIDE', rx, 0.21), 2.0), nb.m('POWER', nb.m('DIVIDE', ry, 0.6), 2.0))
        h = nb.m('SQRT', nb.m('MAXIMUM', nb.m('SUBTRACT', 1.0, d2), 0.0))
        # iplik bükümü: ilmek boyunca ince çizgiler
        tw = nb.m('MULTIPLY_ADD', nb.m('SINE', nb.m('MULTIPLY', nb.m('ADD', ry, nb.m('MULTIPLY', rx, 1.6)), 40.0)), 0.12, 0.88)
        legs.append(nb.m('MULTIPLY', h, tw))
    h = nb.m('MAXIMUM', legs[0], legs[1])
    fh = fibre_height(nb, tc.outputs['Object'], 1.3)
    oi = N.new('ShaderNodeObjectInfo')
    hs = N.new('ShaderNodeHueSaturation')
    hs.inputs['Color'].default_value = (*color, 1)
    shade = nb.m('MULTIPLY_ADD', h, 0.55, 0.45)
    L.new(nb.m('MULTIPLY', shade, nb.m('MULTIPLY_ADD', fh, 0.2, 0.9)), hs.inputs['Value'])
    L.new(hs.outputs['Color'], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.85
    bp.inputs['Distance'].default_value = 0.006
    L.new(nb.m('MULTIPLY_ADD', fh, 0.08, h), bp.inputs['Height'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.9
    _inp(b, ['Specular IOR Level'], 0.2)
    _inp(b, ['Sheen Weight'], 1.0)
    _inp(b, ['Sheen Roughness'], 0.4)
    _inp(b, ['Subsurface Weight'], 0.06)
    _inp(b, ['Subsurface Radius'], (1.0, 0.5, 0.3))
    _inp(b, ['Subsurface Scale'], 0.01)
    return m


def thread(name, color, sheen=0.6):
    """Pamuk/yün iplik: bükümlü çizgiler."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nb = NB(nt)
    N, L = nb.N, nb.L
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    wv = N.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'DIAGONAL'
    wv.inputs['Scale'].default_value = 160.0
    wv.inputs['Distortion'].default_value = 1.0
    L.new(tc.outputs['Object'], wv.inputs['Vector'])
    b.inputs['Base Color'].default_value = (*color, 1)
    hs = N.new('ShaderNodeHueSaturation')
    hs.inputs['Color'].default_value = (*color, 1)
    L.new(nb.m('MULTIPLY_ADD', wv.outputs['Fac'], 0.25, 0.8), hs.inputs['Value'])
    L.new(hs.outputs['Color'], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.6
    bp.inputs['Distance'].default_value = 0.002
    L.new(wv.outputs['Fac'], bp.inputs['Height'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.75
    _inp(b, ['Sheen Weight'], sheen)
    _inp(b, ['Specular IOR Level'], 0.25)
    return m


def simple(name, color, rough=0.5, spec=0.5, coat=0.0, coat_rough=0.1):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    _inp(b, ['Specular IOR Level'], spec)
    if coat:
        _inp(b, ['Coat Weight'], coat)
        _inp(b, ['Coat Roughness'], coat_rough)
    return m


def wood(name, color):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nb = NB(nt)
    N, L = nb.N, nb.L
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    wv = N.new('ShaderNodeTexWave')
    wv.wave_type = 'RINGS'
    wv.inputs['Scale'].default_value = 18.0
    wv.inputs['Distortion'].default_value = 6.0
    _inp(wv, ['Detail'], 3.0)
    L.new(nb.mapping(tc.outputs['Object'], (1.0, 1.0, 0.08)), wv.inputs['Vector'])
    hs = N.new('ShaderNodeHueSaturation')
    hs.inputs['Color'].default_value = (*color, 1)
    L.new(nb.m('MULTIPLY_ADD', wv.outputs['Fac'], 0.3, 0.8), hs.inputs['Value'])
    L.new(hs.outputs['Color'], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.15
    L.new(wv.outputs['Fac'], bp.inputs['Height'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.55
    _inp(b, ['Specular IOR Level'], 0.35)
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


# renk: kanalın sıcak krem / aşı / yeşil paleti. Çakıl safran-aşı, kese kök boya kırmızısı, taş yastığı serin gri.
M_GROUND = felt('zemin_kece', (0.14, 0.27, 0.055), var=0.0, mottle=0.18, fscale=0.7, bump=0.3, sss=0.0, sheen=0.3, heather=0.5)
M_PATCH = [felt('yama1', (0.36, 0.45, 0.12), var=0.0, bump=0.3, sss=0.0),
           felt('yama2', (0.52, 0.52, 0.18), var=0.0, bump=0.3, sss=0.0)]
M_GRASS_F = simple('ot_lif', (0.25, 0.42, 0.09), rough=0.7, spec=0.3)
M_STONE = felt('tas_kece', None, palette=[(0.40, 0.39, 0.37), (0.31, 0.31, 0.31), (0.47, 0.45, 0.42),
                                           (0.36, 0.34, 0.33), (0.27, 0.28, 0.29)], var=0.08, sss=0.0, bump=0.6,
               heather=1.0, dimple=0.5, fcontrast=0.2, sheen=0.7)
M_STONE_F = simple('tas_lif', (0.46, 0.45, 0.43), rough=0.6, spec=0.3)
M_WOOL = felt('yun', (0.93, 0.87, 0.74), var=0.05, sss=0.15, bump=0.6, sheen=1.0, fcontrast=0.12, heather=0.6, dimple=0.6)
M_WOOL_F = simple('yun_lif', (0.95, 0.90, 0.80), rough=0.6, spec=0.3)
M_FACE = felt('yuz', (0.13, 0.095, 0.08), var=0.1, sss=0.0, bump=0.35, sheen=1.0, fcontrast=0.2)
M_FACE_F = simple('yuz_lif', (0.18, 0.14, 0.12), rough=0.6, spec=0.3)
M_EAR_IN = felt('kulak_ic', (0.72, 0.45, 0.40), var=0.05, sss=0.1)
M_BEAD = simple('boncuk', (0.01, 0.01, 0.012), rough=0.08, spec=0.6, coat=1.0, coat_rough=0.03)
M_KNIT = knit('kese_orgu', (0.55, 0.10, 0.07))
M_KNIT_F = simple('kese_lif', (0.62, 0.16, 0.10), rough=0.6, spec=0.3)
M_YARN = thread('ip_yun', (0.90, 0.80, 0.60), sheen=0.8)
M_STITCH = thread('dikis', (0.93, 0.86, 0.70))
M_STITCH_R = thread('dikis_kirmizi', (0.62, 0.20, 0.10))
M_WOOD = wood('tahta', (0.46, 0.29, 0.15))
M_PEBBLE = felt('cakil', (0.84, 0.48, 0.13), var=0.12, hue_var=0.02, sss=0.05, bump=0.5, fcontrast=0.14, heather=0.6, dimple=0.4, sheen=0.7)
M_LAST = felt('son_cakil', (0.84, 0.48, 0.13), var=0.0, sss=0.05, bump=0.5, fcontrast=0.14, heather=0.6, dimple=0.4, sheen=0.7, emission=(1.0, 0.72, 0.38))
M_PEBBLE_F = simple('cakil_lif', (0.90, 0.58, 0.22), rough=0.6, spec=0.3)
M_SLAB = felt('yastik', (0.40, 0.42, 0.45), var=0.0, sss=0.0, bump=0.4, heather=0.6, sheen=0.5)
M_HILL = [felt('tepe1', (0.30, 0.40, 0.13), var=0.0, fscale=0.4, sss=0.0),
          felt('tepe2', (0.68, 0.48, 0.18), var=0.0, fscale=0.4, sss=0.0),
          felt('tepe3', (0.52, 0.55, 0.36), var=0.0, fscale=0.4, sss=0.0),
          felt('tepe4', (0.42, 0.47, 0.18), var=0.0, fscale=0.4, sss=0.0)]
M_LEAF = felt('yaprak', (0.20, 0.33, 0.09), var=0.05, sss=0.05)
M_TRUNK = felt('govde', (0.36, 0.22, 0.12), var=0.0, sss=0.0)
M_PETAL = felt('tac_yaprak', (0.97, 0.90, 0.72), var=0.1, sss=0.1)
M_KNOT = felt('fransiz_dugum', (0.95, 0.70, 0.18), var=0.1, sss=0.0)


# ---------------------------------------------------------------- yün lifleri (geometri düğümleri)
def fuzz_group(name, density, length, radius, mat, tilt=0.8, smin=0.4, smax=1.3, dens_attr=None):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Kaynak', in_out='INPUT', socket_type='NodeSocketObject')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    oinf = N.new('GeometryNodeObjectInfo')
    oinf.transform_space = 'RELATIVE'
    L.new(gi.outputs['Kaynak'], oinf.inputs['Object'])
    dp = N.new('GeometryNodeDistributePointsOnFaces')
    dp.inputs['Density'].default_value = density
    if dens_attr:
        na = N.new('GeometryNodeInputNamedAttribute')
        na.data_type = 'FLOAT'
        na.inputs['Name'].default_value = dens_attr
        mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'
        mu.inputs[1].default_value = density
        L.new(na.outputs['Attribute'], mu.inputs[0])
        L.new(mu.outputs[0], dp.inputs['Density'])
    L.new(oinf.outputs['Geometry'], dp.inputs['Mesh'])
    line = N.new('GeometryNodeCurvePrimitiveLine')
    line.inputs['End'].default_value = (0, 0, length)
    rsub = N.new('GeometryNodeResampleCurve')
    rsub.inputs['Count'].default_value = 4
    L.new(line.outputs['Curve'], rsub.inputs['Curve'])
    ip = N.new('GeometryNodeInstanceOnPoints')
    L.new(dp.outputs['Points'], ip.inputs['Points'])
    L.new(rsub.outputs['Curve'], ip.inputs['Instance'])
    rr = N.new('FunctionNodeRandomValue'); rr.data_type = 'FLOAT_VECTOR'
    rr.inputs['Min'].default_value = (-tilt, -tilt, 0.0); rr.inputs['Max'].default_value = (tilt, tilt, 6.283)
    e2r = N.new('FunctionNodeEulerToRotation'); L.new(rr.outputs['Value'], e2r.inputs[0])
    rot = N.new('FunctionNodeRotateRotation')
    try:
        rot.rotation_space = 'LOCAL'
    except Exception:
        pass
    L.new(dp.outputs['Rotation'], rot.inputs['Rotation'])
    L.new(e2r.outputs[0], rot.inputs['Rotate By'])
    L.new(rot.outputs[0], ip.inputs['Rotation'])
    rs = N.new('FunctionNodeRandomValue'); rs.data_type = 'FLOAT'
    rs.inputs['Min'].default_value = smin; rs.inputs['Max'].default_value = smax
    L.new(rs.outputs['Value'], ip.inputs['Scale'])
    re = N.new('GeometryNodeRealizeInstances')
    L.new(ip.outputs['Instances'], re.inputs['Geometry'])
    # lif hafifçe kıvrılır: noktaları gürültüyle kaydır (uca doğru artar)
    sp = N.new('GeometryNodeSetPosition')
    L.new(re.outputs['Geometry'], sp.inputs['Geometry'])
    pos = N.new('GeometryNodeInputPosition')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 90.0 / max(0.01, length * 30)
    try:
        nz.noise_dimensions = '3D'
    except Exception:
        pass
    L.new(pos.outputs[0], nz.inputs['Vector'])
    sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'
    L.new(nz.outputs['Color'], sub.inputs[0]); sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    par = N.new('GeometryNodeSplineParameter')
    sc = N.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'
    L.new(sub.outputs[0], sc.inputs[0])
    fac = N.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'; fac.inputs[1].default_value = length * 2.2
    L.new(par.outputs['Factor'], fac.inputs[0])
    L.new(fac.outputs[0], sc.inputs['Scale'])
    L.new(sc.outputs[0], sp.inputs['Offset'])
    cr = N.new('GeometryNodeSetCurveRadius'); cr.inputs['Radius'].default_value = radius
    L.new(sp.outputs['Geometry'], cr.inputs['Curve'])
    sm = N.new('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = mat
    L.new(cr.outputs['Curve'], sm.inputs['Geometry'])
    L.new(sm.outputs[0], go.inputs[0])
    return ng


def add_fuzz(ob, group):
    if not A.tuy or group is None:
        return
    cu = bpy.data.hair_curves.new(ob.name + '_lif')
    for sl in group.nodes:
        if sl.bl_idname == 'GeometryNodeSetMaterial':
            cu.materials.append(sl.inputs['Material'].default_value)
    co = link(bpy.data.objects.new(ob.name + '_lif', cu))
    co.parent = ob
    co.matrix_parent_inverse = Matrix.Identity(4)
    g2 = group.copy()
    for nd in g2.nodes:
        if nd.bl_idname == 'GeometryNodeObjectInfo':
            for lk in list(nd.inputs['Object'].links):
                g2.links.remove(lk)
            nd.inputs['Object'].default_value = ob
    md = co.modifiers.new('lif', 'NODES')
    md.node_group = g2


FZ_WOOL = fuzz_group('lif_yun', 30000.0, 0.016, 0.0006, M_WOOL_F, tilt=1.1)
FZ_FACE = fuzz_group('lif_yuz', 20000.0, 0.005, 0.0003, M_FACE_F, tilt=1.3)
FZ_KNIT = fuzz_group('lif_kese', 30000.0, 0.006, 0.00025, M_KNIT_F, tilt=1.3)
FZ_PEB = fuzz_group('lif_cakil', 30000.0, 0.006, 0.0003, M_PEBBLE_F, tilt=1.3)
FZ_STONE = fuzz_group('lif_tas', 16000.0, 0.006, 0.0003, M_STONE_F, tilt=1.3)
FZ_GRASS = fuzz_group('lif_ot', 6500.0, 0.036, 0.002, M_GRASS_F, tilt=0.6, smin=0.35, smax=1.2, dens_attr='ot')


# ---------------------------------------------------------------- yerleşim (kil sürümüyle aynı düzen)
PEN_C = Vector((0.3, 1.3))
PEN_R = 1.35
GATE_ANG = math.radians(228)
GAP_HALF = 0.26
CAM_POS0 = Vector((1.0, -3.9, 1.75))
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
    h = 0.55 * smooth(3.6, 13.0, y)
    h += flat * (0.07 * math.sin(0.55 * x + 0.3) * math.cos(0.42 * y + 0.8) + 0.03 * math.sin(1.3 * x - 0.7 * y))
    h += 0.01 * noise.noise(Vector((x * 0.9, y * 0.9, 3.1)))
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
LAND = [p + Vector((_rr.uniform(-0.008, 0.008), _rr.uniform(-0.008, 0.008))) for p in LAND]

# koyun yolları: soldan, dizinin arkasından geçip kapıya
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


# ---------------------------------------------------------------- zemin (keçe) + yün otlar
def ot_density(x, y):
    """yün ot öbekleri: gürültülü öbekler; sağ alt üçte bir, dizi, yol ve kese önü boş."""
    p = Vector((x, y))
    n = noise.noise(Vector((x * 3.2, y * 3.2, 0.7)))
    d = smooth(0.1, 0.35, n)
    dpen = (p - PEN_C).length
    wall = math.exp(-((dpen - PEN_R - 0.12) / 0.09) ** 2) + 0.7 * math.exp(-((dpen - PEN_R + 0.14) / 0.07) ** 2)
    d = max(d * 0.55, min(1.0, wall * (0.6 + 0.8 * max(0, n + 0.2))))
    if ang_dist(math.atan2(y - PEN_C.y, x - PEN_C.x), GATE_ANG) < GAP_HALF + 0.08 and abs(dpen - PEN_R) < 0.3:
        d = 0.0
    rel = p - CAM_POS0.xy
    fx, rx = rel.dot(FWD0), rel.dot(RIGHT)
    if rx > 0.35 * fx - 0.4 and fx < 4.3:          # kameranın sağ önü (sağ alt üçte bir)
        d *= 0.08
    if (p - ROW_CENTER).length < 0.75 or (p - FP).length < 0.35:
        d = 0.0
    if near_path(p, 0.28):
        d *= 0.15
    if y > 3.8:
        d *= 0.3
    return d


def build_ground():
    bm = bmesh.new()
    x0, x1, y0, y1 = -9.0, 9.0, -6.0, 14.0
    nx, ny = 200, 190
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
    setmat(ob, M_GROUND)
    me = ob.data
    at = me.attributes.new('ot', 'FLOAT', 'POINT')
    vals = [ot_density(v.co.x, v.co.y) if v.co.y < 6.0 else 0.0 for v in me.vertices]
    at.data.foreach_set('value', vals)
    add_fuzz(ob, FZ_GRASS)
    return ob


def cylinder_between(bm, p0, p1, r, seg=6):
    d = p1 - p0
    L = d.length
    if L < 1e-5:
        return
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    M = Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=L, matrix=M)


def resample(pts, step):
    out = [pts[0]]
    acc = 0.0
    for k in range(1, len(pts)):
        a, b = pts[k - 1], pts[k]
        seg = (b - a).length
        t = step - acc
        while t <= seg:
            out.append(a.lerp(b, t / seg))
            t += step
        acc = seg - (t - step)
    return out


def running_stitch(name, pts, mat, r=0.0028, dash=0.024, gap=0.014):
    bm = bmesh.new()
    rs = resample([Vector(p) for p in pts], 0.002)
    per = int(round((dash + gap) / 0.002))
    nd = int(round(dash / 0.002))
    for k in range(0, len(rs) - nd, per):
        cylinder_between(bm, rs[k], rs[k + nd], r)
    ob = bm_to_obj(name, bm, smooth_shade=True)
    setmat(ob, mat)
    return ob


def blanket_stitch(name, outline, z_top, z_low, mat, inward=0.016, step=0.03, r=0.0026, zf=None):
    """keçe parçasının kenarı: kenara dik iğne geçişleri + kenar boyunca ip."""
    bm = bmesh.new()
    n = len(outline)
    cx = sum((p.x for p in outline), 0.0) / n
    cy = sum((p.y for p in outline), 0.0) / n
    c = Vector((cx, cy))
    rs = resample([Vector(p) for p in outline] + [Vector(outline[0])], step)
    edge = []
    for p in rs:
        dirv = (p - c).normalized()
        zt = (zf(p.x, p.y) if zf else 0.0) + z_top
        zl = (zf(p.x, p.y) if zf else 0.0) + z_low
        a = Vector((p.x, p.y, zt + r)) - dirv.to_3d() * inward
        b = Vector((p.x, p.y, zt + r * 0.6)) + dirv.to_3d() * 0.003
        e = Vector((p.x, p.y, zl)) + dirv.to_3d() * 0.005
        cylinder_between(bm, a, b, r)
        cylinder_between(bm, b, e, r)
        edge.append(b)
    for k in range(len(edge) - 1):
        cylinder_between(bm, edge[k], edge[k + 1], r * 0.95)
    ob = bm_to_obj(name, bm)
    setmat(ob, mat)
    return ob


def felt_patch(name, outline, thick, mat, zf, lift=0.0):
    """düz keçe parça: çevre çokgeni, üst ve alt yüz, zemine uyar."""
    bm = bmesh.new()
    top = [bm.verts.new((p.x, p.y, zf(p.x, p.y) + lift + thick)) for p in outline]
    bot = [bm.verts.new((p.x, p.y, zf(p.x, p.y) + lift - 0.004)) for p in outline]
    ft = bm.faces.new(top)
    fb = bm.faces.new(list(reversed(bot)))
    n = len(outline)
    for k in range(n):
        bm.faces.new((bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k]))
    bmesh.ops.triangulate(bm, faces=[ft, fb])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = bm_to_obj(name, bm, smooth_shade=False)
    setmat(ob, mat)
    return ob


def blob_outline(rx, ry, n, seed, jit=0.12, rot=0.0, c=Vector((0, 0))):
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        f = 1.0 + jit * noise.noise(Vector((math.cos(t) * 1.6, math.sin(t) * 1.6, seed * 0.37)))
        x, y = rx * math.cos(t) * f, ry * math.sin(t) * f
        cs, sn = math.cos(rot), math.sin(rot)
        out.append(c + Vector((x * cs - y * sn, x * sn + y * cs)))
    return out


# ---------------------------------------------------------------- ağıl: keçe taşlar
def stone(bm, loc, radii, yaw, seed, tilt=0.1):
    r = rng(seed)
    rot = Euler((r.uniform(-tilt, tilt), r.uniform(-tilt, tilt), yaw))
    blob(bm, loc, radii, subdiv=3, amp=0.2, nscale=1.8, seed=seed, rot=rot)


def build_pen():
    r = rng(21)
    n = int(2 * math.pi * PEN_R / 0.15)
    for course in range(5):
        # basit yol: taşları yeniden, her renk grubu için ayrı nesne olarak üret
        for g in range(5):
            bmg = bmesh.new()
            rg = rng(21 + course)
            for j in range(n):
                a = (j + 0.5 * course + rg.uniform(-0.1, 0.1)) * 2 * math.pi / n
                if ang_dist(a, GATE_ANG) < GAP_HALF + 0.12:
                    continue
                skip = course == 4 and rng(900 + j * 7 + course).random() < 0.18
                if skip or (j * 7 + course * 3) % 5 != g:
                    continue
                p = ring_pos(a, PEN_R + rng(j * 31 + course).uniform(-0.015, 0.015))
                r2 = rng(j * 13 + course * 101)
                sx = r2.uniform(0.07, 0.092) * (0.9 if course == 4 else 1.0)
                sy = r2.uniform(0.052, 0.066)
                sz = r2.uniform(0.038, 0.046)
                z = hfun(p.x, p.y) + 0.036 + course * 0.07 + r2.uniform(-0.005, 0.005)
                stone(bmg, (p.x, p.y, z), (sx, sy, sz), a + math.pi / 2 + r2.uniform(-0.12, 0.12), 100 + course * 100 + j)
            ob = bm_to_obj('duvar_%d_%d' % (course, g), bmg)
            add_subsurf(ob, 1, 0)
            setmat(ob, M_STONE)
            add_fuzz(ob, FZ_STONE)
    # kapı direkleri: iri keçe taşlar üst üste
    for side, a in (('on', FRONT_A), ('arka', BACK_A)):
        p = ring_pos(a)
        z = hfun(p.x, p.y) + 0.055
        for k in range(8):
            bm = bmesh.new()
            rr = r.uniform(0.11, 0.125) - k * 0.004
            hz = r.uniform(0.042, 0.05)
            stone(bm, (p.x + r.uniform(-0.012, 0.012), p.y + r.uniform(-0.012, 0.012), z), (rr, rr * 0.92, hz),
                  r.uniform(0, 6.28), 500 + k + (0 if side == 'on' else 50), tilt=0.06)
            ob = bm_to_obj('direk_%s_%d' % (side, k), bm)
            add_subsurf(ob, 1, 0)
            setmat(ob, M_STONE)
            add_fuzz(ob, FZ_STONE)
            z += hz * 1.78
    return z


POST_TOP = build_pen()
print('t duvar %.1f' % (time.time() - T_START), flush=True)


# ---------------------------------------------------------------- kapı kanadı (tahta çıta, yünle bağlı)
def build_hurdle():
    p = BP
    t = Vector((math.sin(BACK_A), -math.cos(BACK_A)))
    inward = (PEN_C - p).normalized()
    start = p + inward * 0.2 + t * 0.12
    d = (t * 0.85 + inward * 0.15).normalized()
    yaw = math.atan2(d.y, d.x)
    bm = bmesh.new()
    Lh = 0.62
    z0 = hfun(start.x, start.y)
    for k, zz in enumerate((0.12, 0.23, 0.34)):
        c = start + d * (Lh / 2)
        blob(bm, (c.x, c.y, z0 + zz), (Lh / 2, 0.018, 0.022), subdiv=3, amp=0.04, nscale=2.0, seed=700 + k, rot=Euler((0, 0, yaw)))
    for k, s in enumerate((0.03, Lh / 2, Lh - 0.03)):
        c = start + d * s
        blob(bm, (c.x, c.y, z0 + 0.2), (0.02, 0.02, 0.21), subdiv=3, amp=0.05, nscale=2.0, seed=720 + k, rot=Euler((0, 0, yaw)))
    ob = bm_to_obj('kapi_kanadi', bm)
    add_subsurf(ob, 1, 0)
    setmat(ob, M_WOOD)



# ---------------------------------------------------------------- taş yastığı (dizinin yeri): gri keçe, battaniye dikişi
_slab_out = blob_outline(0.62, 0.155, 72, 55, jit=0.06, rot=math.atan2(RIGHT.y, RIGHT.x), c=ROW_CENTER)
SLAB_T = 0.026
felt_patch('yastik', _slab_out, SLAB_T, M_SLAB, hfun, lift=0.002)
blanket_stitch('yastik_dikis', _slab_out, SLAB_T + 0.002, 0.0, M_STITCH, zf=hfun)
SLAB_TOP = SLAB_T + 0.002


def slab_z(p):
    return hfun(p.x, p.y) + SLAB_TOP


# zeminde birkaç açık yeşil keçe yama, çevresi dikişli (sağ alt üçte bir boş)
for k, (c, rx, ry, rot, mat) in enumerate((((-1.9, 0.9), 0.55, 0.32, 0.4, M_PATCH[0]),
                                            ((1.95, 3.25), 0.5, 0.3, -0.3, M_PATCH[1]),
                                            ((-2.6, -0.9), 0.45, 0.28, 0.9, M_PATCH[0]))):
    ol = blob_outline(rx, ry, 56, 60 + k, jit=0.14, rot=rot, c=Vector(c))
    felt_patch('yama_%d' % k, ol, 0.012, mat, hfun, lift=0.001)
    blanket_stitch('yama_dikis_%d' % k, ol, 0.014, 0.0, M_STITCH, zf=hfun, step=0.035)

GROUND = build_ground()
print('t zemin %.1f' % (time.time() - T_START), flush=True)


# ---------------------------------------------------------------- arka plan: keçe tepeler (dikişli), keçe ağaç, çiçekler
HILLS = []
for k, (c, rad, mat) in enumerate((((-6.5, 16.0, -0.4), (8.5, 3.4, 2.1), M_HILL[0]),
                                   ((7.0, 18.0, -0.6), (9.5, 3.8, 2.5), M_HILL[1]),
                                   ((0.5, 26.0, -1.0), (15.0, 5.0, 3.6), M_HILL[2]),
                                   ((-1.5, 13.5, -0.5), (5.0, 2.2, 1.35), M_HILL[3]))):
    bm = bmesh.new()
    blob(bm, c, rad, subdiv=5, amp=0.04, nscale=1.2, seed=900 + k)
    ob = bm_to_obj('tepe_%d' % k, bm)
    setmat(ob, mat)
    HILLS.append((ob, c, rad))
for k, (c, rad, mat) in enumerate((((-2.8, 7.6, -0.35), (3.0, 1.5, 1.0), M_HILL[2]),
                                   ((1.6, 8.6, -0.45), (3.6, 1.7, 1.2), M_HILL[1]),
                                   ((5.0, 7.2, -0.35), (2.6, 1.3, 0.85), M_HILL[0]))):
    c = (c[0], c[1], c[2] + hfun(c[0], c[1]))
    bm = bmesh.new()
    blob(bm, c, rad, subdiv=5, amp=0.05, nscale=1.4, seed=950 + k)
    ob = bm_to_obj('yakin_tepe_%d' % k, bm)
    setmat(ob, mat)
    HILLS.append((ob, c, rad))
bpy.context.view_layer.update()
_dg = bpy.context.evaluated_depsgraph_get()


def project_down(x, y, z0=12.0):
    hit, loc, nrm, idx, ob, mw = scene.ray_cast(_dg, Vector((x, y, z0)), Vector((0, 0, -1)))
    return (loc + nrm * 0.004) if hit else None


for k, (ob, c, rad) in enumerate(HILLS):
    # tepe üstünde dalgalı dikiş izi (iki keçe parçasının birleşim yeri gibi)
    for s in range(2):
        pts = []
        for j in range(160):
            u = -0.85 + 1.7 * j / 159
            x = c[0] + u * rad[0]
            y = c[1] - rad[1] * (0.55 - 0.35 * s) + 0.35 * math.sin(u * 5 + k + s)
            p = project_down(x, y)
            if p is not None and p.z > hfun(x, y) + 0.05:
                pts.append(p)
            elif len(pts) > 5:
                break
        if len(pts) > 5:
            running_stitch('tepe_dikis_%d_%d' % (k, s), pts, M_STITCH if s == 0 else M_STITCH_R, r=0.012, dash=0.13, gap=0.08)


def felt_tree(name, x, y, sc, seed):
    r = rng(seed)
    z = hfun(x, y)
    bm = bmesh.new()
    blob(bm, (x, y, z + 0.3 * sc), (0.09 * sc, 0.09 * sc, 0.4 * sc), subdiv=3, amp=0.05, seed=seed)
    t = bm_to_obj(name + '_govde', bm)
    setmat(t, M_TRUNK)
    bm = bmesh.new()
    for k in range(5):
        blob(bm, (x + r.uniform(-0.3, 0.3) * sc, y + r.uniform(-0.2, 0.2) * sc, z + (0.9 + r.uniform(-0.05, 0.3)) * sc),
             (r.uniform(0.36, 0.46) * sc,) * 3, subdiv=3, amp=0.05, seed=seed + k)
    lf = remeshed(name + '_tac', bm, 0.03 * sc, 8, 0.9)
    setmat(lf, M_LEAF)
    # tacın ortasından dolanan dikiş
    pts = []
    for j in range(80):
        a = 2 * math.pi * j / 79
        o = Vector((x + math.cos(a) * 1.5 * sc, y + math.sin(a) * 1.5 * sc, z + 1.02 * sc))
        hit, loc, nrm, idx = lf.ray_cast(lf.matrix_world.inverted() @ o, Vector((x, y, z + 1.02 * sc)) - o)
        if hit:
            pts.append(lf.matrix_world @ loc + nrm * 0.004)
    if len(pts) > 10:
        running_stitch(name + '_dikis', pts, M_STITCH, r=0.006, dash=0.05, gap=0.03)


felt_tree('agac1', -2.4, 3.0, 0.62, 1301)
felt_tree('agac2', 2.9, 5.2, 0.5, 1311)
felt_tree('agac3', -1.1, 3.7, 0.5, 1321)
felt_tree('agac4', 2.4, 3.6, 0.45, 1331)
felt_tree('agac5', 0.7, 4.6, 0.4, 1341)


def flowers():
    r = rng(1400)
    bmp = bmesh.new()
    bmk = bmesh.new()
    k = 0
    while k < 46:
        x = r.uniform(-4.5, 4.0); y = r.uniform(-2.2, 5.5)
        p = Vector((x, y))
        rel = p - CAM_POS0.xy
        if rel.dot(RIGHT) > 0.35 * rel.dot(FWD0) - 0.6:
            continue
        if (p - PEN_C).length < PEN_R + 0.35 or near_path(p, 0.45) or (p - ROW_CENTER).length < 0.9:
            continue
        k += 1
        z = hfun(x, y) + 0.012
        sc = r.uniform(0.8, 1.2)
        for j in range(5):
            a = 2 * math.pi * j / 5 + r.uniform(0, 1)
            blob(bmp, (x + math.cos(a) * 0.017 * sc, y + math.sin(a) * 0.017 * sc, z), (0.014 * sc, 0.009 * sc, 0.004),
                 subdiv=2, seed=k * 10 + j, rot=Euler((0, 0, a)))
        blob(bmk, (x, y, z + 0.004), (0.008 * sc, 0.008 * sc, 0.006 * sc), subdiv=2, amp=0.2, seed=k)
    ob = bm_to_obj('cicek_yaprak', bmp); setmat(ob, M_PETAL)
    ob = bm_to_obj('cicek_dugum', bmk); setmat(ob, M_KNOT)


flowers()

# ---------------------------------------------------------------- kese (örgü), çivi, yün ip
POUCH_S = 1.45
PEG_Z = POST_TOP - 0.1
_pd = (TO_CAM * 0.55 + RIGHT * 0.8).normalized()
_pegdir = Vector((_pd.x, _pd.y, 0.16)).normalized()
PEG_BASE = Vector((FP.x, FP.y, PEG_Z))
PEG_LEN = 0.3


def build_peg():
    bm = bmesh.new()
    q = Vector((0, 0, 1)).rotation_difference(_pegdir)
    blob(bm, (PEG_BASE + _pegdir * (PEG_LEN / 2))[:], (0.019, 0.019, PEG_LEN / 2), subdiv=3, amp=0.03, nscale=2.0, seed=77, rot=q)
    peg = bm_to_obj('civi', bm)
    add_subsurf(peg, 1, 0)
    setmat(peg, M_WOOD)


build_peg()
HANG = PEG_BASE + _pegdir * (PEG_LEN - 0.05) + Vector((0, 0, 0.014))
PROF = [(0.0, 0.0), (0.06, 0.004), (0.095, 0.02), (0.115, 0.05), (0.12, 0.085), (0.112, 0.12),
        (0.09, 0.15), (0.064, 0.171), (0.05, 0.182), (0.054, 0.192), (0.066, 0.205), (0.078, 0.218), (0.084, 0.228)]
DROP = 0.37
LIP_Z = 0.228 - DROP
NECK_Z = 0.182 - DROP


def build_pouch():
    seg = 48
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    rings = []
    vs = [0.0]
    for k in range(1, len(PROF)):
        vs.append(vs[-1] + math.hypot(PROF[k][0] - PROF[k - 1][0], PROF[k][1] - PROF[k - 1][1]))
    vt = vs[-1]
    bottom = bm.verts.new((0, 0, -DROP))
    for (rr, zz) in PROF[1:]:
        ring = []
        for s in range(seg):
            th = 2 * math.pi * s / seg
            gather = smooth(0.13, 0.18, zz)
            fold = gather * (0.003 * math.sin(11 * th + 1.3) + 0.006 * noise.noise(Vector((math.cos(th) * 3.0, math.sin(th) * 3.0, zz * 25))))
            wob = 0.008 * noise.noise(Vector((math.cos(th) * 2.6, math.sin(th) * 2.6, zz * 12)))
            r2 = rr + fold + wob * (rr / 0.1)
            if zz < 0.1:
                r2 += 0.006 * max(0.0, math.cos(th - 0.3))
            dz = smooth(0.2, 0.228, zz) * (0.003 * math.sin(9 * th + 1.3))
            ring.append(bm.verts.new((r2 * math.cos(th) * 1.04, r2 * math.sin(th) * 0.96, zz - DROP + dz)))
        rings.append(ring)
    for s in range(seg):
        f = bm.faces.new((bottom, rings[0][s], rings[0][(s + 1) % seg]))
        uvs = [((s + 0.5) / seg, 0.0), (s / seg, vs[1] / vt), ((s + 1) / seg, vs[1] / vt)]
        for lp, uv in zip(f.loops, uvs):
            lp[uvl].uv = uv
    for k in range(len(rings) - 1):
        for s in range(seg):
            f = bm.faces.new((rings[k][s], rings[k + 1][s], rings[k + 1][(s + 1) % seg], rings[k][(s + 1) % seg]))
            uvs = [(s / seg, vs[k + 1] / vt), (s / seg, vs[k + 2] / vt), ((s + 1) / seg, vs[k + 2] / vt), ((s + 1) / seg, vs[k + 1] / vt)]
            for lp, uv in zip(f.loops, uvs):
                lp[uvl].uv = uv
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pouch = bm_to_obj('kese', bm)
    sol = pouch.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.008
    add_subsurf(pouch, 2, 0)
    setmat(pouch, M_KNIT)
    add_fuzz(pouch, FZ_KNIT)
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
        ob.data.materials.append(M_YARN)
        ob.parent = pouch
        return ob
    back = inv @ Vector((-TO_CAM.x, -TO_CAM.y, 0)).normalized()
    side = inv @ Vector((-TO_CAM.y, TO_CAM.x, 0)).normalized()
    zb = NECK_Z
    curve('ip_aski', [(back * 0.052 + Vector((0, 0, zb)))[:], (back * 0.05 + Vector((0, 0, zb + 0.05)))[:],
                      (back * 0.02 + Vector((0, 0, -0.01)))[:], (0, 0, 0.0)], bevel=0.0055)
    curve('ip_bogaz', [(0.056 * math.cos(2 * math.pi * s / 12) * 1.04, 0.056 * math.sin(2 * math.pi * s / 12) * 0.96,
                        zb + 0.004 * math.sin(3 * s)) for s in range(12)], cyclic=True, bevel=0.0068)
    fr = -back
    for k, (dx, ln) in enumerate(((0.012, 0.08), (-0.004, 0.065))):
        curve('ip_uc_%d' % k, [(fr * 0.058 + side * dx + Vector((0, 0, zb)))[:],
                               (fr * 0.068 + side * (dx + 0.01) + Vector((0, 0, zb - ln * 0.5)))[:],
                               (fr * 0.07 + side * (dx + 0.006) + Vector((0, 0, zb - ln)))[:]], bevel=0.0045)
    # ip uçlarında küçük ponpon
    for k, (dx, ln) in enumerate(((0.012, 0.08), (-0.004, 0.065))):
        bm2 = bmesh.new()
        blob(bm2, (fr * 0.07 + side * (dx + 0.006) + Vector((0, 0, zb - ln - 0.008)))[:], (0.011, 0.011, 0.011), subdiv=2, amp=0.15, seed=90 + k)
        pp = bm_to_obj('ponpon_%d' % k, bm2)
        setmat(pp, M_YARN)
        pp.parent = pouch
        add_fuzz(pp, FZ_FACE)
    return pouch, q0


pouch, POUCH_Q0 = build_pouch()


def pouch_quat(f):
    f = fe(f)
    to_cam = TO_CAM
    ax1 = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    ax2 = Vector((to_cam.x, to_cam.y, 0))
    a1 = a2 = 0.0
    for i in range(N_SHEEP):
        tp = T_GATE0 + T_GAP * i - 3
        if f > tp:
            dt = f - tp
            a1 += 0.045 * math.exp(-dt / 12.0) * math.sin(dt * 0.45)
            a2 += 0.025 * math.exp(-dt / 12.0) * math.sin(dt * 0.38 + 1.0)
    return Quaternion(ax1, a1) @ Quaternion(ax2, a2) @ POUCH_Q0


def pouch_matrix(f):
    return Matrix.Translation(HANG) @ pouch_quat(f).to_matrix().to_4x4() @ Matrix.Scale(POUCH_S, 4)


for f in range(-2, N_FRAMES + 3):
    pouch.rotation_quaternion = pouch_quat(f)
    pouch.keyframe_insert('rotation_quaternion', frame=f)
print('t kese %.1f' % (time.time() - T_START), flush=True)


# ---------------------------------------------------------------- çakıllar: keçe toplar (safran-aşı)
def pebble_mesh(name, seed, mat):
    r = rng(seed)
    bm = bmesh.new()
    blob(bm, (0, 0, 0), (r.uniform(0.049, 0.054), r.uniform(0.039, 0.043), r.uniform(0.028, 0.031)),
         subdiv=4, amp=0.08, nscale=1.3, seed=seed)
    ob = bm_to_obj(name, bm)
    setmat(ob, mat)
    add_fuzz(ob, FZ_PEB)
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
    land_q = Quaternion((0, 0, 1), math.atan2(RIGHT.y, RIGHT.x) + rng(6000 + idx).uniform(-0.35, 0.35))
    for f in range(-2, N_FRAMES + 3):
        g = fe(f)
        if g <= t_take:
            M = pouch_matrix(g) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            loc, q, _ = M.decompose()
        else:
            M0 = pouch_matrix(t_take) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            p0, q0, _ = M0.decompose()
            L2 = LAND[order]
            p1 = Vector((L2.x, L2.y, slab_z(L2) + 0.027))
            t = min(1.0, (g - t_take) / FLIGHT)
            e = smoother(t)
            if t < 0.3:
                loc = p0 + Vector((0, 0, 0.1 * smoother(t / 0.3)))
            else:
                v = smoother((t - 0.3) / 0.7)
                loc = (p0 + Vector((0, 0, 0.1))).lerp(p1, v) + Vector((0, 0, 0.16 * 4 * v * (1 - v)))
            q = q0.slerp(land_q, e)
            q = Quaternion((1, 0, 0), 2.0 * math.sin(math.pi * e)) @ q if t < 1 else land_q
            if t >= 1:
                dt = g - t_take - FLIGHT
                loc = p1 + Vector((0, 0, 0.014 * math.exp(-dt / 2.0) * abs(math.sin(dt * 1.3))))
        q = qfix(q, prev_q)
        prev_q = q
        peb.location = loc
        peb.rotation_quaternion = q
        peb.keyframe_insert('location', frame=f)
        peb.keyframe_insert('rotation_quaternion', frame=f)
print('t cakil %.1f' % (time.time() - T_START), flush=True)


# ---------------------------------------------------------------- koyun: iğne keçesi
def build_sheep(i):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('koyun_%d' % i, None))
    bob = link(bpy.data.objects.new('koyun_%d_govde' % i, None))
    bob.parent = root
    s = r.uniform(0.84, 0.92)
    root.scale = (s, s, s)
    # sıkı keçelenmiş gövde: yumurta biçimi, hafif yumrular (pamuk topu değil)
    bm = bmesh.new()
    blob(bm, (0, 0, 0.25), (0.215, 0.14, 0.13), subdiv=4, amp=0.03, seed=i)
    for k in range(26):
        u = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
        if u.z < -0.35:
            u.z = -0.35
        pos = Vector((u.x * 0.2, u.y * 0.128, u.z * 0.118 + 0.25))
        rad = r.uniform(0.045, 0.06)
        blob(bm, pos[:], (rad, rad, rad * 0.85), subdiv=2, seed=i * 50 + k)
    blob(bm, (-0.225, 0, 0.29), (0.035, 0.03, 0.03), subdiv=2, seed=i + 400)
    wool = remeshed('koyun_%d_yun' % i, bm, 0.009, 6, 0.75)
    setmat(wool, M_WOOL)
    wool.parent = bob
    add_fuzz(wool, FZ_WOOL)
    # baş: koyu kahve keçe, yuvarlak burun
    head = link(bpy.data.objects.new('koyun_%d_bas' % i, None))
    head.parent = bob
    head.location = (0.205, 0, 0.31)
    head.rotation_euler = (0, math.radians(20), 0)
    bm = bmesh.new()
    blob(bm, (0.055, 0, 0.0), (0.085, 0.066, 0.074), subdiv=3, amp=0.03, seed=i + 500)
    blob(bm, (0.12, 0, -0.034), (0.064, 0.052, 0.05), subdiv=3, amp=0.03, seed=i + 510)
    hd = remeshed('koyun_%d_yuz' % i, bm, 0.006, 4, 0.6)
    setmat(hd, M_FACE)
    hd.parent = head
    add_fuzz(hd, FZ_FACE)
    # başta yün perçem
    bm = bmesh.new()
    for k in range(4):
        blob(bm, (0.02 + r.uniform(-0.02, 0.02), r.uniform(-0.025, 0.025), 0.06 + r.uniform(0, 0.012)), (0.03, 0.03, 0.024), subdiv=2, seed=i * 9 + k)
    tf = remeshed('koyun_%d_percem' % i, bm, 0.006, 4, 0.6)
    setmat(tf, M_WOOL)
    tf.parent = head
    add_fuzz(tf, FZ_WOOL)
    for sgn in (1, -1):
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.055, 0.024, 0.012), subdiv=3, seed=i + 520 + sgn)
        ear = bm_to_obj('koyun_%d_kulak' % i, bm)
        setmat(ear, M_FACE)
        ear.parent = head
        ear.location = (-0.005, sgn * 0.078, 0.03)
        ear.rotation_euler = (sgn * 0.35, 0.25, sgn * 1.25)
        bm = bmesh.new()
        blob(bm, (0.006, 0, 0.007), (0.036, 0.013, 0.006), subdiv=2, seed=i + 530 + sgn)
        ei = bm_to_obj('koyun_%d_kulak_ic' % i, bm)
        setmat(ei, M_EAR_IN)
        ei.parent = ear
        # boncuk göz
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.0145, 0.0145, 0.0145), subdiv=3)
        eye = bm_to_obj('koyun_%d_goz' % i, bm)
        setmat(eye, M_BEAD)
        eye.parent = head
        eye.location = (0.102, sgn * 0.041, 0.024)
    # bacaklar: koyu keçe
    legs = []
    for k, (lx, ly) in enumerate(((0.12, 0.072), (0.12, -0.072), (-0.12, 0.072), (-0.12, -0.072))):
        bm = bmesh.new()
        blob(bm, (0, 0, -0.078), (0.027, 0.027, 0.092), subdiv=3, amp=0.03, seed=i * 10 + k)
        blob(bm, (0.006, 0, -0.156), (0.031, 0.029, 0.017), subdiv=2, seed=i * 10 + k + 5)
        leg = bm_to_obj('koyun_%d_bacak_%d' % (i, k), bm)
        add_subsurf(leg, 1, 0)
        setmat(leg, M_FACE)
        leg.parent = bob
        leg.location = (lx, ly, 0.168)
        legs.append(leg)
    return root, bob, head, legs


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


for i, (root, bob, head, legs) in enumerate(sheep):
    prev_yaw = None
    prev_s = sheep_s(i, -3)
    for f in range(-2, N_FRAMES + 3):
        g = fe(f)
        s = sheep_s(i, g)
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
        moving = min(1.0, max(0.0, (sheep_s(i, g) - sheep_s(i, g - 2)) / (2 * SPEED)))
        phase = s / 0.2 * 2 * math.pi + i
        root.location = (pos.x, pos.y, hfun(pos.x, pos.y))
        root.rotation_euler = (0, 0, yaw)
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        # el ile oynatılmış kukla: küçük zıplama + yalpalama
        bob.location = (0, 0, 0.016 * abs(math.sin(phase)) * moving)
        bob.rotation_euler = (0.045 * math.sin(phase) * moving, 0.03 * math.cos(phase) * moving, 0)
        bob.keyframe_insert('location', frame=f)
        bob.keyframe_insert('rotation_euler', frame=f)
        head.rotation_euler = (0.05 * math.sin(g * 0.07 + i), math.radians(20) + 0.07 * math.sin(phase) * moving
                               + 0.06 * math.sin(g * 0.05 + i * 2) * (1 - moving), 0.14 * math.sin(g * 0.03 + i) * (1 - moving))
        head.keyframe_insert('rotation_euler', frame=f)
        for k, leg in enumerate(legs):
            off = 0 if k in (0, 3) else math.pi
            leg.rotation_euler = (0, 0.5 * math.sin(phase + off) * moving, 0)
            leg.keyframe_insert('rotation_euler', frame=f)
print('t anim %.1f' % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- ışık: yumuşak, sıcak akşam
world = bpy.data.worlds.new('dunya')
scene.world = world
WN, WL = world.node_tree.nodes, world.node_tree.links
bg = WN['Background']
wtc = WN.new('ShaderNodeTexCoord')
sep = WN.new('ShaderNodeSeparateXYZ')
WL.new(wtc.outputs['Generated'], sep.inputs[0])
ramp = WN.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (1.0, 0.68, 0.42, 1)
ramp.color_ramp.elements[1].position = 0.35
ramp.color_ramp.elements[1].color = (0.95, 0.86, 0.70, 1)
WL.new(sep.outputs['Z'], ramp.inputs['Fac'])
WL.new(ramp.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.38


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


sun_dir = Vector((0.55, -0.80, -0.30)).normalized()
light('gunes', 'SUN', 4.6, (1.0, 0.68, 0.40), direction=sun_dir, size=math.radians(9.0))
light('dolgu', 'AREA', 60.0, (1.0, 0.90, 0.78), loc=(3.5, -4.5, 3.2),
      direction=(Vector((-0.4, 0.4, 0.3)) - Vector((3.5, -4.5, 3.2))), size=4.5)
light('arka_dolgu', 'AREA', 30.0, (1.0, 0.8, 0.6), loc=(-3.0, 4.0, 2.5),
      direction=(Vector((0, 1, 0.3)) - Vector((-3.0, 4.0, 2.5))), size=3.0)

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
ROW3 = Vector((ROW_CENTER.x, ROW_CENTER.y, slab_z(ROW_CENTER)))
GATE3 = Vector((GATE.x, GATE.y, hfun(GATE.x, GATE.y) + 0.25))
TGT0 = GATE3.lerp(ROW3, 0.45) + Vector((0, 0, 0.08)) + RIGHT3 * 0.3 + FWD0.to_3d() * 0.35
TGT1 = TGT0 + Vector((-0.05, -0.05, 0.0))
CAM1 = CAM_POS0 + (TGT0 - CAM_POS0).normalized() * 0.3
CAM_END = P_END + (TO_CAM3 * 0.86 + RIGHT3 * 0.22 + Vector((0, 0, 0.52))).normalized() * 0.98
FOCUS0 = Vector((HANG.x, HANG.y, HANG.z - 0.25)).lerp(ROW3, 0.3)
PUSH0, PUSH1 = 212, 296
for f in range(-2, N_FRAMES + 3):
    g = fe(f)
    t0 = max(0.0, min(1.0, (g - 1) / (PUSH0 - 1)))
    cpos = CAM_POS0.lerp(CAM1, t0)
    tpos = TGT0.lerp(TGT1, t0)
    e = smoother((g - PUSH0) / (PUSH1 - PUSH0))
    cpos = cpos.lerp(CAM_END, e)
    tpos = tpos.lerp(P_END + Vector((0, 0, -0.05)), e)
    cam.location = cpos
    cam.keyframe_insert('location', frame=f)
    target.location = tpos
    target.keyframe_insert('location', frame=f)
    focus = FOCUS0.lerp(P_END, smoother((g - PUSH0 + 10) / (PUSH1 - PUSH0 - 10)))
    cam_data.dof.focus_distance = (cpos - focus).length
    cam_data.dof.keyframe_insert('focus_distance', frame=f)
    cam_data.dof.aperture_fstop = 1.3 + 0.9 * e
    cam_data.dof.keyframe_insert('aperture_fstop', frame=f)

# ---------------------------------------------------------------- son çakılın parıltısı: küçük, sıcak, yumuşak dört kollu yıldız
cam_dir_end = (CAM_END - P_END).normalized()
glint = light('parilti', 'POINT', 0.0, (1.0, 0.8, 0.5), loc=P_END + cam_dir_end * 0.35 + Vector((0, 0, 0.2)), size=0.02)
glint.visible_camera = False
for f, en in ((1, 0.0), (258, 0.0), (278, 0.3), (300, 0.25)):
    glint.data.energy = en
    glint.data.keyframe_insert('energy', frame=f)
b2 = bmesh.new()
bmesh.ops.create_icosphere(b2, subdivisions=2, radius=0.0045)
me = bpy.data.meshes.new('parilti_nokta'); b2.to_mesh(me); b2.free()
spark = link(bpy.data.objects.new('parilti_nokta', me))
M_SPARK = emissive('parilti_mat', (1.0, 0.86, 0.6), 0.0)
spark.data.materials.append(M_SPARK)
spark.parent = LAST
_top = (cam_dir_end * 0.35 + Vector((0, 0, 1))).normalized()
_M300 = pouch_matrix(N_FRAMES) @ Matrix.Translation(heap_local[0]) @ local_rot[0].to_matrix().to_4x4()
_l3, _q3, _s3 = _M300.decompose()
spark.location = (Matrix.Translation(_l3) @ _q3.to_matrix().to_4x4()).inverted() @ (P_END + _top * 0.033)
for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission'):
    setattr(spark, attr, False)
# parıltı yanana kadar nokta görünmez (ışımasız hâlde çakılın üstünde kara nokta gibi duruyordu)
for f, sc in ((1, 0.0), (261, 0.0), (262, 1.0)):
    spark.scale = (sc, sc, sc)
    spark.keyframe_insert('scale', frame=f)
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
C.glossy_bounces = 1
C.transmission_bounces = 2
C.transparent_max_bounces = 4
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.seed = 7
C.sample_clamp_indirect = 6.0
try:
    scene.cycles_curves.shape = 'RIBBONS'
except Exception as ex:
    print('kıvrım biçimi', ex)
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = False          # stop-motion: hareket bulanıklığı yok
R.use_persistent_data = True
vs = scene.view_settings
vs.view_transform = 'AgX'
vs.look = 'AgX - Medium High Contrast'
vs.exposure = -0.2

ng = bpy.data.node_groups.new('kompozit', 'CompositorNodeTree')
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
scene.compositing_node_group = ng
rl = ng.nodes.new('CompositorNodeRLayers')
out = ng.nodes.new('NodeGroupOutput')
gl = ng.nodes.new('CompositorNodeGlare')
for nm, val in (('Type', 'Streaks'), ('Quality', 'High'), ('Threshold', 30.0), ('Strength', 0.34), ('Streaks', 4),
                ('Streaks Angle', 0.0), ('Fade', 0.74), ('Size', 0.3), ('Saturation', 0.9), ('Tint', (1.0, 0.8, 0.55, 1.0))):
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
_dg2 = bpy.context.evaluated_depsgraph_get()
_nc = _np = 0
for _in in _dg2.object_instances:
    if _in.object.type == 'CURVES':
        _nc += 1
        _np += len(_in.object.data.points)
print('LIF nesne %d nokta %d' % (_nc, _np), flush=True)
print('sahne kuruldu: %.1f sn' % (time.time() - T_START), flush=True)
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(A.cikti), 'kece.blend'))

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
    # ikişerli: tek kareler üretilir, çift kare bir öncekinin aynısıdır (poz iki kare durur)
    prev = None
    for f in range(A.bas, A.son + 1):
        fn = os.path.join(outdir, 'k_%04d.png' % f)
        if fe(f) != f and prev is not None:
            shutil.copyfile(prev, fn)
            continue
        scene.frame_set(f)
        R.filepath = fn
        bpy.ops.render.render(write_still=True)
        prev = fn
print('BITTI toplam %.1f sn' % (time.time() - T_START))
