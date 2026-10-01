# Math with Zirek · video 1 · sahne H · MİNYATÜR "Nuzi kabı" (temsilî canlandırma)
# Blender 5.2, Cycles + Freestyle. Tamamen yordamsal, dış varlık yok.
# Onaylı minyatür tarzı (blender-deneme/minyatur): ortografik dik bakış, ışıksız "boyalı" yüzeyler, kâğıt greni,
# ince sepya kontur, maden renkleri, altın süslü pervaz.
# İçerik: Nuzi'de (bugünkü Kerkük yakını, MÖ ~1500-1350) bir kâtip odası: hasır örtülü sedir, lacivert örtü, üstünde
# içi boş yumurta biçimli kil kap (yüzeyinde OKUNMAYAN, yalnız süs olan çivi izleri). Pencereden uzakta küçük bir sürü,
# toprağa dikili çoban değneği, tepede kerpiç evler. 15,29 sn'de kap çatlar, iki yarıya ayrılır; tam 48 çakıl dökülür ve
# 8x6 düzgün bir diziye yerleşir (~18,3 sn). Görüntüde hiçbir dilde yazı, rakam, harf yok (çok dilli kanal kararı).
# Kare: 609 (20,284 sn, 30 fps). Sağ üst (bindirme "48" ve etiketler) ve sağ alt üçte bir (2B karakterler) sakin.
# Kullanım:
#   blender -b -P sahne.py -- --mod kare --kareler 61,301,481,586 --w 960 --h 540 --ornek 16 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 41 --cikti out                (gerçek kare numaraları)
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 20 --harita 300 --cikti out   (iş akışının 300'lük bölüşü 609'a eşlenir)
#   blender -b -P sahne.py -- --mod yok                                                (yalnız kurar, KADRAJ yazar)
import bpy, bmesh, math, random, sys, os, time, argparse
from mathutils import Vector, Matrix, Quaternion, Euler, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--mod', default='kare')
ap.add_argument('--kareler', default='61,301,481,586')
ap.add_argument('--bas', type=int, default=1)
ap.add_argument('--son', type=int, default=609)
ap.add_argument('--harita', type=int, default=0)
ap.add_argument('--w', type=int, default=1920)
ap.add_argument('--h', type=int, default=1080)
ap.add_argument('--ornek', type=int, default=32)
ap.add_argument('--cikti', default='out')
ap.add_argument('--cihaz', default='auto')
ap.add_argument('--cizgi', type=int, default=1)
ap.add_argument('--blend', action='store_true')
A = ap.parse_args(argv)
T_START = time.time()

FPS = 30
N_FRAMES = 609
F_CRACK = 447              # çatlak çizgisi büyümeye başlar (14,87 sn)
F_SPLIT = 460              # kap açılır (15,30 sn; görev: 15,29 sn)
N_STONES = 48
GRID_C, GRID_R = 8, 6      # 8 sütun x 6 sıra = 48

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = N_FRAMES
NOLINE = bpy.data.collections.new('cizgisiz')      # konturu çizilmeyenler (çivi izleri, ot, gök, pervaz)
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


def box(bm, x0, x1, y0, y1, z0, z1, mi=0, top_mi=None):
    vs = [bm.verts.new(v) for v in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                    (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    for k, fi in enumerate(faces):
        f = bm.faces.new([vs[i] for i in fi])
        f.material_index = top_mi if (k == 1 and top_mi is not None) else mi


# ---------------------------------------------------------------- kamera geometrisi
EL = math.radians(38.0)                       # yükseklik açısı: masa üstü "dizilir", minyatür gibi yüksek bakış
VIEW = Vector((0.0, math.cos(EL), -math.sin(EL)))
UPV = Vector((0.0, math.sin(EL), math.cos(EL)))   # ekranda yukarı
RIGHT3 = Vector((1.0, 0.0, 0.0))
LDIR = Vector((-0.55, -0.35, 0.75)).normalized()  # boyadaki ışık: sol üst önden


def scr(x, v, depth=0.0):
    """Ekran düzleminde (x sağa, v yukarı) bir nokta; depth > 0 kameradan uzağa."""
    return Vector((x, 0, 0)) + UPV * v + VIEW * depth


# ---------------------------------------------------------------- boya malzemesi (onaylı minyatür tarzından)
def _paper_grain(N, L):
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
          gold=False, grad=None, soft=0.22, uv=False, pstr=1.0, mscale=2.5):
    """Boyalı yüzey (ışıksız). pattern: 'yun', 'tas', 'benek', 'sunger', 'tugla' (kerpiç, x-z), 'hasir' (örgü, x-y)."""
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
        c2, axis, lo, hi = grad[:4]
        sp = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs[grad[4] if len(grad) > 4 else 'Object'], sp.inputs[0])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = lo; mr.inputs['From Max'].default_value = hi
        L.new(sp.outputs[axis], mr.inputs['Value'])
        cc = N.new('ShaderNodeRGB'); cc.outputs[0].default_value = (*s2l(c2), 1)
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L.new(mr.outputs[0], mx.inputs['Factor']); L.new(col, mx.inputs['A']); L.new(cc.outputs[0], mx.inputs['B'])
        col = mx.outputs['Result']
    if pattern is not None:
        pc = N.new('ShaderNodeRGB'); pc.outputs[0].default_value = (*s2l(pcol or (0.35, 0.22, 0.14)), 1)
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (pscale, pscale * (1.6 if uv else 1.0), pscale * (1.5 if pattern == 'tas' else 1.0))
        L.new(tc.outputs['UV' if uv else 'Object'], mp.inputs['Vector'])
        fac = None
        if pattern == 'tugla':
            mp.inputs['Rotation'].default_value = (math.pi / 2, 0.0, 0.0)     # x-z düzlemi -> doku x-y
            mp.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
            br = N.new('ShaderNodeTexBrick')
            br.offset = 0.5
            br.inputs['Scale'].default_value = 1.0
            br.inputs['Mortar Size'].default_value = pwidth
            br.inputs['Mortar Smooth'].default_value = 0.3
            br.inputs['Brick Width'].default_value = pscale
            br.inputs['Row Height'].default_value = pscale * 0.3
            br.inputs['Color1'].default_value = (1, 1, 1, 1); br.inputs['Color2'].default_value = (0.9, 0.9, 0.9, 1)
            br.inputs['Mortar'].default_value = (0, 0, 0, 1)
            L.new(mp.outputs[0], br.inputs['Vector'])
            # tuğla başına ton farkı + harç
            hs0 = N.new('ShaderNodeHueSaturation')
            sepb = N.new('ShaderNodeSeparateColor'); L.new(br.outputs['Color'], sepb.inputs[0])
            vb = N.new('ShaderNodeMath'); vb.operation = 'MULTIPLY_ADD'; vb.inputs[1].default_value = 0.35; vb.inputs[2].default_value = 0.68
            L.new(sepb.outputs[0], vb.inputs[0])
            L.new(col, hs0.inputs['Color']); L.new(vb.outputs[0], hs0.inputs['Value'])
            col = hs0.outputs['Color']
            fm = N.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; fm.inputs[1].default_value = pstr
            L.new(br.outputs['Fac'], fm.inputs[0])
            fac = fm.outputs[0]
        elif pattern == 'hasir':
            w1 = N.new('ShaderNodeTexWave'); w1.wave_type = 'BANDS'; w1.bands_direction = 'X'
            w1.inputs['Scale'].default_value = pscale; w1.inputs['Distortion'].default_value = 0.0
            w2 = N.new('ShaderNodeTexWave'); w2.wave_type = 'BANDS'; w2.bands_direction = 'Y'
            w2.inputs['Scale'].default_value = pscale * 0.22; w2.inputs['Distortion'].default_value = 0.0
            L.new(mp.outputs[0], w1.inputs['Vector']); L.new(mp.outputs[0], w2.inputs['Vector'])
            r1 = N.new('ShaderNodeMapRange'); r1.inputs['From Min'].default_value = 0.75; r1.inputs['From Max'].default_value = 1.0
            L.new(w1.outputs['Fac'], r1.inputs['Value'])
            r2 = N.new('ShaderNodeMapRange'); r2.inputs['From Min'].default_value = 0.85; r2.inputs['From Max'].default_value = 1.0
            L.new(w2.outputs['Fac'], r2.inputs['Value'])
            mxm = N.new('ShaderNodeMath'); mxm.operation = 'MAXIMUM'
            L.new(r1.outputs[0], mxm.inputs[0]); L.new(r2.outputs[0], mxm.inputs[1])
            fm = N.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; fm.inputs[1].default_value = pstr
            L.new(mxm.outputs[0], fm.inputs[0])
            fac = fm.outputs[0]
        elif pattern in ('yun', 'tas'):
            vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'
            if uv:
                vo.voronoi_dimensions = '2D'
            vo.inputs['Randomness'].default_value = 0.85
            L.new(mp.outputs[0], vo.inputs['Vector'])
            rp = N.new('ShaderNodeMapRange'); rp.inputs['From Min'].default_value = pwidth
            rp.inputs['From Max'].default_value = pwidth * 0.35
            rp.inputs['To Max'].default_value = (0.8 if pattern == 'yun' else 1.0) * pstr
            L.new(vo.outputs['Distance'], rp.inputs['Value'])
            fac = rp.outputs[0]
            if pattern == 'tas':
                vc = N.new('ShaderNodeTexVoronoi'); vc.inputs['Randomness'].default_value = 0.85
                if uv:
                    vc.voronoi_dimensions = '2D'
                L.new(mp.outputs[0], vc.inputs['Vector'])
                hs = N.new('ShaderNodeHueSaturation')
                vm = N.new('ShaderNodeMath'); vm.operation = 'MULTIPLY_ADD'; vm.inputs[1].default_value = 0.16; vm.inputs[2].default_value = 0.9
                sep = N.new('ShaderNodeSeparateColor'); L.new(vc.outputs['Color'], sep.inputs[0])
                L.new(sep.outputs[0], vm.inputs[0])
                L.new(col, hs.inputs['Color']); L.new(vm.outputs[0], hs.inputs['Value'])
                col = hs.outputs['Color']
            else:
                v2 = N.new('ShaderNodeTexVoronoi'); v2.inputs['Randomness'].default_value = 0.85
                L.new(mp.outputs[0], v2.inputs['Vector'])
                rg = N.new('ShaderNodeMapRange'); rg.interpolation_type = 'SMOOTHSTEP'
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
            rp.inputs['To Max'].default_value = pstr
            L.new(vo.outputs['Distance'], rp.inputs['Value'])
            fac = rp.outputs[0]
            if pattern == 'benek':
                sep = N.new('ShaderNodeSeparateColor'); L.new(vo.outputs['Color'], sep.inputs[0])
                gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.55
                L.new(sep.outputs[0], gt.inputs[0])
                ml = N.new('ShaderNodeMath'); ml.operation = 'MULTIPLY'
                L.new(fac, ml.inputs[0]); L.new(gt.outputs[0], ml.inputs[1])
                fac = ml.outputs[0]
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L.new(fac, mx.inputs['Factor']); L.new(col, mx.inputs['A']); L.new(pc.outputs[0], mx.inputs['B'])
        col = mx.outputs['Result']
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
    mt = N.new('ShaderNodeTexNoise'); mt.inputs['Scale'].default_value = mscale; mt.inputs['Detail'].default_value = 3.0
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


# ---------------------------------------------------------------- palet
SEPIA = (0.30, 0.18, 0.10)
M_CLAY = paint('kil', (0.83, 0.64, 0.44), mottle=0.07, soft=0.35, shade=(0.80, 0.74, 0.80), mscale=7.0)
M_CLAY_IN = paint('kil_ic', (0.52, 0.34, 0.22), mottle=0.06, soft=0.3, shade=(0.85, 0.82, 0.88), mscale=9.0)
M_WEDGE = flat_emit('civi_izi', (0.42, 0.26, 0.16))
M_RULE = flat_emit('cizgi_izi', (0.60, 0.42, 0.27))
M_CRACK = flat_emit('catlak', (0.24, 0.13, 0.08))
M_PEBBLES = [paint('cakil_%d' % k, c, mottle=0.06, soft=0.3, shade=(0.80, 0.76, 0.86), mscale=12.0)
             for k, c in enumerate(((0.86, 0.38, 0.16), (0.82, 0.33, 0.15), (0.89, 0.44, 0.20)))]
M_CLOTH = paint('ortu', (0.14, 0.27, 0.62), pattern='benek', pcol=(0.86, 0.68, 0.30), pscale=7.0, pwidth=0.10, soft=0.3,
                shade=(0.80, 0.80, 0.92))
M_GOLD = paint('altin', (0.84, 0.65, 0.28), gold=True, soft=0.35, shade=(0.82, 0.78, 0.74))
M_VERMB = paint('kirmizi_serit', (0.78, 0.24, 0.12), soft=0.3)
M_MAT = paint('hasir', (0.86, 0.72, 0.46), pattern='hasir', pcol=(0.70, 0.54, 0.32), pscale=3.2, pstr=0.3, soft=0.4,
              mottle=0.05, shade=(0.86, 0.84, 0.90))
M_BENCH = paint('sedir_yuz', (0.80, 0.63, 0.45), pattern='tugla', pcol=(0.62, 0.46, 0.32), pscale=1.1, pwidth=0.03, pstr=0.6,
                soft=0.3, mottle=0.06)
M_WALL = paint('duvar', (0.94, 0.86, 0.74), pattern='tugla', pcol=(0.78, 0.64, 0.50), pscale=1.3, pwidth=0.02, pstr=0.35,
               soft=0.25, mottle=0.07, mscale=0.8, shade=(0.84, 0.80, 0.86))
M_WOOD = paint('ahsap', (0.52, 0.34, 0.20), soft=0.3, pattern='tas', pcol=(0.40, 0.25, 0.15), pscale=3.0, pwidth=0.02, pstr=0.5)
M_REED = paint('kamis', (0.86, 0.74, 0.46), soft=0.3)
M_POT = paint('testi', (0.80, 0.50, 0.30), soft=0.35, mottle=0.05)
M_POT_BAND = paint('testi_bant', (0.22, 0.15, 0.13), soft=0.3)
M_POT_WHITE = flat_emit('testi_beyaz', (0.95, 0.91, 0.82))
# dış dünya (pencereden)
M_FIELD = paint('tarla', (0.66, 0.70, 0.42), mottle=0.05, pattern='benek', pcol=(0.93, 0.86, 0.66), pscale=4.0, pwidth=0.075,
                soft=0.5, shade=(0.88, 0.88, 0.92))
M_HILLROCK = paint('kaya', (0.52, 0.40, 0.60), mottle=0.06, pattern='tas', pcol=(0.36, 0.24, 0.40), pscale=6.0, pwidth=0.03,
                   grad=((0.93, 0.78, 0.80), 'Z', -1.3, -0.85), soft=0.3)
M_HILLROCK2 = paint('kaya2', (0.74, 0.48, 0.34), mottle=0.06, pattern='tas', pcol=(0.50, 0.30, 0.20), pscale=6.0, pwidth=0.03,
                    grad=((0.97, 0.84, 0.64), 'Z', -1.3, -0.85), soft=0.3)
M_CYPRESS = paint('servi', (0.17, 0.38, 0.28), pattern='tas', pcol=(0.10, 0.25, 0.18), pscale=22.0, pwidth=0.06, soft=0.3)
M_TRUNK = paint('govde', (0.46, 0.30, 0.20), soft=0.3)
M_HOUSE = paint('ev', (0.86, 0.72, 0.52), soft=0.3, shade=(0.78, 0.74, 0.84))
M_DOOR = flat_emit('kapi_ici', (0.36, 0.24, 0.17))
M_SKY = paint('gok', (0.84, 0.64, 0.27), gold=True, grad=((0.97, 0.86, 0.58), 'Y', 0.80, 0.45, 'Window'), soft=0.0, mottle=0.04)
M_CLOUD = paint('bulut', (0.97, 0.93, 0.88), grad=((0.80, 0.76, 0.90), 'Z', 0.06, -0.06), soft=0.4)
M_GRASS = flat_emit('ot', (0.22, 0.42, 0.26))
M_FLOWER = [flat_emit('cicek_k', (0.84, 0.24, 0.14)), flat_emit('cicek_b', (0.98, 0.95, 0.86))]
WOOL_COLS = [(0.97, 0.94, 0.86), (0.84, 0.68, 0.48), (0.96, 0.92, 0.84), (0.55, 0.45, 0.40)]
M_WOOLS = [paint('yun_%d' % k, c, pattern='yun', pcol=((0.62, 0.52, 0.42) if sum(c) > 1.2 else (0.70, 0.60, 0.52)),
                 pscale=34.0, pwidth=0.05, soft=0.3, shade=(0.84, 0.82, 0.90)) for k, c in enumerate(WOOL_COLS)]
M_FACES = [paint('yuz_%d' % k, ((0.93, 0.84, 0.74) if sum(c) > 1.2 else (0.36, 0.28, 0.25)), soft=0.3) for k, c in enumerate(WOOL_COLS)]
GOAT_COLS = [(0.30, 0.22, 0.18), (0.62, 0.46, 0.32), (0.20, 0.16, 0.14)]
M_GOATS = [paint('keci_%d' % k, c, soft=0.3, shade=(0.84, 0.82, 0.90), mottle=0.06) for k, c in enumerate(GOAT_COLS)]
M_HORN = paint('boynuz', (0.62, 0.54, 0.44), soft=0.3)
M_EAR_IN = paint('kulak_ic', (0.90, 0.58, 0.52), soft=0.3)
M_LEG = paint('bacak', (0.34, 0.24, 0.18), soft=0.3)
M_EYE = flat_emit('goz', (0.10, 0.06, 0.04), paper=False)
M_CREAM = flat_emit('pervaz_kagit', (0.94, 0.89, 0.77))
M_LAPIS = flat_emit('pervaz_lacivert', (0.13, 0.24, 0.56))
M_VERM = flat_emit('pervaz_kirmizi', (0.78, 0.24, 0.12))
M_BGOLD = paint('pervaz_altin', (0.85, 0.67, 0.30), gold=True, soft=0.0, mottle=0.03)

# ---------------------------------------------------------------- oda: sedir (hasır üstü), duvar, pencere
BENCH_Y0, WALL_Y0, WALL_Y1 = -1.9, 1.1, 1.45
WIN_X0, WIN_X1, WIN_Z0, WIN_Z1 = -2.75, -0.55, 0.35, 2.2
bm = bmesh.new()
box(bm, -7.0, 6.0, BENCH_Y0, WALL_Y0 + 0.01, -2.2, 0.0, mi=1, top_mi=0)
bm_obj('sedir', bm, [M_MAT, M_BENCH], smooth_shade=False)
bm = bmesh.new()
XS, ZS = (-7.0, WIN_X0, WIN_X1, 6.0), (0.0, WIN_Z0, WIN_Z1, 5.0)
for yy in (WALL_Y0, WALL_Y1):
    G = [[bm.verts.new((x, yy, z)) for x in XS] for z in ZS]
    for iz in range(3):
        for ix in range(3):
            if ix == 1 and iz == 1:
                continue
            q = (G[iz][ix], G[iz][ix + 1], G[iz + 1][ix + 1], G[iz + 1][ix])
            bm.faces.new(q if yy == WALL_Y0 else tuple(reversed(q)))
    if yy == WALL_Y0:
        GF = G
    else:
        GB = G
for (a0, a1) in (((1, 1), (1, 2)), ((1, 2), (2, 2)), ((2, 2), (2, 1)), ((2, 1), (1, 1))):   # pencere içi yüzleri
    bm.faces.new((GF[a0[0]][a0[1]], GF[a1[0]][a1[1]], GB[a1[0]][a1[1]], GB[a0[0]][a0[1]]))
bm.normal_update()
bm_obj('duvar', bm, [M_WALL], smooth_shade=False)
bm = bmesh.new()
box(bm, WIN_X0 - 0.22, WIN_X1 + 0.22, WALL_Y0 - 0.06, WALL_Y1 + 0.02, WIN_Z1, WIN_Z1 + 0.2)        # ahşap lento
box(bm, WIN_X0 - 0.1, WIN_X1 + 0.1, WALL_Y0 - 0.08, WALL_Y0 + 0.2, WIN_Z0 - 0.06, WIN_Z0 + 0.02)   # eşik tahtası
bm_obj('lento', bm, [M_WOOD], smooth_shade=False)

# ---------------------------------------------------------------- dış dünya: tarla, sırt, tepede kerpiç evler, gök
FIELD_Z = -1.3


def crest_y(x):
    return 4.6 + 0.12 * math.sin(1.3 * x + 0.5) + 0.06 * math.sin(3.1 * x)


def hout(x, y):
    yc = crest_y(x)
    if y <= yc:
        return FIELD_Z + 0.03 * noise.noise(Vector((x * 0.9, y * 0.9, 0.3)))
    return FIELD_Z - 1.4 * (y - yc) ** 1.3 + 0.03 * noise.noise(Vector((x * 0.9, y * 0.9, 0.3)))


bm = bmesh.new()
X0, X1, Y0, Y1, nx, ny = -4.5, 1.5, 1.5, 7.5, 90, 90
grid = [[bm.verts.new((X0 + (X1 - X0) * i / nx, Y0 + (Y1 - Y0) * j / ny, 0)) for i in range(nx + 1)] for j in range(ny + 1)]
for row in grid:
    for v in row:
        v.co.z = hout(v.co.x, v.co.y)
for j in range(ny):
    for i in range(nx):
        bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
bm_obj('tarla', bm, [M_FIELD])

# gök: bakışa dik büyük düzlem (yalnız pencereden görünür)
bm = bmesh.new()
c = scr(-1.6, 2.0, 30.0)
vs = [bm.verts.new(c + RIGHT3 * sx * 12 + UPV * sy * 8) for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
bm.faces.new(vs)
bm_obj('gok', bm, [M_SKY], noline=True)


def on_crest(x, back=0.0):
    y = crest_y(x) + back
    return Vector((x, y, hout(x, y)))


# bulutlar: pencerenin gök şeridinde, sol tarafta
for k, (x, v, w) in enumerate(((-2.25, 2.08, 0.36), (-1.05, 2.16, 0.28))):
    bm = bmesh.new()
    pts = []
    for s in range(64):
        t = 2 * math.pi * s / 64
        rr = 1.0 + 0.22 * abs(math.sin(7 * t / 2 + k))
        pts.append((math.cos(t) * w * rr, math.sin(t) * w * 0.3 * rr))
    vv = [bm.verts.new((px, 0, pz)) for (px, pz) in pts]
    f = bm.faces.new(vv)
    ex = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0.02, 0))
    cl = bm_obj('bulut_%d' % k, bm, [M_CLOUD], smooth_shade=False)
    cl.matrix_world = Matrix.Translation(scr(x, v, 14.0)) @ Matrix((RIGHT3, VIEW, UPV)).transposed().to_4x4()

# sırttaki kayalar, serviler, kerpiç evler (küçük, uzak; minyatürde yukarı dizilmiş)
for k, (x, back, s, m) in enumerate(((-2.55, 0.15, 0.32, M_HILLROCK), (-2.1, 0.3, 0.22, M_HILLROCK2), (-0.75, 0.2, 0.26, M_HILLROCK))):
    p = on_crest(x, back)
    bm = bmesh.new()
    r = rng(400 + k)
    for j in range(5):
        off = Vector((r.uniform(-0.8, 0.8) * s, r.uniform(-0.3, 0.3) * s, 0))
        hh = r.uniform(0.5, 1.1) * s * (1.3 if j < 2 else 1.0)
        blob(bm, p + off + Vector((0, 0, hh * 0.3)), (0.45 * s, 0.4 * s, hh), subdiv=3, amp=0.12, seed=400 + k * 10 + j,
             curls=0.1, curl_scale=4.0)
    bm_obj('kaya_%d' % k, bm, [m])
for k, (x, back, s) in enumerate(((-1.85, 0.25, 0.26), (-1.68, 0.1, 0.2))):
    p = on_crest(x, back)
    bm = bmesh.new()
    tube(bm, p - Vector((0, 0, 0.03)), p + Vector((0, 0, 0.5 * s)), 0.07 * s, 0.06 * s, seg=8)
    bm_obj('servi_govde_%d' % k, bm, [M_TRUNK])
    bm = bmesh.new()
    prof = [(0.0, 0.25), (0.28, 0.45), (0.36, 1.0), (0.32, 1.8), (0.2, 2.6), (0.0, 3.1)]
    seg = 16
    rings = []
    for (rr, zz) in prof[1:-1]:
        rings.append([bm.verts.new((p.x + rr * s * math.cos(2 * math.pi * t / seg), p.y + rr * s * math.sin(2 * math.pi * t / seg),
                                    p.z + zz * s)) for t in range(seg)])
    b0 = bm.verts.new((p.x, p.y, p.z + prof[0][1] * s)); b1 = bm.verts.new((p.x, p.y, p.z + prof[-1][1] * s))
    for t in range(seg):
        bm.faces.new((b0, rings[0][(t + 1) % seg], rings[0][t]))
        bm.faces.new((b1, rings[-1][t], rings[-1][(t + 1) % seg]))
    for j in range(len(rings) - 1):
        for t in range(seg):
            bm.faces.new((rings[j][t], rings[j][(t + 1) % seg], rings[j + 1][(t + 1) % seg], rings[j + 1][t]))
    bm_obj('servi_%d' % k, bm, [M_CYPRESS], subsurf=1)
# kerpiç evler: düz damlı küçük kutular, koyu kapı ağzı (yazı, süs, dinî yapı yok)
for k, (x, back, w, h) in enumerate(((-1.42, 0.12, 0.26, 0.17), (-1.16, 0.22, 0.2, 0.22), (-1.27, 0.38, 0.3, 0.14))):
    p = on_crest(x, back)
    bm = bmesh.new()
    box(bm, x - w / 2, x + w / 2, p.y - 0.09, p.y + 0.09, p.z - 0.15, p.z + h)
    box(bm, x - w / 2 - 0.012, x + w / 2 + 0.012, p.y - 0.1, p.y + 0.1, p.z + h, p.z + h + 0.022)
    bm_obj('ev_%d' % k, bm, [M_HOUSE], smooth_shade=False)
    bm = bmesh.new()
    dw = 0.045
    dv = [bm.verts.new((x - w * 0.15 + dx, p.y - 0.093, p.z + dz)) for (dx, dz) in ((-dw / 2, 0.0), (dw / 2, 0.0), (dw / 2, h * 0.55), (-dw / 2, h * 0.55))]
    bm.faces.new(dv)
    bm_obj('ev_kapi_%d' % k, bm, [M_DOOR], noline=True)


# ---------------------------------------------------------------- sürü (koyun + keçi), toprağa dikili çoban değneği
def leg_set(bm_parent, bob, i, kind):
    legs = []
    for k, (lx, ly) in enumerate(((0.25, 0.12), (0.25, -0.12), (-0.25, 0.12), (-0.25, -0.12))):
        leg = link(bpy.data.objects.new('%s_%d_bacak_%d' % (kind, i, k), None))
        leg.parent = bob
        leg.location = (lx, ly, 0.44)
        bm = bmesh.new()
        tube(bm, Vector((0, 0, 0.03)), Vector((0, 0, -0.4)), 0.034, 0.026, seg=8)
        blob(bm, Vector((0.008, 0, -0.415)), (0.036, 0.03, 0.03), subdiv=2, amp=0.0, seed=4)
        g = bm_obj('%s_%d_bacak_%d_m' % (kind, i, k), bm, [M_LEG])
        g.parent = leg
        legs.append(leg)
    return legs


def build_animal(i, kind, ci):
    r = rng(1000 + i)
    root = link(bpy.data.objects.new('%s_%d' % (kind, i), None))
    bob = link(bpy.data.objects.new('%s_%d_govde' % (kind, i), None))
    bob.parent = root
    bm = bmesh.new()
    if kind == 'koyun':
        mat = M_WOOLS[ci]; face = M_FACES[ci]
        blob(bm, Vector((0, 0, 0.6)), (0.48, 0.27, 0.27), subdiv=4, amp=0.03, seed=i * 7, curls=0.05, curl_scale=5.0)
        blob(bm, Vector((-0.46, 0, 0.66)), (0.08, 0.06, 0.09), subdiv=3, amp=0.05, seed=i * 7 + 1, curls=0.1, curl_scale=5.0)
    else:
        mat = M_GOATS[ci]; face = M_GOATS[ci]
        blob(bm, Vector((0, 0, 0.62)), (0.44, 0.2, 0.22), subdiv=4, amp=0.03, seed=i * 7)
        tube(bm, Vector((-0.4, 0, 0.72)), Vector((-0.5, 0, 0.86)), 0.04, 0.015, seg=8)       # dik kısa kuyruk
    body = bm_obj('%s_%d_govde_m' % (kind, i), bm, [mat])
    body.parent = bob
    head = link(bpy.data.objects.new('%s_%d_bas' % (kind, i), None))
    head.parent = bob
    head.location = (0.42, 0, 0.76)
    bm = bmesh.new()
    rot = Quaternion((0, 1, 0), math.radians(28))
    blob(bm, Vector((0.12, 0, -0.03)), (0.16, 0.08 if kind == 'keci' else 0.085, 0.09), subdiv=3, amp=0.0, seed=1, rot=rot, mi=0)
    for sy in (-1, 1):
        blob(bm, Vector((0.03, sy * 0.1, 0.03)), (0.075, 0.03, 0.022), subdiv=2, amp=0.0, seed=2,
             rot=Quaternion((0, 0, 1), sy * 0.9) @ Quaternion((1, 0, 0), sy * (0.4 if kind == 'koyun' else 1.0)), mi=2)
        blob(bm, Vector((0.14, sy * 0.066, 0.02)), (0.017, 0.012, 0.019), subdiv=2, amp=0.0, seed=3, mi=1)
    mats = [face, M_EYE, M_EAR_IN]
    if kind == 'koyun':
        blob(bm, Vector((0.04, 0, 0.06)), (0.09, 0.08, 0.06), subdiv=3, amp=0.05, seed=i + 77, mi=3, curls=0.12, curl_scale=6.0)
        mats.append(mat)
    else:
        # geriye kıvrık boynuzlar + küçük sakal
        for sy in (-1, 1):
            pts = [Vector((0.02 - 0.16 * (1 - math.cos(t * 1.6)) * 0.7, sy * (0.035 + 0.02 * t), 0.08 + 0.17 * math.sin(t * 1.6) * 0.8))
                   for t in [k / 6 for k in range(7)]]
            for k in range(6):
                tube(bm, pts[k], pts[k + 1], 0.024 * (1 - k / 7.5), 0.024 * (1 - (k + 1) / 7.5), seg=6, mi=3)
        blob(bm, Vector((0.2, 0, -0.14)), (0.02, 0.018, 0.05), subdiv=2, mi=0)
        mats.append(M_HORN)
    hd = bm_obj('%s_%d_bas_m' % (kind, i), bm, mats)
    hd.parent = head
    legs = leg_set(bm, bob, i, kind)
    return root, bob, head, legs


ANIMAL_S = 0.29
FLOCK = [  # (tür, renk, x, y, yön (rad), otluyor mu)
    ('koyun', 0, -2.42, 3.62, 0.15, True), ('keci', 0, -2.05, 3.98, 3.0, False), ('koyun', 2, -1.78, 3.55, 3.3, True),
    ('koyun', 1, -1.45, 4.05, 0.1, True), ('keci', 1, -1.12, 3.66, 2.9, True), ('koyun', 3, -0.95, 4.18, 0.4, False),
    ('keci', 2, -2.62, 4.2, 0.2, True)]
animals = []
for i, (kind, ci, x, y, yaw, graze) in enumerate(FLOCK):
    root, bob, head, legs = build_animal(i, kind, ci)
    root.location = (x, y, hout(x, y))
    root.rotation_euler = (0, 0, yaw)
    root.scale = (ANIMAL_S,) * 3
    animals.append((root, bob, head, legs, graze, i))
for (root, bob, head, legs, graze, i) in animals:
    for f in range(-2, N_FRAMES + 3, 2):
        if graze:
            pitch = 0.55 + 0.08 * math.sin(f * 0.11 + i * 1.7)
            yawh = 0.12 * math.sin(f * 0.031 + i)
        else:
            pitch = 0.05 * math.sin(f * 0.05 + i)
            yawh = 0.35 * math.sin(f * 0.018 + i * 2.0)
        head.rotation_euler = (0, pitch, yawh)
        head.keyframe_insert('rotation_euler', frame=f)
# çoban değneği: toprağa dikili, üstte kıvrık sap
bm = bmesh.new()
sx_, sy_ = -2.28, 3.86
z0 = hout(sx_, sy_)
top = Vector((sx_ + 0.04, sy_, z0 + 0.62))
tube(bm, Vector((sx_, sy_, z0 - 0.05)), top, 0.016, 0.013, seg=8)
prev = top
for k in range(1, 9):
    a = math.pi * k / 8 * 1.15
    p = top + Vector((0.07 * math.sin(a), 0, 0.07 * (1 - math.cos(a))))
    tube(bm, prev, p, 0.013, 0.013, seg=8)
    prev = p
bm_obj('degnek', bm, [M_WOOD])

# tarlada seyrek ot tutamları
r = rng(123)
bm1 = bmesh.new(); bf = [bmesh.new() for _ in M_FLOWER]
for k in range(70):
    x = r.uniform(-2.8, -0.5); y = r.uniform(3.3, 4.5)
    if y > crest_y(x) - 0.05:
        continue
    if any((Vector((x, y)) - Vector((a[2], a[3]))).length < 0.2 for a in FLOCK):
        continue
    z = hout(x, y)
    for b in range(5):
        ang = -0.9 + 1.8 * b / 4
        tip = Vector((x, y, z)) + RIGHT3 * math.sin(ang) * 0.04 + Vector((0, 0, math.cos(ang) * 0.065))
        base = Vector((x, y, z - 0.005)); side = RIGHT3 * 0.006
        v0 = bm1.verts.new(base - side); v1 = bm1.verts.new(base + side); v2 = bm1.verts.new(tip)
        bm1.faces.new((v0, v1, v2))
    if r.random() < 0.35:
        fb = bf[r.randrange(len(bf))]
        cc = Vector((x, y, z + 0.065))
        ring = [fb.verts.new(cc + (RIGHT3 * math.cos(2 * math.pi * t / 6) + UPV * math.sin(2 * math.pi * t / 6)) * 0.013) for t in range(6)]
        fb.faces.new(ring)
bm_obj('ot', bm1, [M_GRASS], smooth_shade=False, noline=True)
for j, fb in enumerate(bf):
    bm_obj('cicek_%d' % j, fb, [M_FLOWER[j]], smooth_shade=False, noline=True)

# ---------------------------------------------------------------- masa üstü: örtü, kamış kalem, Nuzi tipi boyalı kadeh
CLOTH_X0, CLOTH_X1, CLOTH_Y0, CLOTH_Y1, CLOTH_T = -1.85, 0.62, -1.82, 0.52, 0.012
bm = bmesh.new()
box(bm, CLOTH_X0, CLOTH_X1, CLOTH_Y0, CLOTH_Y1, 0.0, CLOTH_T)
bm_obj('ortu', bm, [M_CLOTH], smooth_shade=False)


def flat_frame(bm, x0, x1, y0, y1, t, z, mi=0):
    o = [bm.verts.new(v) for v in ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))]
    n = [bm.verts.new(v) for v in ((x0 + t, y0 + t, z), (x1 - t, y0 + t, z), (x1 - t, y1 - t, z), (x0 + t, y1 - t, z))]
    for k in range(4):
        f = bm.faces.new((o[k], o[(k + 1) % 4], n[(k + 1) % 4], n[k]))
        f.material_index = mi


bm = bmesh.new()
flat_frame(bm, CLOTH_X0 + 0.05, CLOTH_X1 - 0.05, CLOTH_Y0 + 0.05, CLOTH_Y1 - 0.05, 0.05, CLOTH_T + 0.001, 0)
flat_frame(bm, CLOTH_X0 + 0.125, CLOTH_X1 - 0.125, CLOTH_Y0 + 0.125, CLOTH_Y1 - 0.125, 0.012, CLOTH_T + 0.001, 1)
bm_obj('ortu_serit', bm, [M_GOLD, M_VERMB], smooth_shade=False, noline=True)

# kamış kalem (örtünün solunda, hasır üstünde)
bm = bmesh.new()
p0 = Vector((-2.35, -1.25, 0.022)); p1 = Vector((-2.05, -0.35, 0.022))
tube(bm, p0, p1, 0.02, 0.02, seg=8)
tube(bm, p0 + (p0 - p1).normalized() * 0.0, p0 + (p0 - p1).normalized() * 0.07, 0.02, 0.004, seg=8)
bm_obj('kalem', bm, [M_REED])

# Nuzi tipi kadeh (ince, düğme ayaklı; koyu bant üstünde beyaz geometrik süs) - sol arkada, duvarın önünde
POT_C = Vector((-3.45, 0.55, 0.0))
prof = [(0.0, 0.0), (0.11, 0.0), (0.11, 0.04), (0.05, 0.08), (0.06, 0.2), (0.16, 0.45), (0.24, 0.8), (0.27, 1.05),
        (0.27, 1.22), (0.26, 1.36), (0.245, 1.4), (0.225, 1.38)]
bm = bmesh.new()
seg = 40
rings = [[bm.verts.new(POT_C + Vector((rr * math.cos(2 * math.pi * t / seg), rr * math.sin(2 * math.pi * t / seg), z))) for t in range(seg)]
         for (rr, z) in prof[1:]]
cb = bm.verts.new(POT_C)
for t in range(seg):
    bm.faces.new((cb, rings[0][(t + 1) % seg], rings[0][t]))
for j in range(len(rings) - 1):
    for t in range(seg):
        f = bm.faces.new((rings[j][t], rings[j][(t + 1) % seg], rings[j + 1][(t + 1) % seg], rings[j + 1][t]))
        zc = (prof[j + 1][1] + prof[j + 2][1]) / 2
        f.material_index = 1 if 0.8 < zc < 1.3 else 0
cin = bm.verts.new(POT_C + Vector((0, 0, 1.3)))
for t in range(seg):
    bm.faces.new((cin, rings[-1][t], rings[-1][(t + 1) % seg])).material_index = 1      # koyu ağız
pot = bm_obj('kadeh', bm, [M_POT, M_POT_BAND])


def pot_r(z):
    for k in range(len(prof) - 1):
        (r0, z0), (r1, z1) = prof[k], prof[k + 1]
        if z0 <= z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return 0.27


# kadeh süsü: koyu bant üstünde beyaz noktalar ve çapraz çizgi (geometrik, dinî değil)
bm = bmesh.new()
for t in range(28):
    a = 2 * math.pi * t / 28
    if math.sin(a) > 0.3:
        continue          # arka taraf (görünmez)
    for (z, rad) in ((0.9, 0.018), (1.2, 0.018)):
        rr = pot_r(z) + 0.004
        c = POT_C + Vector((rr * math.cos(a), rr * math.sin(a), z))
        nrm = Vector((math.cos(a), math.sin(a), 0))
        tg = Vector((-math.sin(a), math.cos(a), 0))
        ring = [bm.verts.new(c + (tg * math.cos(2 * math.pi * s / 8) + Vector((0, 0, 1)) * math.sin(2 * math.pi * s / 8)) * rad) for s in range(8)]
        bm.faces.new(ring)
    # zikzak
    for (z0, z1) in ((0.96, 1.14),):
        a1 = a + 2 * math.pi / 56
        for (aa, za, ab, zb) in ((a, z0, a1, z1), (a1, z1, a + 2 * math.pi / 28, z0)):
            pa = POT_C + Vector(((pot_r(za) + 0.004) * math.cos(aa), (pot_r(za) + 0.004) * math.sin(aa), za))
            pb = POT_C + Vector(((pot_r(zb) + 0.004) * math.cos(ab), (pot_r(zb) + 0.004) * math.sin(ab), zb))
            d = (pb - pa); nrm = Vector((math.cos(aa), math.sin(aa), 0)); sd = d.cross(nrm).normalized() * 0.008
            q = [bm.verts.new(v) for v in (pa - sd, pb - sd, pb + sd, pa + sd)]
            bm.faces.new(q)
bm_obj('kadeh_sus', bm, [M_POT_WHITE], noline=True)

# ---------------------------------------------------------------- Nuzi kabı: içi boş, yumurta biçimli kil kap
EGG_A = 0.46               # yarı uzunluk (x)
EGG_R = 0.30               # en büyük yarıçap
EGG_C = Vector((-0.52, -0.02, 0.0))   # z sonra hesaplanır (örtüye oturur)
WALL_T = 0.035             # kabuk kalınlığı


def egg_r(x):
    t = x / EGG_A
    return EGG_R * math.sqrt(max(0.0, 1.0 - t * t)) * (1.0 + 0.09 * t)


def egg_pt(x, th):
    """Yüzey noktası (kap yerel): uzun eksen x; th, x ekseni çevresinde açı. Hafif el yapımı yamukluk."""
    rr = egg_r(x)
    d = Vector((0.0, math.cos(th), math.sin(th)))
    lump = 1.0 + 0.035 * noise.noise(Vector((x * 3.0, math.cos(th) * 1.6, math.sin(th) * 1.6)) + Vector((5.1, 2.3, 0.7)))
    return Vector((x, 0, 0)) + d * rr * lump


def egg_normal(x, th):
    e = 1e-3
    p = egg_pt(x, th)
    tx = egg_pt(min(EGG_A - 1e-4, x + e), th) - egg_pt(max(-EGG_A + 1e-4, x - e), th)
    tt = egg_pt(x, th + e) - egg_pt(x, th - e)
    n = tt.cross(tx).normalized()
    if n.dot(p - Vector((x, 0, 0))) < 0:
        n = -n
    return n


_jr = rng(909)
JAG = [_jr.uniform(-1, 1) for _ in range(18)]


def split_x(th):
    """Çatlağın x konumu (açıya göre zikzak)."""
    u = (th % (2 * math.pi)) / (2 * math.pi) * len(JAG)
    k = int(u) % len(JAG)
    t = u - int(u)
    a, b = JAG[k], JAG[(k + 1) % len(JAG)]
    return 0.025 + 0.05 * (a + (b - a) * t)


def egg_mesh(name, part, mats, seg=72, nphi=44):
    """part: 'tam' (bütün), 'sol' (x < çatlak), 'sag' (x > çatlak). Kutuptan çatlağa meridyen açısıyla örülür.
    Yarılar elle kurulan kalın kabuk: dış yüz + içe ölçeklenmiş iç yüz + kırık kenar (kutupta sivri uç çıkmaz)."""
    bm = bmesh.new()
    KX, KR = 1.0 - WALL_T / EGG_A * 1.4, 1.0 - WALL_T / EGG_R

    def inner(p):
        return Vector((p.x * KX, p.y * KR, p.z * KR))

    layers = ('out',) if part == 'tam' else ('out', 'in')
    rows = {L_: [] for L_ in layers}
    for j in range(seg):
        th = 2 * math.pi * j / seg
        xs = split_x(th)
        if part == 'tam':
            ph0, ph1 = 0.0, math.pi
        elif part == 'sol':
            ph0, ph1 = 0.0, math.acos(max(-1.0, min(1.0, -xs / EGG_A)))
        else:
            ph0, ph1 = math.acos(max(-1.0, min(1.0, -xs / EGG_A))), math.pi
        for L_ in layers:
            row = []
            for i in range(nphi + 1):
                ph = ph0 + (ph1 - ph0) * i / nphi
                x = -EGG_A * math.cos(ph)
                if (part == 'tam' and i in (0, nphi)) or (part == 'sol' and i == 0) or (part == 'sag' and i == nphi):
                    row.append(None)
                    continue
                p = egg_pt(x, th)
                row.append(bm.verts.new(p if L_ == 'out' else inner(p)))
            rows[L_].append(row)
    out_faces, in_faces, rim_faces = [], [], []
    for L_ in layers:
        k = 1.0 if L_ == 'out' else None
        pole0 = bm.verts.new(Vector((-EGG_A * (1 if L_ == 'out' else KX), 0, 0))) if part in ('tam', 'sol') else None
        pole1 = bm.verts.new(Vector((EGG_A * (1 if L_ == 'out' else KX), 0, 0))) if part in ('tam', 'sag') else None
        R_ = rows[L_]
        lst = out_faces if L_ == 'out' else in_faces
        for j in range(seg):
            a, b = R_[j], R_[(j + 1) % seg]
            for i in range(nphi):
                if a[i] is None and b[i] is None:
                    lst.append(bm.faces.new((pole0, b[i + 1], a[i + 1])))
                elif a[i + 1] is None and b[i + 1] is None:
                    lst.append(bm.faces.new((a[i], b[i], pole1)))
                else:
                    lst.append(bm.faces.new((a[i], a[i + 1], b[i + 1], b[i])))
    if part != 'tam':
        ii = nphi if part == 'sol' else 0
        for j in range(seg):
            jn = (j + 1) % seg
            rim_faces.append(bm.faces.new((rows['out'][j][ii], rows['out'][jn][ii], rows['in'][jn][ii], rows['in'][j][ii])))
    rim_set, in_set = set(rim_faces), set(in_faces)
    for f in out_faces + in_faces + rim_faces:
        f.normal_update()
        c = f.calc_center_median()
        if f in rim_set:
            want = Vector((1, 0, 0)) if part == 'sol' else Vector((-1, 0, 0))
            f.material_index = 1
        else:
            want = c - Vector((c.x * 0.5, 0, 0))
            if f in in_set:
                want = -want
                f.material_index = 1
        if f.normal.dot(want) < 0:
            f.normal_flip()
    return bm_obj(name, bm, mats)


egg = egg_mesh('kap', 'tam', [M_CLAY])
half_l = egg_mesh('kap_sol', 'sol', [M_CLAY, M_CLAY_IN])
half_r = egg_mesh('kap_sag', 'sag', [M_CLAY, M_CLAY_IN])
_minz = min(v.co.z for v in egg.data.vertices)
EGG_C.z = CLOTH_T - _minz - 0.004            # örtüye hafifçe gömülü oturur (temas çizgisi)
for ob in (egg, half_l, half_r):
    ob.rotation_mode = 'XYZ'
    ob.location = EGG_C

# ---------------------------------------------------------------- yüzeyde süs çivi izleri (okunmaz; gerçek işaret değil)
WEDGE = [(0.0, -0.011), (0.0, 0.011), (0.015, 0.0028), (0.044, 0.0009), (0.044, -0.0009), (0.015, -0.0028)]
HOOK = [(0.0, -0.012), (0.0, 0.012), (0.02, 0.0)]       # köşe çivisi (yalnız baş)
TH_CAM = math.atan2(math.sin(EL), -math.cos(EL))          # kameraya bakan açı (~142°)


def add_mark(bm, x, th, ang, shape, sc=1.0):
    p = egg_pt(x, th)
    n = egg_normal(x, th)
    tx = (egg_pt(x + 1e-3, th) - egg_pt(x - 1e-3, th)).normalized()
    tt = n.cross(tx).normalized()         # ekranda kabaca aşağı/yukarı
    ca, sa = math.cos(ang), math.sin(ang)
    vs = []
    for (u, w) in shape:
        uu, ww = (u * ca - w * sa) * sc, (u * sa + w * ca) * sc
        q = p + tx * uu + tt * ww
        # yüzeye yapıştır: yüzeyden biraz dışarı
        vs.append(bm.verts.new(q + n * 0.0025))
    bm.faces.new(vs)


def mark_list():
    """Süs çivi izleri: yatay sıralar (kayıt şeritleri), her 'işaret' 1-4 rastgele çivi. Okunur metin değildir."""
    r = rng(2024)
    marks = []       # (x, th, ang, shape, sc)
    rules = []       # (th) şerit çizgileri
    reg = math.radians(12.5)
    th_list = [TH_CAM + reg * k for k in range(-5, 5)]
    for k, th_c in enumerate(th_list):
        rules.append(th_c - reg / 2)
        x = -0.37 + 0.08 * abs(k - 4.5) / 5 + r.uniform(0, 0.03)
        while True:
            w = r.uniform(0.045, 0.075)
            if x + w > 0.37 - 0.08 * abs(k - 4.5) / 5:
                break
            kind = r.random()
            cx = x + w / 2
            dth = reg * 0.28
            rr = egg_r(cx)
            if kind < 0.3:        # yatay çiviler üst üste
                n_ = r.choice((1, 2, 2, 3))
                for j in range(n_):
                    marks.append((x + 0.004, th_c + (j - (n_ - 1) / 2) * dth * 0.9, 0.0, WEDGE, 0.85))
            elif kind < 0.55:     # dikey çiviler yan yana
                n_ = r.choice((1, 2, 3))
                for j in range(n_):
                    marks.append((x + 0.012 + j * 0.017, th_c + dth * 1.15, -math.pi / 2, WEDGE, 0.82))
            elif kind < 0.75:     # yatay + dikey
                marks.append((x + 0.002, th_c, 0.0, WEDGE, 0.8))
                marks.append((x + 0.04, th_c + dth * 1.1, -math.pi / 2, WEDGE, 0.8))
            elif kind < 0.9:      # köşe çivileri
                n_ = r.choice((1, 2))
                for j in range(n_):
                    marks.append((x + 0.012 + j * 0.022, th_c, math.pi, HOOK, 0.9))
            else:                 # çapraz
                marks.append((x + 0.004, th_c + dth * 0.7, -0.6, WEDGE, 0.8))
                marks.append((x + 0.004, th_c - dth * 0.7, 0.6, WEDGE, 0.8))
            x += w + r.uniform(0.008, 0.02)
    rules.append(th_list[-1] + reg / 2)
    return marks, rules


MARKS, RULES = mark_list()


def mark_obj(name, part):
    bm = bmesh.new()
    for (x, th, ang, shape, sc) in MARKS:
        xs = split_x(th)
        if part == 'sol' and x + 0.05 > xs - 0.006:
            continue
        if part == 'sag' and x < xs + 0.006:
            continue
        add_mark(bm, x, th, ang, shape, sc * 1.25)
    ob = bm_obj(name, bm, [M_WEDGE], smooth_shade=False, noline=True)
    # şerit çizgileri: ince, açık ton
    bm = bmesh.new()
    for th in RULES:
        xs = split_x(th)
        lo, hi = -0.38, 0.38
        if part == 'sol':
            hi = min(hi, xs - 0.008)
        if part == 'sag':
            lo = max(lo, xs + 0.008)
        n = 40
        prevp = None
        for i in range(n + 1):
            x = lo + (hi - lo) * i / n
            p = egg_pt(x, th) + egg_normal(x, th) * 0.002
            tt = egg_normal(x, th).cross(Vector((1, 0, 0))).normalized() * 0.0022
            if prevp is not None:
                q = [bm.verts.new(v) for v in (prevp[0] - prevp[1], p - tt, p + tt, prevp[0] + prevp[1])]
                bm.faces.new(q)
            prevp = (p, tt)
    bm.free()
    return (ob,)


for (part, host) in (('tam', egg), ('sol', half_l), ('sag', half_r)):
    for ob in mark_obj('izler_' + part, part):
        ob.parent = host

# çatlak: bütün kabın üstünde zikzak koyu çizgi, 13 karede ön yüzden çevreye büyür (Build)
bm = bmesh.new()
segn = 144
order = sorted(range(segn), key=lambda j: abs(((2 * math.pi * j / segn - TH_CAM + math.pi) % (2 * math.pi)) - math.pi))
pts = []
for j in range(segn + 1):
    th = 2 * math.pi * j / segn
    xs = split_x(th)
    pts.append((egg_pt(xs, th) + egg_normal(xs, th) * 0.003, egg_normal(xs, th)))
faces = []
for j in order:
    (pa, na), (pb, nb) = pts[j], pts[j + 1]
    d = (pb - pa).normalized()
    sa = d.cross(na).normalized() * 0.0065
    sb = d.cross(nb).normalized() * 0.0065
    q = [bm.verts.new(v) for v in (pa - sa, pb - sb, pb + sb, pa + sa)]
    bm.faces.new(q)
crack = bm_obj('catlak', bm, [M_CRACK], smooth_shade=False, noline=True)
crack.parent = egg
bd = crack.modifiers.new('buyu', 'BUILD')
bd.frame_start = F_CRACK
bd.frame_duration = 12
bd.use_random_order = False

# ---------------------------------------------------------------- kabın hareketi: titreme, açılma
# kap F_SPLIT karesinde de bütün kalır (yarılar kapalıyken çatlak bir kare incelip "sıçramasın"); yarılar bir sonraki karede
for f, hid in ((1, False), (F_SPLIT, False), (F_SPLIT + 1, True)):
    egg.hide_render = hid; egg.keyframe_insert('hide_render', frame=f)
    for ch in egg.children:
        ch.hide_render = hid; ch.keyframe_insert('hide_render', frame=f)
for ob in (half_l, half_r):
    for f, hid in ((1, True), (F_SPLIT, True), (F_SPLIT + 1, False)):
        ob.hide_render = hid; ob.keyframe_insert('hide_render', frame=f)
        for ch in ob.children:
            ch.hide_render = hid; ch.keyframe_insert('hide_render', frame=f)
for f in range(-2, F_SPLIT + 1):
    a = 0.0
    if f >= F_CRACK - 4:
        tt = f - (F_CRACK - 4)
        a = 0.022 * smooth(0, 10, tt) * math.sin(tt * 1.9)
    egg.rotation_euler = (a, 0.0, 0.0)
    egg.location = EGG_C
    egg.keyframe_insert('rotation_euler', frame=f)
    egg.keyframe_insert('location', frame=f)

SEP = 0.37


def half_pose(side, f):
    """side -1 sol, +1 sağ. Ayrılma, açık yüzün yukarı dönmesi, sönen sallanma; en alt nokta örtüde kalır."""
    tau = max(0.0, f - F_SPLIT)
    d = SEP * (1.0 - math.exp(-tau / 4.0))
    ph = math.radians(24) * (1.0 - math.exp(-tau / 5.0)) + math.radians(7) * math.exp(-tau / 9.0) * math.sin(tau * 0.55) * min(1.0, tau / 3)
    yaw = math.radians(9) * (1.0 - math.exp(-tau / 6.0))
    return d, side * ph, -side * yaw


_vl = [v.co.copy() for v in half_l.data.vertices]
_vr = [v.co.copy() for v in half_r.data.vertices]
for f in range(-2, N_FRAMES + 3):
    for (ob, side, vv) in ((half_l, -1, _vl), (half_r, 1, _vr)):
        d, ph, yw = half_pose(side, f)
        rot = Euler((0.0, ph, yw), 'XYZ')
        R3 = rot.to_matrix()
        mz = min((R3 @ v).z for v in vv[::3])
        loc = Vector((EGG_C.x + side * d, EGG_C.y, CLOTH_T - mz - 0.004))
        ob.location = loc
        ob.rotation_euler = rot
        ob.keyframe_insert('location', frame=f)
        ob.keyframe_insert('rotation_euler', frame=f)

# ---------------------------------------------------------------- 48 çakıl: kabın içinden dökülür, 8x6 diziye dizilir
PEB_R = 0.062
COL_GAP, ROW_GAP = 0.185, 0.235
GRID_X0 = EGG_C.x - COL_GAP * (GRID_C - 1) / 2
GRID_Y0 = -0.52                          # kaba en yakın sıra
SLOTS = [Vector((GRID_X0 + COL_GAP * c, GRID_Y0 - ROW_GAP * rr)) for rr in range(GRID_R) for c in range(GRID_C)]
assert len(SLOTS) == N_STONES


def pebble_mesh(name, seed, mat):
    r = rng(seed)
    bm = bmesh.new()
    blob(bm, Vector((0, 0, 0)), (PEB_R * r.uniform(0.95, 1.08), PEB_R * r.uniform(0.76, 0.86), PEB_R * r.uniform(0.55, 0.62)),
         subdiv=3, amp=0.08, seed=seed, nscale=1.2)
    ob = bm_obj(name, bm, [mat])
    ob.rotation_mode = 'QUATERNION'
    return ob


# yığın: kabın ortasında, örtü üstünde küçük bir tümsek (üstteki önce kalkar)
_hr = rng(77)
_cand = []
for layer, (rad, zl) in enumerate(((0.36, 0.0), (0.25, 0.065), (0.14, 0.13), (0.06, 0.19))):
    sp = 0.112
    for jy in range(-6, 7):
        for jx in range(-6, 7):
            px = (jx + 0.5 * (jy % 2) + 0.25 * layer) * sp
            py = jy * sp * 0.866
            rho = math.hypot(px, py)
            if rho > rad:
                continue
            _cand.append((layer, rho + _hr.uniform(0, 0.01),
                          Vector((EGG_C.x + px + _hr.uniform(-0.01, 0.01), EGG_C.y + py * 0.85 + _hr.uniform(-0.01, 0.01),
                                  CLOTH_T + PEB_R * 0.55 + zl + _hr.uniform(0, 0.012)))))
_cand.sort(key=lambda c: (c[0], c[1]))
HEAP = [c[2] for c in _cand[:N_STONES]]
assert len(HEAP) == N_STONES, len(_cand)
HEAP.sort(key=lambda p: -p.z)
# iç küme (kap kapalıyken; gizli): kabın içinde
INNER = [EGG_C + Vector((0, 0, EGG_R * 0.05)) + (h - Vector((EGG_C.x, EGG_C.y, CLOTH_T))) * Vector((0.55, 0.7, 0.9)) for h in HEAP]
# dizi yerleri: kaba yakından uzağa (sıra sıra), aynı sırada ortadan kenara
slot_order = sorted(range(N_STONES), key=lambda s: (s // GRID_C, abs(SLOTS[s].x - EGG_C.x) + 0.001 * (s % GRID_C)))
F_LAUNCH0 = F_SPLIT + 8
LAUNCH_GAP = 1.22
FLIGHT = 16
stones = []
for k in range(N_STONES):
    st = pebble_mesh('tas_%02d' % k, 3000 + k, M_PEBBLES[k % 3])
    stones.append(st)
    slot = SLOTS[slot_order[k]]
    t_launch = F_LAUNCH0 + k * LAUNCH_GAP
    drop_end = F_SPLIT + 4 + 0.08 * k
    q_start = Quaternion((0, 0, 1), rng(5000 + k).uniform(0, 6.28)) @ Quaternion((1, 0, 0), rng(5100 + k).uniform(-0.4, 0.4))
    q_land = Quaternion((0, 0, 1), rng(6000 + k).uniform(-0.3, 0.3))
    p_land = Vector((slot.x, slot.y, CLOTH_T + PEB_R * 0.55))
    prev_q = None
    for f in range(-2, N_FRAMES + 3):
        if f < F_SPLIT:
            loc, q = INNER[k], q_start
        elif f < t_launch:
            u = smooth(F_SPLIT, drop_end, f)
            loc = INNER[k].lerp(HEAP[k], u * u)
            q = q_start
        else:
            t = min(1.0, (f - t_launch) / FLIGHT)
            dist = (p_land.xy - HEAP[k].xy).length
            hgt = 0.12 + 0.22 * dist
            loc = HEAP[k].lerp(p_land, smoother(t) * 0.35 + t * 0.65) + Vector((0, 0, hgt * 4 * t * (1 - t)))
            q = q_start.slerp(q_land, smoother(t))
            if t < 1:
                q = Quaternion((1, 0, 0), 2.4 * math.sin(math.pi * t)) @ q
            else:
                dt = f - t_launch - FLIGHT
                loc = p_land + Vector((0, 0, 0.016 * math.exp(-dt / 2.0) * abs(math.sin(dt * 1.4))))
        if prev_q is not None and q.dot(prev_q) < 0:
            q = -q
        prev_q = q
        st.location = loc
        st.rotation_quaternion = q
        st.keyframe_insert('location', frame=f)
        st.keyframe_insert('rotation_quaternion', frame=f)
    for f, hid in ((1, True), (F_SPLIT - 1, True), (F_SPLIT, False)):
        st.hide_render = hid; st.keyframe_insert('hide_render', frame=f)
LAST_LAND = F_LAUNCH0 + (N_STONES - 1) * LAUNCH_GAP + FLIGHT
print('son taş iner: kare %.1f (%.2f sn), yerleşir ~%.2f sn' % (LAST_LAND, (LAST_LAND - 1) / FPS, (LAST_LAND + 6 - 1) / FPS))

# ---------------------------------------------------------------- dünya (ışık yok)
world = bpy.data.worlds.new('dunya')
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs['Color'].default_value = (*s2l((0.86, 0.68, 0.34)), 1)
bg.inputs['Strength'].default_value = 1.0

# ---------------------------------------------------------------- kamera: ortografik, yavaş süzülme (geniş -> kap)
cam_data = bpy.data.cameras.new('kamera')
cam_data.type = 'ORTHO'
cam_data.clip_start = 0.05
cam_data.clip_end = 200.0
cam = link(bpy.data.objects.new('kamera', cam_data))
scene.camera = cam
cam.rotation_mode = 'QUATERNION'
CAM_Q = (-VIEW).to_track_quat('Z', 'Y')
CAM_DIST = 40.0
X_W, V_W, S_W = -0.62, 0.62, 7.2           # geniş: pencere (sürü, kentin evleri), kadeh, kap
X_C, V_C, S_C = -0.30, 0.10, 2.75          # yakın: kap kahraman (~%34 genişlik), sol-orta
X_E, V_E, S_E = -0.12, -0.25, 4.45         # son: açılmış kap ve 48 taşlık dizi, sol-orta
F_C0, F_C1 = 430, 458                      # yakın planda bekleme (çatlak bu sırada)
F_E = 566                                  # geri çekilme bitişi (taşlar yerleşirken)
ORTHO = []


def cam_state(f):
    if f <= F_C0:
        e = smoother((f - 1) / (F_C0 - 1))
        a, b = (X_W, V_W, S_W), (X_C, V_C, S_C)
        # yakın plan içinde çok hafif süzülme sürsün
    elif f <= F_C1:
        e = (f - F_C0) / (F_C1 - F_C0)
        a, b = (X_C, V_C, S_C), (X_C + 0.02, V_C - 0.01, S_C * 0.985)
    else:
        e = smoother((f - F_C1) / (F_E - F_C1))
        a, b = (X_C + 0.02, V_C - 0.01, S_C * 0.985), (X_E, V_E, S_E)
    x = a[0] + (b[0] - a[0]) * e
    v = a[1] + (b[1] - a[1]) * e
    sc = math.exp(math.log(a[2]) * (1 - e) + math.log(b[2]) * e)
    return x, v, sc


for f in range(-2, N_FRAMES + 3):
    x, v, sc = cam_state(f)
    cam.location = scr(x, v) - VIEW * CAM_DIST
    cam.rotation_quaternion = CAM_Q
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_quaternion', frame=f)
    cam_data.ortho_scale = sc
    cam_data.keyframe_insert('ortho_scale', frame=f)
    ORTHO.append((f, sc))


# ---------------------------------------------------------------- pervaz (onaylı tarzla aynı)
def frame_band(bm, x0, y0, t, mi=0):
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
frame_band(bm, HX + 0.02, HY + 0.02, 0.028, 0)
for (ins, th, mi) in lay[1:]:
    frame_band(bm, HX - ins, HY - ins, th, mi)
mid = 0.0105 + 0.0125 / 2
step = 0.022
for side in range(4):
    L_ = 2 * (HX - mid) if side in (0, 1) else 2 * (HY - mid)
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
me = bpy.data.meshes.new('pervaz_m')
bm.to_mesh(me); bm.free()
for m in (M_CREAM, M_BGOLD, M_LAPIS, M_VERM):
    me.materials.append(m)
bord = link(bpy.data.objects.new('pervaz_m', me), noline=True)
bord.parent = border
for f, sc in ORTHO:
    border.scale = (sc, sc, sc)
    border.keyframe_insert('scale', frame=f)

# ---------------------------------------------------------------- render ayarları
R = scene.render
R.engine = 'CYCLES'
C = scene.cycles
C.device = 'CPU'
C.samples = A.ornek
C.use_adaptive_sampling = True
C.adaptive_threshold = 0.01
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
C.pixel_filter_type = 'BLACKMAN_HARRIS'
C.filter_width = 1.4
R.resolution_x = A.w
R.resolution_y = A.h
R.resolution_percentage = 100
R.use_motion_blur = False
R.use_persistent_data = True
vs_ = scene.view_settings
vs_.view_transform = 'Standard'
vs_.look = 'None'
vs_.exposure = 0.0
vs_.gamma = 1.0

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
    ls.select_edge_mark = False
    ls.select_by_collection = True
    ls.collection = NOLINE
    ls.collection_negation = 'EXCLUSIVE'
    if ls.linestyle is None:
        ls.linestyle = bpy.data.linestyles.new('kontur_stil')
    st_ = ls.linestyle
    st_.color = s2l(SEPIA)
    base_t = max(1.1, 1.9 * A.h / 1080)
    st_.thickness = base_t
    st_.thickness_position = 'CENTER'
    st_.caps = 'ROUND'
    cal = st_.thickness_modifiers.new('kalem', 'CALLIGRAPHY')
    cal.orientation = math.radians(50)
    cal.thickness_min = base_t * 0.55
    cal.thickness_max = base_t * 1.25
    cal.blend = 'MIX'
    st_.geometry_modifiers.new('ornek', 'SAMPLING').sampling = 2.0

from bpy_extras.object_utils import world_to_camera_view
print('TAS SAYISI', len([o for o in bpy.data.objects if o.name.startswith('tas_')]))
print('IZ SAYISI', len(MARKS))
for _f in (1, 430, 460, 520, 566, 609):
    scene.frame_set(_f)
    pts_ = [('kap', EGG_C + Vector((0, 0, 0.3))), ('kap_sol_uc', EGG_C + Vector((-EGG_A - SEP, 0, 0.2))),
            ('kap_sag_uc', EGG_C + Vector((EGG_A + SEP, 0, 0.2))),
            ('dizi_arka_sol', SLOTS[0].to_3d()), ('dizi_on_sag', SLOTS[-1].to_3d()),
            ('pencere_sol_alt', Vector((WIN_X0, WALL_Y0, WIN_Z0))), ('pencere_sag_ust', Vector((WIN_X1, WALL_Y0, WIN_Z1))),
            ('sirt', on_crest(-1.6)), ('kadeh_ust', POT_C + Vector((0, 0, 1.4))), ('ortu_sag_on', Vector((CLOTH_X1, CLOTH_Y0, 0)))]
    for _nm, _p in pts_:
        _c = world_to_camera_view(scene, cam, _p)
        print('KADRAJ f%d %-16s x=%.2f y(ust)=%.2f' % (_f, _nm, _c.x, 1 - _c.y))
    for (root, bob, head, legs, graze, i) in animals[:7:3]:
        _c = world_to_camera_view(scene, cam, root.matrix_world.to_translation())
        print('KADRAJ f%d hayvan%d         x=%.2f y(ust)=%.2f' % (_f, i, _c.x, 1 - _c.y))
print('sahne kuruldu: %.1f sn' % (time.time() - T_START), flush=True)
os.makedirs(A.cikti, exist_ok=True)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(A.cikti), 'nuzi.blend'))

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
    bas, son = A.bas, A.son
    if A.harita:
        # iş akışı kareleri 1..harita (300) aralığında böler; bunu 1..609'a eşle (bitişik, örtüşmesiz)
        bas = (bas - 1) * N_FRAMES // A.harita + 1
        son = son * N_FRAMES // A.harita
    print('PARCA %d-%d' % (bas, son), flush=True)
    scene.frame_start = bas
    scene.frame_end = son
    R.filepath = os.path.join(os.path.abspath(A.cikti), 'k_')
    bpy.ops.render.render(animation=True)
print('BITTI toplam %.1f sn' % (time.time() - T_START))
