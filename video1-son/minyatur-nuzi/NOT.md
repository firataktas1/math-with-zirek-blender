# Minyatür "Nuzi kabı" klibi (video 1, sahne H) · TEMSİLÎ CANLANDIRMA

**Tarih:** 2 Ekim 2026 · Dosyalar: `sahne.py` (Blender 5.2, Cycles + Freestyle, tamamen yordamsal, dış varlık yok),
`videolar/video1-son/klipler/minyatur-nuzi.mp4`, `minyatur-nuzi-kareler.png` (2 / 10 / 16 / 19,5 sn).

**Bu görüntü temsilîdir (canlandırma).** Gerçek Nuzi kabının (HSS 16 149) kopyası değildir: biçimi (içi boş, yumurta
biçimli kil kap), içinden çıkan taş sayısı (48) ve dönemi belgeye dayanır; renk, oda, sürü, kadeh, örtü ve kabın
yüzeyindeki işaretler süs amaçlı canlandırmadır. Kabın üstündeki çivi izleri **okunur bir yazı değildir**: rastgele dizilmiş
süs çivileridir (gerçek işaret, gerçek metin ya da herhangi bir dilde yazı yok). Ana videoda "temsilî" etiketi dil
dosyasından bindirilir.

## Ne
- Süre: video 201,007 → 221,291 sn; 609 kare, 30 fps, 1920×1080, sessiz. H.264 CRF 14, yuv420p, BT.709 (etiketler
  doğrulandı), vinyet yok, ek gren yok (gren boyada).
- 0-14,3 sn: geniş plan (pencereden uzakta küçük sürü: koyun ve keçi, toprağa dikili çoban değneği, tepede düz damlı
  kerpiç evler, altın gök; solda Nuzi tipi boyalı kadeh, hasır üstünde kamış kalem) → kamera yavaşça kaba süzülür.
- 14,87 sn: kabın üstünde çatlak belirir, kap hafifçe titrer. 15,33 sn: kap ikiye ayrılır, 48 taş dökülür,
  8 sütun × 6 sıra düzgün diziye yerleşir (son taş 18,0 sn'de iner, ~18,2 sn'de durur), kamera aynı anda geri çekilip
  diziyi kadraja alır (18,8 sn'de durur). 18,8-20,3 sn sabit.
- Kadraj: kap ve dizi sol-ortada; sağ üst (bindirme "48" ve etiketler) yalnız düz duvar sıvası ve hasır; sağ alt üçte
  bir yalnız hasır ve sedir yüzü (2B karakterler için).
- Görüntüde hiçbir dilde yazı, harf, rakam yok (kurucu kararı 1 Ekim: ~10 dilde izlenecek).

## Render (ölçüldü)
- Yalnız bulutta (herkese açık depo `firataktas1/math-with-zirek-blender`, iş akışı `sahne.yml`,
  `sahne=../video1-son/minyatur-nuzi`, `mod=tam`, `isler=15`, `ek=--harita 300`). İş akışı kareleri 300 üzerinden
  böldüğü için betik `--harita 300` ile her parçayı 609 karelik aralığa eşler (bitişik, örtüşmesiz, 40-41 kare/iş).
- 1920×1080, 32 örnek + Freestyle: kare başına ~30-33 sn. 15 paralel iş, en uzunu 25 dk; toplam **~332 koşucu
  dakikası** (ücretsiz). Kuyruk (aynı anda koşan öteki klip) yüzünden duvar saati ~90 dk. Önizleme turları
  (960×540, 16 örnek) ve 460. kare yaması ~4 dk ek.
- İş akışının birleştirme adımı bu klasör yolunda başarısız olur (çıktı adı `../` içeriyor); kullanılmadı. Video,
  buluttaki kayıpsız PNG parçalarından yerelde CRF 14 ile parça parça kodlanıp kayıpsız birleştirildi (disk dolu
  olduğu için karelerin hepsi aynı anda inmedi). Yerelde Blender render yapılmadı (yalnız sahne kurma denetimi).
- Yama: ilk tam render'da 460. karede kap yarıları kapalıyken çatlak bir kare inceliyordu; betik düzeltildi
  (kap 460'ta bütün kalır, yarılar 461'de), yalnız 460. kare bulutta yeniden render edildi.

## Dayanak tablosu (parça → dayandığı doğru ya da karar)
| Parça | Dayandığı doğru / karar |
|---|---|
| İçi boş, yumurta biçimli kil kap; içinden tam 48 taş | kokenler-dogrulama.md §2 (HSS 16 149, Oppenheim 1959): 48 koyun-keçi, 48 taş |
| Kap üstünde çivi izleri, ama okunmaz | METIN.md H "üstünde çivi yazısı"; görev "gerçek okunur metin yazma"; kurucu kararı 1 Ekim (görüntüde hiçbir dilde yazı yok) |
| Sürü koyun + keçi, çoban değneği | §2: "48 koyun ve keçi", çobana teslim |
| Kerpiç oda, düz damlı evler, dinî yapı yok | Nuzi kerpiç Hurri kenti (§2); görev: dinî motif yok |
| Nuzi tipi kadeh (koyu bantta beyaz geometrik süs) | Nuzi'ye özgü boyalı çanak çömlek türü; yalnız geometrik süs (dinî/figürlü motif yok) |
| İnsan figürü yok | Görev: yüz gerekmez; değnek çobanı temsil eder |
| Kap çatlar ve ikiye ayrılır | Taşlar ancak kap kırılınca çıkar; METIN.md H "kap açılır, 48 taş dökülür" |
| 8×6 düzgün dizi | Görev: düzgün dizi; ana video "48" bindirir; izleyici 48'i göz kararı değil düzen olarak görür |
| Zencefre taşlar | Sahne G'deki çobanın çakıllarıyla aynı renk: izleyici "benim taşlarım" bağını kurar (METIN 37 "torbamın aynısı") |
| Lacivert örtü | Taş ve kil renginden ayrışsın; telefonda 48 taş tek tek okunur (~55 px) |
| Kamera: geniş → kap → geri çekilme | Görev: 15,29 sn'ye kadar kap tanıtılır, kamera üstünde süzülür; açılışta dizi kadraja girer |
| Sağ üst ve sağ alt sakin | Görev: "48"/etiket bindirmesi ve 2B karakterler |
| Ortografik dik bakış, ışıksız boya, sepya kontur, altın pervaz, kâğıt greni | Onaylı minyatür tarzı (blender-deneme/minyatur) |
| Açılış 15,33 sn (461. kare), çatlak 14,87 sn'den | Görev: 15,29 sn'de açılır; çatlak hemen önce bir vuruş hazırlar |
| Yerleşme ~18,2 sn | Görev: ~18,5 sn'ye kadar yerleşir |
| Yalnız bulutta render | Görev kısıtı; laptop RAM düşük |
