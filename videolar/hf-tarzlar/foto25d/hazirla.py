# foto25d varlık hazırlığı. Kaynaklar KAYNAKLAR.txt'de (hepsi Poly Haven, CC0).
# Gerekli ham dosyalar (indirme adresleri KAYNAKLAR.txt'de):
#   ham/drackenstein_quarry.jpg (8192x4096 tonemapped JPG)
#   ham/stacked_stone_wall.jpg, ham/hessian_230.jpg, ham/curly_teddy_natural.jpg,
#   ham/rock_boulder_dry.jpg, ham/rock_surface.jpg (2k diffuse JPG)
# Çıktı: assets/*.jpg
import sys
import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None
HAM = sys.argv[1] if len(sys.argv) > 1 else "ham"


def reproject(src, yaw, pitch, fov, w, h):
    H, W, _ = src.shape
    f = (w / 2) / np.tan(np.radians(fov) / 2)
    xs, ys = np.meshgrid(np.arange(w) - w / 2 + 0.5, np.arange(h) - h / 2 + 0.5)
    d = np.stack([xs, -ys, np.full_like(xs, f)], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    p = np.radians(pitch)
    cy, sy = np.cos(p), np.sin(p)
    y2 = d[..., 1] * cy + d[..., 2] * sy
    z2 = -d[..., 1] * sy + d[..., 2] * cy
    x2 = d[..., 0]
    lon = np.arctan2(x2, z2) + np.radians(yaw)
    lat = np.arcsin(np.clip(y2, -1, 1))
    u = ((lon / (2 * np.pi)) % 1) * W
    v = (0.5 - lat / np.pi) * H
    u0 = np.floor(u).astype(int) % W
    v0 = np.clip(np.floor(v).astype(int), 0, H - 2)
    fu = (u - np.floor(u))[..., None]
    fv = (v - np.floor(v))[..., None]
    u1 = (u0 + 1) % W
    a = src[v0, u0] * (1 - fu) + src[v0, u1] * fu
    b = src[v0 + 1, u0] * (1 - fu) + src[v0 + 1, u1] * fu
    return a * (1 - fv) + b * fv


def curve(x, lift=0.0, gamma=1.0, contrast=1.0):
    x = np.clip(x, 0, 1)
    x = lift + (1 - lift) * x ** gamma
    return np.clip(0.5 + (x - 0.5) * contrast, 0, 1)


src = np.asarray(Image.open(f"{HAM}/drackenstein_quarry.jpg").convert("RGB")).astype(np.float32)
# 2304x1296 = 1920x1080 kadrajın 1,2 katı (kamera kayması payı); ufuk ~ y 480
bg = reproject(src, 225, -7, 82.2, 2304, 1296) / 255.0
del src
H, W, _ = bg.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# rüzgâr türbinlerini sil (gökyüzüne küçük dikey çizgiler): komşu gökle doldur
for (cx, cy, hw, top, bot) in [(900, 0, 14, 436, 471), (1092, 0, 15, 440, 471), (1222, 0, 17, 436, 486)]:
    x0, x1, y0, y1 = cx - hw, cx + hw, top, bot
    left = bg[y0:y1, x0 - 8:x0 - 2].mean(axis=1, keepdims=True)
    right = bg[y0:y1, x1 + 2:x1 + 8].mean(axis=1, keepdims=True) if x1 + 8 < W else left
    t = np.linspace(0, 1, x1 - x0)[None, :, None]
    bg[y0:y1, x0:x1] = left * (1 - t) + right * t

# akşam renk ayarı: sıcak, yumuşak kontrast, yeşiller biraz kısık
lum = (0.3 * bg[..., 0] + 0.59 * bg[..., 1] + 0.11 * bg[..., 2])[..., None]
bg = lum + (bg - lum) * 0.86
bg[..., 0] = curve(bg[..., 0] * 1.07, 0.02, 0.95, 1.06)
bg[..., 1] = curve(bg[..., 1] * 0.96, 0.02, 1.0, 1.06)
bg[..., 2] = curve(bg[..., 2] * 0.88, 0.04, 1.06, 1.02)
# güneş ışıması (bulutun arkasında, sol-orta üst) ve ufuk pusu
sun = np.exp(-(((xx - 980) / 700) ** 2 + ((yy - 330) / 360) ** 2))
bg += sun[..., None] * np.array([0.16, 0.07, 0.0])
haze = np.exp(-((yy - 500) / 90) ** 2)
bg = bg * (1 - 0.18 * haze[..., None]) + 0.18 * haze[..., None] * np.array([1.0, 0.86, 0.62])
# ön plan hafif kararır (göz ağıla gitsin)
bot = np.clip((yy - 900) / 400, 0, 1)
bg *= (1 - 0.22 * bot[..., None])
bg = np.clip(bg, 0, 1)
out = Image.fromarray((bg * 255).astype(np.uint8))
out.save("assets/manzara.jpg", quality=90)
out.filter(ImageFilter.GaussianBlur(7)).save("assets/manzara-flu.jpg", quality=86)


def tex(name, size, sat, mul, lift=0.0, gamma=1.0, contrast=1.0, blur=0):
    im = Image.open(f"{HAM}/{name}.jpg").convert("RGB").resize((size, size), Image.LANCZOS)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(im).astype(np.float32) / 255.0
    l = (0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2])[..., None]
    a = l + (a - l) * sat
    a = a * np.array(mul)
    a = curve(a, lift, gamma, contrast)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


tex("stacked_stone_wall", 512, 0.28, [1.02, 1.0, 0.95], 0.02, 1.05, 1.1).save("assets/duvar.jpg", quality=88)
tex("hessian_230", 384, 0.9, [1.08, 0.98, 0.84], 0.0, 1.0, 1.05).save("assets/kese.jpg", quality=88)
tex("curly_teddy_natural", 384, 0.55, [1.02, 0.99, 0.93], 0.0, 1.05, 1.25).save("assets/yun.jpg", quality=88)
tex("rock_boulder_dry", 512, 0.7, [0.86, 0.84, 0.8], 0.0, 1.1, 1.15).save("assets/tas.jpg", quality=88)
tex("rock_surface", 256, 0.8, [1.32, 1.12, 0.9], 0.02, 0.95, 1.9).save("assets/cakil.jpg", quality=88)
print("tamam")
