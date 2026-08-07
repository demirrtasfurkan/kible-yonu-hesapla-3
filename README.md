# Kıble Yönü Hesapla

Statik site, Python ile `src/` klasöründen üretilir. İçerikler Sveltia CMS üzerinden GitHub'a kaydedilir; GitHub'a bağlı Cloudflare dağıtımı değişiklikleri otomatik olarak yayınlar.

## Yerel build

```bash
python build.py
```

Çıktı `dist/` klasörüne yazılır. Cloudflare yapılandırmasındaki çıktı dizini de `dist` olarak ayarlıdır.

## İçerik paneli

Yayındaki panel adresi: `https://kibleyonuhesapla.com/admin/`

Panelden ana sayfa metinleri, blog yazıları ve şehir verileri düzenlenebilir. Girişte GitHub access token yöntemi kullanılır. Şehir koordinatları, kıble açısı, mesafe ve slug alanları yalnızca doğrulanmış değerlerle değiştirilmelidir.

Ayrıntılı kullanım adımları için `CMS-KULLANIM-REHBERI.txt` dosyasına bakın.
