# Monaco Editor 0.2.4 — başlık ve eşleşme işaretleri

## Değişiklik

- Kaydet, Normal editör ve tam ekran düğmeleri erişilebilir metinlerini koruyan statik SVG ikonlarla üst sağa taşındı. Kontroller alt satırda kaldı; üst boşluk azaltıldı.
- Tam ekran aktifken Esc ile çıkış açıklaması görünür; normal görünümde gizlenir. SVG'ler tam ekran düğme metni değişirken korunur.
- Dosya yolu, yalnızca bu frame'in kendi yetkili formundaki `full_filepath-textdata` → `isp-form-view-text-auxiliary .text-block` alanından okunur. Bu kontrol kimliği native renderer'da textdata adından türetilir. Tek/uygun alan yoksa yol gösterilmez; başka form/URL/depoya fallback yoktur. Yol sadece textContent/title olarak gösterilir, URL/log/storage veya API isteğine eklenmez. Mutlak, kontrol karakteri içermeyen ve en fazla 4096 byte değer kabul edilir. Bu bir dosya erişim yetkisi kaynağı değildir.
- Başlık açık temada açık gri, koyu temada kod alanından biraz daha açık gri olur. Dar ekranda işlem grubu ayrı satıra geçer.
- HTML/PHP dosyalarındaki gerçek HTML etiket adları açılış/kapanış çifti olarak vurgulanır; alt çubukta iki satır numarası gösterilir. PHP parantezleri için Monaco'nun bracket matching katkısı ve renkli kılavuzları açıldı. Etiket işareti editördür; PHP/Laravel LSP veya semantic analiz değildir.

## Eşleşmenin sınırı

HTML ve PHP'nin kurulu Monaco Monarch tanımları senkron kaydedilir. Eşleşme, düz regex ile dosyanın tamamını HTML saymak yerine bu tokenizer'ın `tag.html`/`delimiter.html` tokenlarından çıkarılır. PHP string/comment ve script gövdelerindeki markup görünümlü metinler etiket sayılmaz. Void/self-closing etiketler kapanış çifti üretmez; eşleşmeyen etiket işaretlenmez. Eksik/hatalı HTML için tarayıcı düzeyinde DOM onarım veya tam validator vaadi yoktur.

Tarama mevcut 512 KiB metin sınırındadır; 20.000 etiket aşıldığında işaretleme kapatılır. İçerik değişiminde 160 ms debounce ve cursor hareketinde önbellekli arama kullanılır. Kaynak metin değiştirilmez, diske erişilmez. Model değişimi/kapanışında listener, timer ve decoration temizlenir.

## 0.2.3 → 0.2.4

Kullanıcı doğrudan 0.2.1→0.2.3 kurulumunu yaptığını bildirdi ve yeni editör/ayar görünümünü paylaştı. Bu paket **kurulu 0.2.3** tabanını doğrular; önceki doğrudan paketin hedef payload manifesti canonical 0.2.3 ile aynı olduğundan desteklenir. Mevcut `defaults-v2.json` ve bütün tercihler değiştirilmez.

Yeni ZIP ve SHA-256 dosyasını `/root` içine yükleyin. Açık düzenlemeleri kaydedip dosya sekmelerini kapatın. Shell-client:

```sh
cd /root && sha256sum -c /root/ismonaco-editor-0.2.4.sha256 && mkdir -m 700 /root/ismonaco-editor-0.2.4-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-editor-0.2.4.zip /root/ismonaco-editor-0.2.4-stage && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.4-stage/update.py --check
```

`MONACO_EDITOR_UPDATE_CHECK_OK` gelirse:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.4-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.4-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Son komut yeni eklenti XML/handler kaydı için panel sürecini kısa süre yeniden başlatır. Hata varsa ilerlemeyin; stage veya ayar dosyası silmeyin. Paneli yenileyip dosyayı yeniden açın. Yeni dosyalar kendi 0.2.4 ad alanına eklenir; en son eklenti XML kaydı değişir, eski kayıt `.pre-0.2.4` olarak korunur.

Geri dönüş, açık düzenlemeler kaydedilip sekmeler kapatıldıktan sonra:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.4-stage/update.py --rollback && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Tercihler ve yeni dosyalar korunur. Önceki dağıtım ZIP'leri değiştirilmez. Site dosyaları ve panel çekirdek JS/CSS dosyaları düzenlenmez.

## Dar doğrulama

- 15 ilgili JavaScript testi (son eklenen yoğun markup sınırı dahil): eşleşmeler, yanlış/eksik etiket, PHP string/comment dışlama, CRLF ve aynı formdan bounded yol okuma; boot/izin sınırları.
- Gerçek Monaco/Ace kullanılan yerel Chrome: 1440×1000/390×844; dosya yolu, SVG, sağ hizalama, kısa başlık, açık/koyu kontrast, yalnızca tam ekranda Esc açıklaması, gerçek PHP dosyasında HTML çiftleri, PHP string dışlama ve brace highlight, normal editöre çift yönlü geçiş geçti. Görünüm ve konsol kontrol edildi.
- Mevcut editor browser regresyonu yeri değişen kayıt/tam ekran/normal editör düğmeleri, BOM, undo/redo, readonly ve hata/fallback akışında geçti.

Browser plugin olmadığı için kurulu Playwright/Chrome kullanıldı; bütün tarayıcı istekleri localhost test ortamındaydı. Native Save diske yazmayan simülasyondur. Gerçek panelde başlık/yol bağlamı, görüntü ve kayıt kabulü güncelleme sonrası doğrulanacak; normal hesap izolasyonu bu UI testlerinden çıkarılamaz.


Paket doğrulaması: 8 ilgili yükseltme/hata testi gerçek Python 3.6.15 altında geçti. Nihai ZIP ile ağsız geçici container'da canonical 0.2.3 install → 0.2.4 check/apply/verify → mevcut tercihlerle ayar GET/SET ve tekrar kayıt → verify → rollback → 0.2.3 verify başarılı. Root ayar dosyası güncellemede byte/inode/zaman damgasıyla korundu; eski handler ve tercihler geri dönüşte korunur. Agent gerçek sunucuya işlem yapmadı. Son paket değişikliği yalnızca bu test kaydıdır; sınanan payload manifesti değişmedi.
