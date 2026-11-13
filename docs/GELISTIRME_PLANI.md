# ISPmanager Monaco Editor geliştirme planı

## Fazlar

Her fazın kabul ölçütleri ilgili özelliğin yayımlanmasının önkoşuludur. Bağımsız bileşenler yerelde geliştirilebilir; eksik güvenlik deneyleri tamamlanmış sayılmaz. Yerel test, test paneli ve canlı sunucu sonucu ayrı raporlanır. Marketplace çalışması bu planın dışındadır.

Bu bölüm ilk Faz 0 planının tarihsel durumudur; güncel özellikler ve doğrulanmış uyumluluk için [README](../README.md) esas alınır. Faz 0'ın sunucu envanteri yerel çalışma kaydı olarak tutulur ve genel depoya dahil edilmez. Kod ve yayın çalışmaları [geliştirme standartlarını](GELISTIRME_STANDARTLARI.md) izler.

Faz 0 deneyi için [root kontrol prototipi](../lab/phase0/README.md) kullanıcı tarafından kuruldu; `PHASE0_INSTALL_OK` ve `PHASE0_VERIFY_OK` alındı. Native `devel` yanıtında root formu doğrulandı. Prototip yalnızca kendi fonksiyonunu kaydeder; native dosya yöneticisine hook, kaydetme veya LSP eklemez. Tarayıcı görünümü, native dosya yöneticisi regresyonu ve root dışı erişim reddi bekleniyor. Root CLI formu HTTP oturum/CSRF veya kullanıcılar arası dosya izolasyon testinin yerine geçmez.

Yeni çıktı: [Monaco 0.1.2 native frame düzeltmesi](MONACO_ONIZLEME_KURULUM.md). Kurulu 0.1.1'in CLI ve gerçek HTTP yanıtına alan eklediği doğrulandı; Phoenix form kodunun `htmldata` dalını render etmediği gözlendi. Yeni pilot desteklenen native frame ve yalnızca aynı formun Ace değerini okuyan dar adapter kullanır. Yerel testler ve gerçek Ace/Chrome akışı geçti; kurulu 0.1.1 için hash kontrolü, bağımsız yedek ve atomik handler değişimiyle güncelleme hazırlanmıştır. Kullanıcı sunucuda 0.1.2 güncelleme ön kontrolünü, uygulamayı ve dosya doğrulamasını başarıyla tamamladı; gerçek tarayıcı görünümü, native regresyon ve normal hesap izolasyon kabulü bekliyor. Monaco'dan kaydetme ve LSP açılmaz.

0.2.0 ilerlemesi: 0.1.2'nin gerçek Monaco görünümü kullanıcı ekranıyla doğrulandı. [Düzenlenebilir tek editör ve sunucu genelinde varsayılanlar](EDITOR_0_2_0.md) yerelde hazırlandı. 20 JavaScript ve gerçek Python 3.6.15 altında 25 Python testi ile Chrome/Ace entegrasyonu geçti. Kaydetme panelin mevcut modeli/işlemi üzerinden yürür; yeni bir dosya yazma API'si yoktur. Gerçek sunucu kayıt testi, normal hesap/iki kullanıcı ret deneyleri, encoding/kota/oturum/çakışma kabulü ve LSP bekler. Önceki paragraflar tarihsel aşama kayıtlarıdır; fazlar topluca tamamlanmış sayılmaz.

0.2.1 dar düzeltme: kullanıcının 0.2.0 görüntüsü sonrasında yerleşim, başlıksız araç çubuğu, native ↔ Monaco geçişi ve sunucu ayar formu düzeltildi. 22 JavaScript, Python 3.6 altında 29 Python testi, yerel Chrome ve ZIP yükseltme/rollback geçti. Mevcut tercihler korunur; gerçek ayar menüsü ve kayıt kabulü bekler. [0.2.1 yönergesi](EDITOR_0_2_1.md).

0.2.2 dar geliştirme: kullanıcı 0.2.1 arayüzü/ayar menüsünü doğruladı. Editör araç çubuğu sadeleştirildi; varsayılan açık fullscreen, manuel/Esc çıkışı ve root-only Evet/Hayır ayarı eklendi. Eski tercih dosyası korunur; sürümlü yeni kopya kullanılır. Yerel 24 JavaScript/29 Python testi, Chrome ve yükseltme/rollback doğrulaması yapıldı; gerçek Phoenix fullscreen kabulü bekler. [0.2.2 yönergesi](EDITOR_0_2_2.md).

0.2.3 hata düzeltmesi: kullanıcı ayar kayıt sonrası beyaz ekran ve `tab_standalone=true` bildirdi. Eski handler ile gerçek native kayıt metodu kullanılarak blank durum tekrar üretildi. Başarılı kayıt artık tam form ve başarı metni; hata ise tam form/görünür mesaj döndürür, eski başarı metni temizlenir. Native metotlu yerel Chrome kayıt/reload/tekrar kayıt/hata testleri ve Python 3.6 doğrulaması yapıldı; canlı oturumlu panel kabulü ayrıca bekler. [0.2.3 hata ve doğrulama kaydı](EDITOR_0_2_3.md).

Kurulu sürüm düzeltmesi: kullanıcının salt okunur çıktısı 0.2.1 handler'ını doğruladı; 0.2.3'ün 0.2.2 taban kontrolü bu yüzden eksik dosyada duruyordu. [Doğrudan 0.2.1 → 0.2.3 paketi](EDITOR_0_2_3_FROM_0_2_1.md) aynı sabit 0.2.3 payload'ıyla hazırlanıp 10 ilgili Python 3.6 testi ve gerçek CLI akışıyla sınandı. Önceki kurulum sürümü hakkında görüntüden yapılan çıkarımlar sürüm kanıtı sayılmaz; canlı geçiş/kabul bekler.

0.2.4 UI düzenlemesi: kullanıcı 0.2.3 kurulumunu ve editör/ayar görünümünü doğruladı. İkonlu sağ işlem grubu, dosya yolu, fullscreen Esc açıklaması, iki temada başlık kontrastı ve token tabanlı etiket/parantez vurgusu eklendi. 15 ilgili JS testi, 8 Python 3.6 yükseltme testi, yerel Chrome yeni görünüm/mevcut akış kontrolleri ve paket CLI doğrulaması yapıldı; gerçek panel görünüm kabulü bekler. [0.2.4](EDITOR_0_2_4.md).

| Faz | İş | Tamamlanma ölçütü |
| --- | --- | --- |
| 0 | Ortam ve güvenlik deneyi | Tam sürüm/runtime envanteri; XML işlem ekleme, güvenli oturum, native dosya yetkileri, kaydetme/çakışma ve LSP sandbox yolunun doğrulanması |
| 1 | Salt okunur panel entegrasyonu | Dosya listesinden kontrollü prototip girişiyle Monaco açılır; root ve normal hesapta mevcut dosya yetkileri korunur; yanlış kullanıcı/dosya ve oturumsuz istek reddedilir; eklenti hatasında native editör davranışı sınanır |
| 2 | Düzenleme ve ayarlar | Doğrulama sonrasında standart **Düzenle** işlemi yetkili tüm hesaplarda Monaco'yu açar; manuel kaydetme, dil/mod, tema, girinti, boyut sınırı ve kaydedilmemiş değişiklik uyarıları; izin/encoding/çakışma kontrolleri geçer |
| 3 | PHP ve Laravel analizi | Kullanıcı/proje izolasyonuyla cross-file completion, hover ve definition; tanımlı Laravel örnekleri; analiz arızasında editör kullanılabilir kalır |
| 4 | Paketleme ve uyumluluk | Pilot kurulum/güncelleme/geri dönüş/kaldırma; hedef RPM/DEB ve panel sürümleri için doğrulanmış destek matrisi |

## Faz 0 kararları

Test sunucusunda işlem yapılmadan önce erişim yöntemi ve root yetkisi netleştirilir; kimlik bilgileri dokümana yazılmaz. İlk envanter okuma amaçlıdır. Kurulum, yeni servis, bağımlılık, panel yeniden başlatma ve test dosyası yazma işlemleri kapsamları gösterilerek ayrıca onaylanır.

Kaydedilecek bilgiler: panel/COREmanager tam sürümleri, dağıtım, mimari, aktif arayüz, panel dosya limitleri, mevcut runtime'lar, test kullanıcıları ve kaynak kapasitesi. Kullanıcının bildirdiği `ispmanager-6-5.450` değeri güncel `6.x` sürüm numarası varsayılmaz.

| Karar | Deney | Sonuç yetersizse |
| --- | --- | --- |
| Dosya listesindeki giriş | Gerçek `file` XML'inde seçili dosya ve işlem parametreleri | Tahminî alan adıyla entegrasyon yazılmaz |
| Native editörden geçiş | Kirli tampon, kaydet/iptal, pencere kapatma | Sadece dosya listesinden açma kullanılır |
| Oturum ve CSRF | Frame'den panel isteği; çıkış/expiry/rol değişimi; kötü origin | Güvenli native yol bulunmadan veri erişimi açılmaz |
| Dosya izinleri | İki kullanıcı, rol/fonksiyon kısıtları, symlink ve izin iptali | Root dosya yazıcısına geçilmez; ilgili özellik durdurulur |
| Güvenli içerik taşıma | Çok satırlı ve limit boyutunda içerik; sırların URL/argv/loglara düşmemesi | Güvensiz taşıma kullanılmaz |
| Kaydetme semantiği | Eşzamanlı native/SFTP yazma, ağ kopması, encoding ve sahiplik | Kalan risk/çözüm kararlaştırılana kadar yazma kapalı |
| PHP sağlayıcısı | Lisans, ayrı CLI runtime, çalışma zamanı kod/konfigürasyon yükleme davranışı | Sağlayıcı değişir veya analiz kapalı kalır |
| Worker izolasyonu | Proje dışı dosya/ağ/süreç erişimi ve kaynak limitleri | Sandbox gevşetilmez; worker başlatılmaz |

Faz sonunda transport, handler dili, LSP sağlayıcısı ve minimum destek sürümleri kanıtlarıyla kaydedilir. Bu teknik kararlar kesinleşmeden paket veya üretim uyumluluğu ilan edilmez.

## Dar kapsamlı doğrulama

| Alan | Gerekli hata veya mantık testi |
| --- | --- |
| Panel entegrasyonu | İşlemin yalnızca uygun dosyada görünmesi; malformed XML, handler çökmesi ve eklenti kapalıyken native editör |
| Yetkilendirme | A kullanıcısının B dosyasını/projesini okuyamaması; sahte kullanıcı/rol/su parametresi; doğrudan fonksiyon çağrısı |
| Dosya sınırları | Traversal ve encoded yol, symlink kaçışı/değişimi, özel dosya, uzantısı değiştirilmiş binary ve boyut aşımı |
| Oturum | Çıkış/expiry/kullanıcı değiştirme; CSRF ve kötü origin; LSP bağlantısının iptali |
| Güvenli metin | PHP/HTML içeriği, zararlı dosya adı ve LSP Markdown'ının script/komut/uzak istek çalıştırmaması |
| Kaydetme | UTF-8/Türkçe, desteklenen encoding, BOM ve LF/CRLF; izin reddi, disk/kota hatası, eşzamanlı yazma, belirsiz zaman aşımı ve çift tıklama |
| Kirli tampon | Native'den geçiş, sekme kapatma, salt okunura geçiş ve bağlantı kaybında sessiz içerik kaybı olmaması |
| LSP | İki proje/iki oturum tampon ayrımı; kaçak URI, applyEdit/executeCommand, zehirli proje config'i, worker çökmesi, limit aşımı ve boşta kapanma |
| Laravel | Ayrı Controller/Service/Model dosyalarında completion; vendor sembolü; PHPDoc/helper ile Eloquent; statik route/view ve Blade örneği |
| Yaşam döngüsü | Tekrarlı aç/kapat sonrası model/worker temizliği; başarısız güncelleme sonrası geri dönüş; kaldırmada site dosyalarının korunması |

Fixture'lar ayrı test projelerinde tutulur. Laravel kabul testleri veritabanı, gerçek e-posta veya dış servis kullanmaz. Kod oluştuğunda yalnızca değişen özelliğin gerekli testleri çalıştırılır; her küçük değişiklikte tüm proje testi, build veya bütün dağıtım matrisi tekrarlanmaz. Paket üretiminde frontend build ve ilgili entegrasyon kontrolleri gerekir.

## Uyumluluk yaklaşımı

İlk hedef kullanıcının Rocky Linux 8.10 x86_64 ve Lite ortamıdır. Sonraki matris güncel desteklenen RPM ve DEB tabanlı dağıtımları, Lite/Pro/Host'u ve hedef arayüzleri kapsar. Sürüme bağlı XML ve API farklılıkları tek adapter katmanında tutulur; iş mantığında dağıtım dalları çoğaltılmaz. Bilinmeyen sürümde çalışıyor varsaymak yerine ilgili kabiliyet kontrol edilir; uyumsuz özellik kapalı kalır.

Her matris satırı panel sürümü, COREmanager, dağıtım, edition, arayüz, PHP analiz runtime'ı, tarayıcı ve test sonucunu taşır. Temel editör ile PHP/Laravel analiz desteği ayrı işaretlenir. Tüm tarihsel ISPmanager 6 sürümlerine destek sözü verilmez. Business doğrulanmadan aynı paketle desteklenmiş sayılmaz.

## Netleşenler ve açık noktalar

Netleşen kapsam: Monaco tabanlı dosya editörü ve PHP/Laravel proje genelinde akıllı tamamlama. Standart File Manager **Düzenle** işlemiyle root, yönetici ve normal hesapların mevcut dosya yetkileri kapsamında aynı editörün açılması hedeflenir. Kullanım için normal hesaba geçmek gerekmez; ayrı hesaplar güvenlik testinde gereklidir. Test sunucusu mevcut. Hedef, birden fazla güncel ISPmanager 6 ortamında çalışabilen paketli eklentidir.

Geliştirme öncesi ortamdan doğrulanacaklar: tam sürüm, root kurulum erişimi, ayrı test kullanıcıları/projeleri, runtime ve kapasite. Erişim bilgileri kullanıcıdan güvenli kanal üzerinden alınır; plana eklenmez.

Kullanıcıyla ayrıca kararlaştırılacak bir sonuç çıkarsa yalnızca o karar sorulur: native kaydetmede kalan eşzamanlı yazma riski, yeni runtime/servis ihtiyacı veya Laravel'in dinamik özellikleri için uygulama çalıştırma talebi. Güvenlik sınırı gevşetilerek sessiz alternatif uygulanmaz.
