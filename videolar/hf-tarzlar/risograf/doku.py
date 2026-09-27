# Pre-baked textures for the four "b" group styles (karakalem, risograf, suluboya, teknik).
# Everything is generated here from seeded noise: no downloaded images.
# Usage:  python doku.py <stil>   (writes into ./assets/)
import sys, os
import numpy as np
from PIL import Image

STIL = sys.argv[1] if len(sys.argv) > 1 else os.path.basename(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20260927)


def fnoise(h, w, beta, seed):
    """Periodic (tileable) 1/f^beta noise, normalised to 0..1."""
    r = np.random.default_rng(seed)
    wn = r.standard_normal((h, w))
    F = np.fft.fft2(wn)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    F = F / (f ** beta)
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    n = (n - n.min()) / (n.max() - n.min())
    return n


def band(h, w, lo, hi, seed):
    """Band-limited periodic noise (only frequencies between lo and hi cycles/pixel)."""
    r = np.random.default_rng(seed)
    F = np.fft.fft2(r.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    F = F * ((f >= lo) & (f <= hi))
    n = np.real(np.fft.ifft2(F))
    n = (n - n.mean()) / (n.std() + 1e-9)
    return n


def save_rgb(a, name, q=None):
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")
    p = os.path.join(OUT, name)
    if name.endswith(".jpg"):
        img.save(p, quality=q or 92, subsampling=0)
    else:
        img.save(p, optimize=True)
    print(name, img.size)


def save_rgba(a, name):
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    img.save(os.path.join(OUT, name), optimize=True)
    print(name, img.size)


H, W = 1080, 1920


def paper(base, low_amp, fine_amp, fiber_amp, seed, tooth=0.0):
    low = fnoise(H, W, 1.6, seed) - 0.5
    fine = band(H, W, 0.18, 0.5, seed + 1)
    mid = band(H, W, 0.02, 0.08, seed + 2)
    # fibres: stretched noise
    fib = band(H // 8, W, 0.05, 0.25, seed + 3)
    fib = np.array(Image.fromarray(((fib - fib.min()) / (np.ptp(fib) + 1e-9) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)) / 255.0 - 0.5
    v = 1 + low * low_amp + fine * fine_amp + fib * fiber_amp + mid * tooth
    out = np.stack([base[i] * v for i in range(3)], -1)
    return out


if STIL == "karakalem":
    save_rgb(paper((243, 235, 219), 0.05, 0.02, 0.015, 11, tooth=0.0), "kagit.jpg")
    # graphite grain (stroke texture): dark warm grey with granular alpha
    n = band(512, 512, 0.15, 0.5, 21)
    m = band(512, 512, 0.03, 0.12, 22)
    a = np.clip(0.78 + 0.16 * n + 0.08 * m, 0.35, 1.0)
    rgba = np.zeros((512, 512, 4))
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 52, 48, 46
    rgba[..., 3] = a * 255
    save_rgba(rgba, "grafit.png")
    # hatch tiles: diagonal pencil strokes (45 deg), tileable because the period divides the tile
    for name, gap, dens, cross in (("tarama1.png", 8, 0.42, False), ("tarama2.png", 6, 0.62, False), ("tarama3.png", 6, 0.72, True)):
        S = 384
        yy, xx = np.mgrid[0:S, 0:S]
        d = (xx + yy) % gap
        line = np.clip(1.4 - np.abs(d - gap / 2) / 1.0, 0, 1)
        # break strokes into segments of varying pressure
        pres = band(S, S, 0.004, 0.03, 31 + gap)
        pres = np.clip(0.55 + 0.35 * pres, 0.1, 1)
        g = band(S, S, 0.2, 0.5, 33)
        a = line * pres * np.clip(0.8 + 0.25 * g, 0, 1) * dens
        if cross:
            d2 = (xx - yy) % gap
            l2 = np.clip(1.4 - np.abs(d2 - gap / 2) / 1.0, 0, 1)
            a = np.maximum(a, l2 * pres[::-1] * dens * 0.8)
        rgba = np.zeros((S, S, 4))
        rgba[..., 0], rgba[..., 1], rgba[..., 2] = 58, 52, 50
        rgba[..., 3] = np.clip(a, 0, 1) * 255
        save_rgba(rgba, name)

elif STIL == "risograf":
    save_rgb(paper((244, 238, 225), 0.035, 0.02, 0.015, 41), "kagit.jpg")
    # ink voids / speckle: alpha = where ink is knocked out
    S = 1024
    n = band(S, S, 0.25, 0.5, 42)
    m = band(S, S, 0.01, 0.05, 43)
    v = np.clip((n * 0.8 + m * 0.9 - 1.1) / 1.2, 0, 1)
    speck = (rng.random((S, S)) < 0.004).astype(float)
    a = np.clip(v + speck, 0, 1)
    rgba = np.zeros((S, S, 4)); rgba[..., 3] = a * 255
    save_rgba(rgba, "gren.png")

elif STIL == "suluboya":
    save_rgb(paper((248, 243, 233), 0.03, 0.022, 0.01, 51, tooth=0.018), "kagit.jpg")
    # wash modulation: smooth large variations + a few soft blooms (back-runs); multiply (white = no change)
    Hh, Ww = 1152, 2048
    low = fnoise(Hh, Ww, 2.4, 52) - 0.5
    mid = band(Hh, Ww, 0.002, 0.009, 53)
    v = 0.93 + 0.22 * low + 0.018 * mid
    yy, xx = np.mgrid[0:Hh, 0:Ww]
    r2 = np.random.default_rng(54)
    for i in range(9):
        cx, cy, R = r2.random() * Ww, r2.random() * Hh, 130 + r2.random() * 200
        ang = np.arctan2(yy - cy, xx - cx)
        wob = np.ones_like(ang)
        for hk in range(2, 9):
            wob += (0.08 / hk) * np.sin(ang * hk + r2.random() * 6.28)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (R * wob)
        ring = np.exp(-((d - 1) ** 2) / 0.0025) * 0.055
        inner = np.clip(1 - d, 0, 1) ** 0.5 * 0.035
        v = v - ring + inner
    v = np.clip(v, 0.7, 1.0)
    g = v * 255
    save_rgb(np.stack([g, g, g], -1), "yikama.jpg", q=90)
    # granulation specks (tile)
    S = 512
    n = band(S, S, 0.2, 0.5, 55)
    m = band(S, S, 0.02, 0.08, 56)
    a = np.clip((n * 0.7 + m * 0.6 - 0.4) / 1.6, 0, 1)
    rgba = np.zeros((S, S, 4)); rgba[..., 0], rgba[..., 1], rgba[..., 2] = 70, 60, 70
    rgba[..., 3] = a * 255
    save_rgba(rgba, "granul.png")

elif STIL == "teknik":
    base = np.array((30, 78, 142), float)
    low = fnoise(H, W, 1.7, 61) - 0.5
    fine = band(H, W, 0.2, 0.5, 62)
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.2
    v = vig * (1 + low * 0.16) + fine * 0.012
    # two soft fold creases
    fold = np.exp(-((xx - W * 0.5) ** 2) / 30) * 0.05 + np.exp(-((yy - H * 0.5) ** 2) / 30) * 0.035
    out = np.stack([base[i] * v for i in range(3)], -1) + fold[..., None] * 255 * np.array([0.5, 0.7, 1.0])
    save_rgb(out, "kagit.jpg")
