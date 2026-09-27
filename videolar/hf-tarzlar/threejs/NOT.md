# Three.js basit 3B (HyperFrames) · NOT

**Ne:** HyperFrames içinde Three.js (r181, yerel dosya) ile düz gölgeli (low-poly) 3B sahne: çimenli tepe, akşam gök kubbesi ve sisli uzak tepeler, alçak sıcak güneşten uzun yumuşak gölgeler. Duvar ~150 taştan tek "instanced" nesne; koyunlar yün toplarından, kese döndürülmüş profil, çakıllar yassı çokyüzlü. Her şey zamandan hesaplanıyor (hf-seek olayı, rastgele sayı sabit tohumlu): kareye atlamaya güvenli. Son 3 sn kamera keseye iner, kalan çakılda sıcak parıltı + küçük ışık.

**Bulut render:** 4 dk 47 sn (ölçüm aralığı 2 dk 47 sn - 4 dk 59 sn; 4 çekirdek ama WebGL yüzünden tek işçi, yazılım WebGL + ekran görüntüsü yolu, kare başına ~0,9 sn). 6 dakikalık video için tek işte ~2,5-3 saat; parçalara bölünüp paralel işlerle (herkese açık depoda dakika sınırsız) ~20-30 dk'ya iner.

**6 dakikalık, iki konuşan 2B karakterli video için dürüst değerlendirme**
- Artı: Gerçek derinlik, ışık, gölge ve serbest kamera; Blender'a göre çok ucuz (Blender kil sahnesi ~900 koşucu dakikası, bu ~5 dk) ve aynı HTML projesinde 2B katmanlarla birleşebiliyor. Sahne kodla kurulduğu için yeni açı / yeni an eklemek kolay.
- Eksi: Görünüm "basit oyun" düzeyinde; koyunlar sevimli ama kese hâlâ biraz çömleğe benziyor, doku ve ayrıntı az. Daha iyi görünüm için gerçek modeller (GLTF) ve daha çok ışık ayarı gerekir; render süresi de artar.
- Eksi: Düz 2B Zirek ve öğrenci 3B sahnenin önünde "yapıştırılmış" durabilir; karakterlerin de benzer düz gölgeli biçimde çizilmesi ya da 3B'nin yalnız geniş plan/keşif anlarında kullanılması daha uyumlu.
- Eksi: Yerelde bu laptopta WebGL önizleme bellek yiyor; bütün kontrol bulutta yapıldı.

## Dayanak tablosu
| Parça | Dayandığı doğru ya da karar |
|---|---|
| Akşam, 8 koyun ~0,73 sn arayla, her koyuna bir çakıl, kesede tek çakıl, son 3 sn yaklaşma + parıltı | ORTAK-BRIEF sahnesi; Blender RAPOR zamanlaması |
| Hafif geometri, tek "instanced" duvar, 2048 gölge haritası | Brief: bulutta yazılım WebGL; süre ölçüldü (kare başına ~0,9 sn) |
| Zamana bağlı çizim, sabit tohum | hyperframes-animation Three.js adaptörü sözleşmesi (hf-seek) |
| Çakıl açık kum rengi, düz taş koyu gri | Blender tur 10 ve bu işin 3. turu: dizi zeminden ayrışmıyordu |
| Parıltı küçük, sıcak, dört kollu | Blender tur 8, 11-12 |
| Sağ alt üçte bir boş çayır | Brief |
| Dış model/doku yok, yalnız three.js (MIT) | Brief varlık kuralı |
