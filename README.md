# Kıble Yönü Hesapla

Statik site, Python ile `src/` klasöründen üretilir. İçerikler Sveltia CMS üzerinden GitHub'a kaydedilir; GitHub'a bağlı Cloudflare dağıtımı değişiklikleri otomatik olarak yayınlar.

Şehir altyapısı 81 il ve 971 ilçe merkezini kapsar. İl ve ilçe verileri statik HTML'e build sırasında yazılır. Şehir sayfaları ayrıca harita, canlı pusula, ilçe tablosu, açı aralığı, karşılaştırmalar ve özgün doğrulama adımlarını otomatik üretir.

## Yerel build

```bash
python build.py
```

Çıktı `dist/` klasörüne yazılır. Cloudflare yapılandırmasındaki çıktı dizini de `dist` olarak ayarlıdır.

Kaynakların tek doğrusu `src/` klasörüdür. `dist/` üretilmiş çıktıdır; repoya veya ZIP paketine eklenmemelidir. Sitemap build sırasında üretilir ve her URL için kaynak değişiklik tarihinden hesaplanan `lastmod` içerir. Arama motorlarının dikkate almadığı `priority` ve `changefreq` alanları bilerek kullanılmaz.

## Cloudflare Pages ayarları

- Build komutu: `python build.py`
- Çıktı dizini: `dist`
- Kök dizin: depo kökü
- Son kontrol: `python build.py` komutunun hatasız tamamlanması

## İçerik paneli

Yayındaki panel adresi: `https://kibleyonuhesapla.com/admin/`

Panelden ana sayfa, Sık Sorulan Sorular, Hakkımızda, Gizlilik Politikası, Kullanım Şartları, İletişim ve Hesaplama Yöntemi içerikleri düzenlenebilir. Blog yazıları ile şehir ve ilçe verileri de aynı panelde yönetilir. Girişte GitHub access token yöntemi kullanılır. Koordinat, kıble açısı, mesafe ve slug alanları yalnızca doğrulanmış değerlerle değiştirilmelidir.

Kurumsal ve rehber sayfalarının kaynakları `src/data/pages/` klasöründedir. Görünen HTML ve yapılandırılmış veri build sırasında aynı içerik kaynağından üretildiği için SSS metni ile FAQ schema birbirinden kopmaz.

Ayrıntılı kullanım adımları için `CMS-KULLANIM-REHBERI.txt` dosyasına bakın.
