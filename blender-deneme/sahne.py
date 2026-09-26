# Math with Zirek · Blender kil deneme sahnesi (video 1, sahne G: akşam, koyunlar girer, taş çıkar, tek taş kalır)
# Tamamen yordamsal: indirilmiş varlık yok. Sabit tohumlar: her çalıştırma aynı sonucu verir.
# Kullanım (yalnız bulutta):
#   blender -b -P sahne.py -- --mod kare --kareler 1,120,300 --w 960 --h 540 --ornek 32 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 30 --cikti out
import bpy, bmesh, math, random, sys, os, time, argparse
from mathutils import Vector, Matrix, Quaternion, Euler, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--mod', default='kare')          # kare | parca
ap.add_argument('--kareler', default='1,120,300')
ap.add_argument('--bas', type=int, default=1)
ap.add_argument('--son', type=int, default=300)
ap.add_argument('--w', type=int, default=1920)
ap.add_argument('--h', type=int, default=1080)
ap.add_argument('--ornek', type=int, default=128)
ap.add_argument('--cikti', default='out')
ap.add_argument('--blend', action='store_true')
A = ap.parse_args(argv)
T_START = time.time()

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
    """bm'ye gürültülü elipsoid ekler (dünya/yerel koordinatta)."""
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


# ---------------------------------------------------------------- malzemeler
def _inp(node, names, value):
    for n in names:
        if n in node.inputs:
            try:
                node.inputs[n].default_value = value
                return node.inputs[n]
            except Exception:
                pass
    return None


def clay(name, color, rough=0.55, sss=0.12, var=0.10, hue_var=0.015, mottle=0.10, mottle_scale=3.0,
         fp_scale=70.0, bump=0.25, coat=0.0, coat_rough=0.3, sheen=0.0, weave=0.0, spec=0.35, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    oi = N.new('ShaderNodeObjectInfo')
    # renk: nesne başına küçük ton/değer farkı + geniş lekelenme
    hsv = N.new('ShaderNodeHueSaturation')
    hsv.inputs['Color'].default_value = (*color, 1.0)
    vr = N.new('ShaderNodeMath'); vr.operation = 'MULTIPLY_ADD'
    vr.inputs[1].default_value = var; vr.inputs[2].default_value = 1.0 - var / 2
    L.new(oi.outputs['Random'], vr.inputs[0])
    hr = N.new('ShaderNodeMath'); hr.operation = 'MULTIPLY_ADD'
    hr.inputs[1].default_value = hue_var * 2; hr.inputs[2].default_value = 0.5 - hue_var
    L.new(oi.outputs['Random'], hr.inputs[0])
    L.new(hr.outputs[0], hsv.inputs['Hue'])
    mt = N.new('ShaderNodeTexNoise')
    mt.inputs['Scale'].default_value = mottle_scale
    _inp(mt, ['Detail'], 3.0)
    L.new(tc.outputs['Object'], mt.inputs['Vector'])
    mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY_ADD'
    mm.inputs[1].default_value = mottle * 2; mm.inputs[2].default_value = 1.0 - mottle
    L.new(mt.outputs['Fac'], mm.inputs[0])
    vv = N.new('ShaderNodeMath'); vv.operation = 'MULTIPLY'
    L.new(vr.outputs[0], vv.inputs[0]); L.new(mm.outputs[0], vv.inputs[1])
    L.new(vv.outputs[0], hsv.inputs['Value'])
    L.new(hsv.outputs['Color'], bsdf.inputs['Base Color'])
    # parmak izi: halka dalgası, lekeler hâlinde + ince yüzey greni
    wv = N.new('ShaderNodeTexWave')
    wv.wave_type = 'RINGS'
    try:
        wv.rings_direction = 'SPHERICAL'
    except Exception:
        pass
    wv.inputs['Scale'].default_value = fp_scale
    wv.inputs['Distortion'].default_value = 5.0
    _inp(wv, ['Detail'], 1.0)
    _inp(wv, ['Detail Scale'], 1.2)
    wmap = N.new('ShaderNodeMapping')
    L.new(tc.outputs['Object'], wmap.inputs['Vector'])
    wmap.inputs['Location'].default_value = (0.37, 0.11, 0.73)
    L.new(wmap.outputs['Vector'], wv.inputs['Vector'])
    mask = N.new('ShaderNodeTexNoise')
    mask.inputs['Scale'].default_value = fp_scale / 12.0
    L.new(tc.outputs['Object'], mask.inputs['Vector'])
    mramp = N.new('ShaderNodeValToRGB')
    mramp.color_ramp.elements[0].position = 0.56
    mramp.color_ramp.elements[1].position = 0.72
    L.new(mask.outputs['Fac'], mramp.inputs['Fac'])
    fpm = N.new('ShaderNodeMath'); fpm.operation = 'MULTIPLY'
    L.new(wv.outputs['Fac'], fpm.inputs[0]); L.new(mramp.outputs['Color'], fpm.inputs[1])
    fine = N.new('ShaderNodeTexNoise')
    fine.inputs['Scale'].default_value = fp_scale * 2.5
    _inp(fine, ['Detail'], 3.0)
    _inp(fine, ['Roughness'], 0.6)
    L.new(tc.outputs['Object'], fine.inputs['Vector'])
    h1 = N.new('ShaderNodeMath'); h1.operation = 'MULTIPLY_ADD'
    h1.inputs[1].default_value = 0.6
    L.new(fpm.outputs[0], h1.inputs[0])
    fine_s = N.new('ShaderNodeMath'); fine_s.operation = 'MULTIPLY'
    fine_s.inputs[1].default_value = 0.45
    L.new(fine.outputs['Fac'], fine_s.inputs[0])
    L.new(fine_s.outputs[0], h1.inputs[2])
    height = h1.outputs[0]
    if weave > 0:
        wx = N.new('ShaderNodeTexWave'); wx.wave_type = 'BANDS'; wx.bands_direction = 'X'
        wy = N.new('ShaderNodeTexWave'); wy.wave_type = 'BANDS'; wy.bands_direction = 'Z'
        for w in (wx, wy):
            w.inputs['Scale'].default_value = weave
            w.inputs['Distortion'].default_value = 1.5
            L.new(tc.outputs['Object'], w.inputs['Vector'])
        wm = N.new('ShaderNodeMath'); wm.operation = 'MULTIPLY'
        L.new(wx.outputs['Fac'], wm.inputs[0]); L.new(wy.outputs['Fac'], wm.inputs[1])
        wa = N.new('ShaderNodeMath'); wa.operation = 'MULTIPLY_ADD'
        wa.inputs[1].default_value = 0.8
        L.new(wm.outputs[0], wa.inputs[0]); L.new(height, wa.inputs[2])
        height = wa.outputs[0]
    if bump > 0:
        bn = N.new('ShaderNodeBump')
        bn.inputs['Strength'].default_value = bump
        bn.inputs['Distance'].default_value = 0.004
        L.new(height, bn.inputs['Height'])
        L.new(bn.outputs['Normal'], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = rough
    _inp(bsdf, ['Specular IOR Level', 'Specular'], spec)
    if sss > 0:
        _inp(bsdf, ['Subsurface Weight', 'Subsurface'], sss)
        _inp(bsdf, ['Subsurface Radius'], (1.0, 0.55, 0.35))
        _inp(bsdf, ['Subsurface Scale'], 0.03)
        try:
            bsdf.subsurface_method = 'BURLEY'
        except Exception:
            pass
    if coat > 0:
        _inp(bsdf, ['Coat Weight', 'Clearcoat'], coat)
        _inp(bsdf, ['Coat Roughness', 'Clearcoat Roughness'], coat_rough)
    if sheen > 0:
        _inp(bsdf, ['Sheen Weight', 'Sheen'], sheen)
        _inp(bsdf, ['Sheen Tint'], (1.0, 0.9, 0.75, 1.0))
    if emission is not None:
        _inp(bsdf, ['Emission Color', 'Emission'], (*emission, 1.0))
        _inp(bsdf, ['Emission Strength'], 0.0)
    return m


def setmat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


M_GRASS = clay('cim', (0.17, 0.30, 0.065), rough=0.85, sss=0.0, var=0.0, mottle=0.3, mottle_scale=0.7,
               fp_scale=25, bump=0.0, spec=0.15)
M_TUFT = clay('ot', (0.22, 0.38, 0.07), rough=0.65, sss=0.0, var=0.0, mottle=0.25, mottle_scale=1.2,
              fp_scale=90, bump=0.0)
M_STONE = clay('tas_duvar', (0.36, 0.34, 0.31), rough=0.66, sss=0.0, var=0.6, hue_var=0.035,
               mottle=0.18, mottle_scale=6.0, fp_scale=55, bump=0.4)
M_WOOL = clay('yun', (0.90, 0.83, 0.70), rough=0.72, sss=0.22, var=0.08, mottle=0.06, fp_scale=60,
              bump=0.3, sheen=0.25)
M_FACE = clay('yuz', (0.17, 0.12, 0.10), rough=0.5, sss=0.0, var=0.15, fp_scale=90, bump=0.2, coat=0.1)
M_EYE = clay('goz', (0.95, 0.93, 0.88), rough=0.3, sss=0.1, var=0.0, fp_scale=200, bump=0.05, coat=0.6,
             coat_rough=0.2)
M_PUPIL = clay('bebek', (0.02, 0.02, 0.02), rough=0.25, sss=0.0, var=0.0, fp_scale=200, bump=0.05,
               coat=0.7, coat_rough=0.2)
M_WOOD = clay('tahta', (0.50, 0.32, 0.17), rough=0.6, sss=0.06, var=0.2, fp_scale=50, bump=0.3, weave=0.0)
M_CLOTH = clay('bez', (0.45, 0.28, 0.13), rough=0.85, sss=0.0, var=0.0, mottle=0.18, mottle_scale=9,
               fp_scale=80, bump=0.6, weave=260.0, sheen=0.35)
M_CORD = clay('ip', (0.42, 0.30, 0.18), rough=0.8, sss=0.0, var=0.0, fp_scale=200, bump=0.2)
M_PEBBLE = clay('cakil', (0.66, 0.52, 0.32), rough=0.5, sss=0.0, var=0.22, hue_var=0.025, mottle=0.22,
                mottle_scale=45, fp_scale=160, bump=0.35, coat=0.2, coat_rough=0.25)
M_LAST = clay('son_cakil', (0.66, 0.52, 0.32), rough=0.5, sss=0.0, var=0.0, mottle=0.22, mottle_scale=45,
              fp_scale=160, bump=0.35, coat=0.2, coat_rough=0.25, emission=(1.0, 0.72, 0.38))
M_HILL1 = clay('tepe1', (0.30, 0.38, 0.12), rough=0.8, sss=0.0, var=0.0, mottle=0.2, mottle_scale=0.4, fp_scale=8, bump=0.0)
M_HILL2 = clay('tepe2', (0.66, 0.46, 0.17), rough=0.8, sss=0.0, var=0.0, mottle=0.2, mottle_scale=0.4, fp_scale=8, bump=0.0)
M_HILL3 = clay('tepe3', (0.48, 0.52, 0.36), rough=0.8, sss=0.0, var=0.0, mottle=0.15, mottle_scale=0.3, fp_scale=6, bump=0.0)
M_LEAF = clay('yaprak', (0.16, 0.27, 0.07), rough=0.7, sss=0.15, var=0.1, mottle=0.2, fp_scale=40, bump=0.0)
M_FLOWER = clay('cicek', (0.97, 0.86, 0.55), rough=0.5, sss=0.0, var=0.25, fp_scale=200, bump=0.0)


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N = m.node_tree.nodes
    N.remove(N['Principled BSDF'])
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1.0)
    em.inputs['Strength'].default_value = strength
    m.node_tree.links.new(em.outputs[0], N['Material Output'].inputs['Surface'])
    return m


# ---------------------------------------------------------------- zemin
def build_ground():
    bm = bmesh.new()
    x0, x1, y0, y1 = -14.0, 14.0, -7.0, 16.0
    nx, ny = 220, 180
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


def build_tufts():
    r = rng(11)
    bm = bmesh.new()
    count = 0
    while count < 380:
        if r.random() < 0.85:
            a = r.uniform(0, 2 * math.pi)
            if ang_dist(a, GATE_ANG) < GAP_HALF:
                continue
            rr = PEN_R + (r.uniform(0.07, 0.2) if r.random() < 0.6 else -r.uniform(0.07, 0.14))
            x, y = PEN_C.x + rr * math.cos(a), PEN_C.y + rr * math.sin(a)
        else:
            x = r.uniform(-4.0, 3.5)
            y = r.uniform(-2.8, 3.0)
        # sağ alt üçte bir sakin: orada seyrek
        if x > 0.6 and y < -0.6 and r.random() < 0.85:
            continue
        # taş dizisinin ve kesenin önü temiz
        if -1.0 < x < 0.05 and -0.95 < y < -0.2:
            continue
        count += 1
        z = hfun(x, y)
        big = r.random() < 0.35
        for b in range(r.randint(6, 10) if big else r.randint(3, 5)):
            h = r.uniform(0.04, 0.09) if big else r.uniform(0.03, 0.06)
            tilt = Euler((r.uniform(-0.45, 0.45), r.uniform(-0.45, 0.45), r.uniform(0, 6.28))).to_matrix().to_4x4()
            base = Matrix.Translation((x + r.uniform(-0.02, 0.02), y + r.uniform(-0.02, 0.02), z - 0.004))
            M = base @ tilt @ Matrix.Translation((0, 0, h / 2))
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=5,
                                  radius1=0.01, radius2=0.0015, depth=h, matrix=M)
    ob = bm_to_obj('otlar', bm)
    setmat(ob, M_TUFT)
    # küçük çiçekler
    bm = bmesh.new()
    k = 0
    while k < 70:
        x = r.uniform(-6, 5); y = r.uniform(-3.5, 7)
        if x > 1.2 and y < -1.0:
            continue
        if (Vector((x, y)) - PEN_C).length < PEN_R + 0.3:
            continue
        k += 1
        blob(bm, (x, y, hfun(x, y) + 0.05), (0.013, 0.013, 0.009), subdiv=2, seed=k)
    ob = bm_to_obj('cicekler', bm)
    setmat(ob, M_FLOWER)


# ---------------------------------------------------------------- ağıl
def ring_pos(a, r=PEN_R):
    return Vector((PEN_C.x + r * math.cos(a), PEN_C.y + r * math.sin(a)))


def ang_dist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


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


def box_plank(bm, center, size, rotz, seed):
    blob(bm, center, (size[0] / 2, size[1] / 2, size[2] / 2), subdiv=3, amp=0.05, nscale=2.0, seed=seed,
         rot=Euler((0, 0, rotz)))


def build_hurdle(back_post):
    _, a, p = back_post
    t = Vector((math.sin(a), -math.cos(a)))       # açıklıktan uzaklaşan teğet
    inward = (PEN_C - p).normalized()
    start = p + inward * 0.2 + t * 0.12
    d = (t * 0.85 + inward * 0.15).normalized()
    yaw = math.atan2(d.y, d.x)
    bm = bmesh.new()
    L = 0.62
    z0 = hfun(start.x, start.y)
    for k, zz in enumerate((0.12, 0.23, 0.34)):
        c = start + d * (L / 2)
        blob(bm, (c.x, c.y, z0 + zz), (L / 2, 0.018, 0.022), subdiv=3, amp=0.04, nscale=2.0, seed=700 + k,
             rot=Euler((0, 0, yaw)))
    for k, s in enumerate((0.03, L / 2, L - 0.03)):
        c = start + d * s
        blob(bm, (c.x, c.y, z0 + 0.2), (0.02, 0.02, 0.21), subdiv=3, amp=0.05, nscale=2.0, seed=720 + k,
             rot=Euler((0, 0, yaw)))
    ob = bm_to_obj('kapi_kanadi', bm)
    add_subsurf(ob, 1, 0)
    setmat(ob, M_WOOD)


# ---------------------------------------------------------------- kese, çakıllar
CAM_POS0 = Vector((1.0, -3.9, 1.7))
POUCH_S = 1.15


def build_pouch(front_post):
    _, a, p = front_post
    n_out = Vector((math.cos(a), math.sin(a)))
    to_cam = (CAM_POS0.xy - p).normalized()
    pegdir2 = to_cam.normalized()
    pegdir = Vector((pegdir2.x, pegdir2.y, 0.18)).normalized()
    z_top = hfun(p.x, p.y) + 0.06 + 0.05 * 1.75 * 6
    peg_base = Vector((p.x, p.y, z_top - 0.05))
    peg_len = 0.3
    # çivi (tahta)
    bm = bmesh.new()
    q = Vector((0, 0, 1)).rotation_difference(pegdir)
    blob(bm, (peg_base + pegdir * (peg_len / 2))[:], (0.017, 0.017, peg_len / 2), subdiv=3, amp=0.05, nscale=2.0,
         seed=77, rot=q)
    peg = bm_to_obj('civi', bm)
    add_subsurf(peg, 1, 0)
    setmat(peg, M_WOOD)
    hang = peg_base + pegdir * (peg_len - 0.03) + Vector((0, 0, 0.012))
    # kese: profil döndürme
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
            # büzgü kıvrımları: boğazda sık, ağızda düzensiz; gövdede aşağı inen uzun kırışıklar
            gather = smooth(0.13, 0.18, zz)
            fold = gather * (0.0025 * math.sin(11 * th + 1.3) + 0.007 * noise.noise(Vector((math.cos(th) * 3.0, math.sin(th) * 3.0, zz * 25))))
            crease = (1 - gather) * smooth(0.06, 0.15, zz) * 0.006 * math.sin(6 * th + 0.4 + 2 * noise.noise(Vector((th, 0.3, 2.2))))
            wob = 0.012 * noise.noise(Vector((math.cos(th) * 2.6, math.sin(th) * 2.6, zz * 12)))
            r2 = rr + fold + crease + wob * (rr / 0.1)
            if zz < 0.1:
                r2 += 0.008 * max(0.0, math.cos(th - 0.3))   # öne sarkık karın
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
    # ağız kameraya hafif dönük
    tilt_axis = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    base_q = Quaternion(tilt_axis, math.radians(-22))
    pouch.rotation_quaternion = base_q
    pouch.scale = (POUCH_S, POUCH_S, POUCH_S)
    # ip: askı + boğaz bağı (keseye bağlı)
    cord_mat = M_CORD

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
        ob.data.materials.append(cord_mat)
        ob.parent = pouch
        return ob
    zt = 0.228 - DROP
    side = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    # yerel eksende kamera yönüne dik düzlem
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


def pebble_mesh(name, seed, mat):
    r = rng(seed)
    bm = bmesh.new()
    blob(bm, (0, 0, 0), (r.uniform(0.041, 0.047), r.uniform(0.034, 0.038), r.uniform(0.024, 0.028)),
         subdiv=3, amp=0.12, nscale=1.3, seed=seed)
    ob = bm_to_obj(name, bm)
    add_subsurf(ob, 1, 0)
    setmat(ob, mat)
    ob.rotation_mode = 'QUATERNION'
    return ob


# ---------------------------------------------------------------- koyun
def build_sheep(i):
    r = rng(1000 + i)
    root = bpy.data.objects.new('koyun_%d' % i, None)
    link(root)
    bob = bpy.data.objects.new('koyun_%d_govde' % i, None)
    link(bob)
    bob.parent = root
    s = r.uniform(0.8, 0.9)
    root.scale = (s, s, s)
    # yün: çekirdek + yüzey topakları, voksel ile birleştirilir
    bm = bmesh.new()
    blob(bm, (0, 0, 0.25), (0.22, 0.135, 0.12), subdiv=3, seed=i)
    for k in range(34):
        u = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
        if u.z < -0.45:
            u.z = -0.45
        pos = Vector((u.x * 0.21, u.y * 0.13, u.z * 0.115 + 0.25))
        rad = r.uniform(0.055, 0.078)
        blob(bm, pos[:], (rad, rad, rad * 0.9), subdiv=2, seed=i * 50 + k)
    blob(bm, (0.2, 0, 0.36), (0.055, 0.05, 0.045), subdiv=2, seed=i + 300)      # başta yün perçem
    blob(bm, (-0.245, 0, 0.29), (0.04, 0.035, 0.035), subdiv=2, seed=i + 400)    # kuyruk
    wool = bm_to_obj('koyun_%d_yun' % i, bm)
    rm = wool.modifiers.new('rm', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = 0.011
    sm = wool.modifiers.new('sm', 'SMOOTH')
    sm.factor = 0.7
    sm.iterations = 5
    bake_modifiers(wool)
    for pl in wool.data.polygons:
        pl.use_smooth = True
    setmat(wool, M_WOOL)
    wool.parent = bob
    # baş
    bm = bmesh.new()
    blob(bm, (0.06, 0, 0.0), (0.085, 0.064, 0.072), subdiv=3, amp=0.04, seed=i + 500)
    blob(bm, (0.125, 0, -0.035), (0.062, 0.05, 0.048), subdiv=3, amp=0.04, seed=i + 510)
    head = bm_to_obj('koyun_%d_bas' % i, bm)
    add_subsurf(head, 1, 0)
    setmat(head, M_FACE)
    head.parent = bob
    head.location = (0.2, 0, 0.3)
    head.rotation_euler = (0, math.radians(18), 0)
    for sgn in (1, -1):
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.048, 0.02, 0.016), subdiv=2, seed=i + 520 + sgn)
        ear = bm_to_obj('koyun_%d_kulak' % i, bm)
        add_subsurf(ear, 1, 0)
        setmat(ear, M_FACE)
        ear.parent = head
        ear.location = (0.0, sgn * 0.075, 0.035)
        ear.rotation_euler = (sgn * 0.5, 0.2, sgn * 1.2)
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.019, 0.019, 0.019), subdiv=2)
        eye = bm_to_obj('koyun_%d_goz' % i, bm)
        add_subsurf(eye, 1, 0)
        setmat(eye, M_EYE)
        eye.parent = head
        eye.location = (0.1, sgn * 0.036, 0.03)
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.009, 0.009, 0.009), subdiv=2)
        pu = bm_to_obj('koyun_%d_bebek' % i, bm)
        setmat(pu, M_PUPIL)
        pu.parent = eye
        pu.location = (0.014, sgn * 0.004, 0.002)
    # bacaklar
    legs = []
    for k, (lx, ly) in enumerate(((0.13, 0.075), (0.13, -0.075), (-0.13, 0.075), (-0.13, -0.075))):
        bm = bmesh.new()
        blob(bm, (0, 0, -0.075), (0.026, 0.026, 0.09), subdiv=3, amp=0.03, seed=i * 10 + k)
        blob(bm, (0.005, 0, -0.152), (0.03, 0.028, 0.018), subdiv=2, seed=i * 10 + k + 5)
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
        pos = self.p[lo].lerp(self.p[hi], t)
        d = self.p[hi] - self.p[lo]
        return pos, d

    def closest_s(self, q):
        best, bs = 1e9, 0
        for k, p in enumerate(self.p):
            d = (p - q).length
            if d < best:
                best, bs = d, self.s[k]
        return bs


# ---------------------------------------------------------------- sahneyi kur
build_ground()
build_tufts()
posts = build_pen()
front_post = [p for p in posts if p[0] == 'on'][0]
back_post = [p for p in posts if p[0] == 'arka'][0]
pouch, pouch_q0, HANG, PEGDIR, LIP_Z = build_pouch(front_post)

# arka plan tepeleri ve ağaçlar
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
    setmat(t, M_WOOD)
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

# koyun yolları
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
    r = rng(2000 + i)
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
        bob.location = (0, 0, 0.012 * abs(math.sin(phase)) * moving)
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
pouch_R0 = pouch_q0


def pouch_quat(f):
    """kese her taş alınışında hafifçe sallanır."""
    q = pouch_R0.copy()
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
    return Quaternion(ax1, a1) @ Quaternion(ax2, a2) @ q


def pouch_matrix(f):
    return Matrix.Translation(HANG) @ pouch_quat(f).to_matrix().to_4x4() @ Matrix.Scale(POUCH_S, 4)


# kesenin ağzındaki yığın: 0 = son kalan (ortada), sonra halka, en üstte üçlü
heap_local = [Vector((0, 0, LIP_Z - 0.006))]
for k in range(5):
    th = 2 * math.pi * k / 5 + 0.3
    heap_local.append(Vector((0.052 * math.cos(th), 0.052 * math.sin(th), LIP_Z + 0.02)))
for k in range(3):
    th = 2 * math.pi * k / 3 + 0.9
    heap_local.append(Vector((0.025 * math.cos(th), 0.025 * math.sin(th), LIP_Z + 0.052)))
# alınma sırası: üstten başlar, en son ortadaki kalır
take_order = [8, 7, 6, 5, 4, 3, 2, 1]
pebbles = []
for k in range(9):
    pebbles.append(pebble_mesh('cakil_%d' % k, 3000 + k, M_LAST if k == 0 else M_PEBBLE))
LAST = pebbles[0]

_, fa, fp = front_post
to_cam0 = (CAM_POS0.xy - fp).normalized()
row_start = HANG.xy + to_cam0 * 0.13
row_dir = Vector((to_cam0.y, -to_cam0.x)).normalized()   # kameraya göre sola
LAND = []
rr = rng(4000)
for k in range(N_SHEEP):
    p = row_start + row_dir * (0.105 * k + 0.03) + Vector((rr.uniform(-0.012, 0.012), rr.uniform(-0.015, 0.015)))
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
    land_q = Quaternion((0, 0, 1), rng(6000 + idx).uniform(0, 6.28))
    for f in range(-2, N_FRAMES + 3):
        if f <= t_take:
            M = pouch_matrix(f) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            loc, q, _ = M.decompose()
        else:
            M0 = pouch_matrix(t_take) @ Matrix.Translation(heap_local[idx]) @ local_rot[idx].to_matrix().to_4x4()
            p0, q0, _ = M0.decompose()
            L2 = LAND[order]
            p1 = Vector((L2.x, L2.y, hfun(L2.x, L2.y) + 0.024))
            t = min(1.0, (f - t_take) / FLIGHT)
            e = smoother(t)
            if t < 0.3:
                loc = p0 + Vector((0, 0, 0.09 * smoother(t / 0.3)))
            else:
                v = smoother((t - 0.3) / 0.7)
                loc = (p0 + Vector((0, 0, 0.09))).lerp(p1, v) + Vector((0, 0, 0.16 * 4 * v * (1 - v)))
            q = q0.slerp(land_q, e)
            q = Quaternion((1, 0, 0), 2.0 * math.sin(math.pi * e)) @ q if t < 1 else q
            if t >= 1:
                dt = f - t_take - FLIGHT
                loc = p1 + Vector((0, 0, 0.012 * math.exp(-dt / 2.0) * abs(math.sin(dt * 1.3))))
        q = qfix(q, prev_q)
        prev_q = q
        peb.location = loc
        peb.rotation_quaternion = q
        key_obj(peb, f)

for f in range(-2, N_FRAMES + 3):
    pouch.rotation_quaternion = pouch_quat(f)
    pouch.keyframe_insert('rotation_quaternion', frame=f)

# ---------------------------------------------------------------- ışık
world = bpy.data.worlds.new('dunya')
scene.world = world
world.use_nodes = True
WN, WL = world.node_tree.nodes, world.node_tree.links
bg = WN['Background']
wtc = WN.new('ShaderNodeTexCoord')
sep = WN.new('ShaderNodeSeparateXYZ')
WL.new(wtc.outputs['Generated'], sep.inputs[0])
ramp = WN.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (1.0, 0.66, 0.40, 1)
ramp.color_ramp.elements[1].position = 0.35
ramp.color_ramp.elements[1].color = (0.93, 0.84, 0.66, 1)
WL.new(sep.outputs['Z'], ramp.inputs['Fac'])
WL.new(ramp.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.45


def light(name, kind, energy, color, loc=None, direction=None, size=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    link(ob)
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


sun_dir = Vector((0.55, -0.80, -0.24)).normalized()
light('gunes', 'SUN', 4.6, (1.0, 0.66, 0.36), direction=sun_dir, size=math.radians(3.0))
light('dolgu', 'AREA', 70.0, (1.0, 0.90, 0.78), loc=(3.5, -4.5, 3.2),
      direction=(Vector((-0.4, 0.4, 0.3)) - Vector((3.5, -4.5, 3.2))), size=4.0)
light('arka_dolgu', 'AREA', 25.0, (1.0, 0.8, 0.6), loc=(-3.0, 4.0, 2.5),
      direction=(Vector((0, 1, 0.3)) - Vector((-3.0, 4.0, 2.5))), size=3.0)

# ---------------------------------------------------------------- kamera
cam_data = bpy.data.cameras.new('kamera')
cam_data.lens = 50
cam_data.sensor_width = 36
cam = bpy.data.objects.new('kamera', cam_data)
link(cam)
scene.camera = cam
target = bpy.data.objects.new('hedef', None)
link(target)
tr = cam.constraints.new('TRACK_TO')
tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'
tr.up_axis = 'UP_Y'
cam_data.dof.use_dof = True
cam_data.dof.aperture_blades = 0

LAST_POS = LAST.matrix_world  # placeholder
bpy.context.view_layer.update()


def last_world(f):
    M = pouch_matrix(f) @ Matrix.Translation(heap_local[0])
    return M.to_translation()


P_END = last_world(N_FRAMES)
TGT0 = Vector((-0.15, 0.55, 0.22))
TGT1 = Vector((-0.22, 0.48, 0.24))
CAM1 = Vector((0.85, -3.65, 1.62))
v_end = (CAM1 - P_END)
v_end.z = 0
v_end = Matrix.Rotation(math.radians(-32), 3, 'Z') @ v_end.normalized()
CAM_END = P_END + (v_end * 0.75 + Vector((0, 0, 0.95))).normalized() * 1.1
FOCUS0 = (GATE.to_3d() + Vector((0, 0, 0.3))).lerp(Vector((HANG.x, HANG.y, HANG.z - 0.25)), 0.8)

PUSH0, PUSH1 = 212, 296
for f in range(-2, N_FRAMES + 3):
    t0 = max(0.0, min(1.0, (f - 1) / (PUSH0 - 1)))
    cpos = CAM_POS0.lerp(CAM1, t0)
    tpos = TGT0.lerp(TGT1, t0)
    e = smoother((f - PUSH0) / (PUSH1 - PUSH0))
    cpos = cpos.lerp(CAM_END, e)
    tpos = tpos.lerp(P_END + Vector((0, 0, -0.035)), e)
    # el kamerası değil: çok hafif nefes
    cpos = cpos + Vector((0.004 * math.sin(f * 0.041), 0.0, 0.003 * math.sin(f * 0.057 + 1)))
    cam.location = cpos
    cam.keyframe_insert('location', frame=f)
    target.location = tpos
    target.keyframe_insert('location', frame=f)
    focus = FOCUS0.lerp(P_END, smoother((f - PUSH0 + 10) / (PUSH1 - PUSH0 - 10)))
    cam_data.dof.focus_distance = (cpos - focus).length
    cam_data.dof.keyframe_insert('focus_distance', frame=f)
    cam_data.dof.aperture_fstop = 0.9 + 1.5 * e
    cam_data.dof.keyframe_insert('aperture_fstop', frame=f)

# ---------------------------------------------------------------- son taşın parıltısı
cam_dir_end = (CAM_END - P_END).normalized()
l_dir = Vector((-cam_dir_end.x, -cam_dir_end.y, cam_dir_end.z * 2.2)).normalized()
glint = light('parilti', 'POINT', 0.0, (1.0, 0.8, 0.5), loc=P_END + l_dir * 0.5, size=0.01)
try:
    glint.visible_camera = False
    glint.visible_diffuse = True
except Exception:
    pass
G0, G1, G2 = 258, 278, 300
for f in (1, G0, G1, G2):
    en = {1: 0.0, G0: 0.0, G1: 0.5, G2: 0.4}[f]
    glint.data.energy = en
    glint.data.keyframe_insert('energy', frame=f)
emis = LAST.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
for f, en in ((1, 0.0), (G0, 0.0), (G1, 0.0), (G2, 0.0)):
    emis.default_value = en
    emis.keyframe_insert('default_value', frame=f)
_lb = LAST.data.materials[0].node_tree.nodes['Principled BSDF']
b2 = bmesh.new()
blob(b2, (0, 0, 0), (0.0035, 0.0035, 0.0035), subdiv=2)
spark = bm_to_obj('parilti_nokta', b2)
M_SPARK = emissive('parilti_mat', (1.0, 0.85, 0.55), 0.0)
setmat(spark, M_SPARK)
spark.parent = LAST
_top = (cam_dir_end * 0.35 + Vector((0, 0, 1))).normalized()
_M300 = pouch_matrix(N_FRAMES) @ Matrix.Translation(heap_local[0]) @ local_rot[0].to_matrix().to_4x4()
_l3, _q3, _s3 = _M300.decompose()
spark.location = (Matrix.Translation(_l3) @ _q3.to_matrix().to_4x4()).inverted() @ (P_END + _top * 0.029)
for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission'):
    try:
        setattr(spark, attr, False)
    except Exception:
        pass
_sp = M_SPARK.node_tree.nodes['Emission'].inputs['Strength']
for f, v in ((1, 0.0), (262, 0.0), (272, 320.0), (281, 150.0), (290, 260.0), (300, 180.0)):
    _sp.default_value = v
    _sp.keyframe_insert('default_value', frame=f)
for nm, vals in (('Coat Weight', (0.2, 0.2, 0.2, 0.2)), ('Coat Roughness', (0.25, 0.25, 0.25, 0.25))):
    if nm in _lb.inputs:
        for f, v in zip((1, G0 - 12, G1, G2), vals):
            _lb.inputs[nm].default_value = v
            _lb.inputs[nm].keyframe_insert('default_value', frame=f)

# havada süzülen toz: flu ışık benekleri (bokeh), sağ alt üçte bir boş
from bpy_extras.object_utils import world_to_camera_view
scene.frame_set(1)
bpy.context.view_layer.update()
M_MOTE = emissive('toz', (1.0, 0.82, 0.55), 3.0)
try:
    M_MOTE.emission_sampling = 'NONE'
except Exception:
    pass
rm = rng(8000)
motes = 0
tries = 0
bm = bmesh.new()
mote_objs = []
while motes < 12 and tries < 2000:
    tries += 1
    d = rm.uniform(1.3, 2.2) if rm.random() < 0.6 else rm.uniform(7.0, 10.0)
    ang = rm.uniform(-0.3, 0.3)
    base = CAM_POS0 + (TGT0 - CAM_POS0).normalized() * d
    p = base + Vector((rm.uniform(-1.0, 1.0) * d * 0.33, 0, rm.uniform(-0.55, 0.55) * d * 0.2))
    sc = world_to_camera_view(scene, cam, p)
    if not (0.02 < sc.x < 0.98 and 0.05 < sc.y < 0.98):
        continue
    if (sc.x > 0.62 and sc.y < 0.42) or (0.22 < sc.x < 0.58 and 0.08 < sc.y < 0.65):
        continue
    if p.z < hfun(p.x, p.y) + 0.1:
        continue
    b2 = bmesh.new()
    blob(b2, (0, 0, 0), (0.004 if d < 5 else 0.02,) * 3, subdiv=1)
    mo = bm_to_obj('toz_%d' % motes, b2)
    setmat(mo, M_MOTE)
    ph = rm.uniform(0, 6.28)
    for f in range(-2, N_FRAMES + 3, 3):
        mo.location = p + Vector((0.03 * math.sin(f * 0.02 + ph), 0.02 * math.cos(f * 0.017 + ph), 0.0012 * f))
        mo.keyframe_insert('location', frame=f)
    try:
        mo.visible_shadow = False
        mo.visible_diffuse = False
        mo.visible_glossy = False
    except Exception:
        pass
    motes += 1
bm.free()

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
C.max_bounces = 4
C.diffuse_bounces = 2
C.glossy_bounces = 1
C.transmission_bounces = 2
C.transparent_max_bounces = 4
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.blur_glossy = 0.6
C.seed = 7
C.use_animated_seed = False
C.sample_clamp_indirect = 8.0
try:
    C.use_light_tree = False
except Exception:
    pass
try:
    C.texture_limit_render = 'OFF'
except Exception:
    pass
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = True
R.motion_blur_shutter = 0.3
R.use_persistent_data = True
R.film_transparent = False
vs = scene.view_settings
try:
    vs.view_transform = 'AgX'
    vs.look = 'AgX - Medium High Contrast'
except Exception as ex:
    print('görünüm', ex)
vs.exposure = -0.35

# kompozit: parlak noktalara yumuşak yıldız parıltısı
scene.use_nodes = True
tree = scene.node_tree
for n in list(tree.nodes):
    tree.nodes.remove(n)
rl = tree.nodes.new('CompositorNodeRLayers')
comp = tree.nodes.new('CompositorNodeComposite')
try:
    gl = tree.nodes.new('CompositorNodeGlare')
    for attr, val in (('glare_type', 'STREAKS'), ('quality', 'HIGH'), ('streaks', 4), ('angle_offset', 0.0),
                      ('fade', 0.88), ('threshold', 40.0), ('mix', 0.0), ('size', 8)):
        if hasattr(gl, attr):
            try:
                setattr(gl, attr, val)
            except Exception as ex:
                print('glare', attr, ex)
    for nm, val in (('Threshold', 40.0), ('Highlights Threshold', 40.0), ('Strength', 0.55), ('Streaks', 4),
                    ('Streaks Angle', 0.0), ('Fade', 0.8), ('Mix', 0.0), ('Size', 0.6), ('Tint', (1.0, 0.78, 0.5, 1.0))):
        if nm in gl.inputs:
            try:
                gl.inputs[nm].default_value = val
            except Exception as ex:
                print('glare in', nm, ex)
    print('glare girişleri:', [s.name for s in gl.inputs])
    fg = tree.nodes.new('CompositorNodeGlare')
    if hasattr(fg, 'glare_type'):
        fg.glare_type = 'FOG_GLOW'
    for attr, val in (('threshold', 40.0), ('size', 7), ('quality', 'HIGH'), ('mix', 0.0)):
        if hasattr(fg, attr):
            try:
                setattr(fg, attr, val)
            except Exception:
                pass
    for nm, val in (('Threshold', 40.0), ('Strength', 0.12), ('Size', 0.35), ('Tint', (1.0, 0.75, 0.45, 1.0))):
        if nm in fg.inputs:
            try:
                fg.inputs[nm].default_value = val
            except Exception as ex:
                print('fog in', nm, ex)
    tree.links.new(rl.outputs['Image'], fg.inputs[0])
    tree.links.new(fg.outputs[0], gl.inputs[0])
    tree.links.new(gl.outputs[0], comp.inputs['Image'])
except Exception as ex:
    print('glare kurulamadı:', ex)
    tree.links.new(rl.outputs['Image'], comp.inputs['Image'])

print('sahne kuruldu: %.1f sn' % (time.time() - T_START))
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(A.cikti, 'sahne.blend'))

_t = {}


def _pre(sc, *a):
    _t['t'] = time.time()


def _post(sc, *a):
    print('KARE %d: %.1f sn' % (sc.frame_current, time.time() - _t.get('t', time.time())), flush=True)


bpy.app.handlers.render_pre.append(_pre)
bpy.app.handlers.render_post.append(_post)

if A.mod == 'deney':
    R.image_settings.file_format = 'PNG'
    f = int(A.kareler.split(',')[0])
    scene.frame_set(f)
    mats = [m for m in bpy.data.materials if m.use_nodes and 'Principled BSDF' in m.node_tree.nodes]

    def sss(on):
        for m in mats:
            b = m.node_tree.nodes['Principled BSDF']
            if 'Subsurface Weight' in b.inputs:
                if not on:
                    b['_sss'] = b.inputs['Subsurface Weight'].default_value
                    b.inputs['Subsurface Weight'].default_value = 0.0
                else:
                    b.inputs['Subsurface Weight'].default_value = b.get('_sss', 0.0)

    saved_links = []

    def bump(on):
        for m in mats:
            nt = m.node_tree
            b = nt.nodes['Principled BSDF']
            if not on:
                for l in list(b.inputs['Normal'].links):
                    saved_links.append((nt, l.from_socket, b.inputs['Normal']))
                    nt.links.remove(l)
            else:
                for nt2, a, bb in saved_links:
                    nt2.links.new(a, bb)
                saved_links.clear()

    variants = [
        ('taban', lambda: None, lambda: None),
        ('sss_yok', lambda: sss(False), lambda: sss(True)),
        ('bulanik_yok', lambda: setattr(R, 'use_motion_blur', False), lambda: setattr(R, 'use_motion_blur', True)),
        ('alan_derinligi_yok', lambda: setattr(cam_data.dof, 'use_dof', False), lambda: setattr(cam_data.dof, 'use_dof', True)),
        ('kabartma_yok', lambda: bump(False), lambda: bump(True)),
        ('ornek_yarim', lambda: setattr(C, 'samples', max(1, A.ornek // 2)), lambda: setattr(C, 'samples', A.ornek)),
    ]
    for nm, on, off in variants:
        on()
        R.filepath = os.path.join(os.path.abspath(A.cikti), 'deney_%s.png' % nm)
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print('DENEY %s: %.1f sn' % (nm, time.time() - t0), flush=True)
        off()
elif A.mod == 'kare':
    R.image_settings.file_format = 'PNG'
    R.image_settings.color_mode = 'RGB'
    R.image_settings.color_depth = '8'
    for f in [int(x) for x in A.kareler.split(',') if x.strip()]:
        scene.frame_set(f)
        R.filepath = os.path.join(os.path.abspath(A.cikti), 'kare_%04d.png' % f)
        bpy.ops.render.render(write_still=True)
else:
    if A.son < 258:
        # parıltı henüz yok: parlama düğümleri çıktıyı değiştirmez, atlanır (CPU süresi)
        for l in list(comp.inputs['Image'].links):
            tree.links.remove(l)
        tree.links.new(rl.outputs['Image'], comp.inputs['Image'])
        print('parlama atlandı (kare < 258)')
    scene.frame_start = A.bas
    scene.frame_end = A.son
    R.image_settings.file_format = 'PNG'
    R.image_settings.color_mode = 'RGB'
    R.image_settings.color_depth = '8'
    R.filepath = os.path.join(os.path.abspath(A.cikti), 'k_')
    bpy.ops.render.render(animation=True)
print('BITTI toplam %.1f sn' % (time.time() - T_START))
