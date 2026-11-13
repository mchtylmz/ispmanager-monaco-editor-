# ISPmanager Monaco Editor

ISPmanager 6 için bağımsız bir eklenti: File Manager'daki dosya düzenleme ekranına Monaco Editor, site oluşturma/düzenleme ekranına sunucu genelinde yönetilen bilgi veya uyarı notu ekler.

ISPmanager tarafından geliştirilen veya onaylanan resmî bir ürün değildir. Marketplace yayını yapılmamıştır.

## Özellikler

- File Manager'ın mevcut **Düzenle** işlemi üzerinden Monaco arayüzü.
- Dil seçimi, açık/koyu tema, yazı boyutu, satır kaydırma, kod haritası, arama ve tam ekran.
- Tam ekranda dosya yolu, **Kaydet** ve **Kaydet ve çık**; Ctrl/Command+S ile yalnızca kayıt.
- Mevcut panel editörüne ve Monaco'ya aynı form içinde geçiş.
- HTML etiket ve parantez eşleşme işaretleri.
- Root tarafından belirlenen sunucu genelinde editör varsayılanları.
- Site oluştururken veya düzenlerken görünen **Bilgi / Uyarı** notu; beş satırlık metin alanı, boş metinde gizleme.
- Çevrimdışı tek dosya kurulumu; temiz kurulum, desteklenen güncelleme ve zaten güncel kurulum ayrımı.

PHP/Laravel proje genelinde akıllı tamamlama ve terminal geliştirmesi bu sürümde bulunmaz. Sözdizimi renklendirmesi veya etiket eşleştirme bir PHP dil sunucusu değildir.

## Uyumluluk

**Hedef ISPmanager 6'dır. Bütün 6.x sürümleri veya gelecekteki ana sürümler için uyumluluk garantisi verilmez.**

| Ortam | Durum |
| --- | --- |
| ISPmanager Lite 6.155.0, Phoenix, Rocky Linux 8.10 x86_64 | Editör ve site notu gerçek panelde kullanıcı tarafından doğrulandı |
| Python 3.6.15 | Kurulum/güncelleme ve hata senaryoları yerel, ağsız container ortamında sınandı |
| Diğer ISPmanager 6 sürümleri, Pro/Host, diğer Linux dağıtımları | Henüz ayrı ayrı doğrulanmadı |
| Business, ISPmanager 5, sonraki ana sürümler | Destek beyanı yok |

Entegrasyon Phoenix form yapısına, mevcut Ace editörüne ve `file.edit` / `site.edit` işlevlerine bağlıdır. Kurucunun önkontrolü Linux, root, Python, dosya yerleşimi ve bütünlüğü denetler; panel sürümü/edition veya arayüz uyumluluğunu otomatik doğrulamaz. Başka bir ortamda önce test sunucusunda deneyin.

## Kurulum

Gerekenler: Linux, root erişimi, Python 3.6 veya üzeri için `/usr/bin/python3` ve standart `/usr/local/mgr5` panel yerleşimi. Sunucuda Node.js, NPM, pip, derleyici veya ek servis kurulmaz; kurucu internetten kod indirmez.

Dağıtım dosyası **`ismonaco-setup-0.3.1.pyz`** dosyasıdır. [v0.3.1 sürümü](https://github.com/mchtylmz/ispmanager-monaco-editor-/releases/tag/v0.3.1) üzerinden [tek dosyalık kurucuyu](https://github.com/mchtylmz/ispmanager-monaco-editor-/releases/download/v0.3.1/ismonaco-setup-0.3.1.pyz) ve [SHA-256 dosyasını](https://github.com/mchtylmz/ispmanager-monaco-editor-/releases/download/v0.3.1/ismonaco-setup-0.3.1.sha256) indirin. `dist/` kaynak depoya eklenmez. Kaynak depoyu ZIP olarak indirmek, kurulum paketini indirmekle aynı işlem değildir.

Dosyayı `/root` içine yükleyin. Açık düzenlemelerinizi kaydedip dosya sekmelerini kapatın:

```sh
/usr/bin/python3 -I -B /root/ismonaco-setup-0.3.1.pyz
```

| Sonuç | Davranış |
| --- | --- |
| `NEW_INSTALL` | Editör ve site notu kurulur; not boş başlar |
| `UPDATE_0_2_5` | Doğrulanmış editör 0.2.5'ten güncellenir; mevcut editör ayarları korunur |
| `ALREADY_CURRENT` | Plugin 0.3.0 ve iki ayar dosyası doğrulanır; yeniden yazılmaz, panel yeniden başlatılmaz |

Yeni kurulum/güncelleme başarıyla doğrulandıktan sonra panelin yeni eklenti kaydını yüklemesi için kısa bir yeniden başlatma istenir. Sonrasında paneli yenileyin. Tanınmayan, değiştirilmiş, kısmi veya devre dışı kurulumların üzerine yazılmaz; hata halinde dosya/ayar silmeden çıktıyı inceleyin.

Hedefe yazmadan önkontrol ve kurulu dosyaları doğrulama:

```sh
/usr/bin/python3 -I -B /root/ismonaco-setup-0.3.1.pyz check
/usr/bin/python3 -I -B /root/ismonaco-setup-0.3.1.pyz verify
```

`install --no-restart`, `restart` ve koşullu `rollback` için [tek dosya kurulum belgesine](docs/TEK_DOSYA_KURULUM.md) bakın. Kurucu **0.3.1**, içerdiği plugin **0.3.0**, editör payload'u **0.2.5** sürümündedir; bu numaraların farklı olması beklenir.

## Ayarlar

Root hesabıyla **Monaco settings** menüsünü açın. Editörün varsayılan görünümünü ve site notunun türünü/metnini kaydedin. Not, site oluşturma/düzenleme formunun **Ana ayarlar** sekmesinde gösterilir; boş metinde gizlenir.

Not metni sunucu genelinde ilgili formu açan kullanıcılara görünür. Parola veya erişim anahtarı yazmayın. En fazla 4096 UTF-8 byte metin kabul edilir; kullanıcı HTML'i çalıştırılmaz. Not, IP seçimine ilişkin açıklama gösterir; IP'yi veya site ayarlarını değiştirmez.

## Güvenlik ve veri sınırları

- Dosya erişimi ve gerçek kayıt işlemleri ISPmanager'ın mevcut formundan yürür; ayrı bir site dosyası okuma/yazma API'si açılmaz.
- Root ve normal hesaplar aynı editör arayüzünü hedefler; mevcut panel yetkileri geçerli kalır. Gerçek iki-hesap izolasyon testleri ayrıca gereklidir.
- Global ayarlar yalnızca root kimliğiyle eklentinin sabit yollarına kaydedilir. Dosya içeriği ve oturum bilgileri frame URL'sine konmaz.
- Kurulum eklentiye ait handler, statik dosya, XML kaydı ve ayarlarla sınırlıdır; site dosyalarını, veritabanlarını veya panel çekirdek dosyalarını değiştirmez.
- Mevcut ayarlar korunur. Gerçek `/usr/local/mgr5/etc/ismonaco-editor/` yapılandırmalarını kaynak depoya eklemeyin.
- Gömülü hash ve manifestler iç bütünlüğü denetler; bağımsız yayıncı imzası değildir. Paketi güvenilir kaynaktan alın ve yayımlanan SHA-256 ile karşılaştırın.

Yerel testlerin geçmesi bütün sürümlerde uyumluluk veya sıfır güvenlik açığı garantisi değildir. Bağımlılıkların tamamını kapsayan bir güvenlik sertifikası sunulmaz.

## Geliştirme

| Dizin | İçerik |
| --- | --- |
| `frontend/` | Monaco arayüzü ve native editör köprüsü |
| `integration/editor/` | Dosya düzenleme XML handler'ı |
| `integration/site-notice/` | Site notu ve birleşik root ayar formu |
| `integration/plugin/` | Kurulum/güncelleme yardımcıları |
| `integration/standalone/` | Tek dosya kurulum yöneticisi |
| `tools/`, `tests/` | Paketleme ve yerel test araçları |

Frontend geliştirme ortamında:

```sh
npm ci
npm run build
```

Yalnızca değişen özelliğin ilgili testlerini çalıştırın. Arşiv kullanan kurulum testlerinden önce aşağıda belirtilen canonical dağıtım girdilerini `dist/` altına yerleştirin. Kurucu için örnek:

```sh
python3 -I -B -m unittest discover -s tests -p test_standalone_setup.py
```

`tests/standalone_release_cli.py` yalnızca geçici Docker panel kökünde çalışır. Yerel kurucu kabul kaydı: Python 3.6 altında 8 test ve iki CLI senaryosu. Gerçek panel doğrulaması bunlardan ayrı tutulur.

Paketleyiciler sabit önceki dağıtımları kullanır: `npm run package:standalone` için canonical `dist/ismonaco-plugin-0.3.0.zip`; `npm run package:plugin` için canonical `dist/ismonaco-editor-0.2.5.zip` gerekir. Bu iki eski canonical ZIP, ilk v0.3.1 yayınının varlıkları arasında yer almaz; yalnızca kaynak checkout'u veya kurulum PYZ dosyasını indirmek geliştirme paketleme/test girdilerinin tamamını sağlamaz. Paketleme çalışması için bu girdiler ayrıca temin edilmelidir. Hash eşleşmeyen arşivler kabul edilmez. Frontend değişikliği, eski arşivi kullanan tek dosya paketinin içeriğini kendiliğinden değiştirmez.

### Yerel test araçları

`tools/editor_server.py` ve `tools/preview_server.py` yalnızca yerel geliştirme araçlarıdır; kurulan eklenti paketinde bulunmaz. Statik dosya erişimi çözümlenmiş `dist/frontend` diziniyle sınırlıdır. Mutlak yol ve dizin dışına çıkan sembolik bağlantı kaçışı için regresyon testleri `tests/test_harness_assets.py` dosyasındadır; normal dosya sunumu/MIME ve hata davranışı dahil dört odaklı test Python 3.6 altında da geçmiştir.

## GitHub'da paylaşılacak içerik

Kaynak kod, testler, herkese açık belgeler ve lisans paylaşılabilir. `node_modules/`, `dist/`, test/scan raporları, `.DS_Store`, gerçek ortam yapılandırmaları, anahtarlar ve HAR/log dosyaları paylaşılmamalıdır. Tarihsel sunucu envanteri `docs/FAZ_0.md` yerel çalışma kaydı olarak tutulur ve `.gitignore` ile dışlanır; genel uyumluluk bilgisi yukarıdaki tabloda bulunur.

`.gitignore` önceki commit'leri veya elle yüklenen Releases varlıklarını temizlemez. Bir geçmiş veya yeni paket yayımlanmadan önce ayrıca kontrol edilmelidir. Hata bildirirken panel/OS sürümü ve sansürlenmiş hata çıktısı yeterlidir; parola, cookie, oturum URL'si veya site dosyası içeriği paylaşmayın.

## Lisans

Projenin kendi kodu [MIT lisansı](LICENSE) ile sunulur. Üçüncü taraf bileşenler kendi lisanslarını korur:

| Bileşen | Lisans |
| --- | --- |
| Monaco Editor | MIT |
| DOMPurify | MPL-2.0 veya Apache-2.0 |
| Marked | MIT |
| Ace (yalnızca yerel test bağımlılığı) | BSD-3-Clause |

Dağıtımdaki lisans metinlerini ve `ThirdPartyNotices.txt` dosyasını koruyun. ISPmanager adı ve markaları ilgili hak sahiplerine aittir; bu lisans ISPmanager ürününü lisanslamaz.

Ek belgeler: [mimari](docs/MIMARI.md), [plugin kapsamı](docs/PLUGIN_0_3_0.md), [yayın standartları](docs/GELISTIRME_STANDARTLARI.md). Resmî kaynaklar: [geliştirici belgeleri](https://www.ispmanager.com/docs/developer-guide), [ISPmanager sistem gereksinimleri](https://www.ispmanager.com/docs/ispmanager/system-requirements). Panelin resmî OS desteği bu eklentinin test matrisi yerine geçmez.
