# Monaco Editor 0.2.1 — yerleşim, editör geçişi ve ayar formu

Bu sürüm kurulu 0.2.0'dan yükseltme içindir. Kullanıcının 9 Kasım 2026 görüntüsü, 0.2.0 düzenlenebilir görünümünü doğruladı; gerçek dosya kaydı ve normal hesap izolasyonu için ayrıca kabul gerekir.

## Değişiklikler

- Monaco, native kod alanının hemen önüne eklenir. Dosya adı ve encoding/UTF-8 kontrolleri üstte, editör altta kalır. Native alanların sırası/içeriği değiştirilmez; birden fazla kod alanı varsa ekleme yapılmaz.
- Editör üstündeki **Monaco Editor** başlığı kaldırıldı; kısa kaydetme açıklaması ve araçlar kaldı. Düzenlenebilir/salt okunur durum alt çubukta gösterilir.
- **Mevcut editöre dön** sonrasında yalnızca native editör ve küçük bir **Gelişmiş editöre geç** çubuğu görünür. Dosyayı kapatmadan tekrar Monaco'ya geçilir. Geçiş native tamponun en güncel metnini alır; diski yeniden okumaz ve kaydedilmemiş native değişiklikleri üzerine yazmaz. Salt okunur izin korunur; kaynak alan değişmişse geçiş reddedilir ve native kullanılabilir kalır.
- Root **Sunucu varsayılanları**, yeni boş tarayıcı penceresi yerine mevcut Phoenix panelinin sabit `#/form?func=ismonaco.settings` rotasını açar. Menü kaydında action/type açıkça belirtilir. Ayar handler'ı tam form metadata'sı, beş alan, seçenekler, mevcut değerler, butonlar ve mesajları döndürür. Önceki handler yalnızca değerleri döndürüyordu; XML handler'ın tam yanıtı STDOUT'a vermesi [resmî belgede](https://www.ispmanager.com/docs/developer-guide/xml-description-of-pages) anlatılır. Gerçek Phoenix form/menü kabulü güncelleme sonrasında teyit edilecek.

## Korunan davranış

Koyu tema, yazı 14, satır kaydırma/kod haritası açık, yükseklik 760 px ilk varsayılanlarıdır; root sunucu genelinde değiştirebilir. Mevcut `/usr/local/mgr5/etc/ismonaco-editor/defaults.json` dosyası yükseltme ve geri dönüşte **üzerine yazılmadan** korunur. Sahiplik/izin/şema doğrulanır; mevcut root ayarlarının başlangıç hash'inden farklı olması hata sayılmaz. Yeni ayarlar yeni açılan editörlerde uygulanır.

Dosya kaydetme hâlâ panelin mevcut Ace modeli ve native Kaydet işlemlerinden geçer. Yeni site dosyası endpoint'i, yetki genişletmesi, otomatik kaydetme, LSP veya ek CAS/eşzamanlı-yazma garantisi yoktur. Önceki [0.2.0 güvenlik ve kabul sınırları](EDITOR_0_2_0.md) geçerlidir. Aktarım hatasında bekleyen Monaco metni korunur ve uyuşmayan kayıt engellenir; metinden vazgeçmek açık onay ister. Native moda geçtikten sonra Monaco'nun görünmeyen eski tamponu kayıt yapmaz. Geçiş yalnızca aynı formun aynı Ace kaynağına dönebilir.

## 0.2.0 → 0.2.1 kurulum

Önce açık düzenlemeleri kaydedip dosya sekmelerini kapatın. `ismonaco-editor-0.2.1.zip` ve `.sha256` dosyalarını File Manager üzerinden `/root` içine yükleyin. Bunlar **Shell-client / Bash** komutlarıdır:

```sh
cd /root && sha256sum -c /root/ismonaco-editor-0.2.1.sha256 && mkdir -m 700 /root/ismonaco-editor-0.2.1-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-editor-0.2.1.zip /root/ismonaco-editor-0.2.1-stage && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.1-stage/update.py --check
```

Beklenen son satır `MONACO_EDITOR_UPDATE_CHECK_OK`. Hata varsa uygulamaya geçmeyin; çıktıyı paylaşın. Stage klasörü varsa silmeyin/üzerine çıkarmayın.

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.1-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.1-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Beklenen `MONACO_EDITOR_UPDATE_APPLY_OK`, `MONACO_EDITOR_VERIFY_OK`. Son komut eklentinin değişen XML kaydını yüklemek için panel sürecini kısa süre yeniden başlatır. Sonra paneli yenileyip dosyayı yeniden açın.

Yeni `addon/ismonaco_0_2_1.py`, `.sh` ve `skins/ismonaco-editor-0.2.1/` eklenir; en son sadece eklenti XML kaydı değiştirilir. XML yedeği `etc/xml/ispmgr_mod_ismonaco_preview.xml.pre-0.2.1` olur. 0.2.0 dosyaları, sunucu tercihleri, Phase 0 ve siteler korunur. Eski ZIP'ler yeniden üretilmez.

## Dar kapsamlı gerçek panel kabulü

1. Bir test dosyasında dosya adı/UTF-8 alanlarının üstte, tek editörün altta olduğunu ve üst başlığın kalktığını kontrol edin.
2. Monaco'da bir değişiklik yapın → mevcut editöre dönün → native'de başka bir değişiklik yapın → gelişmiş editöre geçin. En son metin korunmalı; dosyayı kapatmak gerekmemeli. Test dosyasında native Kaydet ve yeniden açma ile doğrulayın.
3. Root **Sunucu varsayılanları** düğmesine basın. Aynı panelde beş ayarlı dolu form açılmalı; yeni boş tarayıcı sekmesi açılmamalı. Bir ayarı kaydedip yeni açılan editörde kontrol edin. Normal kullanıcı ayar fonksiyonuna erişememelidir.

Gerçek panelde ayar formu hâlâ açılmazsa yalnızca şu salt okunur çıktıyı paylaşın; dosya içeriği, parola veya oturum bilgisi gerekmez:

```sh
/usr/local/mgr5/sbin/mgrctl -m ispmgr -o xml ismonaco.settings
```

Bu fonksiyonun yanıtında sadece görünüm ayarları/form tanımı bulunur.

## Geri dönüş

Açık değişiklikleri kaydedip sekmeleri kapattıktan sonra:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.1-stage/update.py --rollback && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Beklenen `MONACO_EDITOR_UPDATE_ROLLBACK_OK`. 0.2.0 XML kaydı geri gelir; ayarlar ve yeni sürüm dosyaları korunur. Kısmi kurulumda otomatik silme yapılmaz; rollback tam yeni kurulum doğrulaması ister.

## Yerel doğrulama

Akış: native File Manager formu → dosya adı/encoding altında Monaco → native editöre geçiş ve kaydedilmemiş değişiklik → yeniden Monaco → root ayar rotası ve dolu form.

Browser plugin mevcut olmadığından kurulu Playwright/Chrome kullanıldı. Testler `http://127.0.0.1:8766`, 1440×1100 ve 390×844 görünümde gerçek Monaco/Ace ile yerel sentetik form üzerinde yürütüldü. Sayfa kimliği, boş ekran/overlay, konsol hatası, görünüm sırası, başlık yokluğu, tek aktif editör, çift yönlü geçiş, içerik korunması, readonly ve ayar rotası/form alanları doğrulandı. Yerel Native Save diske yazmayan simülasyondur; gerçek Phoenix menü/kayıt ve normal hesap izolasyon testi değildir.


Sonuç: 22 ilgili JavaScript testi ve gerçek Python 3.6.15 altında 29 ilgili Python testi geçti. Wrapper parametre sınırları ve temiz ortam regresyonu kapsandı. ZIP ile ağsız geçici container'da canonical 0.2.0 install → değiştirilmiş mevcut tercihlerle update check/apply → verify → kurulu wrapper üzerinden tam ayar GET/SET ve root dışı ret → native form adapter → rollback → 0.2.0 verify başarılı. Ayar dosyasının byte/inode/zaman damgasının yükseltmede değişmediği, eski handler'ların korunduğu doğrulandı. Gerçek sunucuya agent tarafından işlem yapılmadı. Paketlemedeki son değişiklik yalnızca bu test kaydıdır; sınanan payload manifesti korunmuştur.
