# Kıble Yönü Hesapla

Statik site, Python ile `src/` klasöründen üretilir. İçerikler Sveltia CMS üzerinden GitHub'a kaydedilir; GitHub'a bağlı Cloudflare dağıtımı değişiklikleri otomatik olarak yayınlar.

V2 şehir altyapısı 81 il ve 971 ilçe merkezini kapsar. İl ve ilçe sayfalarındaki kıble açısı, yön ve Kâbe mesafesi statik HTML'e build sırasında yazılır. Şehir sayfaları ayrıca ilçe tablosu, açı aralığı, yakın il karşılaştırması ve coğrafi uç istatistiklerini otomatik üretir.

## Yerel build

```bash
python build.py
```

Çıktı `dist/` klasörüne yazılır. Cloudflare yapılandırmasındaki çıktı dizini de `dist` olarak ayarlıdır.

## İçerik paneli

Yayındaki panel adresi: `https://kibleyonuhesapla.com/admin/`

Panelden ana sayfa metinleri, blog yazıları, şehir ve ilçe verileri düzenlenebilir. Girişte GitHub access token yöntemi kullanılır. Koordinat, kıble açısı, mesafe ve slug alanları yalnızca doğrulanmış değerlerle değiştirilmelidir.

Ayrıntılı kullanım adımları için `CMS-KULLANIM-REHBERI.txt` dosyasına bakın.
