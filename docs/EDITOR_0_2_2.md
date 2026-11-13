# Monaco Editor 0.2.2 — tam ekran

## Değişen editör

- Editör araç çubuğundan **Sunucu varsayılanları** kaldırıldı; soldaki **Monaco Settings / Monaco ayarları** menüsü kullanılmaya devam eder.
- **Mevcut editöre dön** düğmesinin adı **Normal editör** oldu. Geri dönüş için **Gelişmiş editöre geç** korunur.
- **Tam ekran** / **Tam ekrandan çık** düğmesi eklendi. Dosya ilk açılışta varsayılan olarak tam ekran gelir. Esc ile çıkılır; arama gibi Monaco kontrolleri Esc'yi kullanıyorsa önce o kontrol kapanabilir.
- Soldaki ayarlara **Varsayılan tam ekran: Evet/Hayır** eklendi. Sunucu genelinde bütün hesapların yeni açılan editörlerine uygulanır. Hayır seçilince normal 760 px veya mevcut tercih edilen yükseklikle açılır; kullanıcı düğmeyle yine tam ekrana geçebilir.
- Tam ekranda **Kaydet** düğmesi bulunur. Kaydet/Ctrl/⌘+S, panelin kendi kayıt işlemini çağırmadan önce normal görünüme döner; native hata/sonuç mesajları görünür kalır. **Kaydet ve kapat** için normal görünümdeki panel düğmesi kullanılabilir.

## Uygulama ve güvenlik sınırı

Bu, panel alanını kaplayan görünüm modudur; tarayıcı menülerini gizleyen Fullscreen API izni istemez. Mevcut frame'in yalnızca kendi wrapper'ı `manual` popover ile üst katmana alınır; DOM'da başka yere taşınmaz, aynı form/Ace kimliği ve yetki sınırı korunur. Bu yöntem üst elemanların transform/overflow sınırlarından etkilenmeden çalışır ([Popover davranışı](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/popover)). Panelin genel CSS'i, scroll kilidi veya native editör bileşeninin sınıfları değiştirilmez. Destek yoksa ya da açılış başarısızsa normal görünüm korunur; tarayıcı uyumluluğu kabiliyet kontrolüyle belirlenir.

Çıkışta yalnızca bu görünümün değiştirdiği stil değerleri geri yüklenir. Normal editöre geçiş, aktarım hatası, sayfa kapanışı veya native formun gizlenmesi/kaldırılmasında üst katman kapatılır. İzleme yalnızca form ve atalarının attribute/doğrudan child değişimleriyle sınırlıdır; panelin bütün alt ağacı izlenmez. Otomatik taslak, ayrı dosya kaydetme endpoint'i veya yeni dosya yetkisi eklenmez. PHP/Laravel LSP bu sürüme dahil değildir.

## Mevcut ayarlar ve geri dönüş

0.2.1'deki root:root 0600 `etc/ismonaco-editor/defaults.json` değiştirilmez. Mevcut beş tercih, yeni `etc/ismonaco-editor/defaults-v2.json` dosyasına kopyalanır; şema sürümü 2 ve `fullscreen=true` eklenir. Yeni dosya da root:root 0600'dür ve aynı özel dizinde tutulur. Bu sürümde ayarlar sadece yeni dosyaya yazılır. Böylece önceki paket/şema ve tercihler geri dönüşte kullanılabilir kalır; eski veya yeni tercih dosyası silinmez.

Rollback 0.2.1'in yükseltme öncesi tercihleriyle çalışır; 0.2.2 sırasında yeni dosyada yapılan değişiklikler eski şemaya geri yazılmaz, yeni dosyada korunur. Root dışı kullanıcılar ayar okuyup yazamaz; görünüm tercihi dosya yetkisi vermez. Bilinmeyen alanlar ve boolean olmayan tam ekran değerleri reddedilir.

## 0.2.1 → 0.2.2 yükseltme

Açık düzenlemeleri kaydedip dosya sekmelerini kapatın. `ismonaco-editor-0.2.2.zip` ve `.sha256` dosyalarını `/root` içine yükleyin. Bunlar **Shell-client / Bash** komutlarıdır:

```sh
cd /root && sha256sum -c /root/ismonaco-editor-0.2.2.sha256 && mkdir -m 700 /root/ismonaco-editor-0.2.2-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-editor-0.2.2.zip /root/ismonaco-editor-0.2.2-stage && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.2-stage/update.py --check
```

`MONACO_EDITOR_UPDATE_CHECK_OK` gelirse:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.2-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.2-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Beklenen `MONACO_EDITOR_UPDATE_APPLY_OK`, `MONACO_EDITOR_VERIFY_OK`. Son komut değişen XML kaydı için panel sürecini kısa süre yeniden başlatır. Hata varsa sonraki adıma geçmeyin; mevcut stage veya ayar dosyasını silmeyin. Sonra paneli yenileyip test dosyasını açın. Menüdeki yeni tam ekran seçeneğini Evet/Hayır olarak kaydedip yeni dosya açılışını sınayın.

Yeni dosyalar: `addon/ismonaco_0_2_2.py`, `.sh`, `skins/ismonaco-editor-0.2.2/` ve `etc/ismonaco-editor/defaults-v2.json`. Önce yeni dosyalar hazırlanır; en son eklentinin XML kaydı değiştirilir. XML yedeği `etc/xml/ispmgr_mod_ismonaco_preview.xml.pre-0.2.2` olur. Eski ZIP, handler, statik dosya, ayarlar, Phase 0 ve siteler korunur.

## Geri dönüş

Açık düzenlemeleri kaydedip sekmeleri kapattıktan sonra:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.2-stage/update.py --rollback && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Beklenen `MONACO_EDITOR_UPDATE_ROLLBACK_OK`. Yeni dosyalar/tercihler korunur; 0.2.1 XML kaydı geri gelir. Kısmi kurulumda otomatik silme yapılmaz; rollback tam kurulum doğrulaması ister.

## Dar doğrulama

Akış: yetkili form → varsayılan tam ekran veya normal görünüm → düğme/Esc/normal editör/kaydetme ile çıkış → mevcut native akış. Browser plugin mevcut olmadığından kurulu Playwright/Chrome ile `127.0.0.1:8766` üzerinde gerçek Monaco/Ace ve sentetik form kullanıldı; 1440×1100 ve 390×844 ekranlarda görüntü, boş sayfa/overlay, konsol, düğme yokluğu/metni, tam alan boyutu, açık/kapalı varsayılan, kaynak metin, readonly, native geçiş ve kayıt simülasyonu kontrol edildi. Gerçek sunucu dosyası yazılmadı. Gerçek Phoenix, tarayıcı matrisi ve normal hesap izolasyonu kabulü ayrıca bekler.


Yerel sonuç: 24 ilgili JavaScript testi ve ağsız gerçek Python 3.6.15 altında 29 Python testi geçti. Ek fullscreen hata kontrolü, CSS ile görünür kılınmış olsa bile `hidden` işaretli formda üst katmanı kapatır; son değişiklik için üç fullscreen birim testi ve Chrome akışı yeniden geçti. Chrome'da transform/overflow içindeki kapsayıcıdan bağımsız tam alan boyutu ve gizlenen native sekmede overlay temizliği de doğrulandı.

ZIP akışı ağsız geçici Linux/Python 3.6.15 container'ında sınandı: canonical 0.2.1 install → değiştirilmiş mevcut tercihlerle 0.2.2 update check/apply → verify → kurulu shell wrapper üzerinden altı alanlı ayar GET/SET, fullscreen on/off ve root dışı ret → native form tercih aktarımı → rollback → 0.2.1 verify. Önceki ayar dosyası ve handler byte/inode/zaman damgaları değişmedi; yeni tercihler geri dönüşte korundu. `/usr/local/mgr5` sadece geçici tmpfs, host proje salt okunur ve ağ kapalıydı. Gerçek sunucuya agent tarafından yükleme/kayıt yapılmadı.
