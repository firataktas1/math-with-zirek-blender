# Math with Zirek · çizim tarzları (karakalem, risograf) için ortak görüntü araçları.
# Blender'ın kendi Python'unda çalışır (numpy + OpenImageIO Blender'la gelir). scipy gerekmez.
import numpy as np

F32 = np.float32


# ---------------------------------------------------------------- EXR okuma / PNG yazma
def exr_oku(yol):
    """Blender çok katmanlı EXR'yi okur: {'DiffDir': (h,w,3), 'Depth': (h,w), ...}."""
    import OpenImageIO as oiio
    inp = oiio.ImageInput.open(yol)
    if inp is None:
        raise RuntimeError('EXR açılamadı: ' + yol + ' ' + oiio.geterror())
    spec = inp.spec()
    names = list(spec.channelnames)
    data = inp.read_image(0, 0, 0, spec.nchannels, 'float')
    inp.close()
    data = np.asarray(data, dtype=F32).reshape(spec.height, spec.width, spec.nchannels)
    out = {}
    groups = {}
    for k, n in enumerate(names):
        parts = n.split('.')
        if len(parts) >= 2:
            pas, comp = parts[-2], parts[-1]
        else:
            pas, comp = n, n
        groups.setdefault(pas, []).append((comp, k))
    order = {'R': 0, 'G': 1, 'B': 2, 'A': 3, 'X': 0, 'Y': 1, 'Z': 2, 'V': 0}
    for pas, lst in groups.items():
        lst.sort(key=lambda t: order.get(t[0], 9))
        if len(lst) == 1:
            out[pas] = data[:, :, lst[0][1]].copy()
        else:
            out[pas] = np.stack([data[:, :, k] for (_, k) in lst], axis=-1)
    return out


def png_yaz(yol, rgb):
    """rgb: (h,w,3) float 0..1 (sRGB değerleri)."""
    import OpenImageIO as oiio
    a = np.ascontiguousarray(np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8))
    h, w = a.shape[:2]
    out = oiio.ImageOutput.create(yol)
    spec = oiio.ImageSpec(w, h, 3, 'uint8')
    out.open(yol, spec)
    out.write_image(a)
    out.close()


# ---------------------------------------------------------------- temel işlemler
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _box1(a, r, axis):
    if r <= 0:
        return a
    k = 2 * r + 1
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    p = np.pad(a, pad, mode='edge')
    c = np.cumsum(p, axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(k, k + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / k).astype(F32)


def blur(a, r):
    """Yaklaşık Gauss bulanıklığı (3 kutu geçişi), r piksel."""
    r = int(round(r))
    if r <= 0:
        return a
    for _ in range(3):
        a = _box1(a, r, 0)
        a = _box1(a, r, 1)
    return a


def blur3(a):
    """1-2-1 çekirdek (yarım piksellik yumuşatma)."""
    p = np.pad(a, [(1, 1), (1, 1)] + [(0, 0)] * (a.ndim - 2), mode='edge')
    v = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]
    return (0.25 * v[:, :-2] + 0.5 * v[:, 1:-1] + 0.25 * v[:, 2:]).astype(F32)


def dilate(a, r=1):
    """Kare en-büyük süzgeç (r piksel)."""
    out = a.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            out = np.maximum(out, shift(a, dx, dy))
    return out


def shift(a, dx, dy):
    """Tam sayı kaydırma, kenar tekrarı. Sonuç[y,x] = a[y-dy, x-dx]."""
    h, w = a.shape[:2]
    ys = np.clip(np.arange(h) - dy, 0, h - 1)
    xs = np.clip(np.arange(w) - dx, 0, w - 1)
    return a[ys][:, xs]


def remap(a, dx, dy):
    """Çift doğrusal örnekleme: sonuç[y,x] = a[y+dy, x+dx] (dx,dy alan dizileri ya da sayılar)."""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    sx = np.clip(xx + dx, 0, w - 1.001)
    sy = np.clip(yy + dy, 0, h - 1.001)
    x0 = sx.astype(np.int32)
    y0 = sy.astype(np.int32)
    fx = sx - x0
    fy = sy - y0
    if a.ndim == 3:
        fx = fx[..., None]
        fy = fy[..., None]
    a00 = a[y0, x0]
    a01 = a[y0, x0 + 1]
    a10 = a[y0 + 1, x0]
    a11 = a[y0 + 1, x0 + 1]
    return ((a00 * (1 - fx) + a01 * fx) * (1 - fy) + (a10 * (1 - fx) + a11 * fx) * fy).astype(F32)


def vnoise(h, w, cell, seed, octaves=1, gain=0.5):
    """Değer gürültüsü 0..1, hücre boyu piksel. Sabit tohum."""
    rs = np.random.RandomState(seed & 0x7fffffff)
    tot = np.zeros((h, w), F32)
    amp, norm = 1.0, 0.0
    c = float(cell)
    for o in range(octaves):
        gh, gw = int(h / c) + 3, int(w / c) + 3
        g = rs.rand(gh, gw).astype(F32)
        oy, ox = rs.rand() * 1.0, rs.rand() * 1.0
        y = np.arange(h, dtype=F32) / c + oy
        x = np.arange(w, dtype=F32) / c + ox
        y0 = y.astype(np.int32)
        x0 = x.astype(np.int32)
        fy = y - y0
        fx = x - x0
        fy = (fy * fy * (3 - 2 * fy))[:, None]
        fx = (fx * fx * (3 - 2 * fx))[None, :]
        g00 = g[y0][:, x0]
        g01 = g[y0][:, x0 + 1]
        g10 = g[y0 + 1][:, x0]
        g11 = g[y0 + 1][:, x0 + 1]
        tot += amp * ((g00 * (1 - fx) + g01 * fx) * (1 - fy) + (g10 * (1 - fx) + g11 * fx) * fy)
        norm += amp
        amp *= gain
        c = max(1.0, c / 2.0)
    return tot / norm


def white(h, w, seed):
    return np.random.RandomState(seed & 0x7fffffff).rand(h, w).astype(F32)


# ---------------------------------------------------------------- çizgi bulma (derinlik, normal, nesne kimliği)
def kenarlar(z, n, iob, bg, d_esik=0.012, n_esik=0.22):
    """Döndürür: (siluet, kivrim, kimlik) 0..1 kenar güçleri.
    siluet: 1/Z'nin Laplace'ı (düzlemlerde sıfır) göreli; kivrim: normal açısı; kimlik: nesne sınırı."""
    iz = np.where(bg, 0.0, 1.0 / np.maximum(z, 1e-4)).astype(F32)
    lap = np.abs(4 * iz - shift(iz, 1, 0) - shift(iz, -1, 0) - shift(iz, 0, 1) - shift(iz, 0, -1))
    ref = np.maximum(np.maximum(iz, 1e-6), 0.0)
    rel = lap / ref
    sil = smoothstep(d_esik, d_esik * 3.0, rel)
    # arka planla sınır: her zaman siluet
    bgd = bg.astype(F32)
    bge = np.maximum.reduce([np.abs(bgd - shift(bgd, 1, 0)), np.abs(bgd - shift(bgd, 0, 1)),
                             np.abs(bgd - shift(bgd, -1, 0)), np.abs(bgd - shift(bgd, 0, -1))])
    sil = np.maximum(sil, bge)
    # normaller
    kv = np.zeros(z.shape, F32)
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        d = 1.0 - np.sum(n * shift(n, dx, dy), axis=-1)
        kv = np.maximum(kv, d)
    kv = smoothstep(n_esik, n_esik * 2.2, kv) * (1 - bgd)
    # kimlik
    ii = np.rint(iob).astype(np.int32)
    idd = ((ii != shift(ii, 1, 0)) | (ii != shift(ii, 0, 1))).astype(F32)
    idd *= (1 - bgd)
    return sil, kv, idd


def yansit(uv_pix, W, H):
    return uv_pix
