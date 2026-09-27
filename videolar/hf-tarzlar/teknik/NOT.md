# Teknik çizim · not

**Ne:** Mavi ozalit (blueprint) kâğıdı üstünde beyaz/camgöbeği çizgi: çizim ızgarası, yapı çizgileri (ağılın eksenleri ve taban elipsi, kesenin çekül çizgisi), ok uçlu ölçü çizgileri (rakamsız, yazısız). Sahne ilk ~1,5 saniyede çizgi çizgi çiziliyor; her çakılın uçuş yayı kesikli çizgiyle önceden çiziliyor, indiği yere çentik atılıyor. Çakıllar ve parıltı tek sıcak renk (kehribar). Sonda son çakılın etrafına bir "odak" dairesi çiziliyor, sonra parlıyor.

**Bulut render:** 37 sn (4 çekirdek, CRF 16, 23 MB). 6 dakika için tahmin (denenmedi): tek işte ~22 dk.

**6 dakikalık, iki konuşan 2B karakterli video için dürüst değerlendirme**
- Artı: En net ve en "matematik" duran. Çizerek açma ve yörünge çizgileri eşleştirme fikrini gösteriyor (her koyun → bir çentik). En ucuz render.
- Eksi: Mavi zemin soğuk; KANAL-BAGLAM "soğuk/karanlık renk alınmaz" diyor ve kurucu koyu arayüz (HUD) sahnelerini sevmedi. Kırmızı panda beyaz çizgiyle sıcaklığını ve kimliğini kaybeder. 6 dakika boyunca teknik resim duygusu soğuk ve mesafeli kalır.
- Karar önerisi: Bütün video için değil; ana stilin içinde kısa "açıklama anı" olarak (fikrin iskeletini gösterirken 5-10 sn) çok iyi çalışır, özellikle krem kâğıt üstünde koyu çizgiyle uyarlanırsa.

## Dayanak tablosu
| Parça | Dayandığı doğru / karar |
|---|---|
| Sahne, zamanlama, tek çakıl, parıltı, sağ alt sakin | ORTAK-BRIEF; blender-deneme/RAPOR.md |
| Ekranda rakam ve yazı yok (ölçü çizgileri rakamsız) | ORTAK-BRIEF, stil tanımı |
| Tek sıcak vurgu (çakıl, parıltı) | RAPOR tur 10; KANAL-BAGLAM sıcak ışık |
| Soğuk zemin uyarısı | KANAL-BAGLAM: soğuk/karanlık renk alınmaz; HUD sahnelerini sevmedi |
| Çizgiyle çizilerek giriş | Stil tanımı (stroke animation) |
