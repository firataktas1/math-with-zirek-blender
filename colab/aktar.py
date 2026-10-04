"""Sonuç klasörünü, tarayıcı indirmesi çalışmadığında, aynı bilgisayarda 127.0.0.1:8765'te dinleyen alıcıya parça parça gönderir.
Colab hücresinde: exec(urllib.request.urlopen(".../colab/aktar.py").read())"""
import base64, pathlib
from google.colab.output import eval_js

_S = pathlib.Path("/content/zirek/sonuc")
_PARCA = 1_500_000
for _p in sorted(x for x in _S.iterdir() if x.is_file() and not x.name.endswith("-onizleme.mp4")):
    _veri = _p.read_bytes()
    for _i in range(0, max(len(_veri), 1), _PARCA):
        _b64 = base64.b64encode(_veri[_i:_i + _PARCA]).decode()
        _js = ('(async()=>{const b=Uint8Array.from(atob("%s"),c=>c.charCodeAt(0));'
               'const r=await fetch("http://127.0.0.1:8765/?ad=%s&ekle=%d",{method:"POST",body:b});'
               'return r.status})()') % (_b64, _p.name, 1 if _i else 0)
        _durum = eval_js(_js, timeout_sec=120)
        if _durum != 200:
            raise RuntimeError(f"{_p.name}: alıcı {_durum} döndü")
    print("gönderildi:", _p.name, len(_veri), "bayt")
print("hepsi gönderildi")
