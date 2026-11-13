# Geliştirme ve yayın standartları

## Her kod değişikliğinde

1. Mevcut mimari ve ilgili fazın kabul ölçütü esas alınır. Belgelenmemiş panel fonksiyonu veya parametresi tahminle kullanılmaz.
2. Girdi şeması, yetki sınırı ve hata davranışı koddan önce belirlenir. Geçersiz veya belirsiz durumda yetki artırılmaz ve özellik kendiliğinden açılmaz.
3. Değişen özelliğin normal akışı ve gerekli hata/istismar senaryoları yerelde test edilir. Test doubles ile elde edilen sonuç gerçek panel doğrulamasından ayrı belirtilir.
4. Yalnızca ilgili testler çalıştırılır. Başarılı kontroller gerekçesiz tekrarlanmaz; başarısızlık veya yeni değişiklik varsa etkilenen kontroller yenilenir.
5. Sonuçta değişen dosyalar, yapılan işlem, test sonucu ve kalan gerçek ortam engeli kısa raporlanır. Bilinen test hatası gizlenerek faz tamamlandı sayılmaz.

## Güvenlik ve veri sınırları

Root handler'ları küçültülür; tarayıcıdan gelen kullanıcı/rol/komut bilgileri güvenilir kimlik kabul edilmez. Shell üzerinden kullanıcı girdisi çalıştırılmaz. Dosya ve LSP erişimi her işlemde doğru kullanıcı/projeye bağlanır. Güvenlik kontrolünü devre dışı bırakan son kullanıcı ayarı eklenmez.

Site dosyası, oturum, anahtar ve parola loglanmaz. Tanılama çıktıları izin verilen alanlardan oluşur; ham istisna ve alt süreç çıktıları kullanıcıya kopyalanmaz. Testlerde gerçek sır veya üretim verisi kullanılmaz.

Sunucuya kurulum, bağımlılık/servis ekleme, panel yeniden başlatma ve test dosyası değiştirme kapsamı uygulanmadan önce gösterilir. Mevcut izinler tekrar tekrar sorulmaz. Salt okunur erişim izni yazma veya yeniden başlatma izni sayılmaz. Panelin çekirdek dosyaları ve kullanıcı projelerinin bağımlılıkları değiştirilmez.

## Yayına hazırlık

Marketplace kabulü şu anda doğrulanmış değildir. Yayın adayı için teknik asgari kayıtlar şunlardır:

- Desteklenen panel sürümü/edition, dağıtım, mimari, tarayıcı ve gerekli runtime matrisi.
- Tekrarlanabilir paket üretimi, sabit bağımlılıklar, dosya manifesti, hash ve üçüncü taraf lisans bildirimleri.
- Ürünün lisansı ve üçüncü taraf yeniden dağıtım koşulları netleşmeden lisans varsayımı veya izinsiz bağımlılık paketlemesi yapılmaması.
- Güncelleme, geri dönüş, devre dışı bırakma ve kaldırma testleri; site dosyalarının korunması.
- Oturum/CSRF, kullanıcılar arası erişim, dosya kaydetme ve LSP izolasyonu için geçerli test kanıtı.
- Sürüm notu, kurulum/kaldırma yönergeleri, sınırlar ve destek iletişim yöntemi.

Resmî marketplace başvurusu ve sağlayıcının ek kuralları paketleme fazında ayrıca araştırılır. Yerel testlerin geçmesi marketplace onayı veya bütün ISPmanager 6 sürümlerinde uyumluluk olarak sunulmaz.
