# Pre-bakes the warm cream paper grain overlay as a seamless 640 px tile (own code, CC0).
# Run once: python doku.py   -> assets/kagit-tane.png
import numpy as np
from PIL import Image, ImageDraw

N = 640
rs = np.random.RandomState(7)

def lowpass(a, sigma):
    # periodic gaussian blur via FFT, so the tile wraps without seams
    f = np.fft.fft2(a)
    ky = np.fft.fftfreq(a.shape[0])[:, None]
    kx = np.fft.fftfreq(a.shape[1])[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))
    r = np.real(np.fft.ifft2(f * g))
    return (r - r.mean()) / (r.std() + 1e-9)

fine = (rs.rand(N, N) - 0.5) / 0.29
mid = lowpass(rs.rand(N, N), 1.1)
mott = lowpass(rs.rand(N, N), 22)

fib = Image.new("L", (N, N), 0)
d = ImageDraw.Draw(fib)
for _ in range(900):
    x, y = rs.rand() * N, rs.rand() * N
    a = rs.rand() * np.pi
    L = 6 + rs.rand() * 22
    col = int(90 + rs.rand() * 120)
    for ox in (-N, 0, N):
        for oy in (-N, 0, N):
            d.line([(x + ox, y + oy), (x + ox + np.cos(a) * L, y + oy + np.sin(a) * L)], fill=col, width=1)
fib = np.asarray(fib, dtype=np.float32) / 255.0

v = fine * 0.18 + mid * 0.45 + mott * 0.14 + fib * 0.9
v = v / np.abs(v).max()

rgba = np.zeros((N, N, 4), np.float32)
rgba[..., 0] = np.where(v < 0, 92, 255)
rgba[..., 1] = np.where(v < 0, 70, 250)
rgba[..., 2] = np.where(v < 0, 48, 236)
rgba[..., 3] = np.where(v < 0, np.clip(-v, 0, 1) * 150, np.clip(v, 0, 1) * 170)
Image.fromarray(np.uint8(np.clip(rgba, 0, 255)), "RGBA").save("assets/kagit-tane.png", optimize=True)
print("ok")
