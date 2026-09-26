# Math with Zirek · sahne G, GERÇEKÇİ sürüm (akşam, koyunlar girer, taş çıkar, tek taş kalır)
# Blender 5.2 LTS, Cycles. Gerçek ölçek (metre). Dış varlıklar: Poly Haven CC0 (KAYNAKLAR.txt, indir.py).
# Hikâye, zamanlama ve kamera vuruşları kil sürümüyle (../sahne.py) aynı.
# Kullanım:
#   blender -b -P sahne.py -- --mod kare --kareler 60,150,290 --w 640 --h 360 --ornek 16 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 15 --cikti out            (1920x1080, son kalite)
#   --doku 1k|2k|4k  --hdri 2k|4k  --cihaz auto|cpu  --tuy 0|1  --cim 0..1  --blend
import bpy, bmesh, math, random, sys, os, time, argparse
from mathutils import Vector, Matrix, Quaternion, Euler, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--mod', default='kare')            # kare | parca
ap.add_argument('--kareler', default='60,150,290')
ap.add_argument('--bas', type=int, default=1)
ap.add_argument('--son', type=int, default=300)
ap.add_argument('--w', type=int, default=1920)
ap.add_argument('--h', type=int, default=1080)
ap.add_argument('--ornek', type=int, default=128)
ap.add_argument('--cikti', default='out')
ap.add_argument('--doku', default='2k')
ap.add_argument('--hdri', default='2k')
ap.add_argument('--cihaz', default='auto')
ap.add_argument('--tuy', type=int, default=1)        # yünde ince tüy (eğri)
ap.add_argument('--cim', type=float, default=1.0)    # 3B ot yoğunluğu çarpanı
ap.add_argument('--bulanik', type=int, default=1)    # hareket bulanıklığı
ap.add_argument('--blend', action='store_true')
ap.add_argument('--yakin', default='')              # hata ayıklama: 'koyun' = tek koyuna yakın kamera
A = ap.parse_args(argv)
T_START = time.time()


def _script_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.dirname(os.path.abspath(sys.argv[sys.argv.index('-P') + 1]))


KOK = _script_dir()
VAR = os.path.join(KOK, 'assets')

FPS = 30
N_FRAMES = 300
N_SHEEP = 8
T_GATE0 = 40          # ilk koyunun kapıdan geçtiği kare
T_GAP = 22            # koyunlar arası (0,73 sn)
SPEED = 2.1 / FPS     # m/kare (sürü kapıdan tırıs geçer)

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


def link(ob, coll=None):
    (coll or scene.collection).objects.link(ob)
    return ob


def bm_to_obj(name, bm, smooth_shade=True):
    if smooth_shade:
        for f in bm.faces:
            f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


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
        v.co = R @ Vector((n.x * radii[0], n.y * radii[1], n.z * radii[2])) * d + Vector(center)
    me = bpy.data.meshes.new('tmp')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def setmat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


# ---------------------------------------------------------------- yerleşim (metre)
PEN_C = Vector((0.0, 6.0))
PEN_R = 4.0                   # duvar ekseni yarıçapı
GATE_ANG = math.radians(228)
GAP_HALF = 0.20               # açıklık yarı açısı (~1,3 m kapı + direkler)
WALL_H = 0.95
POST_R = 0.39
POST_H = 1.22


def ang_dist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def ring_pos(a, r=PEN_R):
    return Vector((PEN_C.x + r * math.cos(a), PEN_C.y + r * math.sin(a)))


def hfun(x, y):
    d = (Vector((x, y)) - PEN_C).length
    flat = smooth(5.0, 11.0, d)
    h = 2.2 * smooth(12.0, 45.0, y) + 0.6 * smooth(-4.0, -30.0, y) * 0   # arkada yumuşak yükselen tepe
    h += flat * (0.25 * math.sin(0.21 * x + 0.3) * math.cos(0.17 * y + 0.8) + 0.08 * math.sin(0.5 * x - 0.3 * y))
    h += 0.03 * noise.noise(Vector((x * 0.35, y * 0.35, 3.1)))
    return h


# ---------------------------------------------------------------- dokular / malzemeler
def img(path, noncolor=False):
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    return im


def tex_path(tid, kind, res):
    ext = {'diff': 'jpg', 'rough': 'jpg', 'nor_gl': 'png', 'disp': 'png'}[kind]
    for r in (res, '2k', '1k', '4k'):
        p = os.path.join(VAR, 'doku', tid, '%s_%s_%s.%s' % (tid, kind, r, ext))
        if os.path.exists(p):
            return p
    raise FileNotFoundError(tid + ' ' + kind)


def pbr(name, tid, tile=2.0, coord='UV', hue=0.5, sat=1.0, val=1.0, tint=None, rough_add=0.0, rough_mul=1.0,
        nor=1.0, box_blend=0.25, bump_noise=0.0, extra=None):
    """Poly Haven PBR doku malzemesi. coord: 'UV' | 'BOX' (nesne koordinatı, kutu izdüşümü)."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1.0 / tile,) * 3
    L.new(tc.outputs['UV' if coord == 'UV' else 'Object'], mp.inputs['Vector'])

    def itex(kind, noncolor):
        t = N.new('ShaderNodeTexImage')
        t.image = img(tex_path(tid, kind, A.doku), noncolor)
        if coord == 'BOX':
            t.projection = 'BOX'
            t.projection_blend = box_blend
        L.new(mp.outputs['Vector'], t.inputs['Vector'])
        return t
    d = itex('diff', False)
    hs = N.new('ShaderNodeHueSaturation')
    hs.inputs['Hue'].default_value = hue
    hs.inputs['Saturation'].default_value = sat
    hs.inputs['Value'].default_value = val
    L.new(d.outputs['Color'], hs.inputs['Color'])
    col = hs.outputs['Color']
    if tint is not None:
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1.0
        L.new(col, mx.inputs['A']); mx.inputs['B'].default_value = (*tint, 1.0)
        col = mx.outputs['Result']
    L.new(col, bsdf.inputs['Base Color'])
    r = itex('rough', True)
    rm = N.new('ShaderNodeMath'); rm.operation = 'MULTIPLY_ADD'
    rm.inputs[1].default_value = rough_mul; rm.inputs[2].default_value = rough_add
    rm.use_clamp = True
    L.new(r.outputs['Color'], rm.inputs[0])
    L.new(rm.outputs[0], bsdf.inputs['Roughness'])
    n = itex('nor_gl', True)
    nm = N.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = nor
    L.new(n.outputs['Color'], nm.inputs['Color'])
    normal = nm.outputs['Normal']
    if bump_noise > 0:
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60.0
        nz.inputs['Detail'].default_value = 6.0
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump_noise
        bp.inputs['Distance'].default_value = 0.002
        L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(normal, bp.inputs['Normal'])
        normal = bp.outputs['Normal']
    L.new(normal, bsdf.inputs['Normal'])
    bsdf.inputs['Specular IOR Level'].default_value = 0.4
    if extra:
        extra(m, N, L, bsdf, tc)
    return m


def simple(name, color, rough=0.6, sss=0.0, sheen=0.0, spec=0.4):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = spec
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
    if sheen:
        b.inputs['Sheen Weight'].default_value = sheen
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


# duvar: serin gri kuru taş (çakıldan ayrışsın diye doygunluk düşük)
M_WALL = pbr('duvar', 'stacked_stone_wall', tile=1.6, sat=0.38, val=0.95, tint=(0.93, 0.95, 1.0), nor=1.5)
# çakıl: sıcak aşı/okra, mat (inci gibi parlamasın)
def _pebble_extra(m, N, L, bsdf, tc):
    # taş başına renk farkı + ince benekler (kum taşı): düz, cilasız, mat
    oi = N.new('ShaderNodeObjectInfo')
    sp = N.new('ShaderNodeTexNoise'); sp.inputs['Scale'].default_value = 420.0; sp.inputs['Detail'].default_value = 2.0
    L.new(tc.outputs['Object'], sp.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].position = 0.62; rp.color_ramp.elements[0].color = (1, 1, 1, 1)
    rp.color_ramp.elements[1].position = 0.70; rp.color_ramp.elements[1].color = (0.55, 0.5, 0.45, 1)
    L.new(sp.outputs['Fac'], rp.inputs['Fac'])
    src = bsdf.inputs['Base Color'].links[0].from_socket
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
    L.new(src, mx.inputs['A']); L.new(rp.outputs['Color'], mx.inputs['B'])
    hs = N.new('ShaderNodeHueSaturation')
    hr = N.new('ShaderNodeMath'); hr.operation = 'MULTIPLY_ADD'; hr.inputs[1].default_value = 0.04; hr.inputs[2].default_value = 0.48
    L.new(oi.outputs['Random'], hr.inputs[0]); L.new(hr.outputs[0], hs.inputs['Hue'])
    vr = N.new('ShaderNodeMath'); vr.operation = 'MULTIPLY_ADD'; vr.inputs[1].default_value = 0.3; vr.inputs[2].default_value = 0.85
    L.new(oi.outputs['Random'], vr.inputs[0]); L.new(vr.outputs[0], hs.inputs['Value'])
    L.new(mx.outputs['Result'], hs.inputs['Color'])
    L.new(hs.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Specular IOR Level'].default_value = 0.3


M_PEBBLE = pbr('cakil', 'rock_surface', tile=0.14, coord='BOX', sat=1.3, val=1.25, tint=(1.0, 0.70, 0.40),
               rough_add=0.45, rough_mul=0.6, nor=1.3, extra=_pebble_extra)
M_LAST = M_PEBBLE.copy(); M_LAST.name = 'son_cakil'
M_SLAB = pbr('yassi_tas', 'rock_surface', tile=0.6, coord='BOX', sat=0.2, val=0.85, tint=(0.95, 0.97, 1.0), rough_add=0.2, nor=1.2)
M_CLOTH = pbr('cuval', 'hessian_230', tile=0.09, sat=0.45, val=0.55, tint=(0.92, 0.9, 0.86), rough_add=0.15, nor=1.8)
M_WOOD = pbr('tahta', 'rough_wood', tile=0.25, coord='BOX', sat=1.1, val=0.55, tint=(0.85, 0.7, 0.55), rough_add=0.1, nor=1.4)
M_CORD = pbr('ip', 'hessian_230', tile=0.03, sat=0.5, val=0.6, rough_add=0.2, nor=1.5)
M_PUPIL = simple('goz', (0.012, 0.009, 0.007), rough=0.12, spec=0.6)
M_HOOF = simple('tirnak', (0.035, 0.03, 0.028), rough=0.45)


def mat_face():
    """Suffolk koyunun kara yüzü: kısa kıl, mat, hafif kadife."""
    m = bpy.data.materials.new('kara_yuz')
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.016, 0.013, 0.011, 1)
    b.inputs['Roughness'].default_value = 0.62
    b.inputs['Sheen Weight'].default_value = 0.35
    b.inputs['Sheen Roughness'].default_value = 0.4
    b.inputs['Sheen Tint'].default_value = (0.35, 0.28, 0.22, 1)
    tc = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900.0; nz.inputs['Detail'].default_value = 2.0
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.25; bp.inputs['Distance'].default_value = 0.0015
    L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_wool():
    m = bpy.data.materials.new('yun')
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    geo = N.new('ShaderNodeNewGeometry')
    oi = N.new('ShaderNodeObjectInfo')
    # renk: krem, alt ve kıvrım içleri kirli bej-gri, üst güneşte ağarmış
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    low = N.new('ShaderNodeMapRange'); low.inputs['From Min'].default_value = 0.45; low.inputs['From Max'].default_value = 0.85
    L.new(sep.outputs['Z'], low.inputs['Value'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.30, 0.25, 0.19, 1)
    ramp.color_ramp.elements[1].color = (0.80, 0.72, 0.58, 1)
    L.new(low.outputs['Result'], ramp.inputs['Fac'])
    cav = N.new('ShaderNodeMapRange'); cav.inputs['From Min'].default_value = 0.42; cav.inputs['From Max'].default_value = 0.56
    L.new(geo.outputs['Pointiness'], cav.inputs['Value'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
    L.new(ramp.outputs['Color'], mx.inputs['A'])
    cr = N.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0.55, 0.5, 0.44, 1)
    cr.color_ramp.elements[1].color = (1, 1, 1, 1)
    L.new(cav.outputs['Result'], cr.inputs['Fac'])
    mx.inputs['Factor'].default_value = 1.0
    L.new(cr.outputs['Color'], mx.inputs['B'])
    blot = N.new('ShaderNodeTexNoise'); blot.inputs['Scale'].default_value = 3.0
    L.new(tc.outputs['Object'], blot.inputs['Vector'])
    hs = N.new('ShaderNodeHueSaturation')
    L.new(mx.outputs['Result'], hs.inputs['Color'])
    vr = N.new('ShaderNodeMath'); vr.operation = 'MULTIPLY_ADD'
    vr.inputs[1].default_value = 0.14; vr.inputs[2].default_value = 0.93
    L.new(oi.outputs['Random'], vr.inputs[0])
    L.new(vr.outputs[0], hs.inputs['Value'])
    L.new(hs.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.92
    b.inputs['Specular IOR Level'].default_value = 0.25
    b.inputs['Subsurface Weight'].default_value = 0.25
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.7, 0.45)
    b.inputs['Subsurface Scale'].default_value = 0.015
    b.inputs['Sheen Weight'].default_value = 0.8
    b.inputs['Sheen Roughness'].default_value = 0.5
    b.inputs['Sheen Tint'].default_value = (1.0, 0.92, 0.8, 1)
    # lif dokusu: ince kıvırcık kabartma
    fib = N.new('ShaderNodeTexNoise'); fib.inputs['Scale'].default_value = 260.0; fib.inputs['Detail'].default_value = 8.0
    fib.inputs['Distortion'].default_value = 2.5
    L.new(tc.outputs['Object'], fib.inputs['Vector'])
    vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 55.0
    vo.feature = 'SMOOTH_F1'
    L.new(tc.outputs['Object'], vo.inputs['Vector'])
    add = N.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 0.6
    L.new(vo.outputs['Distance'], add.inputs[0]); L.new(fib.outputs['Fac'], add.inputs[2])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.55; bp.inputs['Distance'].default_value = 0.006
    bp.invert = True
    L.new(add.outputs[0], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_wool_hair():
    m = bpy.data.materials.new('yun_tuy')
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.78, 0.70, 0.56, 1)
    b.inputs['Roughness'].default_value = 0.75
    b.inputs['Subsurface Weight'].default_value = 0.0
    b.inputs['Transmission Weight'].default_value = 0.25
    b.inputs['Sheen Weight'].default_value = 0.5
    return m


M_FACE = mat_face()
M_WOOL = mat_wool()
M_HAIR = mat_wool_hair()


# ---------------------------------------------------------------- dünya (HDRI + güneş)
HDRI_SUN_AZ = math.radians(-35.9)     # hilly_terrain_01: güneşin HDRI içindeki yönü (ölçüldü: el 11,3°)
SUN_AZ = math.radians(193.0)          # sahnede güneşin geldiği yön (soldan, hafif arkadan: yan ışık)
SUN_EL = math.radians(10.5)
HDRI_ROT = HDRI_SUN_AZ - SUN_AZ


def hdri_path():
    for r in (A.hdri, '2k', '4k'):
        p = os.path.join(VAR, 'hdri', 'hilly_terrain_01_%s.hdr' % r)
        if os.path.exists(p):
            return p
    raise FileNotFoundError('hdri')


HDRI_IMG = img(hdri_path())
HDRI_STRENGTH = 0.45
HDRI_CLAMP = 40.0      # HDRI'deki güneş kırpılır; güneşi güneş lambası verir (gürültüsüz, keskin gölge)


def env_nodes(nt, vec_socket):
    """nt içinde: yön vektörü -> döndürülmüş, kırpılmış, ısıtılmış HDRI rengi."""
    N, L = nt.nodes, nt.links
    mp = N.new('ShaderNodeMapping'); mp.vector_type = 'VECTOR'
    mp.inputs['Rotation'].default_value = (0, 0, HDRI_ROT)
    L.new(vec_socket, mp.inputs['Vector'])
    et = N.new('ShaderNodeTexEnvironment'); et.image = HDRI_IMG
    L.new(mp.outputs['Vector'], et.inputs['Vector'])
    cl = N.new('ShaderNodeMix'); cl.data_type = 'RGBA'; cl.blend_type = 'DARKEN'; cl.inputs['Factor'].default_value = 1.0
    L.new(et.outputs['Color'], cl.inputs['A']); cl.inputs['B'].default_value = (HDRI_CLAMP,) * 3 + (1,)
    warm = N.new('ShaderNodeMix'); warm.data_type = 'RGBA'; warm.blend_type = 'MULTIPLY'; warm.inputs['Factor'].default_value = 1.0
    L.new(cl.outputs['Result'], warm.inputs['A']); warm.inputs['B'].default_value = (1.0, 0.9, 0.78, 1)
    return warm.outputs['Result']


world = bpy.data.worlds.new('dunya')
scene.world = world
WN, WL = world.node_tree.nodes, world.node_tree.links
wtc = WN.new('ShaderNodeTexCoord')
wcol = env_nodes(world.node_tree, wtc.outputs['Generated'])
# kameranın gördüğü gökyüzü akşam rengine çekilir (aydınlatma HDRI'nin kendisiyle kalır)
_lp = WN.new('ShaderNodeLightPath')
_sk = WN.new('ShaderNodeMix'); _sk.data_type = 'RGBA'; _sk.blend_type = 'MULTIPLY'; _sk.inputs['Factor'].default_value = 1.0
WL.new(wcol, _sk.inputs['A']); _sk.inputs['B'].default_value = (1.0, 0.80, 0.58, 1)
_sel = WN.new('ShaderNodeMix'); _sel.data_type = 'RGBA'
WL.new(_lp.outputs['Is Camera Ray'], _sel.inputs['Factor'])
WL.new(wcol, _sel.inputs['A']); WL.new(_sk.outputs['Result'], _sel.inputs['B'])
WL.new(_sel.outputs['Result'], WN['Background'].inputs['Color'])
WN['Background'].inputs['Strength'].default_value = HDRI_STRENGTH


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


SUN_VEC = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))
light('gunes', 'SUN', 8.0, (1.0, 0.70, 0.42), direction=-SUN_VEC, size=math.radians(1.2))


# ---------------------------------------------------------------- kamera başlangıcı (kapıya dışarıdan, hafif sağdan bakar)
gu = Vector((math.cos(GATE_ANG), math.sin(GATE_ANG)))
GATE_PT = PEN_C + gu * PEN_R
CAM_AZ = GATE_ANG + math.radians(40)
_cxy = GATE_PT + Vector((math.cos(CAM_AZ), math.sin(CAM_AZ))) * 4.6
CAM_POS0 = Vector((_cxy.x, _cxy.y, hfun(_cxy.x, _cxy.y) + 1.75))


# ---------------------------------------------------------------- zemin


def build_ground():
    bm = bmesh.new()
    # yakın bölge sık, uzak bölge seyrek: kutupsal ızgara (kamera çevresinde)
    rings = []
    radii = []
    r = 0.0
    while r < 260.0:
        radii.append(r)
        r += 0.12 if r < 14 else (0.45 if r < 40 else 3.0 + r * 0.05)
    seg = 360
    cx, cy = -1.0, 2.0
    centre = bm.verts.new((cx, cy, hfun(cx, cy)))
    for rr in radii[1:]:
        ring = []
        for s in range(seg):
            a = 2 * math.pi * s / seg
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            ring.append(bm.verts.new((x, y, hfun(x, y))))
        rings.append(ring)
    for s in range(seg):
        bm.faces.new((centre, rings[0][s], rings[0][(s + 1) % seg]))
    for k in range(len(rings) - 1):
        for s in range(seg):
            bm.faces.new((rings[k][s], rings[k + 1][s], rings[k + 1][(s + 1) % seg], rings[k][(s + 1) % seg]))
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x, lp.vert.co.y)
    ob = bm_to_obj('zemin', bm)
    return ob


def ground_material():
    def extra(m, N, L, bsdf, tc):
        # uzakta zemin, HDRI'nin kendi zeminine karışır (yalnız kamera ışınları): ufukta dikiş olmaz
        out = N['Material Output']
        cam = N.new('ShaderNodeCameraData')
        rng_ = N.new('ShaderNodeMapRange'); rng_.inputs['From Min'].default_value = 22.0; rng_.inputs['From Max'].default_value = 70.0
        L.new(cam.outputs['View Distance'], rng_.inputs['Value'])
        lp = N.new('ShaderNodeLightPath')
        mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
        L.new(rng_.outputs['Result'], mul.inputs[0]); L.new(lp.outputs['Is Camera Ray'], mul.inputs[1])
        geo = N.new('ShaderNodeNewGeometry')
        neg = N.new('ShaderNodeVectorMath'); neg.operation = 'SCALE'; neg.inputs['Scale'].default_value = -1.0
        L.new(geo.outputs['Incoming'], neg.inputs[0])
        ecol = env_nodes(m.node_tree, neg.outputs['Vector'])
        em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = HDRI_STRENGTH
        L.new(ecol, em.inputs['Color'])
        mix = N.new('ShaderNodeMixShader')
        L.new(mul.outputs[0], mix.inputs['Fac'])
        L.new(bsdf.outputs['BSDF'], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
        L.new(mix.outputs[0], out.inputs['Surface'])
        # büyük ölçekli renk dalgalanması (tekrar eden doku belli olmasın)
        big = N.new('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = 0.08; big.inputs['Detail'].default_value = 3
        L.new(tc.outputs['Object'], big.inputs['Vector'])
        hs2 = N.new('ShaderNodeHueSaturation')
        rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.8; rr.inputs['To Max'].default_value = 1.15
        L.new(big.outputs['Fac'], rr.inputs['Value'])
        L.new(rr.outputs['Result'], hs2.inputs['Value'])
        src = bsdf.inputs['Base Color'].links[0].from_socket
        L.new(src, hs2.inputs['Color'])
        L.new(hs2.outputs['Color'], bsdf.inputs['Base Color'])
    return pbr('cimen', 'leafy_grass', tile=1.6, sat=1.3, val=0.85, tint=(0.78, 1.0, 0.55), rough_add=0.1, extra=extra)


GROUND = build_ground()
print('t zemin %.1f' % (time.time() - T_START), flush=True)
setmat(GROUND, ground_material())


# ---------------------------------------------------------------- ağıl (kuru taş duvar)
def sweep_ring(name, a0, a1, prof, radius, center, step=0.02, tile=1.6, seed=0):
    """Profil (dr, z) çemberin yayı boyunca süpürülür; UV = (yay uzunluğu, profil uzunluğu)."""
    bm = bmesh.new()
    uv_l = bm.loops.layers.uv.new('UVMap')
    arc = abs(a1 - a0) * radius
    n = max(2, int(arc / step))
    # profil noktalarını ~step aralıklı yeniden örnekle
    pts = [prof[0]]
    plen = [0.0]
    for k in range(1, len(prof)):
        p0, p1 = Vector(prof[k - 1]), Vector(prof[k])
        m = max(1, int((p1 - p0).length / step))
        for j in range(1, m + 1):
            q = p0.lerp(p1, j / m)
            plen.append(plen[-1] + (q - Vector(pts[-1])).length)
            pts.append(tuple(q))
    grid = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        ca, sa = math.cos(a), math.sin(a)
        row = []
        for (dr, z) in pts:
            rr = radius + dr
            x, y = center.x + rr * ca, center.y + rr * sa
            row.append(bm.verts.new((x, y, hfun(x, y) + z)))
        grid.append(row)
    for i in range(n):
        for j in range(len(pts) - 1):
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                rr_u = max(radius + pts[jj][0], 0.05) if radius < 0.01 else radius
                lp[uv_l].uv = (ii * abs(a1 - a0) * rr_u / n / tile + seed * 0.37, plen[jj] / tile + seed * 0.19)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = bm_to_obj(name, bm)
    return ob


def displace_by_image(ob, tid, strength, tile, mid=0.5):
    t = bpy.data.textures.new(ob.name + '_disp', 'IMAGE')
    t.image = img(tex_path(tid, 'disp', A.doku), True)
    t.extension = 'REPEAT'
    md = ob.modifiers.new('disp', 'DISPLACE')
    md.texture = t
    md.texture_coords = 'UV'
    md.strength = strength
    md.mid_level = mid
    return md


WALL_PROF = [(0.34, -0.12), (0.33, 0.0), (0.27, WALL_H * 0.5), (0.22, WALL_H - 0.04), (0.14, WALL_H + 0.01),
             (0.0, WALL_H + 0.03), (-0.14, WALL_H + 0.01), (-0.22, WALL_H - 0.04), (-0.27, WALL_H * 0.5),
             (-0.33, 0.0), (-0.34, -0.12)]


def build_pen():
    a_start = GATE_ANG + GAP_HALF
    a_end = GATE_ANG - GAP_HALF + 2 * math.pi
    wall = sweep_ring('duvar', a_start, a_end, WALL_PROF, PEN_R, PEN_C, step=0.025)
    displace_by_image(wall, 'stacked_stone_wall', 0.045, 1.6)
    setmat(wall, M_WALL)
    posts = []
    for side, sgn in (('on', 1), ('arka', -1)):
        a = GATE_ANG + sgn * GAP_HALF
        p = ring_pos(a)
        prof = [(POST_R + 0.02, -0.12), (POST_R, 0.0), (POST_R - 0.03, POST_H - 0.05), (POST_R - 0.08, POST_H),
                (0.0, POST_H + 0.02)]
        post = sweep_ring('direk_' + side, 0.0, 2 * math.pi, prof, 0.0001, p, step=0.025, seed=3 + sgn)
        displace_by_image(post, 'stacked_stone_wall', 0.04, 1.6)
        setmat(post, M_WALL)
        posts.append((side, a, p))
    return posts


def load_models(blend, names):
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    return [o for o in dst.objects if o is not None]


def model_blend(mid):
    for r in ('1k', '2k'):
        p = os.path.join(VAR, 'model', mid, r, '%s_%s.blend' % (mid, r))
        if os.path.exists(p):
            return p
    raise FileNotFoundError(mid)


HIDE = bpy.data.collections.new('kaynaklar')
scene.collection.children.link(HIDE)


def coping(posts):
    """Duvar üstüne ve direk başlarına gerçek taş taramalı kapak taşları (rock_moss_set_01, CC0)."""
    rocks = load_models(model_blend('rock_moss_set_01'), ['rock_moss_set_01_rock0%d' % k for k in range(1, 7)])
    for o in rocks:
        HIDE.objects.link(o)
        o.location = (0, 0, -500)
    r = rng(31)
    a = GATE_ANG + GAP_HALF + 0.05
    a_end = GATE_ANG - GAP_HALF + 2 * math.pi - 0.05
    k = 0
    while a < a_end:
        src = rocks[r.randrange(len(rocks))]
        ob = link(bpy.data.objects.new('kapak_%03d' % k, src.data))
        L = r.uniform(0.26, 0.36)
        dims = src.dimensions
        s = L / max(dims.x, dims.y)
        ob.scale = (s, s * r.uniform(0.8, 1.0), s * r.uniform(0.45, 0.65))
        p = ring_pos(a, PEN_R + r.uniform(-0.03, 0.03))
        ob.location = (p.x, p.y, hfun(p.x, p.y) + WALL_H - 0.02)
        ob.rotation_euler = (r.uniform(-0.15, 0.15), r.uniform(-0.15, 0.15), a + math.pi / 2 + r.uniform(-0.5, 0.5))
        a += (L * 0.82) / PEN_R
        k += 1
    for side, pa, p in posts:
        src = rocks[2 if side == 'on' else 4]
        ob = link(bpy.data.objects.new('direk_basi_' + side, src.data))
        s = (POST_R * 2.2) / max(src.dimensions.x, src.dimensions.y)
        ob.scale = (s, s, s * 0.35)
        ob.location = (p.x, p.y, hfun(p.x, p.y) + POST_H - 0.02)
        ob.rotation_euler = (0.04, -0.03, r.uniform(0, 6.28))
    # duvar dibine birkaç düşmüş taş
    for j in range(7):
        a = GATE_ANG + GAP_HALF + 0.3 + r.uniform(0, 3.0)
        side = 1 if r.random() < 0.6 else -1
        p = ring_pos(a, PEN_R + side * r.uniform(0.42, 0.6))
        src = rocks[r.randrange(len(rocks))]
        ob = link(bpy.data.objects.new('dusmus_%d' % j, src.data))
        s = r.uniform(0.14, 0.22) / max(src.dimensions.x, src.dimensions.y)
        ob.scale = (s, s, s * 0.7)
        ob.location = (p.x, p.y, hfun(p.x, p.y) + 0.02)
        ob.rotation_euler = (0, 0, r.uniform(0, 6.28))
    return rocks


posts = build_pen()
ROCKS = coping(posts)
print('t agil %.1f' % (time.time() - T_START), flush=True)
front_post = [p for p in posts if p[0] == 'on'][0]


# ---------------------------------------------------------------- otlar (Poly Haven çim modelleri, GN ile saçılır)
def build_grass():
    names = ['grass_medium_02_%s' % c for c in 'abcde']
    clumps = load_models(model_blend('grass_medium_02'), names)
    names2 = ['grass_bermuda_01_seedling_%s' % c for c in 'abcd'] + ['grass_bermuda_01_medium_%s' % c for c in 'abcdef']
    small = load_models(model_blend('grass_bermuda_01'), names2)
    cA = bpy.data.collections.new('ot_tutam'); HIDE.children.link(cA)
    cB = bpy.data.collections.new('ot_ince'); HIDE.children.link(cB)
    for o in clumps:
        cA.objects.link(o)
    for o in small:
        cB.objects.link(o)
    for o in clumps + small:
        o.location = (0, 0, -500)
    # saçma yüzeyi: kameranın gördüğü yakın bölge
    bm = bmesh.new()
    x0, x1, y0, y1 = -12.0, 9.0, -4.5, 15.0
    nx, ny = 105, 98
    vs = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            row.append(bm.verts.new((x, y, hfun(x, y) - 0.01)))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    me = bpy.data.meshes.new('ot_yuzey')
    bm.to_mesh(me); bm.free()
    sa = me.attributes.new('yogA', 'FLOAT', 'POINT')
    sb = me.attributes.new('yogB', 'FLOAT', 'POINT')
    # kameradan görünen alan dışında seyrek; duvar içi/dibi, çakıl dizisi, kese altı temiz
    for k, v in enumerate(me.vertices):
        p = v.co.xy
        dpen = (p - PEN_C).length
        dist_cam = (p - CAM_POS0.xy).length
        wA = 1.0
        wB = 1.0
        if abs(dpen - PEN_R) < 0.42:          # duvarın altı
            wA = wB = 0.0
        elif abs(dpen - PEN_R) < 0.9:         # duvar dibi: tutamlar sık
            wA = 2.2
        if dpen < PEN_R - 0.4:                # ağılın içi: otlanmış, kısa
            wA *= 0.25
        if (p - ROW_CENTER).length < 0.8:     # yassı taş ve çakıl dizisi açık kalsın
            wA = 0.0; wB = 0.0
        if (p - GATE_PT).length < 1.2 or path_near(p) < 0.5:   # sürünün çiğnediği yol
            wA *= 0.1; wB *= 0.5
        if dist_cam < 1.2:
            wA = wB = 0.0
        if dist_cam > 16:
            wA *= 0.3; wB *= 0.3
        sa.data[k].value = wA
        sb.data[k].value = wB
    ob = link(bpy.data.objects.new('ot_sac', me))
    ng = bpy.data.node_groups.new('ot_sac', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    join = N.new('GeometryNodeJoinGeometry')

    def scatter(attr, coll, dens, smin, smax, seed):
        dp = N.new('GeometryNodeDistributePointsOnFaces')
        dp.inputs['Density'].default_value = dens * A.cim
        dp.inputs['Seed'].default_value = seed
        na = N.new('GeometryNodeInputNamedAttribute'); na.data_type = 'FLOAT'; na.inputs['Name'].default_value = attr
        mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = dens * A.cim
        L.new(na.outputs['Attribute'], mm.inputs[0])
        L.new(gi.outputs[0], dp.inputs['Mesh'])
        L.new(mm.outputs[0], dp.inputs['Density'])
        ci = N.new('GeometryNodeCollectionInfo')
        ci.inputs['Collection'].default_value = coll
        ci.inputs['Separate Children'].default_value = True
        ci.inputs['Reset Children'].default_value = True
        ip = N.new('GeometryNodeInstanceOnPoints')
        ip.inputs['Pick Instance'].default_value = True
        L.new(dp.outputs['Points'], ip.inputs['Points'])
        L.new(ci.outputs['Instances'], ip.inputs['Instance'])
        ri = N.new('FunctionNodeRandomValue'); ri.data_type = 'INT'
        ri.inputs['Min'].default_value = 0; ri.inputs['Max'].default_value = 20
        ri.inputs['Seed'].default_value = seed + 1
        L.new(ri.outputs['Value'], ip.inputs['Instance Index'])
        rr = N.new('FunctionNodeRandomValue'); rr.data_type = 'FLOAT_VECTOR'
        rr.inputs['Min'].default_value = (-0.12, -0.12, 0.0); rr.inputs['Max'].default_value = (0.12, 0.12, 6.283)
        rr.inputs['Seed'].default_value = seed + 2
        e2r = N.new('FunctionNodeEulerToRotation')
        L.new(rr.outputs['Value'], e2r.inputs[0])
        L.new(e2r.outputs[0], ip.inputs['Rotation'])
        rs = N.new('FunctionNodeRandomValue'); rs.data_type = 'FLOAT'
        rs.inputs['Min'].default_value = smin; rs.inputs['Max'].default_value = smax
        rs.inputs['Seed'].default_value = seed + 3
        L.new(rs.outputs['Value'], ip.inputs['Scale'])
        L.new(ip.outputs['Instances'], join.inputs['Geometry'])
    scatter('yogA', cA, 7.0, 0.55, 1.05, 11)
    scatter('yogB', cB, 220.0, 0.9, 1.6, 21)
    L.new(join.outputs[0], go.inputs[0])
    md = ob.modifiers.new('ot', 'NODES')
    md.node_group = ng
    return ob


# ---------------------------------------------------------------- kese, çivi
POUCH_S = 1.4


def build_pouch(front_post):
    _, a, p = front_post
    to_cam = (CAM_POS0.xy - p).normalized()
    outward = Vector((math.cos(a), math.sin(a)))
    # çivi direğin kameraya bakan yüzünden, kapı tarafına hafif dönük çıkar
    pegdir2 = (to_cam * 0.85 + outward * 0.15).normalized()
    pegdir = Vector((pegdir2.x, pegdir2.y, 0.22)).normalized()
    z_peg = hfun(p.x, p.y) + 1.02
    peg_base = Vector((p.x, p.y, z_peg)) + Vector((pegdir2.x, pegdir2.y, 0)) * (POST_R - 0.12)
    peg_len = 0.26
    # çivi: dolu, uçları yontulmuş tahta kazık (içi boş boru gibi görünmesin: kapaklı, yuvarlatılmış uç)
    bm = bmesh.new()
    q = Vector((0, 0, 1)).rotation_difference(pegdir)
    M = Matrix.Translation(peg_base + pegdir * (peg_len / 2)) @ q.to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=14, radius1=0.021, radius2=0.017,
                          depth=peg_len, matrix=M)
    # uç: kubbe
    tip = peg_base + pegdir * peg_len
    blob(bm, tip[:], (0.017, 0.017, 0.012), subdiv=2, amp=0.1, nscale=3.0, seed=5, rot=q)
    ob = bm_to_obj('civi', bm)
    bev = ob.modifiers.new('bev', 'BEVEL'); bev.width = 0.004; bev.segments = 2
    setmat(ob, M_WOOD)
    hang = peg_base + pegdir * (peg_len - 0.04) + Vector((0, 0, 0.02))
    prof0 = [(0.0, 0.0), (0.05, 0.003), (0.085, 0.014), (0.108, 0.034), (0.12, 0.06), (0.123, 0.088), (0.118, 0.115),
             (0.104, 0.14), (0.083, 0.16), (0.062, 0.174), (0.05, 0.183), (0.052, 0.19), (0.06, 0.199), (0.07, 0.208),
             (0.078, 0.216), (0.083, 0.224), (0.086, 0.231)]
    # profili sık örnekle (kumaş kıvrımları için)
    prof = [prof0[0]]
    for k in range(1, len(prof0)):
        p0, p1 = Vector(prof0[k - 1]), Vector(prof0[k])
        m = max(1, int((p1 - p0).length / 0.006))
        for j in range(1, m + 1):
            prof.append(tuple(p0.lerp(p1, j / m)))
    DROP = 0.29
    seg = 72
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    rings = []
    bottom = bm.verts.new((0, 0, -DROP))
    cr_r = rng(91)
    creases = [(cr_r.uniform(0, 6.283), cr_r.uniform(0.004, 0.008), cr_r.uniform(0.25, 0.45)) for _ in range(9)]
    for (rr, zz) in prof[1:]:
        ring = []
        for s in range(seg):
            th = 2 * math.pi * s / seg
            neck = smooth(0.15, 0.176, zz) * (1 - smooth(0.186, 0.2, zz))
            frill = smooth(0.19, 0.231, zz)
            # boğazda büzgü pilileri
            pleat = neck * (0.0055 * math.sin(15 * th + 1.3 + 0.8 * noise.noise(Vector((th, 0.0, 1.0)))) +
                            0.004 * noise.noise(Vector((math.cos(th) * 4.0, math.sin(th) * 4.0, zz * 30))))
            # ağız: düzensiz kumaş kanatları
            flap = frill * (0.012 * noise.noise(Vector((math.cos(th) * 2.2, math.sin(th) * 2.2, 7.7))) +
                            0.008 * math.sin(7 * th + 0.5 + 1.5 * noise.noise(Vector((th, 1.0, 2.0)))) + 0.004 * frill)
            # gövde: boğazdan aşağı inen uzun kırışıklar
            body = 0.0
            for (ph, am, w) in creases:
                dth = (th - ph + math.pi) % (2 * math.pi) - math.pi
                body += am * math.exp(-(dth / (w * 0.35)) ** 2) * smooth(0.04, 0.16, zz) * (1 - smooth(0.16, 0.18, zz))
            wob = 0.010 * noise.noise(Vector((math.cos(th) * 2.0, math.sin(th) * 2.0, zz * 9)))
            r2 = rr + pleat + flap - body + wob * (rr / 0.1)
            if zz < 0.11:
                r2 += 0.012 * max(0.0, math.cos(th - 0.3)) * (1 - zz / 0.11)   # taşların ağırlığıyla öne sarkan karın
            dz = frill * (0.022 * noise.noise(Vector((math.cos(th) * 1.6, math.sin(th) * 1.6, 3.3))) + 0.006 * math.sin(7 * th + 0.5)
                          - 0.008 * frill)   # kumaş ağız: düzensiz, yer yer sarkan kanatlar
            ring.append(bm.verts.new((r2 * math.cos(th) * 1.05, r2 * math.sin(th) * 0.95, zz - DROP + dz)))
        rings.append(ring)
    for s in range(seg):
        f = bm.faces.new((bottom, rings[0][s], rings[0][(s + 1) % seg]))
    for k in range(len(rings) - 1):
        for s in range(seg):
            f = bm.faces.new((rings[k][s], rings[k + 1][s], rings[k + 1][(s + 1) % seg], rings[k][(s + 1) % seg]))
    zsum = [0.0]
    for k in range(1, len(prof)):
        zsum.append(zsum[-1] + (Vector(prof[k]) - Vector(prof[k - 1])).length)
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co
            th = math.atan2(co.y, co.x)
            lp[uvl].uv = ((th + math.pi) * 0.12, (co.z + DROP) * 1.2)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pouch = bm_to_obj('kese', bm)
    sol = pouch.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.0035
    ss = pouch.modifiers.new('ss', 'SUBSURF'); ss.levels = 0; ss.render_levels = 2
    setmat(pouch, M_CLOTH)
    pouch.location = hang
    pouch.rotation_mode = 'QUATERNION'
    tilt_axis = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    base_q = Quaternion(tilt_axis, math.radians(-22))
    pouch.rotation_quaternion = base_q
    pouch.scale = (POUCH_S,) * 3

    def curve(name, pts, cyclic=False, bevel=0.005):
        cu = bpy.data.curves.new(name, 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = bevel
        cu.bevel_resolution = 3
        cu.use_fill_caps = True
        sp = cu.splines.new('NURBS')
        sp.points.add(len(pts) - 1)
        for i, pt in enumerate(pts):
            sp.points[i].co = (pt[0], pt[1], pt[2], 1.0)
        sp.use_cyclic_u = cyclic
        sp.use_endpoint_u = not cyclic
        sp.order_u = 3
        o = link(bpy.data.objects.new(name, cu))
        o.data.materials.append(M_CORD)
        o.parent = pouch
        return o
    inv = base_q.inverted()
    side = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    sl = inv @ side
    zb = 0.182 - DROP
    back = inv @ Vector((-to_cam.x, -to_cam.y, 0)).normalized()
    curve('ip_aski', [(back * 0.052 + Vector((0, 0, zb)))[:], (back * 0.05 + Vector((0, 0, zb + 0.05)))[:],
                      (back * 0.02 + Vector((0, 0, -0.01)))[:], (0, 0, 0.0)], bevel=0.0045)
    fr = -back
    curve('ip_uc', [(fr * 0.056 + sl * 0.01 + Vector((0, 0, zb)))[:], (fr * 0.066 + sl * 0.02 + Vector((0, 0, zb - 0.03)))[:],
                    (fr * 0.07 + sl * 0.015 + Vector((0, 0, zb - 0.06)))[:]], bevel=0.0035)
    curve('ip_bogaz', [(0.056 * math.cos(2 * math.pi * s / 10) * 1.05, 0.056 * math.sin(2 * math.pi * s / 10) * 0.95,
                        zb + 0.004 * math.sin(3 * s)) for s in range(10)], cyclic=True, bevel=0.005)
    return pouch, base_q, hang, 0.228 - DROP


pouch, pouch_q0, HANG, LIP_Z = build_pouch(front_post)


def pebble_mesh(name, seed, mat):
    r = rng(seed)
    bm = bmesh.new()
    # dere çakılı: yassı, yuvarlak kenarlı, biraz asimetrik
    blob(bm, (0, 0, 0), (r.uniform(0.034, 0.038), r.uniform(0.027, 0.030), r.uniform(0.018, 0.021)),
         subdiv=4, amp=0.10, nscale=1.2, seed=seed)
    ob = bm_to_obj(name, bm)
    setmat(ob, mat)
    ob.rotation_mode = 'QUATERNION'
    return ob


# ---------------------------------------------------------------- koyun (Suffolk tarzı: krem yün, kara yüz ve bacak)
def fuzz_group():
    ng = bpy.data.node_groups.new('yun_tuy', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    dp = N.new('GeometryNodeDistributePointsOnFaces')
    dp.inputs['Density'].default_value = 9000.0
    L.new(gi.outputs[0], dp.inputs['Mesh'])
    line = N.new('GeometryNodeCurvePrimitiveLine')
    line.inputs['End'].default_value = (0, 0, 0.022)
    ip = N.new('GeometryNodeInstanceOnPoints')
    L.new(dp.outputs['Points'], ip.inputs['Points'])
    L.new(line.outputs['Curve'], ip.inputs['Instance'])
    rr = N.new('FunctionNodeRandomValue'); rr.data_type = 'FLOAT_VECTOR'
    rr.inputs['Min'].default_value = (-0.7, -0.7, 0.0); rr.inputs['Max'].default_value = (0.7, 0.7, 6.283)
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
    rs.inputs['Min'].default_value = 0.45; rs.inputs['Max'].default_value = 1.3
    L.new(rs.outputs['Value'], ip.inputs['Scale'])
    re = N.new('GeometryNodeRealizeInstances')
    L.new(ip.outputs['Instances'], re.inputs['Geometry'])
    cr = N.new('GeometryNodeSetCurveRadius'); cr.inputs['Radius'].default_value = 0.0007
    L.new(re.outputs['Geometry'], cr.inputs['Curve'])
    sm = N.new('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = M_HAIR
    L.new(cr.outputs['Curve'], sm.inputs['Geometry'])
    j = N.new('GeometryNodeJoinGeometry')
    L.new(sm.outputs[0], j.inputs['Geometry'])
    L.new(gi.outputs[0], j.inputs['Geometry'])
    L.new(j.outputs[0], go.inputs[0])
    return ng


FUZZ = fuzz_group() if A.tuy else None


def remeshed(name, bm, voxel, smooth_it=4):
    ob = bm_to_obj(name, bm)
    rm = ob.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = voxel
    sm = ob.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.6; sm.iterations = smooth_it
    bake_modifiers(ob)
    return ob


def wool_displace(ob, seed, amp_clump=0.028, amp_big=0.03):
    """Yün topakları: Voronoi hücreleri (kıvırcık öbekler) + geniş dalga. Normaller önce okunur (hızlı)."""
    me = ob.data
    n = len(me.vertices)
    co = [0.0] * (3 * n)
    nr = [0.0] * (3 * n)
    me.vertices.foreach_get('co', co)
    me.vertices.foreach_get('normal', nr)
    off = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    out = [0.0] * (3 * n)
    for k in range(n):
        p = Vector(co[3 * k:3 * k + 3])
        d1, _ = noise.voronoi(p * 16.0 + off, distance_metric='DISTANCE', exponent=2.5)
        d2, _ = noise.voronoi(p * 38.0 + off * 2, distance_metric='DISTANCE', exponent=2.5)
        big = noise.fractal(p * 3.5 + off, 0.6, 2.0, 3)
        clump = (0.55 - d1[0]) * amp_clump + (0.5 - d2[0]) * amp_clump * 0.35
        under = smooth(0.58, 0.42, p.z)
        dd = (clump + big * amp_big) * (1.0 - 0.6 * under)
        out[3 * k] = p.x + nr[3 * k] * dd
        out[3 * k + 1] = p.y + nr[3 * k + 1] * dd
        out[3 * k + 2] = p.z + nr[3 * k + 2] * dd
    me.vertices.foreach_set('co', out)
    me.update()
    for pl in me.polygons:
        pl.use_smooth = True


def build_sheep(i):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('koyun_%d' % i, None))
    bob = link(bpy.data.objects.new('koyun_%d_govde' % i, None))
    bob.parent = root
    s = r.uniform(0.9, 1.04)
    root.scale = (s, s, s)
    bm = bmesh.new()
    blob(bm, (0.0, 0, 0.68), (0.46, 0.27, 0.28), subdiv=4, seed=i)
    blob(bm, (-0.30, 0, 0.69), (0.25, 0.27, 0.29), subdiv=3, seed=i + 1)
    blob(bm, (0.30, 0, 0.69), (0.23, 0.25, 0.28), subdiv=3, seed=i + 2)
    blob(bm, (0.47, 0, 0.80), (0.14, 0.13, 0.16), subdiv=3, seed=i + 3)      # boyun
    for k in range(26):
        u = Vector((r.gauss(0, 1), r.gauss(0, 1), abs(r.gauss(0, 1)) * 0.8 + 0.1)).normalized()
        pos = Vector((u.x * 0.42, u.y * 0.24, u.z * 0.24 + 0.68))
        rad = r.uniform(0.08, 0.13)
        blob(bm, pos[:], (rad, rad, rad * 0.85), subdiv=2, seed=i * 50 + k)
    blob(bm, (-0.54, 0, 0.78), (0.07, 0.07, 0.09), subdiv=2, seed=i + 400)   # kuyruk
    _t0 = time.time()
    wool = remeshed('koyun_%d_yun' % i, bm, 0.011, 5)
    _t1 = time.time()
    wool_displace(wool, i)
    if i == 0:
        print('  koyun yün: remesh %.1f sn, kabartma %.1f sn, %d nokta' % (_t1 - _t0, time.time() - _t1, len(wool.data.vertices)), flush=True)
    setmat(wool, M_WOOL)
    wool.parent = bob
    if FUZZ is not None:
        md = wool.modifiers.new('tuy', 'NODES'); md.node_group = FUZZ
    # baş: kafatası + uzun burun, kara kısa kıl
    bm = bmesh.new()
    blob(bm, (0.0, 0, 0.0), (0.10, 0.072, 0.092), subdiv=3, seed=i + 500)
    blob(bm, (0.115, 0, -0.025), (0.12, 0.056, 0.078), subdiv=3, seed=i + 510, rot=Euler((0, 0.18, 0)))
    blob(bm, (0.215, 0, -0.05), (0.048, 0.05, 0.06), subdiv=2, seed=i + 511)
    head = remeshed('koyun_%d_bas' % i, bm, 0.006, 3)
    for pl in head.data.polygons:
        pl.use_smooth = True
    setmat(head, M_FACE)
    head.parent = bob
    head.location = (0.60, 0, 0.88)
    # alında yün perçemi
    bm = bmesh.new()
    blob(bm, (-0.045, 0, 0.07), (0.055, 0.06, 0.032), subdiv=3, seed=i + 530)
    cap = remeshed('koyun_%d_percem' % i, bm, 0.008, 3)
    wool_displace(cap, i + 9, amp_clump=0.02, amp_big=0.006)
    setmat(cap, M_WOOL)
    cap.parent = head
    for sgn in (1, -1):
        bm = bmesh.new()
        blob(bm, (0.045, 0, 0), (0.07, 0.034, 0.011), subdiv=3, seed=i + 520 + sgn)
        ear = bm_to_obj('koyun_%d_kulak' % i, bm)
        setmat(ear, M_FACE)
        ear.parent = head
        ear.location = (-0.03, sgn * 0.07, 0.035)
        ear.rotation_euler = (sgn * 0.5, 0.45, sgn * 1.75)
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.013, 0.013, 0.013), subdiv=3)
        eye = bm_to_obj('koyun_%d_goz' % i, bm)
        setmat(eye, M_PUPIL)
        eye.parent = head
        eye.location = (0.065, sgn * 0.058, 0.02)
    legs = []
    for k, (lx, ly) in enumerate(((0.28, 0.12), (0.28, -0.12), (-0.28, 0.12), (-0.28, -0.12))):
        bm = bmesh.new()
        blob(bm, (0, 0, -0.05), (0.05, 0.045, 0.09), subdiv=3, amp=0.03, seed=i * 10 + k)
        blob(bm, (0, 0, -0.27), (0.03, 0.029, 0.17), subdiv=3, amp=0.03, seed=i * 10 + k + 3)
        blob(bm, (0.0, 0, -0.22), (0.033, 0.031, 0.03), subdiv=2, seed=i * 10 + k + 4)       # diz
        leg = remeshed('koyun_%d_bacak_%d' % (i, k), bm, 0.007, 3)
        setmat(leg, M_FACE)
        bm = bmesh.new()
        blob(bm, (0.01, 0, -0.44), (0.031, 0.028, 0.022), subdiv=2, seed=i * 10 + k + 5)
        hoof = bm_to_obj('koyun_%d_toynak_%d' % (i, k), bm)
        setmat(hoof, M_HOOF)
        hoof.parent = leg
        leg.parent = bob
        leg.location = (lx, ly, 0.455)
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
# yakındaki koyun önce dursun diye: kapıya uzak noktalar önce
SPOTS.sort(key=lambda q: -(q - INSIDE).length)
START = [CAM_POS0.xy - _RT * 14.0 + _FC * 1.5, CAM_POS0.xy - _RT * 2.6 - _FC * 1.6]
paths = []
for i in range(N_SHEEP):
    jit = _FC * (0.14 * ((i * 7) % 3 - 1))
    paths.append(Path([START[0] + jit, START[1] + jit * 0.7, OUT1, GATE_PT, INSIDE, SPOTS[i]]))


def path_near(p):
    P = paths[0]
    return min((q - p).length for q in P.p[::3])


# çakıl dizisi (yerde): ön direğin dibinde, duvar boyunca kameraya göre sağa
_, FA, FP = front_post
TO_CAM0 = (CAM_POS0.xy - FP).normalized()
cam_fwd = -TO_CAM0
CAM_RIGHT = Vector((cam_fwd.y, -cam_fwd.x)).normalized()
ROW_START = FP + TO_CAM0 * (POST_R + 0.6) - CAM_RIGHT * 0.3
ROW_DIR = CAM_RIGHT
ROW_CENTER = ROW_START + ROW_DIR * 0.3


def build_slab():
    """Çakılların dizildiği yassı taş (çoban sayı taşlarını düz bir taşın üstüne dizer): gri zemin, aşı çakıl okunur."""
    src = ROCKS[2]
    ob = link(bpy.data.objects.new('yassi_tas', src.data))
    d = src.dimensions
    ob.scale = (1.0 / d.x, 0.42 / d.y, 0.075 / d.z)
    c = ROW_START + ROW_DIR * 0.33 - TO_CAM0 * 0.02
    ob.location = (c.x, c.y, hfun(c.x, c.y) - 0.005)
    ob.rotation_euler = (0.0, 0.0, math.atan2(ROW_DIR.y, ROW_DIR.x))
    # yosunsuz, açık gri taş yüzeyi: aşı çakıllar üstünde okunsun
    for sl in ob.material_slots:
        sl.link = 'OBJECT'
        sl.material = M_SLAB
    bpy.context.view_layer.update()
    return ob


SLAB = build_slab()


def slab_top(p):
    """(x, y) noktasında yassı taşın üst yüzeyi (ışın atarak)."""
    mw = SLAB.matrix_world
    inv = mw.inverted()
    o = inv @ Vector((p.x, p.y, 5.0))
    dvec = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    ok, loc, nrm, _ = SLAB.ray_cast(o, dvec)
    if ok:
        return (mw @ loc).z
    return hfun(p.x, p.y) + 0.03

if A.cim > 0:
    build_grass()
print('t ot %.1f' % (time.time() - T_START), flush=True)

sheep = [build_sheep(i) for i in range(N_SHEEP)]
print('t koyun %.1f' % (time.time() - T_START), flush=True)


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


def key_obj(ob, f, loc=True, rot=True):
    if loc:
        ob.keyframe_insert('location', frame=f)
    if rot:
        ob.keyframe_insert('rotation_quaternion' if ob.rotation_mode == 'QUATERNION' else 'rotation_euler', frame=f)


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
        key_obj(root, f)
        bob.location = (0, 0, 0.025 * abs(math.sin(phase)) * moving)
        bob.rotation_euler = (0.02 * math.sin(phase) * moving, 0.015 * math.sin(2 * phase) * moving, 0)
        key_obj(bob, f)
        head.rotation_euler = (0.05 * math.sin(f * 0.07 + i),
                               0.55 + 0.06 * math.sin(phase) * moving + (0.25 + 0.15 * math.sin(f * 0.05 + i * 2)) * (1 - moving),
                               0.15 * math.sin(f * 0.03 + i) * (1 - moving))
        key_obj(head, f, loc=False)
        for k, leg in enumerate(legs):
            off = 0 if k in (0, 3) else math.pi       # tırıs: çapraz bacaklar birlikte
            leg.rotation_euler = (0, 0.32 * math.sin(phase + off) * moving, 0)
            key_obj(leg, f, loc=False)


print('t koyun anim %.1f' % (time.time() - T_START), flush=True)


# ---------------------------------------------------------------- çakıllar
def pouch_quat(f):
    q = pouch_q0.copy()
    to_cam = (CAM_POS0.xy - HANG.xy).normalized()
    ax1 = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    ax2 = Vector((to_cam.x, to_cam.y, 0))
    a1 = a2 = 0.0
    for i in range(N_SHEEP):
        tp = T_GATE0 + T_GAP * i - 3
        if f > tp:
            dt = f - tp
            a1 += 0.045 * math.exp(-dt / 14.0) * math.sin(dt * 0.32)
            a2 += 0.025 * math.exp(-dt / 14.0) * math.sin(dt * 0.27 + 1.0)
    return Quaternion(ax1, a1) @ Quaternion(ax2, a2) @ q


def pouch_matrix(f):
    return Matrix.Translation(HANG) @ pouch_quat(f).to_matrix().to_4x4() @ Matrix.Scale(POUCH_S, 4)


heap_local = [Vector((0, 0, LIP_Z - 0.008))]
for k in range(5):
    th = 2 * math.pi * k / 5 + 0.3
    heap_local.append(Vector((0.047 * math.cos(th), 0.043 * math.sin(th), LIP_Z + 0.004)))
for k in range(3):
    th = 2 * math.pi * k / 3 + 0.9
    heap_local.append(Vector((0.022 * math.cos(th), 0.022 * math.sin(th), LIP_Z + 0.026)))
take_order = [8, 7, 6, 5, 4, 3, 2, 1]
pebbles = [pebble_mesh('cakil_%d' % k, 3000 + k, M_LAST if k == 0 else M_PEBBLE) for k in range(9)]
LAST = pebbles[0]
LAND = []
_rr = rng(4000)
for k in range(N_SHEEP):
    p = ROW_START + ROW_DIR * (0.092 * k) + Vector((_rr.uniform(-0.008, 0.008), _rr.uniform(-0.01, 0.01)))
    LAND.append(p)
local_rot = [Quaternion((0, 0, 1), rng(5000 + k).uniform(0, 6.28)) @ Quaternion((1, 0, 0), rng(5100 + k).uniform(-0.3, 0.3))
             for k in range(9)]
FLIGHT = 22


def qfix(q, prev):
    return -q if (prev is not None and q.dot(prev) < 0) else q


for idx, peb in enumerate(pebbles):
    order = take_order.index(idx) if idx in take_order else None
    prev_q = None
    t_take = T_GATE0 + T_GAP * order - 3 if order is not None else 10 ** 6
    land_q = Quaternion((0, 0, 1), rng(6000 + idx).uniform(0, 6.28))
    for f in range(-2, N_FRAMES + 3):
        if f <= t_take:
            M = pouch_matrix(f) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            loc, q, _ = M.decompose()
        else:
            M0 = pouch_matrix(t_take) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            p0, q0, _ = M0.decompose()
            L2 = LAND[order]
            p1 = Vector((L2.x, L2.y, slab_top(L2) + 0.017))
            t = min(1.0, (f - t_take) / FLIGHT)
            e = smoother(t)
            if t < 0.28:
                loc = p0 + Vector((0, 0, 0.11 * smoother(t / 0.28)))
            else:
                v = smoother((t - 0.28) / 0.72)
                loc = (p0 + Vector((0, 0, 0.11))).lerp(p1, v) + Vector((0, 0, 0.14 * 4 * v * (1 - v)))
            q = q0.slerp(land_q, e)
            q = Quaternion((1, 0, 0), 2.0 * math.sin(math.pi * e)) @ q if t < 1 else q
            if t >= 1:
                dt = f - t_take - FLIGHT
                loc = p1 + Vector((0, 0, 0.01 * math.exp(-dt / 2.0) * abs(math.sin(dt * 1.3))))
        q = qfix(q, prev_q)
        prev_q = q
        peb.location = loc
        peb.rotation_quaternion = q
        key_obj(peb, f)

for f in range(-2, N_FRAMES + 3):
    pouch.rotation_quaternion = pouch_quat(f)
    pouch.keyframe_insert('rotation_quaternion', frame=f)

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
cam_data.dof.aperture_blades = 7
cam_data.dof.aperture_rotation = 0.3


def last_world(f):
    return (pouch_matrix(f) @ Matrix.Translation(heap_local[0])).to_translation()


P_END = last_world(N_FRAMES)
_g3 = Vector((GATE_PT.x, GATE_PT.y, hfun(GATE_PT.x, GATE_PT.y) + 0.55))
MID = _g3.lerp(HANG - Vector((0, 0, 0.35)), 0.5)
_row3 = Vector((ROW_CENTER.x, ROW_CENTER.y, hfun(ROW_CENTER.x, ROW_CENTER.y)))
TGT0 = MID.lerp(_row3, 0.3) + CAM_RIGHT.to_3d() * 0.25 + Vector((0, 0, 0.1))
TGT1 = TGT0 + Vector((-0.08, -0.05, 0.0))
CAM1 = CAM_POS0 + (TGT0 - CAM_POS0).normalized() * 0.35
v_end = (CAM1 - P_END); v_end.z = 0
v_end = Matrix.Rotation(math.radians(6), 3, 'Z') @ v_end.normalized()
CAM_END = P_END + (v_end * 0.8 + Vector((0, 0, 0.6))).normalized() * 0.6
FOCUS0 = (GATE_PT.to_3d() + Vector((0, 0, hfun(GATE_PT.x, GATE_PT.y) + 0.5))).lerp(HANG - Vector((0, 0, 0.3)), 0.6)

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
    cam_data.dof.aperture_fstop = 4.0 - 1.2 * e
    cam_data.dof.keyframe_insert('aperture_fstop', frame=f)

if A.yakin == 'koyun':
    # tasarım bakışı: 0. koyuna yandan-önden yakın kamera (kamera koyunu izler)
    cam.animation_data_clear(); target.animation_data_clear(); cam_data.animation_data_clear()
    _aim = link(bpy.data.objects.new('koyun_hedef', None)); _aim.parent = sheep[0][0]; _aim.location = (0.25, 0, 0.62)
    tr.target = _aim
    cam_data.lens = 50
    cam_data.dof.use_dof = False
    for f in range(1, N_FRAMES + 1):
        scene.frame_set(f)
        rt = sheep[0][0].matrix_world
        cam.location = rt @ Vector((1.6, -2.2, 1.0))
        cam.keyframe_insert('location', frame=f)

# ---------------------------------------------------------------- son taşın parıltısı: küçük, sıcak, yumuşak dört kollu yıldız
cam_dir_end = (CAM_END - P_END).normalized()
l_dir = Vector((-cam_dir_end.x, -cam_dir_end.y, cam_dir_end.z * 2.2)).normalized()
glint = light('parilti', 'POINT', 0.0, (1.0, 0.78, 0.5), loc=P_END + Vector((0, 0, 0.25)) + cam_dir_end * 0.12, size=0.02)
glint.visible_camera = False
G0, G1, G2 = 258, 278, 300
for f, en in ((1, 0.0), (G0, 0.0), (G1, 0.35), (G2, 0.28)):
    glint.data.energy = en
    glint.data.keyframe_insert('energy', frame=f)
b2 = bmesh.new()
blob(b2, (0, 0, 0), (0.0022,) * 3, subdiv=2)
spark = bm_to_obj('parilti_nokta', b2)
M_SPARK = emissive('parilti_mat', (1.0, 0.85, 0.6), 0.0)
setmat(spark, M_SPARK)
spark.parent = LAST
_top = (cam_dir_end * 0.35 + Vector((0, 0, 1))).normalized()
_M300 = pouch_matrix(N_FRAMES) @ Matrix.Translation(heap_local[0]) @ local_rot[0].to_matrix().to_4x4()
_l3, _q3, _s3 = _M300.decompose()
spark.location = (Matrix.Translation(_l3) @ _q3.to_matrix().to_4x4()).inverted() @ (P_END + _top * 0.024)
for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission'):
    setattr(spark, attr, False)
_sp = M_SPARK.node_tree.nodes['Emission'].inputs['Strength']
for f, v in ((1, 0.0), (262, 0.0), (272, 260.0), (281, 120.0), (290, 210.0), (300, 150.0)):
    _sp.default_value = v
    _sp.keyframe_insert('default_value', frame=f)

# yakın planda keseye yumuşak, sıcak dolgu (sinema pratiği: yüz ışığı); geniş planda kapalı
_fill = light('yakin_dolgu', 'AREA', 0.0, (1.0, 0.8, 0.6), loc=CAM_END + Vector((0, 0, 0.35)) + (CAM_END - P_END).normalized() * 0.3,
              direction=(P_END - (CAM_END + Vector((0, 0, 0.35)))), size=0.8)
_fill.visible_camera = False
for f, en in ((1, 0.0), (205, 0.0), (270, 6.0), (300, 6.0)):
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
                print('GPU:', dt, [d.name for d in gpus])
                return 'GPU'
    except Exception as ex:
        print('GPU aranamadı', ex)
    return 'CPU'


C.device = pick_device()
C.samples = A.ornek
C.use_adaptive_sampling = True
C.adaptive_threshold = 0.015
C.use_denoising = True
for k, v in (('denoiser', 'OPENIMAGEDENOISE'), ('denoising_input_passes', 'RGB_ALBEDO_NORMAL'),
             ('denoising_prefilter', 'ACCURATE'), ('denoising_quality', 'HIGH')):
    try:
        setattr(C, k, v)
    except Exception as ex:
        print('ayar yok', k, ex)
C.max_bounces = 6
C.diffuse_bounces = 3
C.glossy_bounces = 2
C.transmission_bounces = 4
C.transparent_max_bounces = 16     # çim yaprakları alfa kullanır
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.blur_glossy = 0.5
C.seed = 7
C.sample_clamp_indirect = 6.0
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = bool(A.bulanik)
R.motion_blur_shutter = 0.5
R.use_persistent_data = True
R.film_transparent = False
vs = scene.view_settings
vs.view_transform = 'AgX'
vs.look = 'AgX - Medium High Contrast'
vs.exposure = 0.3

# kompozit: yalnız çok parlak noktaya (parıltı) yumuşak dört kollu yıldız + hafif hale
ng = bpy.data.node_groups.new('kompozit', 'CompositorNodeTree')
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
scene.compositing_node_group = ng
rl = ng.nodes.new('CompositorNodeRLayers')
out = ng.nodes.new('NodeGroupOutput')
gl = ng.nodes.new('CompositorNodeGlare')
for nm, val in (('Type', 'Streaks'), ('Quality', 'High'), ('Threshold', 30.0), ('Strength', 0.28), ('Streaks', 4),
                ('Streaks Angle', 0.0), ('Fade', 0.72), ('Size', 0.22), ('Saturation', 0.9),
                ('Tint', (1.0, 0.8, 0.55, 1.0))):
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
    for _nm, _p in (('kapi', _g3), ('kese', HANG), ('dizi_bas', LAND[0].to_3d() + Vector((0, 0, hfun(LAND[0].x, LAND[0].y)))),
                    ('dizi_son', LAND[-1].to_3d() + Vector((0, 0, hfun(LAND[-1].x, LAND[-1].y))))):
        _c = world_to_camera_view(scene, cam, _p)
        print('KADRAJ f%d %-8s x=%.2f y(ust)=%.2f' % (_f, _nm, _c.x, 1 - _c.y))
    _c = world_to_camera_view(scene, cam, sheep[0][0].matrix_world.to_translation() + Vector((0, 0, 0.6)))
    print('KADRAJ f%d koyun0   x=%.2f y(ust)=%.2f' % (_f, _c.x, 1 - _c.y))
print('sahne kuruldu: %.1f sn' % (time.time() - T_START), flush=True)
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(A.cikti), 'gercekci.blend'))

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
