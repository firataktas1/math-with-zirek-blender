# Poly Haven (CC0) varlıklarını indirir ve KAYNAKLAR.txt yazar. Hesap/anahtar gerekmez.
# Kullanım: python indir.py            (1k + 2k dokular, 2k HDRI)
#           python indir.py --son      (ek olarak 4k dokular ve 4k HDRI: son render için)
import json, os, sys, urllib.request, time

KOK = os.path.dirname(os.path.abspath(__file__))
VAR = os.path.join(KOK, 'assets')
API = 'https://api.polyhaven.com'
UA = {'User-Agent': 'MathWithZirek-blender-deneme/1.0'}

HDRI = ['hilly_terrain_01', 'grasslands_sunset']
DOKU = {  # ad -> hangi haritalar
    'leafy_grass': ['Diffuse', 'nor_gl', 'Rough', 'Displacement'],
    'stacked_stone_wall': ['Diffuse', 'nor_gl', 'Rough', 'Displacement'],
    'rock_surface': ['Diffuse', 'nor_gl', 'Rough', 'Displacement'],
    'hessian_230': ['Diffuse', 'nor_gl', 'Rough', 'Displacement'],
    'rough_wood': ['Diffuse', 'nor_gl', 'Rough', 'Displacement'],
}
MODEL = ['grass_bermuda_01', 'grass_medium_02', 'rock_moss_set_01', 'dandelion_01']
SON = '--son' in sys.argv


def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as ex:
            print('  tekrar', k, ex)
            time.sleep(2 + 3 * k)
    raise RuntimeError(url)


def save(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = get(url)
    with open(path, 'wb') as f:
        f.write(data)
    print('  indi', os.path.relpath(path, KOK), len(data) // 1024, 'KB')


kayit = []


def info(aid):
    d = json.loads(get(API + '/info/' + aid))
    return d['name'], ', '.join(d.get('authors', {}).keys())


for h in HDRI:
    f = json.loads(get(API + '/files/' + h))
    for res in (['2k', '4k'] if SON else ['2k']):
        u = f['hdri'][res]['hdr']['url']
        save(u, os.path.join(VAR, 'hdri', os.path.basename(u)))
    n, a = info(h)
    kayit.append(('HDRI', h, n, a, 'https://polyhaven.com/a/' + h))

for t, maps in DOKU.items():
    f = json.loads(get(API + '/files/' + t))
    for res in (['1k', '2k', '4k'] if SON else ['1k', '2k']):
        for m in maps:
            fmt = 'jpg' if m in ('Diffuse', 'Rough') else 'png'
            u = f[m][res][fmt]['url']
            save(u, os.path.join(VAR, 'doku', t, os.path.basename(u)))
    n, a = info(t)
    kayit.append(('Doku', t, n, a, 'https://polyhaven.com/a/' + t))

for mdl in MODEL:
    f = json.loads(get(API + '/files/' + mdl))
    for res in (['1k', '2k'] if SON else ['1k']):
        b = f['blend'][res]['blend']
        d = os.path.join(VAR, 'model', mdl, res)
        save(b['url'], os.path.join(d, os.path.basename(b['url'])))
        for rel, inc in b['include'].items():
            save(inc['url'], os.path.join(d, rel))
    n, a = info(mdl)
    kayit.append(('Model', mdl, n, a, 'https://polyhaven.com/a/' + mdl))

with open(os.path.join(KOK, 'KAYNAKLAR.txt'), 'w', encoding='utf-8') as fo:
    fo.write('Gerçekçi sürümde kullanılan dış varlıklar. Hepsi Poly Haven, lisans CC0 (kamu malı; atıf gerekmez, yine de yazıldı).\n')
    fo.write('İndirme: public API https://api.polyhaven.com (hesap yok, anahtar yok, ücret yok). Betik: indir.py\n')
    fo.write('Lisans metni: https://polyhaven.com/license\n\n')
    for tur, aid, n, a, url in kayit:
        fo.write('%s | %s (%s) | yazar: %s | %s | lisans: CC0\n' % (tur, n, aid, a, url))
    fo.write('\nKoyun, taş duvarın biçimi, kese biçimi, ip, çakılların biçimi: betikte yordamsal (dış varlık değil).\n')
    fo.write('Koyun modeli: Poly Haven\'da koyun yok; poly.pizza\'daki CC0 koyunların hepsi düşük poligonlu oyuncak tarzı\n')
    fo.write('(gerçekçi sahneye uymuyor), bu yüzden kullanılmadı. CC0 olmayan hiçbir varlık kullanılmadı.\n')
print('BITTI', len(kayit), 'varlık')
