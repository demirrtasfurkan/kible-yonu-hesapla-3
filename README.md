# Kıble Yönü Hesapla V8

## Bu sürümde ne değişti?

GitHub'a üretilmiş 81 şehir klasörü yüklenmez. Depoda yalnızca kaynak dosyalar bulunur.

Cloudflare her deploy sırasında:

```text
cities.json
+ city.template.html
+ generate.py
→ dist altında 81 SEO uyumlu statik sayfa
```

üretir.

## Depo yapısı

```text
.github/
src/
  data/
    cities.json
  templates/
    city.template.html
    cities-index.template.html
  site/
    assets/
    data/
    index.html
    gizlilik.html
    404.html
    robots.txt
    manifest.webmanifest
    sw.js
scripts/
  generate.py
.gitignore
build.py
wrangler.jsonc
```

## Cloudflare ayarları

Build command:

```text
python build.py
```

Deploy command:

```text
npx wrangler deploy
```

`wrangler.jsonc` içindeki asset directory:

```text
./dist
```

## Tasarım güncelleme

İl sayfalarının tamamını güncellemek için yalnızca:

```text
src/templates/city.template.html
```

dosyasını düzenle.

## İl verisi güncelleme

```text
src/data/cities.json
```

## Ana sayfa ve ortak dosyalar

```text
src/site/
```

## Yerel build

Python bulunan bir bilgisayarda:

```text
python build.py
```

Bu komut `dist/` klasörünü yeniden oluşturur.

## GitHub dosya sayısı

Üretilmiş `dist/` hariç tutulduğu için web arayüzünün 100 dosya sınırına takılmaz.
