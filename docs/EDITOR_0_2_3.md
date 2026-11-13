# Monaco Editor 0.2.3 — ayar kaydından sonra beyaz ekran

## Hata ve düzeltme

Kullanıcı sunucu varsayılanlarını kaydettikten sonra boş içerik ve başlıksız sekme bildirdi; adresinde `tab_standalone=true` olduğunu teyit etti. Sonraki salt okunur tanılamada sunucuda kayıtlı handler'ın 0.2.1 olduğu doğrulandı. Aynı ok-only yanıt hatası 0.2.1 ve 0.2.2'de bulunur; yerel tekrar testinde canonical 0.2.2 baseline kullanıldı. Bu sunucu için [doğrudan 0.2.1 yükseltmesi](EDITOR_0_2_3_FROM_0_2_1.md) kullanılmalıdır. Eski handler başarılı yazmadan sonra yalnızca `<ok/>` döndürüyordu. Phoenix'in `applyFormSubmitResponse` metodu, standalone sekmede bu yanıtı tab'ın yeni dokümanı olarak kullanıyor. Yanıtta metadata olmadığı için form ve başlık kayboluyor. Bu, ayar dosyasına yazmanın başarısız olduğunu tek başına göstermez.

Yeni başarılı kayıt yanıtı aynı formun tam metadata'sını, altı alanın kaydedilmiş değerlerini, seçeneklerini, düğmelerini ve **Ayarlar kaydedildi. / Settings saved.** mesajını içerir. Boş `<ok/>`/yönlendirme döndürmez. Ayar ekranı kayıt sonrası açık kalır; kullanıcı tekrar kaydedebilir veya Kapat düğmesini kullanabilir. Geçerli bir form sayfasının işlem yanıtı olabileceği [resmî XML yanıt belgesinde](https://www.ispmanager.com/docs/developer-guide/xml-description-of-pages) açıklanır.

Geçersiz değer, yapılandırma I/O hatası ve yetki reddinde artık native `<error><msg>` metni bulunur. Özellikle Phoenix'in `getError()` yolu bu metni okur; yalnızca error type/code döndürmek anlamlı hata bildirimi için yeterli değildir. Mesajlar sabittir; girilen özel değer, dosya yolu veya exception ayrıntısı yansıtılmaz. Hatalı kayıt başarı olarak gösterilmez; önceki başarılı kaydın mesajı da temizlenir. Root hata yanıtı güvenli değerlerle tam form taşır.

Dosya editörü, fullscreen, düğmeler, dosya kaydetme ve yetki akışı değiştirilmedi. Frontend yeniden build edilmedi; 0.2.2'nin test edilmiş statik dosyaları yeni sürüm dizinine aynı byte'larla paketlenir. Yeni paket handler düzeltmesi ve sürüm kaydı içindir.

## Doğrulamanın önceki testlerden farkı

- Canonical 0.2.2 ZIP'inden **gerçek eski Python handler'ı** çalıştırıldı.
- Panelin public `chunk-DL5dh_45.js` dosyasındaki **gerçek `applyFormSubmitResponse` metodu**, SHA-256 ile sabitlenerek yerel testte kullanıldı. Eski yanıtla standalone sekmede metadata kaybı ve beyaz form tekrar üretildi.
- Yeni gerçek Python handler'ının yanıtı aynı native metoda verildi. Standalone ve normal sekmede başarılı kayıt sonrası altı alan ve başlık korundu. Sayfayı yeniden açınca değerler diskten okundu; ikinci kayıt da dolu form döndürdü.
- Geçersiz değer, simüle I/O hatası ve root dışı ret; görünür mesaj, formun korunması ve kayıt dosyasının bozulmaması açısından kontrol edildi. Kaydetme sadece geçici yerel config üzerinde yapıldı.
- Browser plugin mevcut olmadığından Playwright/Chrome kullanıldı. `127.0.0.1:8767`, 1200×900 ve 390×844; sayfa kimliği, eski blank durumunun tekrarı, yeni form/başlık, başarı/hata metni, tekrar kayıt, yeniden açma, konsol ve dış istek kontrolleri geçti.

Önemli sınır: native kayıt metodu gerçektir; tab servisi, DOM render ve XML→JSON çevrimi yerel test ortamında modellenmiştir. Bu, oturum açılmış tam Phoenix panelinde canlı POST testi değildir. Agent panel oturumu veya SSH kimlik doğrulaması üzerinden canlı ayar yazmadı. Sunucuya yükledikten sonra aşağıdaki tek kabul akışıyla gerçek panel sonucu teyit edilmelidir. Önceki yerel testler bu standalone yanıt tüketimini kapsamıyordu; test sayıları canlı UI kabulü yerine gösterilmemelidir.

Kanıt özeti: `tests/fixtures/ispmanager-6.155.0/phoenix-settings-submit-contract.json`. Kapalı kaynak panel JS'i kaynak koduna veya dağıtım ZIP'ine kopyalanmaz; test aracı açıkça verilen yerel bundle'ı hash doğrulamasıyla okur.

## 0.2.2 → 0.2.3 yükseltme

Açık dosya düzenlemelerini kaydedip sekmeleri kapatın. ZIP ve SHA-256 dosyasını `/root` içine yükleyin. Shell-client'te:

```sh
cd /root && sha256sum -c /root/ismonaco-editor-0.2.3.sha256 && mkdir -m 700 /root/ismonaco-editor-0.2.3-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-editor-0.2.3.zip /root/ismonaco-editor-0.2.3-stage && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.3-stage/update.py --check
```

`MONACO_EDITOR_UPDATE_CHECK_OK` gelirse:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.3-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.3-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Beklenen `MONACO_EDITOR_UPDATE_APPLY_OK`, `MONACO_EDITOR_VERIFY_OK`. Son komut yalnızca panel sürecini kısa süre yeniden başlatıp yeni handler/XML kaydını yükler. Hata varsa ilerlemeyin; mevcut stage'i silmeyin. Paneli yenileyip eski boş ayar sekmesini kapatın; soldaki menüden yeni ayar ekranını açın.

Güncelleme `defaults-v2.json` dosyasını değiştirmez; mevcut tercihler korunur. Yeni sürümlü handler/statik dosyalar hazırlanır ve en son sadece eklenti XML kaydı değiştirilir; önceki XML `.pre-0.2.3` yedeğinde tutulur. Eski sürüm ZIP'leri, handler'ları, statik dosyaları ve site dosyaları korunur.

## Gerçek panel kabulü

1. Monaco Settings'i soldaki menüden açın. Altı ayar ve başlık görünmeli.
2. Bir görünüm ayarını değiştirip Kaydet'e basın. Form ve başlık kalmalı; **Settings saved. / Ayarlar kaydedildi.** mesajı görünmeli.
3. Aynı ekranda tekrar Kaydet'e basın; form boşalmamalı.
4. Ayar sekmesini kapatıp yeniden açın; kaydedilen değer gelmeli. Bir test dosyası açıp tercihin uygulandığını kontrol edin.

Bu dört adım gerçek sunucuda tamamlanmadan canlı kabul tamamlandı sayılmaz. Site dosyası üzerinde kayıt testi bu hotfix'in kapsamı değildir.

## Geri dönüş

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.3-stage/update.py --rollback && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

0.2.2 XML kaydını geri yükler; global tercihler ve yeni dosyalar korunur. Önceki sürüm ayar-kaydı blank hatasını içerdiğinden geri dönüş bu hatayı da geri getirir. Kısmi kurulumda otomatik silme yapılmaz; rollback tam yeni kurulum doğrulaması ister.


Yerel Python doğrulaması: başlangıçta 31 ilgili handler/kurulum/yükseltme testi gerçek Python 3.6.15 altında geçti. Ardından başarıdan sonra hata mesajı temizliği regresyonu eklendi; değişen backend için 14 test geçti (toplam ilgili test sayısı 32). Frontend uygulaması değişmediği için editörün genel test/build'i tekrarlanmadı. ZIP'in 30 frontend dosyasının 0.2.2 ile byte düzeyinde aynı olduğu doğrulandı.


Nihai ZIP CLI doğrulaması ağsız geçici Python 3.6.15 container'ında geçti: 0.2.2 install → eski kurulu wrapper'da ok-only yanıt → 0.2.3 check/apply/verify → yeni kurulu wrapper'da tam form/başarı, tekrar kayıt ve GET → geçersiz değer/yetki mesajı → verify → rollback → 0.2.2 verify. Güncellemede mevcut config byte/inode/zaman damgası, eski handler'lar ve geri dönüşte son kullanıcı tercihleri korundu. Paketlemede son değişiklik yalnızca bu kayıt; sınanmış payload manifesti değişmedi.
