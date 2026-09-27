# Math with Zirek · KARAKALEM: krem kâğıt üstünde canlanan kurşun kalem çizim.
# Girdi: Cycles veri geçişleri (sahne.py). Çıktı: sRGB kare.
# Kontur (derinlik/normal/kimlik kenarı, titrek el, kâğıt dişine takılan grafit), tarama (üç yön, gölgeye göre),
# grafit tozu, tek sıcak vurgu rengi (kese soluk, çakıllar dolgun renkli kalem), parıltı: sıcak dört kollu yıldız.
# "Kaynama": çizgiler 3 karede bir yeniden çizilmiş gibi hafifçe oynar (el çizimi canlandırma hissi).
import numpy as np
import cizim_ortak as co

F32 = np.float32
KAGIT = np.array([0.955, 0.925, 0.855], F32)       # krem kâğıt
GRAFIT = np.array([0.20, 0.19, 0.20], F32)         # yumuşak kurşun (hafif gümüşi)
VURGU_KESE = np.array([0.80, 0.47, 0.30], F32)     # pişmiş toprak, soluk sürülür
VURGU_CAKIL = np.array([0.91, 0.52, 0.16], F32)    # sıcak turuncu-aşı, dolgun
PARILTI = np.array([1.0, 0.80, 0.36], F32)

# kimlik -> (ton koyuluğu 0..1, vurgu türü 0 yok / 1 kese / 2 çakıl, çizgi ağırlığı, gölge taraması çarpanı)
LUT = {
    0: (0.00, 0, 0.0, 0.0),   # gök
    1: (0.04, 0, 0.8, 0.62),  # çim zemin
    2: (0.30, 0, 0.8, 0.8),   # ot
    3: (0.10, 0, 1.0, 0.72),  # duvar taşı
    4: (0.10, 0, 1.0, 0.75),  # kapı direği
    5: (0.00, 0, 1.0, 0.62),  # yün
    6: (0.80, 0, 1.0, 1.0),   # yüz, bacak
    7: (0.00, 0, 0.7, 0.2),   # göz akı
    8: (0.97, 0, 0.6, 1.0),   # göz bebeği
    9: (0.45, 0, 1.0, 1.0),   # tahta
    10: (0.04, 1, 1.0, 0.85),  # kese
    11: (0.30, 0, 0.9, 0.9),   # ip
    12: (0.05, 2, 1.0, 0.55),  # çakıl
    13: (0.05, 2, 1.0, 0.55),  # son çakıl
    14: (0.22, 0, 1.0, 0.9),   # yassı taş
    15: (0.03, 0, 0.45, 0.35),  # uzak tepe
    16: (0.06, 0, 0.6, 0.5),   # yakın tepe
    17: (0.40, 0, 0.9, 1.0),   # ağaç yaprak
    18: (0.0, 0, 0.5, 0.5),
}
_N = 32
T_TON = np.zeros(_N, F32); T_VUR = np.zeros(_N, np.int32); T_CIZ = np.zeros(_N, F32); T_GOL = np.zeros(_N, F32)
for k, (a, b, c, d) in LUT.items():
    T_TON[k], T_VUR[k], T_CIZ[k], T_GOL[k] = a, b, c, d

_CACHE = {}


def _statik(h, w):
    """Kâğıt dokusu ve diş (kare boyunca sabit: kâğıt oynamaz)."""
    key = (h, w)
    if key in _CACHE:
        return _CACHE[key]
    s = w / 1920.0
    lif = co.vnoise(h, w, 3.0 * s, 11, octaves=2)
    genis = co.vnoise(h, w, 260 * s, 12, octaves=3)
    dis = co.vnoise(h, w, 1.6 * s + 0.4, 13, octaves=2)          # kâğıt dişi (grafit tepelere takılır)
    dis = (dis - dis.mean()) / (dis.std() + 1e-6)
    ton = 1.0 + 0.018 * (genis - 0.5) + 0.02 * (lif - 0.5)
    kagit = KAGIT[None, None, :] * ton[..., None]
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    _CACHE[key] = (kagit.astype(F32), dis.astype(F32), yy, xx, s)
    return _CACHE[key]


def _tarama(xx, yy, aci, aralik, kalinlik, faz, titrek, seed, s, kesik=0.8):
    """Ekran uzayında el taraması: aci derece, aralik px. Döndürür 0..1 çizgi örtüsü.
    kalinlik: (h,w) px cinsinden çizgi kalınlığı (koyuluğa göre)."""
    a = np.radians(aci)
    ca, sa = np.cos(a), np.sin(a)
    u = (xx * ca + yy * sa) / aralik + faz
    v = (-xx * sa + yy * ca)
    u = u + titrek
    idx = np.floor(u)
    fr = u - idx - 0.5
    d = np.abs(fr) * aralik
    # çizgi başına rastgele: parlaklık, kesik parçalar
    hsh = np.sin(idx * 12.9898 + seed * 78.233) * 43758.5453
    hsh = hsh - np.floor(hsh)
    L = 70.0 * s + 50.0 * s * hsh
    seg = (v / L + hsh * 7.0)
    segf = seg - np.floor(seg)
    uc = np.minimum(segf, kesik - segf)
    parca = np.where(segf < kesik, co.smoothstep(0.0, 0.08, uc), 0.0)
    cizgi = np.clip((kalinlik * 0.5 - d) / (0.9 * s + 0.35) + 0.5, 0.0, 1.0)
    return cizgi * parca * (0.75 + 0.25 * hsh)


def isle(P, meta, f):
    dd = P['DiffDir']; dc = P['DiffCol']; n = P['Normal']; z = P['Depth']
    iob = P['IndexOB']; ima = P['IndexMA']
    ao = P.get('AO', None)
    h, w = z.shape
    kagit, dis, yy, xx, s = _statik(h, w)
    bg = (iob < 0.5) & (z > 1e5)
    kaynama = f // 3                                  # 10 çizim/sn
    rs = np.random.RandomState(1000 + kaynama)

    cat = np.clip(np.rint(ima).astype(np.int32), 0, _N - 1)
    ton = co.blur3(T_TON[cat]); vur = T_VUR[cat]; cizw = co.blur3(T_CIZ[cat]); golk = co.blur3(T_GOL[cat])

    # ışık: güneş (gölgeli) + gökyüzü (normal.z ve AO ile)
    isik, aov = co.isik(P, s)
    isik = np.where(bg, 1.0, isik)

    # uzaklık: uzak çizgiler ve tonlar açılır (hava perspektifi); yakın planda odak dışı açılır
    odak = meta.get('odak', 4.0)
    zz = np.where(bg, 1e3, z)
    uzak = np.clip(1.0 - (zz - odak * 1.6) / (odak * 3.0), 0.25, 1.0)
    yakin = meta.get('yakin', 0.0)
    if yakin > 0:
        arka = np.clip(1.0 - (zz - odak * 1.25) / (odak * 0.9), 0.35, 1.0)
        uzak = uzak * (1 - yakin) + arka * yakin

    # koyuluk: malzeme tonu + gölge
    golge = np.clip(1.0 - isik, 0.0, 1.0) * golk
    D = 1.0 - (1.0 - ton) * (1.0 - 0.9 * golge)
    D = D * uzak

    # titrek el: ortak yer değiştirme alanı (kaynama başına yeni)
    tx = (co.vnoise(h, w, 90 * s, 300 + kaynama, octaves=2) - 0.5) * 3.2 * s
    ty = (co.vnoise(h, w, 90 * s, 400 + kaynama, octaves=2) - 0.5) * 3.2 * s
    tit = (co.vnoise(h, w, 45 * s, 500 + kaynama, octaves=2) - 0.5) * 0.35

    # tarama katmanları
    ag = np.zeros((h, w), F32)
    for (aci, esik, aralik, seed) in ((52.0, 0.20, 6.2, 1), (-28.0, 0.46, 6.8, 2), (82.0, 0.70, 7.4, 3)):
        m = co.smoothstep(esik, esik + 0.1, D)
        if not np.any(m > 0.01):
            continue
        kal = (0.9 + 1.6 * np.clip((D - esik) / 0.5, 0, 1)) * s + 0.3
        # kaynama hafif: açı ±1°, çizgiler aralığın en çok çeyreği kadar kayar (titreşim yormasın)
        t = _tarama(xx, yy, aci + rs.uniform(-1, 1), aralik * s + 0.8, kal, rs.uniform(0, 0.25), tit, seed + 10 * kaynama, s)
        ag = 1 - (1 - ag) * (1 - 0.82 * m * t)
    # grafit tozu (parmakla yayılmış ton): diş tepelerinde birikir
    toz = np.clip(D * 0.55 - 0.03, 0, 1)
    tozdis = np.clip(toz * (1.0 + 0.7 * dis), 0, 1)
    ag = 1 - (1 - ag) * (1 - 0.55 * tozdis)

    # kontur
    sil, kv, idd = co.kenarlar(z, n, iob, bg, d_esik=0.010, n_esik=0.20)
    ln = np.maximum.reduce([sil, 0.65 * kv, 0.85 * idd])
    ln0 = ln
    ln = co.remap(ln0, tx, ty)                                   # el titremesi
    # eskiz: aynı çizginin ikinci, hafifçe kayık ve soluk bir geçişi
    tx2 = (co.vnoise(h, w, 70 * s, 700 + kaynama, octaves=2) - 0.5) * 4.0 * s
    ty2 = (co.vnoise(h, w, 70 * s, 800 + kaynama, octaves=2) - 0.5) * 4.0 * s
    ln = np.maximum(ln, 0.45 * co.remap(ln0, tx2, ty2))
    ln = co.blur3(co.dilate(ln, 1) * 0.6 + ln * 0.4) if s > 0.7 else co.blur3(ln)
    ln = ln * cizw * np.maximum(uzak, 0.3)
    basinc = 0.72 + 0.28 * co.vnoise(h, w, 30 * s, 600 + kaynama)
    ln = np.clip(ln * basinc * (1.0 + 0.35 * np.clip(dis, -1.5, 1.5)), 0, 1)
    ag = 1 - (1 - ag) * (1 - 0.92 * ln)

    # vurgu rengi (renkli kalem): kese soluk, çakıllar dolgun; ışıkta açık, gölgede koyu
    out = kagit.copy()
    renk = np.zeros((h, w, 3), F32)
    ra = np.zeros((h, w), F32)
    for tur, col, guc in ((1, VURGU_KESE, 0.50), (2, VURGU_CAKIL, 0.95)):
        m = co.blur3((vur == tur).astype(F32))
        if not np.any(m > 0):
            continue
        tex = _tarama(xx, yy, 38.0, 3.2 * s + 0.6, np.full((h, w), 2.6 * s + 0.6, F32), 0.3, tit * 0.5, 90 + tur, s, kesik=0.93)
        a = m * guc * (0.72 + 0.28 * tex) * (0.8 + 0.2 * (1 - np.clip(dis, 0, 1) * 0.5)) * (0.75 + 0.25 * uzak)
        a = np.clip(a, 0, 1)
        renk += col[None, None, :] * a[..., None]
        ra += a
    ra = np.clip(ra, 0, 1)
    renk = np.where(ra[..., None] > 1e-4, renk / np.maximum(ra[..., None], 1e-4), 0)
    out = out * (1 - ra[..., None]) + (out * renk / KAGIT[None, None, :]) * ra[..., None]

    # grafiti bindir (çoğaltma karışımı)
    out = out * (1 - ag[..., None]) + GRAFIT[None, None, :] * ag[..., None] * (out / KAGIT[None, None, :]) ** 0.3

    # parıltı: sıcak, yumuşak dört kollu yıldız + hale; altındaki grafit silinmiş gibi açılır
    gx, gy, gr, gs = meta.get('parilti', [0, 0, 0, 0])
    if gs > 0.01:
        dx = xx - gx
        dy = yy - gy
        r = np.sqrt(dx * dx + dy * dy)
        R = max(gr, 6.0 * s)
        hale = np.exp(-(r / (1.6 * R)) ** 2) * 0.55 * gs
        silgi = np.exp(-(r / (0.55 * R)) ** 2) * 0.8 * gs
        out = out + (kagit * 1.04 - out) * silgi[..., None]
        out = out * (1 - hale[..., None]) + (out * PARILTI / KAGIT) * hale[..., None] * 1.0
        L = 2.1 * R * (0.85 + 0.15 * gs)
        wdt = 0.09 * R + 0.8 * s
        kol = np.zeros((h, w), F32)
        for (ux, uy) in ((1, 0), (0, 1)):
            al = np.abs(dx * ux + dy * uy)
            pr = np.abs(-dx * uy + dy * ux)
            inc = wdt * np.clip(1 - al / L, 0, 1) ** 1.6
            kol = np.maximum(kol, np.clip((inc - pr) / (0.9 * s + 0.4) + 0.5, 0, 1) * (al < L))
        kol = np.maximum(kol, np.clip((0.22 * R - r) / (0.9 * s + 0.4) + 0.5, 0, 1))
        kol *= gs
        yildiz = np.array([1.0, 0.93, 0.70], F32)
        out = out * (1 - kol[..., None]) + yildiz[None, None, :] * kol[..., None]
        # ince kurşun kenar (çizilmiş yıldız): kolun biraz dışında
        kenar = np.clip(co.dilate(kol, max(1, int(1.2 * s))) - kol, 0, 1) * 0.45 * gs
        out = out * (1 - kenar[..., None]) + (GRAFIT * 1.6)[None, None, :] * kenar[..., None]

    return np.clip(out, 0, 1)
