#!/usr/bin/env python3
from pathlib import Path
import json, shutil, re, html

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"

def tr_number(value):
    return f"{int(value):,}".replace(",", ".")

def render(template, values):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    unresolved = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", template)))
    if unresolved:
        raise ValueError("Çözümlenmemiş alanlar: " + ", ".join(unresolved))
    return template

def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SRC / "site", DIST)

    cities = json.loads((SRC / "data" / "cities.json").read_text(encoding="utf-8"))
    city_template = (SRC / "templates" / "city.template.html").read_text(encoding="utf-8")
    index_template = (SRC / "templates" / "cities-index.template.html").read_text(encoding="utf-8")

    cards = []
    for city in sorted(cities, key=lambda x: x["name"]):
        values = {
            "CITY_NAME": city["name"],
            "CITY_NAME_UPPER": city["name"].upper(),
            "CITY_SLUG": city["slug"],
            "LAT": city["lat"],
            "LNG": city["lng"],
            "BEARING": city["bearing"],
            "BEARING_TR": str(city["bearing"]).replace(".", ","),
            "DIRECTION": city["direction"],
            "DIRECTION_LOWER": city["direction"].lower(),
            "DISTANCE": city["distance"],
            "DISTANCE_TR": tr_number(city["distance"]),
        }
        page = render(city_template, values)
        page_dir = DIST / city["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(page, encoding="utf-8")
        cards.append(
            f'<a href="/{city["slug"]}/"><strong>{html.escape(city["name"])}</strong>'
            f'<span>{str(city["bearing"]).replace(".", ",")}° · {html.escape(city["direction"])}</span></a>'
        )

    city_index = index_template.replace("{{CITY_CARDS}}", "\n".join(cards))
    city_index_dir = DIST / "sehirler"
    city_index_dir.mkdir(parents=True, exist_ok=True)
    (city_index_dir / "index.html").write_text(city_index, encoding="utf-8")

    urls = [
        ("https://kibleyonuhesapla.com/", "1.0", "weekly"),
        ("https://kibleyonuhesapla.com/sehirler/", "0.9", "monthly"),
        ("https://kibleyonuhesapla.com/gizlilik.html", "0.2", "yearly"),
    ]
    urls += [
        (f'https://kibleyonuhesapla.com/{c["slug"]}/', "0.8", "monthly")
        for c in cities
    ]

    sitemap = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for url, priority, frequency in urls:
        sitemap.append(
            f'  <url><loc>{url}</loc><changefreq>{frequency}</changefreq>'
            f'<priority>{priority}</priority></url>'
        )
    sitemap.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")

    print(f"Build tamamlandı: {len(cities)} il sayfası, {len(urls)} sitemap URL'si")
    print(f"Çıktı klasörü: {DIST}")

if __name__ == "__main__":
    main()
