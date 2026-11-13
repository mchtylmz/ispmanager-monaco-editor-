# Monaco Faz 0 kontrol prototipi

Bu laboratuvar eklentisi ISPmanager'ın özel bir fonksiyonu ve handler'ı çağırmasını sınamak için hazırlanmıştır. `ismonaco.phase0` fonksiyonunda sabit bir kontrol ekranı üretir. Üretim editörü, Monaco arayüzü veya marketplace paketi değildir.

Durum: kullanıcı paket hash'ini doğrulayıp kurulumu yaptı; `PHASE0_INSTALL_OK` ve `PHASE0_VERIFY_OK` çıktıları alındı. Native `-o devel` yanıtında form ve `root / AUTH_LEVEL 30` doğrulandı. Dosya okuma/kaydetme/LSP kapalı, oturum/CSRF ve sandbox doğrulanmamış görünüyor. Tarayıcıda görünüm, native dosya yöneticisi regresyonu ve root dışı erişim reddi henüz doğrulanmadı.

## Yapılan kontrol

Menü girdisi yalnızca panel seviyesi 30 için tanımlıdır. Handler ayrıca native `AUTH_USER=root`, `AUTH_LEVEL=30` ve tam `PARAM_func=ismonaco.phase0` eşleşmesini ister. Menü görünürlüğü tek başına yetki denetimi kabul edilmez. İstek alanları ve HTTP başlıkları bu bağlamın yerine kullanılmaz.

Başarılı cevap root bağlamını ve kapalı yetenekleri gösterir: site dosyası okuma, kaydetme ve LSP kapalıdır; oturum/CSRF taşıması ve sandbox doğrulanmamış olarak görünür. STDIN parse edilmez; dosya içeriği veya XML entity işlenmez. Handler site/veritabanı okumaz, ağ veya alt süreç çağrısı yapmaz ve dosya yazmaz.

Shell giriş noktası yalnızca üç gerekli ortam değişkenini sabit isimlerle taşır. Python `-I -B` ile başlar. Bu prototip gözlenen Python 3.6.8 ortamını hedefler; üretim backend dilini belirlemez. Yerel testler bu bilgisayardaki Python ile yapıldı; sunucunun 3.6.8 runtime'ında çalışma ayrı kontroldür.

XML, [resmî başlangıç örneğindeki](https://www.ispmanager.com/docs/developer-guide/hello-world-plugin) menü/fonksiyon yapısını kullanır. [Native bağlam değişkenleri](https://www.ispmanager.com/docs/developer-guide/environment-variables) handler'ın OS kullanıcısından ayrıdır: handler root olarak başlasa da API'yi çağıran normal kullanıcı için izin verilmez.

## Sunucu değişikliği kapsamı

9 Kasım 2026 tarihinde kullanıcı üç dosyalık kurulum ve kısa panel yeniden başlatmasını onaylayıp komutları Shell-client üzerinden kendisi uyguladı. Kurulum ve doğrulama başarı işaretleri ile native root formu paylaşıldı; tarayıcı ve normal kullanıcı reddi kontrolü bekliyor. Bu onay yeni kullanıcı, PHP modülü, servis, LSP veya site dosyası değişikliğini kapsamaz.

| Yerel kaynak | Sunucu hedefi | Sahiplik | Mod |
| --- | --- | --- | --- |
| `ispmgr_mod_ismonaco_phase0.xml` | `/usr/local/mgr5/etc/xml/ispmgr_mod_ismonaco_phase0.xml` | root:root | 0644 |
| `ismonaco_phase0.sh` | `/usr/local/mgr5/addon/ismonaco_phase0.sh` | root:root | 0750 |
| `ismonaco_phase0.py` | `/usr/local/mgr5/addon/ismonaco_phase0.py` | root:root | 0640 |

Tanım dosyası mevcut `file` veya `file.edit` fonksiyonlarına event/handler eklemez. Değişiklik yalnızca kendi fonksiyonu ve root kontrol menüsüdür. Yeni kullanıcı, servis, paket, cron, ağ portu veya veritabanı gerekmez. Kullanıcı projelerine ve mevcut editöre dosya yazılmaz.

## Onay sonrasında uygulanacak sıra

1. Panelden bağımsız bir root konsolu/SSH ile geri alma erişimi bulunmalı. Panel sorun yaşarsa kendi Shell-client ekranı yeterli geri alma kanalı sayılmaz.
2. Üç hedefin mevcut dosya veya symlink ile çakışmadığı kontrol edilir. Çakışma varsa işlem durur; üzerine yazılmaz.
3. Python ve wrapper önce `addon` dizinine, tanım XML'i son olarak `etc/xml` dizinine eklenir. Sahiplik, mod ve SHA-256 doğrulanır. ZIP içeriği doğrudan `/` altına açılmaz.
4. Sunucuda Python 3.6 ile sabit çıktının üretilebilmesi kontrol edilir. Elle verilen AUTH değişkenleriyle yapılan deneme sadece runtime testidir; gerçek panel oturumu kanıtı değildir.
5. Onaylanan kısa panel yeniden başlatması `/usr/local/mgr5/sbin/mgrctl -m ispmgr exit` ile yapılır; işletim sistemi yeniden başlatılmaz. Panel yeniden yüklenir.
6. Root ile Navigation board üzerinde Monaco Faz 0 kontrolü açılır. Ekrandaki bağlam ve kapalı yetenekler kontrol edilir; native dosya yöneticisinin açılmaya devam ettiği doğrulanır.
7. Yetkili bir normal test hesabında doğrudan fonksiyon çağrısının reddi sınanır. Kullanıcı normal test hesabı bulunmadığını bildirdi; yeni hesap oluşturulmayacak ve bu kabul ölçütü bekleyecek. Sadece root denemesi ve yerel sahte bağlam testleri gerçek panelde yetki ayrımı kanıtı değildir.

## Shell client kurulum komutları

Güncel ZIP kullanıcı tarafından File manager ile `/root/ismonaco-phase0-lab.zip` konumuna yüklenir. Kurulum sırasında panelden bağımsız root konsolu açık tutulur. Aşağıdaki her adım tek satırdır; herhangi bir hata durumunda sonraki adıma geçilmez.

1. Sohbette verilen güncel ZIP SHA-256 değeriyle paket doğrulanır; yeni ve 0700 modunda `/root/ismonaco-phase0-stage` oluşturulur. Dizin zaten varsa açılmaz ve içeriği değiştirilmez. ZIP yalnızca bu özel hazırlık dizinine çıkartılır; `/` altına veya panel dizinine doğrudan açılmaz. ZIP hash'i paketin kendisine yazılmaz; sohbette ayrıca verilir.
2. Kurulum yardımcısı çalıştırılır:

```sh
/usr/bin/python3 -I -B /root/ismonaco-phase0-stage/install.py
```

`PHASE0_INSTALL_OK` beklenir. Yardımcı üç kaynak dosyanın sabit hash'lerini, hedef üst dizinlerin sahiplik ve izinlerini kontrol eder. Mevcut hedef dosya, dizin veya symlink varsa durur. Her dosyayı kendi hedef dizinindeki özel geçici dosyadan atomik ve üzerine yazmayan hard-link işlemiyle yayımlar. Geçici dosya temizlenir; mevcut veya kısmen kurulmuş kalıcı dosyalar otomatik silinmez. Python ve wrapper çalışma kontrolleri XML kaydından önce yapılır. XML en son eklenir. Panel bu adımda yeniden başlatılmaz.

3. Dosya hash/sahiplik/mod kontrolü tekrar geçerse onaylanan panel aktivasyonu yapılır:

```sh
/usr/bin/python3 -I -B /root/ismonaco-phase0-stage/install.py --verify && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

`PHASE0_VERIFY_OK` kontrolünden sonra panel oturumu kısa süreli yeniden yüklenebilir. İşletim sistemi yeniden başlatılmaz.

4. Native panel çağrısı sınanır:

```sh
/usr/local/mgr5/sbin/mgrctl -m ispmgr -o devel ismonaco.phase0
```

Çıktı veya hata paylaşılır. Form tanımı ve mesajlar için `devel` gerekir; `xml` yalnızca veri yapısını gösterdiğinden bu prototipin metadata/mesaj ağırlıklı cevabı boş görünebilir. [API çıktı biçimleri](https://www.ispmanager.com/docs/ispmanager/guide-to-ispmanager-software-api)

Beklenen doğrulama: `metadata` altında form, `context_value` için `root / AUTH_LEVEL 30`, dosya erişimi/kaydetme/LSP için `Disabled` değerleri. Bunlar görülmeden native bağlam doğrulandı sayılmaz. Elle verilen AUTH değişkenleriyle yapılan kurulum runtime testi bunun yerine geçmez. Panel yeniden açıldıktan sonra Navigation board ve native dosya yöneticisi ayrıca kontrol edilir.

İlk kurulan ZIP hash'i `0811527350f6199cabce58d1f18847db97c0fb14d85de52228dac4c7496faa43` olarak korunur. Bu kontrol komutu düzeltmesi dokümantasyondadır; kurulu payload veya ZIP değiştirilmedi. Yeniden kurulum veya yeniden başlatma gerektirmez.

## Geri alma

Önce tanım dosyasının bu paketin hash'iyle eşleştiği doğrulanır. Yalnızca yeni tanım XML'i `ispmgr_mod_ismonaco_phase0.xml.disabled` adına taşınır ve panel yeniden yüklenir. `ispmgr_mod_*.xml` biçiminden çıkan tanımın artık yüklenmediği, kontrol menüsünün kaybolduğu ve dosya yöneticisinin çalıştığı doğrulanır. Handler dosyaları bu aşamada silinmez; açıkça istenirse yalnızca bu prototipe ait dosyaların kaldırılması ayrıca uygulanır.

Bu geri alma yolu panelden bağımsız root konsolu gerektirir. Eklenti dosyasının içeriği değişmişse otomatik taşıma/silme yapılmaz; uyuşmazlık bildirilir.

## Yerel test

Proje kökünden sadece bu prototipin kontrolleri:

```sh
python3 -I -B -m unittest discover -s tests -p 'test_phase0_probe.py' -v
```

Sekiz test; root bağlamı, eksik/diğer rollerin reddi, sahte request/header alanları, sır yansıtmama, STDIN ve kullanıcı Python başlangıç kodunu yok sayma, native dosya işlemlerine hook eklememe, sabit shell argümanları ve gerçek native form örneğiyle sözleşme uyumunu kapsar. Testler panel, ağ veya gerçek hosting dosyası kullanmaz. Kaydedilmiş form testi yeni bir canlı doğrulama değildir.

`SHA256SUMS` yalnızca üç çalıştırılabilir/tanım payload dosyasını kapsar. ZIP bu üç dosyayı, bu yönergeyi, checksum listesini ve `install.py` kurulum yardımcısını içerir. Yardımcı için sekiz ayrı yerel kurulum testi; çakışma, symlink, bozuk kaynak, izinler, çalışma hatası ve atomik yayımlama davranışını özel geçici dizinlerde sınar. Gerçek `/usr/local` dizinine dokunmaz. Sunucuda aktivasyon ve geri alma testleri geçene kadar `lab` statüsü korunur.
