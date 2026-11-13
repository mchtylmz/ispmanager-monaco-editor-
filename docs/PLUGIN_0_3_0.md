# Monaco plugin 0.3.0 — site oluşturma/düzenleme notu

## Kapsam

Monaco ayarlarının altına **Site uyarısı türü** (Bilgi / Uyarı) ve **Site oluştururken veya düzenlerken gösterilecek uyarı metni** (5 satırlık textarea) eklendi. Metin en fazla 4096 UTF-8 byte olabilir. Sunucu genelindeki aynı not, yetkili root/yönetici/normal hesapların `site.edit` formunda **Ana ayarlar** sekmesinin en üstünde görünür. Boş veya sadece boşluk içeren metin notu gizler. Metni yalnızca root (`AUTH_USER=root`, `AUTH_LEVEL=30`) değiştirebilir.

Bu bir açıklama notudur; seçilen IP'yi, site oluşturma/kayıt davranışını veya kullanıcı dosya yetkilerini değiştirmez. Ana sayfa bildirimi, eski `webdomain.edit` formu ve editörün ilk yüklenme gecikmesi bu sürümde değiştirilmez.

## Mimari ve güvenlik sınırı

- Editör 0.2.5 handler, wrapper ve bütün frontend dosyaları eski ZIP'ten byte-byte korunur. Yeni bağımsız site-notice XML handler yalnızca `site.edit after` ve mevcut root ayar fonksiyonunu yönetir. Dosya editörünün hook'u eskisiyle aynıdır.
- Gerçek sunucudan salt okunur metadata özeti, `site.edit` / `mainsettings` sekmesini ve native `textdata type=banner status=info|warning` alanlarını doğruladı. Phoenix renderer da `rows=5`, banner/status ve HTML/plain-text yolları açısından incelendi. Sözleşme kaydı: `tests/fixtures/ispmanager-6.155.0/site-notice-contract.json`.
- Kullanıcı metni tamamen escape edilir; yalnızca satır sonları için eklentinin ürettiği `<br>` etiketleri kullanılır. Serbest HTML, link veya script çalıştırma özelliği yoktur. Not URL/argv/log içine taşınmaz; site parametreleri ve native alanlar korunur.
- Not ayrı sabit dosyada tutulur: `/usr/local/mgr5/etc/ismonaco-editor/site-notice-v1.json`, root:root 0600. Parent izin/sahiplik denetimi, O_NOFOLLOW/O_NONBLOCK, regular-file ve boyut sınırı, fsync + atomic replace kullanılır. Eksik/bozuk/güvensiz not ayarında native site formu değiştirilmeden döner. Belirsiz, başarısız, gönderilmiş veya başarı yanıtları değiştirilmez; tekrar eklenmez.
- Root ayar formu mevcut altı editör ayarını korur. Her iki grup yazmadan önce doğrulanır; yalnızca değişen grup yazılır. Her ayar dosyası kendi içinde atomik yazılır; iki dosya ortak transaction değildir. İkinci yazmada IO hatası olursa başarı bildirilmez; tam form, açık hata ve gerçekten kaydedilmiş değerler gösterilir. Başka oturumun ayarını ezebilecek otomatik geri alma yapılmaz.
- Mevcut editör tercihleri taşınmaz veya yeniden yazılmaz. Not dosyası yükseltmede boş olarak eklenir. Geri dönüş not dosyasını korur; önceki XML kaydı tekrar kullanılır.

## 0.2.5 → 0.3.0

ZIP ve SHA-256 dosyasını `/root` içine yükleyin. Açık düzenlemeleri kaydedip dosya sekmelerini kapatın:

```sh
cd /root && sha256sum -c /root/ismonaco-plugin-0.3.0.sha256 && mkdir -m 700 /root/ismonaco-plugin-0.3.0-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-plugin-0.3.0.zip /root/ismonaco-plugin-0.3.0-stage && /usr/bin/python3 -I -B /root/ismonaco-plugin-0.3.0-stage/update.py --check
```

Yalnızca `MONACO_EDITOR_UPDATE_CHECK_OK` gelirse:

```sh
/usr/bin/python3 -I -B /root/ismonaco-plugin-0.3.0-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-plugin-0.3.0-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Son komut eklenti XML kaydını yüklemek için panel sürecini kısa süre yeniden başlatır. Paneli yenileyin. **Monaco settings** altında notunuzu kaydedin; **Create site** ve mevcut sitenin düzenleme formunda Ana ayarlar sekmesinin üstünü kontrol edin. Hata varsa ilerlemeyin; stage veya ayar dosyası silmeyin. Yeni sürüm, native site formunda gerçek site oluşturularak sınanmış sayılmaz; bu doğrulama için site oluşturmak gerekmez.

Geri dönüş (önce açık dosyaları kaydedip sekmeleri kapatın):

```sh
/usr/bin/python3 -I -B /root/ismonaco-plugin-0.3.0-stage/update.py --rollback && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Not ve editör tercihleri korunur; XML yedeği `.pre-0.3.0` olarak kalır. Eski dağıtım ZIP'leri değiştirilmez. Site veya panel çekirdek dosyaları düzenlenmez.

## Doğrulama

8 odaklı not/ayar testi: create/edit ve rol bağlamı; native alanların değişmemesi; boş/tekrarlı/bozuk not; HTML kaçışları ve satırlar; yetkisiz okuma/yazma reddi; geçersiz tür/metin/byte sınırı; readonly/symlink/FIFO/boyut sınırı; disk hatasında kullanılabilir form ve doğru kaydedilmiş değerlerin gösterimi.

Python 3.6.15 altında bu 8 test ve 8 paket yükseltme/hata testi geçti. Ağsız geçici container'da gerçek CLI: 0.2.5 install → 0.3.0 check/apply/verify → paketlenmiş root ayar GET/SET, info/warning ve normal/root site bağlamı, geçersiz/izinsiz kayıt, eski editör frame'i → rollback → 0.2.5 verify. Eski editör dosyaları ve tercihleri byte/inode/zaman damgasıyla korundu; not dosyası geri dönüşte kaldı.

Yerel Chrome testi gerçek Phoenix `kc/Kr` eşleyicilerini hash'i doğrulanmış public bundle'dan izole çalıştırdı: banner/status/html alanları doğru; oluşturulan satır sonları görünür; script/img örnekleri düz metin kaldı; textarea içeriği bozulmadı; ağ isteği veya script hatası oluşmadı. Bu içerik/sözleşme testidir, canlı panelin tamamının UI testi değildir. Browser plugin bulunmadığından kurulu Playwright/Chrome kullanıldı. Frontend değişmediği için build ve bütün proje testleri tekrar çalıştırılmadı.

Son paket güncellemesi yalnızca test kaydıdır; sınanan payload manifesti değişmedi. Önceki dağıtım ZIP kimliği korundu.

Gerçek panelde yeni notun görünümü ve ayar kayıt kabulü kurulum sonrasında kullanıcı tarafından doğrulanacaktır. Gerçek sunucuya agent tarafından kurulum veya site oluşturma işlemi yapılmadı.
