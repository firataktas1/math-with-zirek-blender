"""zirek_video_testi.ipynb dosyasını üretir (elle düzenlemek yerine bu betik düzenlenir)."""
import json
from pathlib import Path

DEPO_HAM = "https://raw.githubusercontent.com/firataktas1/math-with-zirek-blender/main/colab/"


def md(metin):
    return {"cell_type": "markdown", "metadata": {}, "source": metin.strip("\n").splitlines(keepends=True)}


def kod(metin):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": metin.strip("\n").splitlines(keepends=True)}


hucreler = [
    md("""
# Math with Zirek · ücretsiz video modeli denemesi (Colab T4)

Video 1'deki kâğıt kesik bir anı (3:27, Zirek ve öğrenci kapının önünde) ücretsiz bir yerel video modeliyle
yeniden üretir: önce **LTX-Video 2B**, o hiç sonuç vermezse **Wan 2.1 1.3B**. Ücretli API ya da anahtar yok.

**Çalıştırmak için:** menüden **Çalışma zamanı → Tümünü çalıştır** (Ctrl+F9).
"Bu not defteri Google tarafından yazılmadı" uyarısı çıkarsa **Yine de çalıştır**'a bas.

- Süre: genelde 40-60 dakika (modeller ~26 GB iner), en kötü durumda 2 saat. Sekme açık kalsın.
- Üç deneme yapılır: (1) ilk kareden video, (2) var olan videonun hafif yeniden çizimi, (3) daha güçlü yeniden
  çizimi. Bellek ya da süre yetmezse her biri kendiliğinden daha küçük bir ayara iner (en az 3 ayar).
- Sonunda `zirek_sonuc.zip` bilgisayarına iner (videolar + ayrıntılı kayıt). İnmezse soldaki 📁 Dosyalar
  panelinde `zirek_sonuc.zip`'e sağ tıklayıp **İndir**.
"""),
    kod(f"""
# 1) GPU denetimi, eksik paket, girdi dosyaları
import pathlib, shutil, subprocess, urllib.request
r = None
if shutil.which("nvidia-smi"):
    r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
if r is None or r.returncode != 0 or not r.stdout.strip():
    raise SystemExit("GPU bağlı değil. Menü: Çalışma zamanı > Çalışma zamanı türünü değiştir > T4 GPU > Kaydet. "
                     "Sonra yine Çalışma zamanı > Tümünü çalıştır.")
!pip install -q ftfy==6.3.1
KOK = pathlib.Path("/content/zirek")
(KOK / "girdi").mkdir(parents=True, exist_ok=True)
DEPO = "{DEPO_HAM}"
for ad in ["zirek_test.py", "girdi/zirek_klip.mp4", "girdi/zirek_kare.png"]:
    urllib.request.urlretrieve(DEPO + ad, KOK / ad)
    print("indirildi:", ad, (KOK / ad).stat().st_size, "bayt")
"""),
    kod("""
# 2) Denemeler (her deneme ayrı süreçte; biri çökerse sıradaki daha küçük ayarla devam eder)
!cd /content/zirek && python zirek_test.py 2>&1 | tee /content/zirek/surucu.log
"""),
    kod("""
# 3) Sonuçlar: özet tablo, küçük önizlemeler, zip
import json, shutil, subprocess
from IPython.display import Video, display
SONUC = KOK / "sonuc"
SONUC.mkdir(parents=True, exist_ok=True)
if (KOK / "surucu.log").exists():
    shutil.copy(KOK / "surucu.log", SONUC / "surucu.log")
shutil.make_archive("/content/zirek_sonuc", "zip", SONUC)      # önce zip: aşağıda bir şey bozulsa da kanıt kalır
def oku(j):
    try:
        return json.loads(j.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ad": j.name, "durum": "okunamadı", "neden": str(e)}
rp = SONUC / "rapor.json"
rapor = oku(rp) if rp.exists() else {}
if "denemeler" not in rapor:   # sürücü yarıda kaldıysa tek tek deneme kayıtları toplanır
    rapor = {"ortam": {}, "toplam_dk": "?",
             "denemeler": [oku(j) for j in sorted(SONUC.glob("*.json")) if j.name != "rapor.json"]}
print("GPU:", rapor["ortam"].get("nvidia_smi"), "| toplam", rapor["toplam_dk"], "dk")
for d in rapor["denemeler"]:
    print(f"{d.get('ad','?'):32} {d.get('durum','?'):8} {d.get('sure_sn','-'):>7} sn  "
          f"VRAM tepe {d.get('vram_tepe_gb','-')} GB  {d.get('neden','')}")
for d in rapor["denemeler"]:
    if d.get("durum") == "tamam":
        try:
            on = pathlib.Path("/content") / (d["ad"] + "-onizleme.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SONUC / d["dosya"]), "-vf", "scale=640:-2",
                            "-c:v", "libx264", "-crf", "28", "-pix_fmt", "yuv420p", str(on)], check=True)
            print(d["ad"])
            display(Video(str(on), embed=True, width=640))
        except Exception as e:
            print("önizleme yapılamadı:", d.get("ad"), e)
print("zip hazır:", round(pathlib.Path("/content/zirek_sonuc.zip").stat().st_size / 1e6, 1), "MB")
"""),
    kod("""
# 4) İndirme (sekme açık kalsın; inmezse soldaki Dosyalar panelinden zirek_sonuc.zip > İndir)
from google.colab import files
files.download("/content/zirek_sonuc.zip")
"""),
]

defter = {
    "nbformat": 4, "nbformat_minor": 0,
    "metadata": {
        "colab": {"provenance": [], "gpuType": "T4", "name": "zirek_video_testi.ipynb"},
        "accelerator": "GPU",
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    },
    "cells": hucreler,
}
hedef = Path(__file__).with_name("zirek_video_testi.ipynb")
hedef.write_text(json.dumps(defter, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("yazıldı:", hedef)
