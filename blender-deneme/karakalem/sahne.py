# Math with Zirek · sahne G, ÇİZİM sürümleri: KARAKALEM (ve aynı geçişlerden RİSOGRAF)
# Blender 5.2 LTS, Cycles CPU. Tamamen yordamsal, dış varlık yok.
# Yol: Cycles yalnız "veri geçişleri" üretir (doğrudan ışık, derinlik, normal, nesne/malzeme kimliği, AO);
# çizim görünüşü (kontur, tarama, kâğıt, mürekkep, yarım ton) her karede numpy ile bu geçişlerden kurulur.
# Blender 5.2'de Freestyle yok; Grease Pencil/Line Art ise GPU çizimi ister. Bu yol başsız Linux'ta CPU ile çalışır.
# Hikâye, zamanlama ve kamera vuruşları kil sürümüyle (../sahne.py) aynı.
# Kullanım:
#   blender -b -P sahne.py -- --mod kare --kareler 68,180,290 --w 960 --h 540 --ornek 16 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 60 --cikti out            (1920x1080)
#   blender -b -P sahne.py -- --mod post --girdi exr_klasoru --cikti out           (render yok: EXR'den yeniden çiz)
#   --stiller karakalem,risograf   (aynı geçişlerden iki tarz; k_####.png ve r_####.png)
import bpy, bmesh, math, random, sys, os, time, argparse, json, importlib.util
from mathutils import Vector, Matrix, Quaternion, Euler, noise

BURASI = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
KOK = os.path.dirname(BURASI)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--mod', default='kare')             # kare | parca | post
ap.add_argument('--kareler', default='68,180,290')
ap.add_argument('--bas', type=int, default=1)
ap.add_argument('--son', type=int, default=300)
ap.add_argument('--w', type=int, default=1920)
ap.add_argument('--h', type=int, default=1080)
ap.add_argument('--ornek', type=int, default=24)
ap.add_argument('--cikti', default='out')
ap.add_argument('--cihaz', default='cpu')
ap.add_argument('--stiller', default=globals().get('STIL_VARSAYILAN', 'karakalem'))
ap.add_argument('--girdi', default='')
ap.add_argument('--exr', type=int, default=-1)       # 1: EXR'leri tut (kare kipinde varsayılan), 0: sil
ap.add_argument('--blend', action='store_true')
ap.add_argument('--kurma', action='store_true')      # yalnız sahneyi kur, KADRAJ yaz (render yok)
A = ap.parse_args(argv)
T_START = time.time()
STILLER = [s.strip() for s in A.stiller.split(',') if s.strip()]
ONEK = {'karakalem': 'k_', 'risograf': 'r_'}


def stil_modulu(ad):
    yol = os.path.join(KOK, ad, ad + '.py')
    sys.path.insert(0, os.path.join(KOK, 'karakalem'))
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def cizdir(exr_yol, meta, f, cikti):
    import cizim_ortak as co
    P = co.exr_oku(exr_yol)
    for ad in STILLER:
        t0 = time.time()
        m = stil_modulu(ad)
        rgb = m.isle(P, meta, f)
        co.png_yaz(os.path.join(cikti, '%s%04d.png' % (ONEK.get(ad, ad[:1] + '_'), f)), rgb)
        print('CIZIM %s %d: %.1f sn' % (ad, f, time.time() - t0), flush=True)


if A.mod == 'post':
    sys.path.insert(0, os.path.join(KOK, 'karakalem'))
    os.makedirs(A.cikti, exist_ok=True)
    kl = sorted(x for x in os.listdir(A.girdi) if x.endswith('.exr'))
    secili = [int(x) for x in A.kareler.split(',') if x.strip()] if A.kareler != 'hepsi' else None
    for x in kl:
        f = int(''.join(c for c in x if c.isdigit()))
        if secili is not None and f not in secili:
            continue
        with open(os.path.join(A.girdi, 'meta_%04d.json' % f)) as fh:
            meta = json.load(fh)
        cizdir(os.path.join(A.girdi, x), meta, f, A.cikti)
    print('BITTI post %.1f sn' % (time.time() - T_START))
    raise SystemExit(0)

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


# ---------------------------------------------------------------- yerleşim
# Ağıl kil sürümündeki gibi, ama: duvar alçak ve seyrek iri taşlı (kadrajı doldurmasın), kapı sola bakar
# (sürü soldan, dizinin arkasından gelir; dizi ve kese hiçbir koyunun arkasında kalmaz), çakıl ve kese iri.
PEN_C = Vector((0.55, 1.75))
PEN_R = 1.45
GATE_ANG = math.radians(203)
GAP_HALF = 0.25


def hfun(x, y):
    d = (Vector((x, y)) - PEN_C).length
    flat = smooth(1.9, 3.8, d)
    h = 0.6 * smooth(4.0, 14.0, y)
    h += flat * (0.06 * math.sin(0.55 * x + 0.3) * math.cos(0.42 * y + 0.8)
                 + 0.025 * math.sin(1.3 * x - 0.7 * y))
    return h


OBJ_ID = [0]


def link(ob):
    scene.collection.objects.link(ob)
    OBJ_ID[0] += 1
    ob.pass_index = OBJ_ID[0]
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


# ---------------------------------------------------------------- malzemeler: hepsi aynı beyaz yayınık yüzey,
# kimlik malzeme pass_index'inde (çizimde her kimliğin tonu/rengi stil dosyasında)
KIM = dict(cim=1, ot=2, duvar=3, direk=4, yun=5, yuz=6, goz=7, bebek=8, tahta=9, kese=10, ip=11, cakil=12,
           son_cakil=13, yassi=14, tepe_uzak=15, tepe_yakin=16, yaprak=17, cicek=18)
MATS = {}
for ad, k in KIM.items():
    m = bpy.data.materials.new(ad)
    m.use_nodes = True
    N = m.node_tree.nodes
    b = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    N.remove(b)
    d = N.new('ShaderNodeBsdfDiffuse')
    d.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1.0)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    m.node_tree.links.new(d.outputs[0], out.inputs['Surface'])
    m.pass_index = k
    MATS[ad] = m


def setmat(ob, ad):
    ob.data.materials.clear()
    ob.data.materials.append(MATS[ad])


# ---------------------------------------------------------------- zemin
def build_ground():
    bm = bmesh.new()
    x0, x1, y0, y1 = -16.0, 16.0, -7.0, 22.0
    nx, ny = 200, 170
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
    setmat(ob, 'cim')


def ang_dist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def ring_pos(a, r=PEN_R):
    return Vector((PEN_C.x + r * math.cos(a), PEN_C.y + r * math.sin(a)))


def build_tufts(avoid):
    """Seyrek ot öbekleri: duvar dibinde ve yol kenarında; sağ alt üçte bir ve dizinin önü boş."""
    r = rng(11)
    bm = bmesh.new()
    count = 0
    tries = 0
    while count < 150 and tries < 20000:
        tries += 1
        if r.random() < 0.7:
            a = r.uniform(0, 2 * math.pi)
            if ang_dist(a, GATE_ANG) < GAP_HALF + 0.1:
                continue
            rr = PEN_R + (r.uniform(0.12, 0.25) if r.random() < 0.75 else -r.uniform(0.12, 0.2))
            x, y = PEN_C.x + rr * math.cos(a), PEN_C.y + rr * math.sin(a)
        else:
            x = r.uniform(-4.5, 4.0)
            y = r.uniform(-2.5, 4.5)
        p = Vector((x, y))
        if any(fn(p) for fn in avoid):
            continue
        count += 1
        z = hfun(x, y)
        n_bl = r.randint(4, 7)
        for b in range(n_bl):
            h = r.uniform(0.05, 0.1)
            tilt = Euler((r.uniform(-0.5, 0.5), r.uniform(-0.5, 0.5), r.uniform(0, 6.28))).to_matrix().to_4x4()
            base = Matrix.Translation((x + r.uniform(-0.025, 0.025), y + r.uniform(-0.025, 0.025), z - 0.004))
            M = base @ tilt @ Matrix.Translation((0, 0, h / 2))
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=5,
                                  radius1=0.011, radius2=0.001, depth=h, matrix=M)
    ob = bm_to_obj('otlar', bm)
    setmat(ob, 'ot')


# ---------------------------------------------------------------- ağıl: alçak, iri taşlı kuru duvar
def stone(name, loc, radii, yaw, seed, mat='duvar', tilt=0.1):
    r = rng(seed)
    bm = bmesh.new()
    rot = Euler((r.uniform(-tilt, tilt), r.uniform(-tilt, tilt), yaw))
    blob(bm, (0, 0, 0), radii, subdiv=3, amp=0.2, nscale=1.3, seed=seed, rot=rot)
    ob = bm_to_obj(name, bm)
    ob.location = loc
    setmat(ob, mat)
    return ob


WALL_COURSES = 3
COURSE_H = 0.095


def build_pen():
    r = rng(21)
    sid = 0
    n = int(2 * math.pi * PEN_R / 0.2)
    for course in range(WALL_COURSES):
        for j in range(n):
            a = (j + 0.5 * course + r.uniform(-0.1, 0.1)) * 2 * math.pi / n
            if ang_dist(a, GATE_ANG) < GAP_HALF + 0.09:
                continue
            p = ring_pos(a, PEN_R + r.uniform(-0.015, 0.015))
            sx = r.uniform(0.1, 0.125) * (0.9 if course == WALL_COURSES - 1 else 1.0)
            sy = r.uniform(0.07, 0.085)
            sz = r.uniform(0.05, 0.058)
            z = hfun(p.x, p.y) + 0.045 + course * COURSE_H + r.uniform(-0.006, 0.006)
            stone('tas_%03d' % sid, (p.x, p.y, z), (sx, sy, sz), a + math.pi / 2 + r.uniform(-0.12, 0.12), 100 + sid)
            sid += 1
    posts = []
    for side, sgn in (('on', 1), ('arka', -1)):
        a = GATE_ANG + sgn * (GAP_HALF + 0.02)
        p = ring_pos(a)
        posts.append((side, a, p))
        z = hfun(p.x, p.y) + 0.065
        for k in range(6):
            rr = r.uniform(0.135, 0.15) - k * 0.006
            hz = r.uniform(0.055, 0.062)
            ob = stone('direk_%s_%d' % (side, k), (p.x + r.uniform(-0.012, 0.012), p.y + r.uniform(-0.012, 0.012), z),
                       (rr, rr * 0.92, hz), r.uniform(0, 6.28), 500 + k + (0 if sgn > 0 else 50), mat='direk', tilt=0.06)
            add_subsurf(ob, 1, 0)
            z += hz * 1.78
    return posts


# ---------------------------------------------------------------- kese, çivi
CAM_POS0 = Vector((1.05, -3.35, 1.95))
POUCH_S = 1.5


def curve(name, pts, parent, mat, cyclic=False, bevel=0.005):
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
    ob.data.materials.append(MATS[mat])
    ob.parent = parent
    return ob


def build_pouch(front_post):
    _, a, p = front_post
    to_cam = (CAM_POS0.xy - p).normalized()
    pegdir = Vector((to_cam.x, to_cam.y, 0.2)).normalized()
    z_top = hfun(p.x, p.y) + 0.065 + 0.0585 * 1.78 * 5
    peg_base = Vector((p.x, p.y, z_top - 0.02))
    peg_len = 0.3
    bm = bmesh.new()
    q = Vector((0, 0, 1)).rotation_difference(pegdir)
    blob(bm, (peg_base + pegdir * (peg_len / 2))[:], (0.02, 0.02, peg_len / 2), subdiv=3, amp=0.04, nscale=2.0,
         seed=77, rot=q)
    peg = bm_to_obj('civi', bm)
    add_subsurf(peg, 1, 0)
    setmat(peg, 'tahta')
    hang = peg_base + pegdir * (peg_len - 0.035) + Vector((0, 0, 0.014))
    prof = [(0.0, 0.0), (0.06, 0.004), (0.095, 0.02), (0.115, 0.05), (0.12, 0.085), (0.112, 0.12),
            (0.09, 0.15), (0.064, 0.171), (0.05, 0.182), (0.054, 0.192), (0.066, 0.205), (0.078, 0.218),
            (0.084, 0.228)]
    DROP = 0.33
    seg = 40
    bm = bmesh.new()
    rings = []
    bottom = bm.verts.new((0, 0, -DROP))
    for (rr, zz) in prof[1:]:
        ring = []
        for s in range(seg):
            th = 2 * math.pi * s / seg
            gather = smooth(0.13, 0.18, zz)
            fold = gather * (0.003 * math.sin(9 * th + 1.3) + 0.006 * noise.noise(Vector((math.cos(th) * 3.0, math.sin(th) * 3.0, zz * 25))))
            crease = (1 - gather) * smooth(0.06, 0.15, zz) * 0.006 * math.sin(5 * th + 0.4 + 2 * noise.noise(Vector((th, 0.3, 2.2))))
            wob = 0.01 * noise.noise(Vector((math.cos(th) * 2.6, math.sin(th) * 2.6, zz * 12)))
            r2 = rr + fold + crease + wob * (rr / 0.1)
            if zz < 0.1:
                r2 += 0.008 * max(0.0, math.cos(th - 0.3))
            dz = smooth(0.2, 0.228, zz) * (0.003 * math.sin(9 * th + 1.3) + 0.008 * noise.noise(Vector((math.cos(th) * 2.0, math.sin(th) * 2.0, 5.1))))
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
    sol.thickness = 0.008
    add_subsurf(pouch, 2, 0)
    setmat(pouch, 'kese')
    pouch.location = hang
    pouch.rotation_mode = 'QUATERNION'
    tilt_axis = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    base_q = Quaternion(tilt_axis, math.radians(-22))
    pouch.rotation_quaternion = base_q
    pouch.scale = (POUCH_S, POUCH_S, POUCH_S)
    inv = base_q.inverted()
    side = Vector((-to_cam.y, to_cam.x, 0)).normalized()
    sl = inv @ side
    zb = 0.182 - DROP
    back = inv @ Vector((-to_cam.x, -to_cam.y, 0)).normalized()
    curve('ip_aski', [(back * 0.052 + Vector((0, 0, zb)))[:], (back * 0.05 + Vector((0, 0, zb + 0.05)))[:],
                      (back * 0.02 + Vector((0, 0, -0.01)))[:], (0, 0, 0.0)], pouch, 'ip', bevel=0.005)
    fr = -back
    curve('ip_uc', [(fr * 0.056 + sl * 0.01 + Vector((0, 0, zb)))[:], (fr * 0.066 + sl * 0.02 + Vector((0, 0, zb - 0.03)))[:],
                    (fr * 0.07 + sl * 0.015 + Vector((0, 0, zb - 0.06)))[:]], pouch, 'ip', bevel=0.004)
    curve('ip_bogaz', [(0.056 * math.cos(2 * math.pi * s / 10) * 1.05, 0.056 * math.sin(2 * math.pi * s / 10) * 0.95,
                        zb + 0.004 * math.sin(3 * s)) for s in range(10)], pouch, 'ip', cyclic=True, bevel=0.006)
    return pouch, base_q, hang, 0.228 - DROP


def pebble_mesh(name, seed, mat):
    r = rng(seed)
    bm = bmesh.new()
    blob(bm, (0, 0, 0), (r.uniform(0.047, 0.053), r.uniform(0.038, 0.042), r.uniform(0.027, 0.031)),
         subdiv=3, amp=0.1, nscale=1.3, seed=seed)
    ob = bm_to_obj(name, bm)
    add_subsurf(ob, 1, 0)
    setmat(ob, mat)
    ob.rotation_mode = 'QUATERNION'
    return ob


# ---------------------------------------------------------------- koyun (yün: topaklı bulut, kara yüz ve bacak)
def build_sheep(i):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('koyun_%d' % i, None))
    bob = link(bpy.data.objects.new('koyun_%d_govde' % i, None))
    bob.parent = root
    s = r.uniform(0.86, 0.95)
    root.scale = (s, s, s)
    bm = bmesh.new()
    blob(bm, (0, 0, 0.26), (0.22, 0.14, 0.125), subdiv=3, seed=i)
    for k in range(26):
        u = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
        if u.z < -0.4:
            u.z = -0.4
        pos = Vector((u.x * 0.21, u.y * 0.135, u.z * 0.12 + 0.26))
        rad = r.uniform(0.06, 0.085)
        blob(bm, pos[:], (rad, rad, rad * 0.9), subdiv=2, seed=i * 50 + k)
    blob(bm, (0.2, 0, 0.37), (0.055, 0.05, 0.045), subdiv=2, seed=i + 300)      # perçem
    blob(bm, (-0.25, 0, 0.30), (0.04, 0.035, 0.035), subdiv=2, seed=i + 400)    # kuyruk
    wool = bm_to_obj('koyun_%d_yun' % i, bm)
    rm = wool.modifiers.new('rm', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = 0.012
    sm = wool.modifiers.new('sm', 'SMOOTH')
    sm.factor = 0.7
    sm.iterations = 4
    bake_modifiers(wool)
    for pl in wool.data.polygons:
        pl.use_smooth = True
    setmat(wool, 'yun')
    wool.parent = bob
    bm = bmesh.new()
    blob(bm, (0.06, 0, 0.0), (0.085, 0.064, 0.072), subdiv=3, amp=0.03, seed=i + 500)
    blob(bm, (0.13, 0, -0.035), (0.064, 0.05, 0.048), subdiv=3, amp=0.03, seed=i + 510)
    head = bm_to_obj('koyun_%d_bas' % i, bm)
    add_subsurf(head, 1, 0)
    setmat(head, 'yuz')
    head.parent = bob
    head.location = (0.205, 0, 0.31)
    head.rotation_euler = (0, math.radians(18), 0)
    for sgn in (1, -1):
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.05, 0.022, 0.016), subdiv=2, seed=i + 520 + sgn)
        ear = bm_to_obj('koyun_%d_kulak' % i, bm)
        add_subsurf(ear, 1, 0)
        setmat(ear, 'yuz')
        ear.parent = head
        ear.location = (0.0, sgn * 0.078, 0.03)
        ear.rotation_euler = (sgn * 0.5, 0.25, sgn * 1.25)
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.021, 0.021, 0.021), subdiv=2)
        eye = bm_to_obj('koyun_%d_goz' % i, bm)
        add_subsurf(eye, 1, 0)
        setmat(eye, 'goz')
        eye.parent = head
        eye.location = (0.098, sgn * 0.04, 0.03)
        bm = bmesh.new()
        blob(bm, (0, 0, 0), (0.011, 0.011, 0.011), subdiv=2)
        pu = bm_to_obj('koyun_%d_bebek' % i, bm)
        setmat(pu, 'bebek')
        pu.parent = eye
        pu.location = (0.013, sgn * 0.006, 0.003)
    legs = []
    for k, (lx, ly) in enumerate(((0.13, 0.075), (0.13, -0.075), (-0.13, 0.075), (-0.13, -0.075))):
        bm = bmesh.new()
        blob(bm, (0, 0, -0.075), (0.024, 0.024, 0.09), subdiv=3, amp=0.02, seed=i * 10 + k)
        blob(bm, (0.005, 0, -0.152), (0.028, 0.026, 0.017), subdiv=2, seed=i * 10 + k + 5)
        leg = bm_to_obj('koyun_%d_bacak_%d' % (i, k), bm)
        add_subsurf(leg, 1, 0)
        setmat(leg, 'yuz')
        leg.parent = bob
        leg.location = (lx, ly, 0.17)
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
gu = Vector((math.cos(GATE_ANG), math.sin(GATE_ANG)))
GATE = PEN_C + gu * PEN_R
INSIDE = GATE - gu * 0.45
OUT1 = GATE + gu * 0.75
spots_rel = [(0.55, 0.5), (0.8, -0.05), (0.15, 0.8), (0.4, 0.05), (0.5, -0.55), (-0.3, 0.6),
             (-0.1, 0.1), (0.05, -0.5)]
SPOTS = [PEN_C + Vector(s) for s in spots_rel]
START = [Vector((-6.5, 0.05)), Vector((-2.9, 0.42))]
paths = []
for i in range(N_SHEEP):
    jit = Vector((0, 0.06 * ((i * 7) % 3 - 1)))
    paths.append(Path([START[0] + jit, START[1] + jit * 0.6, OUT1, GATE, INSIDE, SPOTS[i]]))

build_ground()
posts = build_pen()
front_post = [p for p in posts if p[0] == 'on'][0]
pouch, pouch_q0, HANG, LIP_Z = build_pouch(front_post)
_, FA, FP = front_post

# çakıl dizisi: kesenin önünde, kameraya yakın, yassı taşın üstünde; soldan sağa dolar
TO_CAM = (CAM_POS0.xy - FP).normalized()
ROW_DIR = Vector((-TO_CAM.y, TO_CAM.x)).normalized()        # ekranda sağa
if ROW_DIR.dot(Vector((1, 0))) < 0:
    ROW_DIR = -ROW_DIR
ROW_GAP = 0.13
ROW_END = FP + TO_CAM * 0.95 + ROW_DIR * 0.12                # son (8.) çakıl kesenin hemen altında
ROW_START = ROW_END - ROW_DIR * (ROW_GAP * (N_SHEEP - 1))
ROW_C = (ROW_START + ROW_END) / 2
bm = bmesh.new()
blob(bm, (0, 0, 0), (0.6, 0.2, 0.05), subdiv=4, amp=0.07, nscale=1.6, seed=55)
SLAB = bm_to_obj('yassi_tas', bm)
setmat(SLAB, 'yassi')
SLAB.location = (ROW_C.x, ROW_C.y, hfun(ROW_C.x, ROW_C.y) - 0.012)
SLAB.rotation_euler = (0, 0, math.atan2(ROW_DIR.y, ROW_DIR.x))
SLAB_TOP = hfun(ROW_C.x, ROW_C.y) - 0.012 + 0.047


def near_path(p):
    return min((q - p).length for q in paths[0].p[::3]) < 0.4


def lower_right(p):
    v = p - CAM_POS0.xy
    return v.dot(ROW_DIR) > 0.9 and v.dot(TO_CAM * -1) < 5.0


build_tufts([near_path, lower_right,
             lambda p: (p - ROW_C).length < 0.9,
             lambda p: (p - FP).length < 0.35,
             lambda p: (p - PEN_C).length < PEN_R - 0.25])

for k, (c, rad, mat) in enumerate((((-8.0, 19.0, -0.4), (10.0, 3.5, 2.4), 'tepe_yakin'),
                                   ((8.5, 21.0, -0.6), (11.0, 4.0, 2.8), 'tepe_yakin'),
                                   ((0.5, 30.0, -1.2), (18.0, 5.0, 4.0), 'tepe_uzak'))):
    bm = bmesh.new()
    blob(bm, c, rad, subdiv=4, amp=0.05, nscale=1.2, seed=900 + k)
    ob = bm_to_obj('tepe_%d' % k, bm)
    setmat(ob, mat)


def tree(name, x, y, sc, seed):
    r = rng(seed)
    z = hfun(x, y)
    bm = bmesh.new()
    blob(bm, (x, y, z + 0.3 * sc), (0.09 * sc, 0.09 * sc, 0.42 * sc), subdiv=3, amp=0.05, seed=seed)
    t = bm_to_obj(name + '_govde', bm)
    setmat(t, 'tahta')
    bm = bmesh.new()
    for k in range(7):
        blob(bm, (x + r.uniform(-0.4, 0.4) * sc, y + r.uniform(-0.3, 0.3) * sc, z + (0.9 + r.uniform(-0.1, 0.35)) * sc),
             (r.uniform(0.34, 0.46) * sc,) * 3, subdiv=3, amp=0.08, seed=seed + k)
    lf = bm_to_obj(name + '_yaprak', bm)
    rm = lf.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.03 * sc
    sm = lf.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 6
    bake_modifiers(lf)
    for pl in lf.data.polygons:
        pl.use_smooth = True
    setmat(lf, 'yaprak')


tree('agac1', -2.6, 4.6, 0.75, 1301)

sheep = [build_sheep(i) for i in range(N_SHEEP)]


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
    prev_s = sheep_s(i, -3)
    for f in range(-2, N_FRAMES + 3):
        s = sheep_s(i, f)
        pos, d = paths[i].at(s)
        if d.length < 1e-6:
            _, d = paths[i].at(s - 0.02)
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
                               + 0.06 * math.sin(f * 0.05 + i * 2) * (1 - moving), 0.14 * math.sin(f * 0.03 + i) * (1 - moving))
        key_obj(head, f, loc=False)
        for k, leg in enumerate(legs):
            off = 0 if k in (0, 3) else math.pi
            leg.rotation_euler = (0, 0.5 * math.sin(phase + off) * moving, 0)
            key_obj(leg, f, loc=False)


# ---------------------------------------------------------------- çakıllar
def pouch_quat(f):
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


# ağızdaki yığın (kese yerel ekseninde): 0 = son kalan (ortada, ağızda), halka 5, üstte 3
heap_local = [Vector((0, 0, LIP_Z - 0.004))]
for k in range(5):
    th = 2 * math.pi * k / 5 + 0.3
    heap_local.append(Vector((0.058 * math.cos(th), 0.058 * math.sin(th), LIP_Z + 0.014)))
for k in range(3):
    th = 2 * math.pi * k / 3 + 0.9
    heap_local.append(Vector((0.03 * math.cos(th), 0.03 * math.sin(th), LIP_Z + 0.045)))
take_order = [8, 7, 6, 5, 4, 3, 2, 1]
pebbles = [pebble_mesh('cakil_%d' % k, 3000 + k, 'son_cakil' if k == 0 else 'cakil') for k in range(9)]
LAST = pebbles[0]
LAND = []
rr = rng(4000)
for k in range(N_SHEEP):
    LAND.append(ROW_START + ROW_DIR * (ROW_GAP * k) + Vector((rr.uniform(-0.01, 0.01), rr.uniform(-0.01, 0.01))))
local_rot = [Quaternion((0, 0, 1), rng(5000 + k).uniform(0, 6.28)) @ Quaternion((1, 0, 0), rng(5100 + k).uniform(-0.25, 0.25))
             for k in range(9)]
FLIGHT = 20


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
            p1 = Vector((L2.x, L2.y, SLAB_TOP + 0.026))
            t = min(1.0, (f - t_take) / FLIGHT)
            e = smoother(t)
            if t < 0.3:
                loc = p0 + Vector((0, 0, 0.1 * smoother(t / 0.3)))
            else:
                v = smoother((t - 0.3) / 0.7)
                loc = (p0 + Vector((0, 0, 0.1))).lerp(p1, v) + Vector((0, 0, 0.18 * 4 * v * (1 - v)))
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

# ---------------------------------------------------------------- ışık: tek akşam güneşi (beyaz; renk çizimde)
world = bpy.data.worlds.new('dunya')
scene.world = world
world.use_nodes = True
bgn = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bgn.inputs['Color'].default_value = (0, 0, 0, 1)
bgn.inputs['Strength'].default_value = 0.0
world.light_settings.distance = 0.22
SUN_DIR = Vector((0.93, 0.28, -0.36)).normalized()    # ışığın gittiği yön: soldan, hafif önden, alçak
ld = bpy.data.lights.new('gunes', 'SUN')
ld.energy = math.pi
ld.color = (1, 1, 1)
ld.angle = math.radians(1.5)
sun = link(bpy.data.objects.new('gunes', ld))
sun.rotation_euler = SUN_DIR.to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- kamera
cam_data = bpy.data.cameras.new('kamera')
cam_data.lens = 40
cam_data.sensor_width = 36
cam = link(bpy.data.objects.new('kamera', cam_data))
scene.camera = cam
target = link(bpy.data.objects.new('hedef', None))
tr = cam.constraints.new('TRACK_TO')
tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'
tr.up_axis = 'UP_Y'
cam_data.dof.use_dof = False


def last_world(f):
    return (pouch_matrix(f) @ Matrix.Translation(heap_local[0])).to_translation()


P_END = last_world(N_FRAMES)
TGT0 = Vector((0.12, 0.95, 0.3))
TGT1 = TGT0 + Vector((-0.1, -0.06, 0.0))
CAM1 = CAM_POS0 + (TGT0 - CAM_POS0).normalized() * 0.3
v_end = CAM1 - P_END
v_end.z = 0
v_end = Matrix.Rotation(math.radians(-28), 3, 'Z') @ v_end.normalized()
CAM_END = P_END + (v_end * 0.78 + Vector((0, 0, 0.85))).normalized() * 1.25
PUSH0, PUSH1 = 212, 296
LENS_END = 45
for f in range(-2, N_FRAMES + 3):
    t0 = max(0.0, min(1.0, (f - 1) / (PUSH0 - 1)))
    cpos = CAM_POS0.lerp(CAM1, t0)
    tpos = TGT0.lerp(TGT1, t0)
    e = smoother((f - PUSH0) / (PUSH1 - PUSH0))
    cpos = cpos.lerp(CAM_END, e)
    tpos = tpos.lerp(P_END + Vector((0, 0, -0.06)), e)
    cpos = cpos + Vector((0.004 * math.sin(f * 0.041), 0.0, 0.003 * math.sin(f * 0.057 + 1)))
    cam.location = cpos
    cam.keyframe_insert('location', frame=f)
    target.location = tpos
    target.keyframe_insert('location', frame=f)
    cam_data.lens = 40 + (LENS_END - 40) * e
    cam_data.keyframe_insert('lens', frame=f)

# ---------------------------------------------------------------- render ayarları (yalnız veri geçişleri)
R = scene.render
R.engine = 'CYCLES'
C = scene.cycles
C.device = 'CPU'
C.samples = A.ornek
C.use_adaptive_sampling = False
C.use_denoising = False
C.max_bounces = 1
C.diffuse_bounces = 0
C.glossy_bounces = 0
C.transmission_bounces = 0
C.transparent_max_bounces = 2
C.volume_bounces = 0
C.caustics_reflective = False
C.caustics_refractive = False
C.seed = 7
C.use_animated_seed = False
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = False
R.film_transparent = True
R.use_persistent_data = True
vl = scene.view_layers[0]
for p in ('use_pass_z', 'use_pass_normal', 'use_pass_object_index', 'use_pass_material_index',
          'use_pass_diffuse_direct', 'use_pass_diffuse_color', 'use_pass_ambient_occlusion'):
    setattr(vl, p, True)
scene.view_settings.view_transform = 'Standard'
try:
    R.image_settings.media_type = 'MULTI_LAYER_IMAGE'
except Exception as ex:
    print('media_type', ex)
R.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
R.image_settings.color_depth = '32'
try:
    R.image_settings.exr_codec = 'ZIP'
except Exception:
    pass

# ---------------------------------------------------------------- kare başına bilgi (parıltı, odak)
from bpy_extras.object_utils import world_to_camera_view


def glint_strength(f):
    keys = ((1, 0.0), (262, 0.0), (272, 1.0), (281, 0.55), (290, 0.85), (300, 0.7))
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            return v0 + (v1 - v0) * smoother((f - f0) / (f1 - f0))
    return 0.0


def meta_for(f):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    cw = cam.matrix_world
    fpx = cam_data.lens / cam_data.sensor_width * A.w
    lp = LAST.matrix_world.to_translation()
    cp = cw.to_translation()
    top = lp + (cp - lp).normalized() * 0.03 + Vector((0, 0, 0.022))
    sc = world_to_camera_view(scene, cam, top)
    dist = (top - cp).length
    hp = world_to_camera_view(scene, cam, HANG)
    return {'kare': f, 'w': A.w, 'h': A.h,
            'parilti': [sc.x * A.w, (1 - sc.y) * A.h, 0.05 / max(dist, 1e-3) * fpx, glint_strength(f)],
            'odak': (P_END - cp).length if f >= PUSH0 else (Vector((HANG.x, HANG.y, 0.3)) - cp).length,
            'yakin': smoother((f - PUSH0) / (PUSH1 - PUSH0)),
            'kese': [hp.x * A.w, (1 - hp.y) * A.h]}


for _f in (1, 68, 180, 290):
    scene.frame_set(_f)
    for _nm, _p in (('kapi', GATE.to_3d() + Vector((0, 0, 0.3))), ('kese', HANG - Vector((0, 0, 0.3))),
                    ('dizi_bas', LAND[0].to_3d() + Vector((0, 0, SLAB_TOP))),
                    ('dizi_son', LAND[-1].to_3d() + Vector((0, 0, SLAB_TOP))),
                    ('agil_sag', ring_pos(math.radians(0)).to_3d()), ('agil_arka', ring_pos(math.radians(90)).to_3d()),
                    ('son_cakil', LAST.matrix_world.to_translation())):
        _c = world_to_camera_view(scene, cam, _p)
        print('KADRAJ f%d %-9s x=%.2f y(ust)=%.2f' % (_f, _nm, _c.x, 1 - _c.y))
    for _i in range(N_SHEEP):
        _c = world_to_camera_view(scene, cam, sheep[_i][0].matrix_world.to_translation() + Vector((0, 0, 0.3)))
        if -0.1 < _c.x < 1.1 and -0.1 < _c.y < 1.1:
            print('KADRAJ f%d koyun%d   x=%.2f y(ust)=%.2f' % (_f, _i, _c.x, 1 - _c.y))
print('sahne kuruldu: %.1f sn, nesne %d' % (time.time() - T_START, OBJ_ID[0]), flush=True)
if A.kurma:
    raise SystemExit(0)

os.makedirs(A.cikti, exist_ok=True)
CIKTI = os.path.abspath(A.cikti)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CIKTI, 'cizim.blend'))

tut = A.exr if A.exr >= 0 else (1 if A.mod == 'kare' else 0)
if A.mod == 'kare':
    frames = [int(x) for x in A.kareler.split(',') if x.strip()]
else:
    frames = list(range(A.bas, A.son + 1))
sys.path.insert(0, os.path.join(KOK, 'karakalem'))
for f in frames:
    meta = meta_for(f)
    scene.frame_set(f)
    exr = os.path.join(CIKTI, 'gecis_%04d.exr' % f)
    R.filepath = exr
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print('KARE %d: %.1f sn' % (f, time.time() - t0), flush=True)
    with open(os.path.join(CIKTI, 'meta_%04d.json' % f), 'w') as fh:
        json.dump(meta, fh)
    try:
        cizdir(exr, meta, f, CIKTI)
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print('CIZIM HATASI', f, ex, flush=True)
    if not tut:
        os.remove(exr)
        os.remove(os.path.join(CIKTI, 'meta_%04d.json' % f))
print('BITTI toplam %.1f sn' % (time.time() - T_START))
