# -*- coding: utf-8 -*-
"""Video 1 v5: her sahnenin ortasından (ve kritik anlardan) headless kare alıp kontak.png üretir.

  python -B -X utf8 kontak.py zamanlar      -> zamanlar.json (ad, sn) + '--at' listesi yazdırır
  python -B -X utf8 kontak.py birlestir DIR -> DIR içindeki PNG'lerden kontak.png (zaman sırasıyla)
Kareler: npx hyperframes snapshot . --at <liste> --no-end --describe false -o snap-v5
"""
import json, sys, pathlib, re
KOK = pathlib.Path(__file__).resolve().parent

def zamanlar():
    y = json.loads((KOK / "yerlesim.json").read_text(encoding="utf-8"))
    M = y["isaretler"]; C = {c["no"]: c for c in y["cumleler"]}
    Ls = lambda n: C[n]["baslangic"]; Le = lambda n: C[n]["baslangic"] + C[n]["sure"]; orta = lambda n: Ls(n) + C[n]["sure"] / 2
    return [
        ("0 harita dalışı", 1.0), ("A iki sepet 3/8", M["A1"] + 0.5), ("A öğrenci 3'ün arkasında", orta(1)),
        ("B sınıf, üç kalem", Ls(2) + C[2]["sure"] * 0.8), ("B soru", orta(3)), ("B eve yürüyüş", orta(4)),
        ("C buradayız", orta(5)), ("C 7", orta(7)),
        ("D 10/20 flaş", M["d10"] + 0.25), ("D 8", orta(8)), ("D 100/110 flaş", M["d100"] + 0.25), ("D 10", orta(10)),
        ("D 100 110 +10", Le(11) - 0.2), ("D yan yana öbek", M["yan"] + 2.0), ("D keşif", M["k1"] + 1.0), ("D 12", Le(12) - 0.2),
        ("D 13 kalem sepet", orta(13)), ("D 15 zy", orta(15)),
        ("E göze dalış", M["E"] + 1.2), ("E 16 şafak", orta(16)), ("E koyunlar çıkıyor", M["cik"] + 2.0), ("E otlakta 18", orta(18)),
        ("E akşam dönüş", M["don"] + 1.5), ("E sürü ağılda", M["bak"] + 0.7), ("E 20 100→110", Le(20) - 0.3),
        ("E yalnız koyun", M["tepe"] + 0.6), ("E 21", orta(21)),
        ("F isimler", Le(23) - 0.2), ("F 20 etiket", Le(24) - 0.2), ("F 25 karışır", orta(25)), ("F boş 1,5 sn", M["bosF"] + 0.7), ("F 28", orta(28)),
        ("G kapı çakıl torba", orta(29)), ("G düşünme 3 sn", M["dus"] + 1.5), ("G 30", orta(30)),
        ("G sabah taş düşer", M["sabahG"] + 2.5), ("G akşam", M["aksamG"] + 0.8), ("G taş çıkar", M["donG"] + 2.0), ("G son taş parlar", M["k2"] + 0.8), ("G 33", orta(33)),
        ("H 34", orta(34)), ("H kil kap", orta(35)), ("H 36 48 yazı", Le(36) - 0.3), ("H taşlar dökülür", M["dok"] + 1.2), ("H 48", orta(37)),
        ("H 38", orta(38)), ("H calculus", Le(39) - 0.3), ("H calculator", orta(40)), ("H telefon torba", Le(41) - 0.2),
        ("I 42 torba", orta(42)), ("I 43 balon", Le(43) - 0.2), ("I yirmi", Le(44) - 0.1), ("I 44 son", Le(44) + 0.5),
        ("J ben mi aptalım", orta(52)), ("J hayır", orta(53)), ("J 54", orta(54)), ("J 55", orta(55)),
        ("K sınıf", M["K"] + 1.2), ("K çizgi 1", M["mon"] + 1.5), ("K çizgi son", M["mons"] - 0.2), ("K 56", orta(56)), ("K 58", orta(58)), ("K renk", M["renk"] + 0.2),
        ("L 59 torba iner", orta(59)), ("L eller", M["el"] + 1.1), ("L 60", orta(60)), ("L 2. durak", orta(61)), ("L son", y["toplam_sure"] - 0.5),
    ]

if sys.argv[1] == "zamanlar":
    z = [(a, round(t, 2)) for a, t in zamanlar()]
    (KOK / "zamanlar.json").write_text(json.dumps(z, ensure_ascii=False, indent=0), encoding="utf-8")
    print(",".join(f"{t:.2f}" for _, t in z))
else:
    from PIL import Image, ImageDraw, ImageFont
    d = pathlib.Path(sys.argv[2])
    z = json.loads((KOK / "zamanlar.json").read_text(encoding="utf-8"))
    png = sorted(d.glob("*.png"), key=lambda p: float(re.findall(r"(\d+(?:\.\d+)?)", p.stem)[-1]) if re.findall(r"\d", p.stem) else 0)
    W, H, S = 480, 270, 6
    out = Image.new("RGB", (W * S, (H + 34) * ((len(z) + S - 1) // S)), "#1B1714")
    fnt = ImageFont.truetype(str(KOK / "assets/fonts/Barlow.woff"), 20)
    for i, ((ad, t), p) in enumerate(zip(z, png)):
        im = Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS)
        x, y = (i % S) * W, (i // S) * (H + 34)
        out.paste(im, (x, y + 34))
        m, s = divmod(t, 60)
        ImageDraw.Draw(out).text((x + 8, y + 6), f"{int(m)}:{s:04.1f}  {ad}", fill="#F3E6CC", font=fnt)
    out.save(KOK / "kontak.png", optimize=True)
    print("kontak.png", out.size, len(png), "kare /", len(z), "zaman")
