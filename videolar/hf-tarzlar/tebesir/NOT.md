# Tebeşir tahtası (HyperFrames) · NOT

**Ne:** Koyu yeşil arduvaz tahtada, tebeşirle çizilmiş sahne kendini çizerek başlar (tepe, güneş, taş duvar, kese, düz taş); koyunlar kadraja girerken çizilir. Her koyun kapıdan geçerken sarı tebeşirden bir çakıl keseden kalkar, yay çizip düz taşa dizilir, inerken tebeşir tozu çıkarır. Son 3 sn kamera keseye yaklaşır; kesede kalan tek çakılda küçük sıcak dört kollu parıltı. Doku: önceden üretilmiş tahta görüntüsü + tebeşir tanecik maskesi (canlı filtre yok).

**Bulut render:** 45 sn (GitHub Actions, 4 çekirdek, 300 kare, CRF 16). 6 dakikalık video için kabaca ~25-30 dk.

**6 dakikalık, iki konuşan 2B karakterli video için dürüst değerlendirme**
- Artı: Kanal kuralı "matematik bir yüzeyde (tahta) yapılır; Zirek tahtanın yanında duran hoca" ile birebir uyuşuyor. Sayma, eşleme, çizim adım adım belirir: anlatımın hızına göre çizdirmek kolay. Çok hızlı render, dosyalar küçük, her şey kodla (tahta dokusu dahil) üretiliyor; yeni sahne = yeni çizim listesi.
- Artı: Karakterler (Zirek ve öğrenci) renkli düz 2B çizim olarak tahtanın önünde durabilir; tebeşir dünyasıyla karışmaz, ayrışır.
- Eksi: Koyu zemin, kurucunun sevdiği sıcak krem/kâğıt havasından uzak; uzun videoda karanlık yorabilir (koyu arayüzü sevmediği not edilmişti). Bu yüzden belki yalnız "matematik anları" için.
- Eksi: Koyunlar basit çizgi sevimliliğinde; "vay" etkisi düşük, derinlik ve ışık yok. Kamera yaklaşınca tebeşir tanesi iriyor (gerçekçi ama biraz kaba).
- Eksi: Kese ağzındaki taş yığını geniş planda küçük; asıl sayım yerdeki dizide okunuyor.

## Dayanak tablosu
| Parça | Dayandığı doğru ya da karar |
|---|---|
| Akşam, 8 koyun ~0,73 sn arayla, her koyuna bir çakıl, kesede tek çakıl, son 3 sn yaklaşma + parıltı | ORTAK-BRIEF sahnesi; Blender RAPOR zamanlaması |
| Rakam ve insan yok | Brief; METIN G: "Ekranda rakam yok" |
| Çakıl sıcak sarı, duvar gri-beyaz | Blender tur 10: aynı renkte çakıl duvara karışıyordu |
| Parıltı dört kollu yıldız, çarpı değil | Blender tur 8: çarpı "yanlış" gibi okunuyordu |
| Sağ alt üçte bir boş (yalnız birkaç ot) | Brief: karakterler oraya bindirilecek |
| Tahta ve tebeşir dokusu önceden üretilmiş görüntü | Brief: canlı SVG türbülans filtresi yok |
| Tahta yüzeyi | KANAL-BAGLAM tasarım kuralı 2: matematik tahtada |
