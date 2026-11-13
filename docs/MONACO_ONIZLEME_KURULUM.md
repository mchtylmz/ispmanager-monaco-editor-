# Monaco 0.1.2 — Phoenix native frame düzeltmesi

Bu sürüm gerçek Monaco arayüzünü standart **File Manager → Düzenle** formunda gösteren salt okunur pilottur. Düzenleme ve kaydetme alttaki mevcut panel editöründe yapılır; Monaco'dan kaydetme ve PHP/Laravel LSP henüz eklenmez.

## Doğrulanan neden

0.1.1 kurulumu, native CLI ve panelin gerçek JSON isteği başarılıydı; yanıtta Monaco verisi ve metadata alanı bulunuyordu. Kullanıcının tarayıcı kontrolünde frame/preview elemanı yoktu. Yüklenen Phoenix form modülü `chunk-BT1IY76K.js` incelendi: alan çeviricisi `htmldata` için bir render dalı sağlamıyor, `frame` alanını destekliyor. `textdata html=yes` içeriği de HTML filtresinden geçtiğinden iframe'i bu yoldan zorlamak tercih edilmedi. Kaynak dosya hash'i ve bağlama adları [sözleşme kaydında](../tests/fixtures/ispmanager-6.155.0/phoenix-renderer-contract.json); üçüncü taraf kaynak dosyası depoya kopyalanmadı.

0.1.2, desteklenen native `frame` alanını kullanır. Frame statik, yerel bir HTML sayfasıdır. İçerik aktarımı, yalnızca bu frame'in içinde bulunduğu Phoenix formunun mevcut Ace editöründeki `getValue()` çağrısıyla bir kez yapılır.

## Güvenlik ve uyumluluk sınırı

- Backend yalnızca yetkilendirilmiş native `file.edit` sonrasında görünüm ekler. Dosya okuma/yazma endpoint'i, yeni port, servis veya root dosya okuyucusu eklenmez.
- Aynı görünüm root ve normal hesapta kullanılır; dosyayı açma/yazma yetkisinin kaynağı native paneldir. Backend yalnızca gerçek `AUTH_USER` / `AUTH_LEVEL` bağlamını kabul eder; mevcut form, `fdata`, encoding, gizli alanlar ve düğmeler korunur.
- Native frame URL'sinde sadece statik dosya yolu ve herkese açık rastgele render kimliği vardır. Dosya yolu/içeriği, kullanıcı kimliği veya erişim anahtarı URL'ye konmaz. Kimlik, her yeniden açmada iframe'in yenilenmesi ve önceki dosyanın kopyasının kalmaması içindir; bir yetkilendirme anahtarı değildir.
- `frontend/native-bridge.mjs`, frame'in `ismonaco_preview-frame` alanına bağlı olduğunu, aynı `isp-new-dynamic-form` içinde tam bir `fdata-code-element` ve bir Ace olduğunu doğrular. Global editör araması veya başka forma fallback yoktur. Ace container kimliği eşleşmeli, form okuma boyunca bağlı kalmalıdır.
- Köprü yalnızca `getValue()` kullanır. Native DOM'u, modelini, kaydetme akışını, Angular servislerini veya istek mekanizmasını değiştirmez. Cookie, storage, kimlik doğrulama başlığı ve oturum anahtarı okunmaz. Yeni API isteği ve parent/frame mesajlaşması yoktur.
- 512 KiB içerik sınırı ve 4 MiB backend XML sınırı korunur. Ace hazır değilse en fazla 5 saniye beklenir; belirsiz/çift alan, form değişimi veya desteklenmeyen arayüzde yalnızca Monaco hata durumu gösterir, native editör kullanılabilir kalır. Boş dosya geçerlidir.
- Frame aynı origin'dedir ve bir origin izolasyonu garantisi değildir. CSP dış ağ/fetch/form gönderimini engeller; yerel JS/CSS/font/worker varlıkları kullanılır. Dosya metni HTML olarak işlenmez. Ayarlar ve kopyalanan metin bellekte kalır; diske veya browser storage'a yazılmaz.
- Bu adapter, kaynak kodu incelenen ISPmanager Lite 6.155.0 Phoenix yapısına bağlıdır. Diğer sürüm/edition'lar doğrulanmış sayılmaz. Uyumsuz arayüzde yetki genişletilmez veya global DOM taraması yapılmaz.
- Monaco açılıştaki native tamponun salt okunur kopyasıdır. Native editördeki sonraki değişiklikler bu sürümde canlı senkronize edilmez.

## Kurulu 0.1.1 sürümünü güncelleme

`ismonaco-preview-0.1.2.zip` ile `ismonaco-preview-0.1.2.sha256` dosyalarını `/root/` altına yükle. Eski stage veya dosyaları silme. Blokları sırayla çalıştır; hatada sonraki adıma geçme.

1. Yeni paketi doğrula ve ayrı dizine çıkar:

```bash
cd /root && sha256sum -c /root/ismonaco-preview-0.1.2.sha256 && mkdir -m 700 /root/ismonaco-preview-0.1.2-stage && /usr/bin/python3 -I -B -m zipfile -e /root/ismonaco-preview-0.1.2.zip /root/ismonaco-preview-0.1.2-stage
```

2. Salt okunur güncelleme ön kontrolü:

```bash
/usr/bin/python3 -I -B /root/ismonaco-preview-0.1.2-stage/update.py --check
```

Beklenen: `MONACO_PREVIEW_UPDATE_CHECK_OK`. Önceki sürümün 32 dosyası canonical 0.1.1 manifestiyle hash/sahiplik/mod bakımından kontrol edilir; değiştirilmiş dosya, symlink, mevcut yedek veya yeni asset dizini varsa durulur. Yeni payload hash'leri ve mevcut Python runtime'ı da doğrulanır. Ön kontrol dosya yazmaz.

3. Yedekli güncelleme ve yeni sürüm doğrulaması:

```bash
/usr/bin/python3 -I -B /root/ismonaco-preview-0.1.2-stage/update.py --apply && /usr/bin/python3 -I -B /root/ismonaco-preview-0.1.2-stage/install.py --verify
```

Beklenen: `MONACO_PREVIEW_UPDATE_APPLY_OK`, `MONACO_PREVIEW_VERIFY_OK`.

Güncelleme önce `/usr/local/mgr5/skins/ismonaco-preview-0.1.2/` varlıklarını oluşturur. Sonra `/usr/local/mgr5/addon/ismonaco_preview.py` dosyasının bağımsız kopyasını `.pre-0.1.2` yedeği olarak oluşturur ve yalnızca bu Python handler'ını atomik değiştirir. XML kaydı ve shell wrapper'ın byte olarak değişmediği kontrol edilir; bunlara yazılmaz. Eski asset dizini ve Phase 0 lab'ı korunur. Panel/site servisleri yeniden başlatılmaz; Node/PHP/LSP kurulmaz.

4. Kaydedilmemiş değişiklik yoksa panel sayfasını yenile; sitenin küçük bir metin dosyasını yeniden **Düzenle** ile aç. Üstte Monaco, altında native editör görünmeli. Tema, dil ve Bul kontrolünü dene; ilk denemede dosya kaydetmek gerekmez. Root testi yapılabilir; gerçek normal hesap/iki kullanıcı izolasyonu testi henüz mevcut sunucuda yapılmış sayılmaz.

Yeni handler doğrudan her açılışta çalıştığından `mgrctl exit` veya sunucu yeniden başlatma gerekmez. Güncellemeden sonra doğrulama için 0.1.2 stage kullanılır; eski 0.1.1 doğrulayıcısı değişen handler hash'ini doğal olarak farklı bulur.

## Geri dönüş

Başarıyla uygulanan güncellemenin geri dönüşü:

```bash
/usr/bin/python3 -I -B /root/ismonaco-preview-0.1.2-stage/update.py --rollback
```

Beklenen: `MONACO_PREVIEW_UPDATE_ROLLBACK_OK`. Yeni sürüm ve yedek hash'leri doğrulanır; yalnızca eski Python handler'ı atomik geri konur. Eski/yeni asset dizinleri ve yedek silinmez, servis yeniden başlatılmaz. Sonradan değiştirilmiş dosyalarda zorla üzerine yazılmaz. Kısmi güncellemede çıktı incelenmeden tekrar deneme veya temizlik yapılmaz.

Native event'i tamamen kapatmak için, 0.1.2 aktif ve dosya doğrulaması başarılıyken:

```bash
/usr/bin/python3 -I -B /root/ismonaco-preview-0.1.2-stage/install.py --disable && /usr/local/mgr5/sbin/mgrctl -m ispmgr exit
```

Bu ayrı işlem kayıt XML'ini `.xml.disabled` olarak koruyup paneli kısa süreli yeniden başlatır; site dosyalarına dokunmaz.

## Sıfır kurulum ve yerel geliştirme

Hiç preview kurulmamış sunucuda yeni paketin `install.py --check`, ardından `install.py --install` ve `install.py --verify` akışı kullanılır. XML'in ilk kaydı için panelin kısa yeniden başlatması gerekir. Mevcut kurulumda bunun yerine yukarıdaki `update.py` kullanılır; kurulum yardımcısı çakışan dosyaların üzerine yazmaz.

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm run build
node --test tests/frontend.test.mjs tests/native-bridge.test.mjs
python3 -I -B -m unittest discover -s tests -p 'test_preview*.py' -v
python3 -I -B tools/preview_server.py 8765
```

Browser plugin mevcut olmadığı için yerel arayüz kontrolü Playwright ve kurulu Chrome ile yapılır: kurulu Playwright `index.mjs` yolu `PLAYWRIGHT_MODULE` ortam değişkenine atanıp `node tests/preview.browser.mjs` çalıştırılır. Harness yalnızca `127.0.0.1:8765` dinler; native Phoenix'in gözlenen frame dalını ve form bağlama adlarını taklit eder, Ace 1.45.2'yi gerçek olarak çalıştırır. Ace yalnızca devDependency'dir; sunucu paketine konmaz.

0.1.2 için 27 Python testi gerçek Python 3.6.15 container'ında, 10 ilgili JavaScript testi yerelde geçti. Chrome'da root/normal sentetik bağlam, gecikmeli Ace, önce gelen başka formun verisinin okunmaması, native yazma sayısının sıfır kalması, salt okunurluk, arama/ayarlar, yerel worker/font ve 1440/390 px görünümler doğrulandı. Native ret, çift alan ve standalone frame durumlarında kapalı hata davranışı sınandı. Bunlar gerçek sunucuda normal kullanıcı/izin iptali ve tüm Phoenix yaşam döngüsü testinin yerine geçmez.

`npm run package:preview` sabitlenmiş frontend'i, dosya manifestlerini, canonical önceki sürüm manifestini, kurulum/güncelleme yardımcılarını ve lisansları ZIP'e koyar; tüm ZIP için SHA-256 üretir. Önceki 0.1.0/0.1.1 ve Phase 0 ZIP'leri değiştirilmez. Monaco 0.57.0, DOMPurify 3.4.17 override'ı ve gömülü eski kopyayı build'de değiştiren resolver korunur. Ürün lisansı, marketplace kabulü ve tüm güncel ISPmanager 6 sürümlerine destek bu pilotla ilan edilmez.
