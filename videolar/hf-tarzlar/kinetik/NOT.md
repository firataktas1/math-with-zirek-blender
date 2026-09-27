# Kinetik yazı (HyperFrames) · NOT

**Ne:** Sahne Türkçe kelimelerle kurulur: gökte batan "akşam" (güneş), süzülen "bulut"lar, tepe sırtı boyunca "çimen · çimen", çayırda "ot"lar; ağıl duvarı "taş" kelimelerinden örülü halka, direkler üst üste "taş". Her koyun yün bulutunun üstünde "koyun" yazan, harfleri adım adım zıplayan bir kelime; kapıdan girer. Her girişte kese ("kese" yazan çuval) ağzından küçük bir "taş" kelimesi kalkar, büyüyerek düz taşın üstüne dizilir. Sonda kesede tek "taş" kalır, kamera yaklaşır, parıltı. Rakam yok. Yazı tipi Baloo 2 (OFL, Türkçe harfler tam).

**Bulut render:** 36 sn (4 çekirdek, 300 kare, CRF 16). 6 dakikalık video için ~20-25 dk (en hızlısı).

**6 dakikalık, iki konuşan 2B karakterli video için dürüst değerlendirme**
- Artı: Neyin ne olduğu yazıyla söylendiği için çok net; "koyun → taş" eşlemesi kelimeyle birebir görülüyor. Çok ucuz ve hızlı; sahne değiştirmek = kelime ve yol değiştirmek. Düz renkli 2B karakterlerle aynı dünyada rahat durur.
- Eksi: Kanal çok dilli sese gidecek; ekrandaki Türkçe kelimeler her dil için yeniden dizilmeli (görüntü dile bağımlı olur). Bu, "aynı görüntü, çok dilli ses" kararına ters.
- Eksi: Kelimeyle anlatmak "göster, ilan etme" ilkesine yarı yarıya ters; uzun videoda yorucu ve çocuksu gelebilir. Duvar yazıları geniş planda küçük ve kalabalık.
- Öneri: Tam video için değil; tanım anlarında (bir kavramın adı ilk kez konduğunda) kısa vurgu olarak.

## Dayanak tablosu
| Parça | Dayandığı doğru ya da karar |
|---|---|
| Akşam, 8 koyun ~0,73 sn arayla, her koyuna bir "taş", kesede tek "taş", son 3 sn yaklaşma + parıltı | ORTAK-BRIEF sahnesi; Blender RAPOR zamanlaması |
| Yalnız Türkçe kelime, rakam yok, doğru yazım (ş, ı, ç) | Görev; METIN G "Ekranda rakam yok"; yazı tipi Türkçe harfleri içeriyor (fontTools ile ölçüldü) |
| Çakıl kelimeleri sıcak altın, duvar kelimeleri gri | Blender tur 10: çakıl duvardan ayrışmalı |
| Koyunda küçük koyu baş | Görev: "tipografik ama görsel olarak açık" |
| Sonda direk yazıları soluklaşır | Tasarım kuralı 1: her anda tek odak |
| Sağ alt üçte bir yalnız çayır | Brief |
