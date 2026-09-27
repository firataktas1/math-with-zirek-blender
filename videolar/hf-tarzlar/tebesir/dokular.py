# Tebeşir tahtası dokuları (hepsi burada üretilir, dış varlık yok). Sabit tohum.
# python dokular.py  ->  assets/tahta.jpg, assets/tebesir-maske.png, assets/toz.png
import numpy as np
from PIL import Image, ImageFilter

rng = np.random.default_rng(7)


def fbm(h, w, octaves, base, rng, stretch=(1.0, 1.0)):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        sh = max(2, int(h / (base * stretch[0]) * 2 ** o))
        sw = max(2, int(w / (base * stretch[1]) * 2 ** o))
        n = rng.random((sh, sw)).astype(np.float32)
        im = Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(im, np.float32) / 255.0)
        tot += amp
        amp *= 0.5
    return out / tot


W, H = 1920, 1080
# 1) Tahta: koyu yeşil-siyah arduvaz, silgi izleri, eski tebeşir bulutları
base = np.array([34, 46, 41], np.float32)
n1 = fbm(H, W, 5, 260, rng)
n2 = fbm(H, W, 4, 90, rng, (1.0, 3.0))
img = np.zeros((H, W, 3), np.float32) + base
img += ((n1 - 0.5) * 16)[..., None]
# silgi izleri: yatay geniş kavisli bantlar, açık gri sis
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
smear = np.zeros((H, W), np.float32)
for k in range(9):
    cy = rng.uniform(80, H - 80)
    cx = rng.uniform(0, W)
    amp = rng.uniform(0.25, 0.7)
    width = rng.uniform(50, 120)
    curve = rng.uniform(-0.00025, 0.00025)
    length = rng.uniform(500, 1300)
    d = np.abs(yy - (cy + curve * (xx - cx) ** 2))
    band = np.exp(-(d / width) ** 2) * np.exp(-((xx - cx) / length) ** 4)
    smear += amp * band
smear *= (0.55 + 0.9 * n2)
img += (smear * 26)[..., None] * np.array([0.93, 1.0, 0.97])
# ince toz lekesi
speck = rng.random((H, W)).astype(np.float32)
img += ((speck > 0.9985) * 30)[..., None]
img += ((rng.random((H, W)) - 0.5) * 5)[..., None]
# kenar kararması
v = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
img *= (1 - 0.28 * np.clip(v - 0.25, 0, 1))[..., None]
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save("assets/tahta.jpg", quality=92)

# 2) Tebeşir maskesi: çizgiye tanecik ve yatay kırık dokusu veren alfa (512x512, döşenir)
S = 512
g = fbm(S, S, 3, 3, rng, (1.0, 4.0))  # yatay lifler
f = rng.random((S, S)).astype(np.float32)
f = np.asarray(Image.fromarray((f * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255.0
a = 0.55 + 0.9 * (g - 0.5) + 0.9 * (f - 0.5)
a = np.clip((a - 0.12) * 1.5, 0, 1)
a = np.where(f < 0.30, a * 0.35, a)
rgba = np.zeros((S, S, 4), np.uint8)
rgba[..., :3] = 255
rgba[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
# döşenebilir olsun: kenarları sarmala (kaba ama yeterli: fbm zaten periyodik değil, ayna harmanı)
Image.fromarray(rgba).save("assets/tebesir-maske.png")

# 3) Ekrana sabit ince toz/gren katmanı (şeffaf PNG, 960x540 büyütülerek kullanılır)
Hs, Ws = 540, 960
d = rng.random((Hs, Ws)).astype(np.float32)
alpha = np.where(d > 0.994, rng.uniform(40, 110, (Hs, Ws)), 0).astype(np.float32)
alpha = np.asarray(Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), np.float32) * 2.2
rgba = np.zeros((Hs, Ws, 4), np.uint8)
rgba[..., :3] = 235
rgba[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
Image.fromarray(rgba).save("assets/toz.png")
print("tamam")
