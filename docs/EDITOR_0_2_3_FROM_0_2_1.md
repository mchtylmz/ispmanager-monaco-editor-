# Doğrudan 0.2.1 → 0.2.3 yükseltme

Kullanıcının salt okunur çıktısı kayıtlı handler'ın `ismonaco_0_2_1.sh` olduğunu ve 0.2.2 handler dosyasının bulunmadığını doğruladı. Önceki 0.2.3 yükselticisi yalnızca 0.2.2'yi taban alıyordu; `UPDATE_IO_ERROR` bu eksik dosyayı gizliyordu. Bu paket doğrulanmış 0.2.1 tabanından doğrudan düzeltilmiş 0.2.3'e geçer; ara 0.2.2 kurulmaz.

0.2.3 handler, frontend, installer ve payload manifesti daha önce yayımlanan 0.2.3 ZIP'iyle aynıdır. Sadece yükseltici, önceki manifest ve kurulum yönergesi farklıdır. Eski dağıtım ZIP'leri yeniden üretilmez. Kayıt sonrası standalone beyaz ekran düzeltmesi ve test kapsamı [0.2.3 belgesindedir](EDITOR_0_2_3.md).

## Ayarların korunması

Eski `etc/ismonaco-editor/defaults.json` (şema 1) değiştirilmez. Geçerli mevcut beş ayar yeni `defaults-v2.json` dosyasına kopyalanır; şema 2 ve `fullscreen=true` eklenir. Her iki dosya root:root 0600'dür. Eski handler/statik dosyalar korunur; önce yeni dosyalar hazırlanır, en son sadece eklenti XML kaydı değiştirilir. Yedek `etc/xml/ispmgr_mod_ismonaco_preview.xml.pre-0.2.3-from-0.2.1` adındadır.

Kurulu 0.2.1 dosyalarının canonical manifesti ve sahiplik/izin/hash'leri denetlenir. Eski değiştirilebilir config'te hash yerine şema/izin/sahiplik denetlenir. Yeni hedef, config veya yedek varsa üzerine yazılmaz. Eksik eski handler için `PREVIOUS_FILE_MISSING: <target>` açık hatası verilir; sürüm kontrolleri atlanmaz.

## Shell-client komutları

Açık değişiklikleri kaydedip dosya sekmelerini kapatın. Yalnızca yeni `ismonaco-editor-0.2.3-from-0.2.1.zip` ve `.sha256` dosyalarını `/root` içine yükleyin. Önceki `/root/ismonaco-editor-0.2.3-stage` klasörünü silmeyin veya yeniden çıkarmayın; bu işlem ayrı stage kullanır.

```sh
cd /root && sha256sum -c /root/ismonaco-editor-0.2.3-from-0.2.1.sha256 && mkdir -m 700 /root/ismonaco-editor-0.2.3-from-0.2.1-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-editor-0.2.3-from-0.2.1.zip /root/ismonaco-editor-0.2.3-from-0.2.1-stage && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.3-from-0.2.1-stage/update.py --check
```

`MONACO_EDITOR_UPDATE_CHECK_OK` gelirse:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.3-from-0.2.1-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-editor-0.2.3-from-0.2.1-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Beklenen `MONACO_EDITOR_UPDATE_APPLY_OK`, `MONACO_EDITOR_VERIFY_OK`. Son komut yeni XML/handler kaydı için panel sürecini kısa süre yeniden başlatır. Ön kontrol hatasında uygulamaya geçmeyin; klasör silmeyin.

Paneli yenileyin. Eski boş ayar sekmesini kapatıp soldaki Monaco Settings'ten yeniden açın. Bir görünüm ayarını kaydedin: form/başlık ve başarı mesajı kalmalı. Tekrar kaydetme ve sekmeyi kapatıp yeniden açarak kalıcılığı doğrulayın. Gerçek panel kabulü bu işlemden sonra yapılacaktır; yerel test bunun yerine sayılmaz.

## Geri dönüş

Açık değişiklikleri kaydedip sekmeleri kapattıktan sonra:

```sh
/usr/bin/python3 -I -B /root/ismonaco-editor-0.2.3-from-0.2.1-stage/update.py --rollback && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Önceki 0.2.1 XML kaydı ve şema 1 tercihleriyle çalışır; yeni dosyalar ve şema 2 tercihleri silinmez. Yeni tercihler eski şemaya geri yazılmaz. 0.2.1 ayar-kaydı beyaz ekran hatasını içerir. Kısmi kurulumda otomatik silme yapılmaz; rollback tam yeni kurulum doğrulaması ister.


## Yerel test sonucu

10 dar yükseltme/hata testi ağsız gerçek Python 3.6.15 container'ında geçti. Canonical 0.2.1 kuruldu; tercihleri değiştirildi ve önceki başarısız 0.2.3 stage'i hazırlandı. Standart 0.2.3 ön kontrolünün bu tabanda hata verdiği tekrar üretildi. Ardından doğrudan pakette check/apply/verify, yeni kurulu wrapper ile tam ayar formu/kayıt/tekrar kayıt/GET ve hata/yetki reddi, rollback ve 0.2.1 verify geçti. Eski ayar/handler byte'ları, inode ve zaman damgaları ile başarısız eski stage korundu; yeni ayarlar rollback'te silinmedi.

Doğrudan paketin 36 payload/manifest/installer girdisinin canonical düzeltilmiş 0.2.3 ile byte düzeyinde aynı olduğu doğrulandı; frontend veya ayar handler'ı yeniden geliştirilmedi/build edilmedi. Son paket değişikliği yalnızca bu test kaydıdır. Gerçek sunucuda agent işlem yapmadı; canlı kabul manuel güncelleme sonrasındadır.
