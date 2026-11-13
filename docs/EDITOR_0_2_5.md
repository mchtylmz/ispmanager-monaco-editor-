# Monaco Editor 0.2.5 — kayıt işlemleri ve tam ekran başlığı

## Değişiklik

- Dosya yolu yalnızca tam ekranda görünür. Normal görünümde panelin kendi dosya yolu alanı kalır.
- Sağ üstte sıralama: **Tam ekran → Metin editörü**. Tam ekranda **Tam ekrandan çık → Metin editörü → Kaydet → Kaydet ve çık**.
- Kaydet ve Ctrl/Command+S mevcut panelin yalnızca kayıt işlemini çalıştırır. Kaydet ve çık, aynı formdaki mevcut Save and close düğmesini çalıştırır.
- Panelin encoding uyarısı ve UTF-8 alanı değiştirilmez. Sunucu varsayılanları korunur.

## Kayıt sınırı

Kaydet ve çık yalnızca native metadata içinde tek bir `name=ok/type=ok` düğmesi varsa etkinleşir. Frontend yalnızca kendi yetkili formundaki tek `data-dynamic-form-element-id=ok` alanının tek düğmesini kullanır; başka forma, URL'ye veya bağımsız dosya yazma API'sine gitmez. Eksik, belirsiz, disabled veya readonly kontrol çalıştırılmaz. Tıklamadan önce tampon eşitliği ve form/düğme kimliği yeniden doğrulanır.

Kayıt öncesi tam ekran kapanır; native hata veya başarı arayüzü görünür kalır. Eklenti kendisi sekmeyi kapatmaz ve düğme tıklamasını sunucudan kayıt onayı saymaz. Gerçek kapatma kararı panelindir. `apply/type=setvalues` native yalnızca-kaydet kontrolü de tampon uyumsuzluğuna karşı mevcut korumaya dahildir.

## 0.2.4 → 0.2.5

ZIP ve SHA-256 dosyasını `/root` içine yükleyin. Açık düzenlemeleri kaydedip dosya sekmelerini kapatın. Shell-client:

```sh
cd /root && sha256sum -c /root/ismonaco-editor-0.2.5.sha256 && mkdir -m 700 /root/ismonaco-editor-0.2.5-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-editor-0.2.5.zip /root/ismonaco-editor-0.2.5-stage && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.5-stage/update.py --check
```

Yalnızca `MONACO_EDITOR_UPDATE_CHECK_OK` geldikten sonra:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.5-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.5-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Son komut eklenti kaydını yüklemek için panel sürecini kısa süre yeniden başlatır. Hata varsa ilerlemeyin ve stage/ayar dosyası silmeyin. Paneli yenileyip dosyayı yeniden açın. Önceki XML `.pre-0.2.5` olarak saklanır; önceki handler/assets, global tercihler ve site dosyaları korunur.

Gerekirse açık düzenlemeleri kaydedip sekmeleri kapattıktan sonra:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.5-stage/update.py --rollback && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

## Dar doğrulama

- 13 ilgili JavaScript testi: köprü, ayrı kayıt işlemleri, readonly/disabled/eksik/çift veya değişmiş düğme, tampon uyumsuzluğu ve boot doğrulaması.
- Python 3.6.15 altında 15 handler testi: gerçek native apply/setvalues ve tek ok/ok metadata koşulu dahil.
- Python 3.6.15 altında 8 yükseltme/hata testi geçti. Ağsız geçici container'da paket CLI akışı: 0.2.4 install → 0.2.5 check/apply/verify → ayar kayıt/yeniden yükleme ve hata/erişim reddi → paketlenmiş wrapper ile root/normal kimlikte native boot → rollback → 0.2.4 verify. Güncellemede global ayarın byte/inode/zaman damgası, geri dönüşte tercihleri ve eski handler dosyaları korundu.
- Gerçek Monaco/Ace kullanılan yerel Chrome: tam ekran/normal görünümde yol ve düğme sırası; Kaydet ve Command+S kapatmama; Kaydet ve çık'ın son tamponu iletmesi; kayıt reddinde editörün açık kalması; readonly; 1440 ve 390 px genişlik. Konsol hatası yok; ekran görüntüleri incelendi.

Browser plugin bulunmadığından kurulu Playwright/Chrome kullanıldı. Native kayıt ve hata sonucu yerel simülasyondur; gerçek sunucu dosyası veya oturumu kullanılmadı. Gerçek ISPmanager'da kayıt/başarısız kayıt ve kapanış kabulü güncellemeden sonra ayrıca doğrulanmalıdır.

Son paket değişikliği yalnızca bu test kaydıdır; test edilen payload manifesti değişmedi. Önceki 0.2.4 ZIP kimliği korundu.
