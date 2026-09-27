# Math with Zirek · RİSOGRAF: üç spot mürekkep (sıcak kırmızı, camgöbeği/teal, hardal-aşı) krem kâğıda basılmış gibi.
# Girdi: Cycles veri geçişleri (../karakalem/sahne.py). Her mürekkep ayrı kalıp: kendi açısında yarım ton noktaları,
# hafif kayık baskı (misregistration), tanecikli mürekkep, üst üste binince çoğaltma karışımı (kırmızı+teal = koyu,
# teal+hardal = yeşil). Anahtar çizgi teal kalıbında. Parıltı: kâğıt beyazı dört kollu yıldız + hardal hale.
import numpy as np
import cizim_ortak as co

F32 = np.float32
KAGIT = np.array([0.960, 0.935, 0.880], F32)
# mürekkep süzgeç renkleri (çoğaltma): Riso tonlarına yakın
MUREKKEP = np.array([[0.965, 0.345, 0.330],     # sıcak kırmızı
                     [0.000, 0.520, 0.560],     # teal
                     [0.985, 0.720, 0.130]], F32)   # hardal / aşı
ACI = (15.0, 75.0, 0.0)                          # kalıp açıları (derece)
KAYMA = ((2.4, -1.3), (-1.8, 1.5), (0.9, 2.2))   # kayık baskı, 1080p piksel

# kimlik -> (ışıkta [kırmızı, teal, hardal], gölgede [...])
LUT = {
    0: ((0, 0, 0), (0, 0, 0)),
    1: ((0.00, 0.30, 0.34), (0.08, 0.68, 0.42)),     # çim
    2: ((0.00, 0.60, 0.60), (0.15, 0.95, 0.70)),     # ot
    3: ((0.12, 0.24, 0.10), (0.30, 0.66, 0.12)),     # duvar taşı
    4: ((0.12, 0.26, 0.10), (0.30, 0.68, 0.12)),     # direk
    5: ((0.00, 0.00, 0.06), (0.14, 0.30, 0.10)),     # yün
    6: ((0.80, 0.95, 0.15), (0.85, 1.00, 0.20)),     # yüz, bacak
    7: ((0.00, 0.00, 0.00), (0.05, 0.10, 0.00)),     # göz akı
    8: ((1.00, 1.00, 0.00), (1.00, 1.00, 0.00)),     # bebek
    9: ((0.50, 0.40, 0.60), (0.75, 0.75, 0.70)),     # tahta
    10: ((0.90, 0.00, 0.10), (1.00, 0.45, 0.15)),    # kese: kırmızı
    11: ((0.15, 0.10, 0.70), (0.40, 0.40, 0.80)),    # ip
    12: ((0.12, 0.00, 1.00), (0.40, 0.15, 1.00)),    # çakıl: hardal (kırmızı keseden ayrılsın)
    13: ((0.12, 0.00, 1.00), (0.40, 0.15, 1.00)),
    14: ((0.00, 0.42, 0.02), (0.15, 0.80, 0.05)),    # yassı taş: teal (çakılla karşıt)
    15: ((0.22, 0.06, 0.32), (0.30, 0.15, 0.38)),    # uzak tepe: sıcak pus
    16: ((0.05, 0.30, 0.40), (0.12, 0.50, 0.45)),    # yakın tepe
    17: ((0.05, 0.70, 0.50), (0.25, 1.00, 0.60)),    # ağaç
    18: ((0.1, 0.0, 0.8), (0.2, 0.2, 0.8)),
}
_N = 32
T_ISIK = np.zeros((_N, 3), F32)
T_GOL = np.zeros((_N, 3), F32)
for k, (a, b) in LUT.items():
    T_ISIK[k] = a
    T_GOL[k] = b

_C = {}


def _statik(h, w):
    if (h, w) in _C:
        return _C[(h, w)]
    s = w / 1920.0
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    lif = co.vnoise(h, w, 2.5 * s + 0.5, 21, octaves=2)
    genis = co.vnoise(h, w, 300 * s, 22, octaves=3)
    kagit = KAGIT[None, None, :] * (1.0 + 0.02 * (genis - 0.5) + 0.025 * (lif - 0.5))[..., None]
    _C[(h, w)] = (kagit.astype(F32), yy, xx, s)
    return _C[(h, w)]


def _yarimton(cov, xx, yy, aci, hucre):
    a = np.radians(aci)
    u = (xx * np.cos(a) + yy * np.sin(a)) / hucre
    v = (-xx * np.sin(a) + yy * np.cos(a)) / hucre
    t = 0.5 - 0.25 * (np.cos(2 * np.pi * u) + np.cos(2 * np.pi * v))
    fw = 0.55 * np.pi / hucre
    return np.clip((cov - t) / fw + 0.5, 0.0, 1.0)


def isle(P, meta, f):
    dd = P['DiffDir']; dc = P['DiffCol']; n = P['Normal']; z = P['Depth']
    iob = P['IndexOB']; ima = P['IndexMA']
    ao = P.get('AO', None)
    h, w = z.shape
    kagit, yy, xx, s = _statik(h, w)
    bg = (iob < 0.5) & (z > 1e5)
    baski = f // 2                                   # her iki karede bir "yeni baskı"
    rs = np.random.RandomState(7000 + baski)

    cat = np.clip(np.rint(ima).astype(np.int32), 0, _N - 1)
    isik, aov = co.isik(P, s)
    g = np.clip((0.8 - isik) / 0.5, 0.0, 1.0)
    g = co.smoothstep(0.0, 1.0, g)
    cov = T_ISIK[cat] + (T_GOL[cat] - T_ISIK[cat]) * g[..., None]
    cov = np.stack([co.blur3(cov[..., k]) for k in range(3)], axis=-1)

    # gök: yukarıda soluk hardal, ufka doğru kırmızı-hardal akşam
    ty = (yy / h)
    gk = np.stack([0.08 + 0.40 * co.smoothstep(0.05, 0.6, ty), np.zeros_like(ty), 0.22 + 0.55 * co.smoothstep(0.0, 0.55, ty)], -1)
    cov = np.where(bg[..., None], gk, cov)

    # uzak planı hafiflet
    odak = meta.get('odak', 4.0)
    zz = np.where(bg, 1e3, z)
    uzak = np.clip(1.0 - (zz - odak * 1.8) / (odak * 3.5), 0.45, 1.0)
    cov = np.where(bg[..., None], cov, cov * uzak[..., None])

    # parıltı: yıldızın içi kâğıt beyazı (mürekkep yok), çevresinde hardal-kırmızı hale
    gx, gy, gr, gs = meta.get('parilti', [0, 0, 0, 0])
    yildiz = None
    if gs > 0.01:
        dx = xx - gx; dy = yy - gy
        r = np.sqrt(dx * dx + dy * dy)
        R = max(gr, 6.0 * s)
        hale = np.exp(-(r / (1.7 * R)) ** 2) * gs
        cov[..., 2] = np.maximum(cov[..., 2], 0.95 * hale)
        cov[..., 0] = cov[..., 0] * (1 - 0.6 * hale) + 0.30 * hale
        cov[..., 1] = cov[..., 1] * (1 - hale)
        L = 2.2 * R * (0.85 + 0.15 * gs)
        wdt = 0.10 * R + 0.8 * s
        kol = np.zeros((h, w), F32)
        for (ux, uy) in ((1, 0), (0, 1)):
            al = np.abs(dx * ux + dy * uy)
            pr = np.abs(-dx * uy + dy * ux)
            inc = wdt * np.clip(1 - al / L, 0, 1) ** 1.6
            kol = np.maximum(kol, np.clip((inc - pr) / (0.8 * s + 0.4) + 0.5, 0, 1) * (al < L))
        kol = np.maximum(kol, np.clip((0.24 * R - r) / (0.8 * s + 0.4) + 0.5, 0, 1))
        yildiz = kol * gs

    # anahtar çizgi (teal kalıbında)
    sil, kv, idd = co.kenarlar(z, n, iob, bg, d_esik=0.012, n_esik=0.24)
    ln = np.maximum.reduce([sil, 0.5 * kv, 0.8 * idd]) * np.maximum(uzak, 0.5)
    ln = co.blur3(ln)
    ln = np.where(bg, 0, ln)

    hucre = 6.5 * s + 1.2
    out = kagit.copy()
    for k in range(3):
        c = cov[..., k]
        ox, oy = KAYMA[k]
        jx, jy = rs.uniform(-0.5, 0.5, 2)
        c = co.remap(c, -(ox + jx) * s, -(oy + jy) * s)
        a = _yarimton(np.clip(c, 0, 1), xx, yy, ACI[k], hucre)
        if k == 1:
            l2 = co.remap(ln, -(ox + jx) * s, -(oy + jy) * s)
            a = np.maximum(a, np.clip(l2 * 1.1, 0, 1))
        if yildiz is not None:
            y2 = co.remap(yildiz, -(ox + jx) * s, -(oy + jy) * s)
            a = a * (1 - y2)
        # mürekkep tanesi: geniş yoğunluk dalgası + küçük boşluklar
        yog = 0.86 + 0.14 * co.vnoise(h, w, 70 * s, 100 * k + baski, octaves=2)
        bos = co.vnoise(h, w, 1.3 * s + 0.4, 200 * k + baski, octaves=1)
        bos = co.smoothstep(0.72, 0.9, bos)
        a = a * yog * (1 - 0.75 * bos)
        T = 1.0 - a[..., None] * (1.0 - MUREKKEP[k][None, None, :])
        out = out * T
    return np.clip(out, 0, 1)
