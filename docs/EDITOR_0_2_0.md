# Monaco Editor 0.2.0 — kontrollü sunucu denemesi

Bu sürüm, çalışan 0.1.2 önizlemesini düzenlenebilir Monaco arayüzüne yükseltir. Standart File Manager **Düzenle** ekranında tek editör görünür. Monaco hazır olup kendi formundaki native Ace ve Kaydet kontrolleri doğrulandıktan sonra yalnızca native kod alanı gizlenir. Monaco değişiklikleri aynı Ace modeline aktarılır; diske yazmayı panelin kendi **Kaydet / Kaydet ve kapat** işlemi yapar. Ctrl/⌘+S de native kısayola iletilir. Eklenti site dosyalarını açan/yazan ayrı root endpoint'i oluşturmaz.

Root ve normal kullanıcı için arayüz aynıdır; erişim ve kaydetme izinlerinin kaynağı ISPmanager'dır. Native salt okunur durum korunur. Yetki iptali, kota, disk ve oturum hatalarının gerçek sunucu kabulü ayrıca yapılmalıdır. Sunucuda normal test hesabı bulunmadığından gerçek hesaplar arası izolasyon henüz doğrulanmamıştır.

## Sunucu genelindeki varsayılanlar

| Ayar | İlk değer | Seçenekler |
| --- | --- | --- |
| Tema | Koyu | Koyu / Açık |
| Yazı | 14 px | 12, 14, 16, 18, 20 |
| Satır kaydır | Açık | Açık / Kapalı |
| Kod haritası | Açık | Açık / Kapalı |
| Toplam editör yüksekliği | 760 px | 620, 760, 900, 1080 |

Root, **Monaco ayarları** menüsünden veya editördeki **Sunucu varsayılanları** bağlantısından bu beş ayarı bütün kullanıcılar için kaydeder. Ayarlar yeni açılan editörlerde uygulanır; açık tamponlar yeniden yüklenmez. Editördeki kontroller yalnızca o açık görünümü değiştirir, sunucu varsayılanını değiştirmez. Tarayıcı depolaması kullanılmaz.

Kalıcı dosya `/usr/local/mgr5/etc/ismonaco-editor/defaults.json`, root:root 0600; kendi dizini 0700'dür. Ayar fonksiyonu hem `AUTH_USER=root` hem `AUTH_LEVEL=30` ister; istek parametrelerinden kimlik kabul etmez. Sabit şema ve seçenek listesi uygulanır. Yazma aynı dizindeki özel geçici dosyadan atomik değiştirmeyle yapılır. Symlink, uygunsuz sahiplik/izin, özel dosya veya bozuk şema reddedilir. Okuma hatasında görünüm güvenli sabit varsayılanlara döner; yetki genişlemez. `--verify`, bu değiştirilebilir dosyada başlangıç hash'i yerine izin/sahiplik/şema doğrular; diğer payload'larda byte/hash kontrolü sürer.

## 0.1.2'den yükseltme

Önce açık dosya değişikliklerini panelin mevcut yöntemiyle kaydedip düzenleme sekmelerini kapatın. `ismonaco-editor-0.2.0.zip` ve aynı adlı `.sha256` dosyasını File Manager ile `/root` içine yükleyin. Aşağıdakiler **Shell-client / Bash** komutlarıdır. Kodları tek satır halinde yapıştırın; DevTools JavaScript alanına yazmayın.

```sh
cd /root && sha256sum -c /root/ismonaco-editor-0.2.0.sha256 && mkdir -m 700 /root/ismonaco-editor-0.2.0-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-editor-0.2.0.zip /root/ismonaco-editor-0.2.0-stage && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.0-stage/update.py --check
```

Beklenen son satır: `MONACO_EDITOR_UPDATE_CHECK_OK`. Ön kontrol, kurulu 0.1.2'nin canonical manifestini, 33 dosyasını ve yeni hedeflerde çakışma olmadığını doğrular. Hata alırsanız ikinci komuta geçmeyin; çıktı kodunu paylaşın. Var olan stage dizinini silmeyin veya üzerine çıkarmayın.

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.0-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.0-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Beklenen: `MONACO_EDITOR_UPDATE_APPLY_OK` ve `MONACO_EDITOR_VERIFY_OK`. Son komut, değişen XML handler/fonksiyon kaydının yüklenmesi için panel sürecini kısa süre yeniden başlatır. Web/PHP/veritabanı servislerini yeniden başlatma komutu yoktur. Ardından paneli yenileyip dosyayı yeniden açın.

Yükseltme yeni sürümlü `addon/ismonaco_0_2_0.py`, `.sh`, `skins/ismonaco-editor-0.2.0/` ve ayar dosyasını ekler; en son yalnızca eklentinin XML kaydını atomik değiştirir. Önceki XML, `etc/xml/ispmgr_mod_ismonaco_preview.xml.pre-0.2.0` olarak korunur. Eski handler, statik dosyalar, Phase 0 lab'ı, panel çekirdeği, PHP ve site dosyaları değiştirilmez. Kısmi kurulumda otomatik silme yapılmaz; hata koduyla durulur.

## İlk gerçek panel testi

1. Root File Manager'da yalnızca bu test için oluşturduğunuz küçük UTF-8 dosyayı açın. Üretim `index.php` üzerinde ilk kayıt denemesini yapmayın.
2. Tek Monaco görünümü, koyu tema, 14 px, açık kaydırma/harita ve 760 px yüksekliği kontrol edin.
3. Zararsız bir metin değiştirip panelin **Kaydet** düğmesini kullanın; dosyayı kapatıp yeniden açarak kaydı doğrulayın. Ctrl/⌘+S ve **Kaydet ve kapat** işlemini de test dosyasında sınayın.
4. Root **Monaco ayarları** ekranında varsayılanı değiştirin. Yeni açılan editörde uygulandığını doğrulayın; sonra istediğiniz değerlere dönebilirsiniz.
5. **Mevcut editöre dön** ile native editörün açıldığını ve iki düzenlenebilir editörün birlikte kalmadığını kontrol edin.

Normal hesapta gerçek açma/kaydetme ve iki ayrı kullanıcı arasında ret testi, hesaplar hazır olduğunda ayrıca yapılacak. Yerel sentetik root/normal testleri bunun yerine sayılmaz.

## Hata ve güvenlik sınırları

- Yanlış/çift alan, kopan veya değişen form, native API/kaydetme metadata uyumsuzluğu, 512 KiB metin sınırı veya başlangıç hatasında native alan gizlenmez.
- Aktarım sırasında eşleşme/setter hatası olursa Monaco salt okunura alınır, bekleyen metin bellekte korunur ve native alan geri gösterilir. Bu durumda iki görünüm sadece kurtarma içindir. Uyuşmayan metnin native Kaydet üzerinden gönderilmesi engellenir; kopyalama yalnızca açık kullanıcı tıklamasıyla yapılır. Bekleyen metinden vazgeçme açık onay ister.
- Native modelin encoding/reload değişikliği Monaco'ya yansır. BOM ve CRLF yerel testte korundu. Diğer encoding'lerin, ağ kopmasının ve gerçek disk/kota hatalarının kabulü bekler.
- Yeni bağımsız kaydetme protokolü, otomatik kaydetme veya atomik eşzamanlı-yazma garantisi eklenmez. Native `savetime`, oturum/CSRF, izin ve hata davranışı devralınır. SFTP/başka sekmeyle eşzamanlı yazmada native panelin mevcut çakışma sınırları geçerlidir; bu sürüm ilave CAS garantisi vermez.
- Monaco frame'i aynı origin'dedir ve origin izolasyonu değildir. Paket script'leri güvenilir bileşendir. İçerik HTML, URL, süreç argümanı, log veya tarayıcı depolamasına yazılmaz. Frame URL'sindeki public nonce/ayarlar/kontrol adları erişim yetkisi değildir.
- PHP/Laravel LSP ve marketplace dağıtımı bu sürüme dahil değildir. Bu paket kontrollü deneme adayıdır; bütün ISPmanager 6 sürümleri için uyumluluk ilan edilmez.

## Geri dönüş

Önce açık değişiklikleri kaydedip sekmeleri kapatın. Kendi XML yedeği ve payload doğrulamalarından sonra 0.1.2 kaydı geri yüklenir. Yeni sürüm dosyaları ve sunucu ayarları silinmez.

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.0-stage/update.py --rollback && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Beklenen `MONACO_EDITOR_UPDATE_ROLLBACK_OK`; paneli yenileyip dosyayı yeniden açın. Ön kontrol/uygulama yarıda kesilirse bu komutu körlemesine kullanmayın: rollback tam yeni kurulum doğrulaması ister.

## Yerel doğrulama kaydı

- 20 ilgili JavaScript testi geçti: form/kimlik eşleşmesi, tek editör, readonly/yetki değişimi, setter hatası, boyut ve ayar doğrulaması, yaşam döngüsü.
- 25 ilgili Python testi ağsız gerçek Python 3.6.15 container'ında geçti: root ayar erişimi, sahte parametre reddi, güvenli config, XML transform, kurulum, çakışma ve geri dönüş.
- Gerçek Monaco + Ace kullanılan yerel Chrome senaryosu 1440/390 px'te geçti: root/normal sentetik formlar, varsayılanlar, düzenleme, native model/Save simülasyonu ve Ctrl/⌘+S, BOM/CRLF, undo/redo, reload, readonly, hata/fallback, yanlış/çift form, dış istek ve script çalıştırma kontrolü. Native Save simülasyonu dosyaya yazmaz; gerçek sunucu kaydı henüz yapılmadı.
- ZIP payload'larıyla gerçek CLI akışı ağsız Python 3.6.15 container'ında geçti: canonical 0.1.2 install → 0.2.0 update check/apply → verify → kurulu shell wrapper üzerinden root ayar GET/SET ve root dışı ret → değişmiş ayarlarla verify → root/normal native form adapter → rollback → 0.1.2 verify. Eski handler byte'ları/zaman damgaları ve geri dönüşte yeni ayarlar korundu. `/usr/local/mgr5` yalnızca geçici container tmpfs'iydi; host proje salt okunur bağlandı. Container panel süreci çalıştırmadığından gerçek `mgrctl exit`/Phoenix menü kabulü bekler. Son paketlemede yalnızca bu test kaydı README'ye eklendi; test edilmiş payload manifesti değişmedi.
