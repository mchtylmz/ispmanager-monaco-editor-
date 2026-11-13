# Tek dosyayla kurulum — setup 0.3.1

Bu dağıtım, kullanıcı tarafından çalıştığı doğrulanan **plugin 0.3.0** (editör 0.2.5 + site uyarısı) payload'unu değiştirmeden tek `.pyz` dosyasına koyar. Terminal özelliği eklemez. Python standart kütüphanesi yeterlidir; sunucuda NPM, pip, derleyici, ek servis veya internetten kod indirme işlemi yoktur.

## Tek dosya, tek komut

`ismonaco-setup-0.3.1.pyz` dosyasını panel File Manager ile `/root` içine yükleyin. Açık düzenlemeleri kaydedip dosya sekmelerini kapatın. Root Shell-client'te:

```sh
/usr/bin/python3 -I -B /root/ismonaco-setup-0.3.1.pyz
```

Kurucu otomatik ayırır:

- **NEW_INSTALL:** temiz panelde editör ve site uyarısı kurulur. Site uyarısı boş başlar.
- **UPDATE_0_2_5:** önceki editör sürümü doğrulanır; site uyarısı eklenir. Mevcut editör tercihleri byte/inode/zaman damgasıyla korunur.
- **ALREADY_CURRENT:** kurulu 0.3.0 dosyaları ve iki ayar dosyası doğrulanır; yeniden yazılmaz, ayarlar sıfırlanmaz ve panel yeniden başlatılmaz.

Kurulum veya güncelleme başarıyla doğrulandıktan sonra kurucu `mgrctl -m ispmgr exit` ile panelin yeni kaydı yüklemesini ister. `MONACO_SETUP_RESTART_REQUESTED` bu isteğin kabul edildiğini belirtir; HTTP erişilebilirlik veya kullanıcı oturumu testi değildir. Sonrasında paneli yenileyin. Güncel kurulumda `MONACO_SETUP_APPLY_OK MODE=ALREADY_CURRENT` yeterlidir.

## Önkoşullar ve sınırlar

Linux/root, Python 3.6 veya üzeri, `/usr/bin/python3`, `/usr/local/mgr5` altındaki mevcut panel dizinleri ve güvenilir `sbin/mgrctl` gerekir. Kurucu dizin/dosya sahipliği, izinler, payload hash'leri ve Python handler runtime'larını denetler. CLI'den veya environment'tan alternatif panel kökü/komut yolu kabul etmez. Başka sunuculardaki arayüz uyumluluğu otomatik ilan edilmez; gerçek panel kanıtı Rocky 8.10 / ISPmanager Lite 6.155.0 ortamındandır.

Desteklenen tabanlar temiz kurulum, canonical editör 0.2.5 ve plugin 0.3.0'dır. Daha eski/elle değiştirilmiş, devre dışı veya kısmi kurulumlarda üzerine yazmadan durur. Otomatik silme/onarım yapmaz. Hata çıktısını paylaşın; dosya veya ayar silmeyin.

İki ayar dosyası mevcut şemalarıyla korunur: `defaults-v2.json` ve `site-notice-v1.json`. Site dosyaları ve panel çekirdek dosyaları değiştirilmez. Kurulum kilidi `var/ismonaco-setup.lock` altında tutulur; eşzamanlı ikinci kurucu reddedilir. Özel 0700 geçici staging yalnızca bu çağrı için açılır ve kapanışta temizlenir; yüklenen paket silinmez.

## İsteğe bağlı işlemler

Hedefe yazmadan denetim (`check` sadece özel geçici staging kullanır):

```sh
/usr/bin/python3 -I -B /root/ismonaco-setup-0.3.1.pyz check
```

Kurulu dosyaları doğrulama:

```sh
/usr/bin/python3 -I -B /root/ismonaco-setup-0.3.1.pyz verify
```

Paneli hemen yeniden başlatmadan kurmak için `install --no-restart` kullanılır. Sonrasında, açık dosyalar kaydedildikten sonra, `restart` aynı tek dosyayla çalıştırılır. Yeniden başlatma başarısızsa kurulum doğrulanmış halde kalır; çıkış kodu 2 ve `RESTART_REQUIRED` gelir. Kurulumu silmek yerine `restart` işlemiyle tekrar denenir.

Yalnızca 0.2.5 → 0.3.0 yükseltmesinin doğrulanmış `.pre-0.3.0` XML yedeği varsa `rollback` kullanılabilir. Ayarlar/not ve eski-yeni handler/assets korunur; temiz kurulumda geri dönülecek önceki sürüm yoktur. Geri dönüş sonrası kalan dosyalar otomatik silinmez; yeniden yükseltme kısmi kurulum incelemesi gerektirebilir.

## Paket bütünlüğü ve üretim

Tek dosya canonical 0.3.0 ZIP'i içerir; çalıştırmadan açılacak yardımcı/payload dosyaları gömülü SHA-256 ve manifest ile denetlenir. Bu, iç bütünlük kontrolüdür; yayıncının dijital imzası değildir. Dağıtımın tamamı için ayrıca SHA-256 üretilir; kurulum için ikinci dosya yüklemek gerekmez. Paket güvenilir kaynaktan alınmalıdır.

`npm run package:standalone` önceki ZIP'i değiştirmez, frontend build yapmaz; tekrar üretilebilir tarih/sıralamayla `.pyz` ve isteğe bağlı `.sha256` oluşturur. Bu değişiklik kapsamındaki testler yalnızca kurulum yöneticisi ve gerçek Python 3.6 CLI senaryolarıdır; editör ve site notu UI'si değiştirilmedi.

## Lokal test sonucu

- Python 3.6.15 altında 8 odaklı unit testi geçti: temiz/güncel/eski sürüm ayrımı, ayar koruma, geri dönüş, değiştirilmiş/kısmi/devre dışı kurulum, runtime/IO hatası, kilit ve symlink reddi, paket hash/path denetimleri, sabit yeniden başlatma komutu ve root sınırı.
- Üretilen `.pyz`, iki ayrı ağsız geçici Python 3.6 container'ında `new` ve `update` senaryolarıyla çalıştırıldı. Gerçek CLI `check`, varsayılan tek-komut kurulum, `--no-restart`, `restart`, `verify`, tekrar kurulum, bozuk bundle, değiştirilmiş handler ve yükseltmeden geri dönüş geçti. Ayarlar gerçek paketlenmiş settings wrapper'ından değiştirildi; tekrar çalıştırmada byte/inode/zaman damgaları korundu.
- Panel yeniden başlatma çağrısı native `mgrctl` yerine sadece bu test kökündeki taklitle sınandı. Başarıda tek çağrı, güncel kurulumda çağrı yapılmaması ve hatada ayrı çıkış kodu 2 doğrulandı. Her çağrı sonrası özel staging temizlendi. Gerçek panel süreci, site, ağ servisi veya kullanıcı verisi kullanılmadı.
- Nihai paket güncellemesi yalnızca bu test kaydıdır; test edilen `__main__.py` ve gömülü 0.3.0 ZIP değişmedi. CRC/SHA-256 ve önceki ZIP kimliği doğrulandı. Frontend build ve tüm proje testleri gereksiz yere tekrar çalıştırılmadı.
