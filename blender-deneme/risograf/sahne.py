# Math with Zirek · sahne G, RİSOGRAF sürüm.
# Sahne, animasyon, kamera ve Cycles veri geçişleri karakalem sürümüyle birebir aynı (../karakalem/sahne.py);
# bu dosya yalnız varsayılan stili "risograf" yapar. Baskı görünüşü: risograf.py.
# Kullanım (karakalem/sahne.py ile aynı anahtarlar):
#   blender -b -P sahne.py -- --mod kare --kareler 68,180,290 --w 960 --h 540 --ornek 16 --cikti out
#   blender -b -P sahne.py -- --mod parca --bas 1 --son 60 --cikti out
import os

STIL_VARSAYILAN = 'risograf'
_yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'karakalem', 'sahne.py')
__file__ = _yol
with open(_yol, encoding='utf-8') as _fh:
    exec(compile(_fh.read(), _yol, 'exec'))
