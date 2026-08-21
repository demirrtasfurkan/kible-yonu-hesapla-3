#!/usr/bin/env python3
from pathlib import Path
import html
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"


def tr(value):
    return f"{int(value):,}".replace(",", ".")


def decimal_tr(value):
    formatted = f"{float(value):.1f}".replace(".", ",")
    return formatted[:-2] if formatted.endswith(",0") else formatted


def direction_16(value):
    labels = [
        "Kuzey", "Kuzey-Kuzeydoğu", "Kuzeydoğu", "Doğu-Kuzeydoğu",
        "Doğu", "Doğu-Güneydoğu", "Güneydoğu", "Güney-Güneydoğu",
        "Güney", "Güney-Güneybatı", "Güneybatı", "Batı-Güneybatı",
        "Batı", "Batı-Kuzeybatı", "Kuzeybatı", "Kuzey-Kuzeybatı",
    ]
    return labels[round(float(value) / 22.5) % 16]


def signed_degree(value):
    value = round(float(value), 1)
    if abs(value) < 0.05:
        return "0°"
    sign = "+" if value > 0 else "−"
    return f"{sign}{decimal_tr(abs(value))}°"


def district_summary(city):
    districts = city.get("districts", [])
    if not districts:
        return {
            "count": 0,
            "minimum": city["bearing"],
            "maximum": city["bearing"],
            "average": city["bearing"],
            "spread": 0,
            "minimum_item": {"name": city["name"], "bearing": city["bearing"]},
            "maximum_item": {"name": city["name"], "bearing": city["bearing"]},
            "closest_item": {"name": city["name"], "bearing": city["bearing"]},
        }
    minimum_item = min(districts, key=lambda item: item["bearing"])
    maximum_item = max(districts, key=lambda item: item["bearing"])
    closest_item = min(districts, key=lambda item: abs(item["bearing"] - city["bearing"]))
    average = sum(item["bearing"] for item in districts) / len(districts)
    return {
        "count": len(districts),
        "minimum": minimum_item["bearing"],
        "maximum": maximum_item["bearing"],
        "average": average,
        "spread": maximum_item["bearing"] - minimum_item["bearing"],
        "minimum_item": minimum_item,
        "maximum_item": maximum_item,
        "closest_item": closest_item,
    }


def district_options(city):
    return "".join(
        '<option '
        f'value="{html.escape(item["slug"], quote=True)}" '
        f'data-name="{html.escape(item["name"], quote=True)}" '
        f'data-lat="{item["lat"]}" data-lng="{item["lng"]}" '
        f'data-bearing="{item["bearing"]}" data-distance="{item["distance"]}">'
        f'{html.escape(item["name"])} · {decimal_tr(item["bearing"])}°</option>'
        for item in city.get("districts", [])
    )


def district_table(city):
    rows = []
    for item in city.get("districts", []):
        difference = item["bearing"] - city["bearing"]
        rows.append(
            '<tr>'
            f'<th scope="row">{html.escape(item["name"])}</th>'
            f'<td>{decimal_tr(item["bearing"])}°</td>'
            f'<td>{tr(item["distance"])} km</td>'
            f'<td>{signed_degree(difference)}</td>'
            '<td><button type="button" class="district-use" aria-label="Haritada göster" '
            f'data-name="{html.escape(item["name"], quote=True)}" '
            f'data-lat="{item["lat"]}" data-lng="{item["lng"]}">↗</button></td>'
            '</tr>'
        )
    return "".join(rows)


def city_comparison_rows(city, city_lookup):
    rows = []
    for nearby in city["nearby"]:
        other = city_lookup.get(nearby["slug"])
        if not other:
            continue
        rows.append(
            '<tr>'
            f'<th scope="row"><a href="/{other["slug"]}/">{html.escape(other["name"])}</a></th>'
            f'<td>{decimal_tr(other["bearing"])}°</td>'
            f'<td>{tr(other["distance"])} km</td>'
            f'<td>{decimal_tr(abs(other["bearing"] - city["bearing"]))}°</td>'
            f'<td>{tr(nearby["distance"])} km</td>'
            '</tr>'
        )
    return "".join(rows)


def angle_comparison_cards(city, cities):
    others = [item for item in cities if item["slug"] != city["slug"]]
    similar = sorted(others, key=lambda item: abs(item["bearing"] - city["bearing"]))[:5]
    different = sorted(others, key=lambda item: abs(item["bearing"] - city["bearing"]), reverse=True)[:5]

    def cards(items):
        return "".join(
            f'<a href="/{item["slug"]}/"><strong>{html.escape(item["name"])}</strong>'
            f'<span>{decimal_tr(item["bearing"])}° · fark '
            f'{decimal_tr(abs(item["bearing"] - city["bearing"]))}°</span></a>'
            for item in items
        )

    return cards(similar), cards(different)


def geographic_extremes(city):
    districts = city.get("districts", [])
    if not districts:
        return ""
    entries = [
        ("Kuzey", max(districts, key=lambda item: item["lat"])),
        ("Güney", min(districts, key=lambda item: item["lat"])),
        ("Doğu", max(districts, key=lambda item: item["lng"])),
        ("Batı", min(districts, key=lambda item: item["lng"])),
    ]
    return "".join(
        '<tr>'
        f'<th scope="row">{position}</th><td>{html.escape(item["name"])}</td>'
        f'<td>{decimal_tr(item["bearing"])}°</td>'
        f'<td>{signed_degree(item["bearing"] - city["bearing"])}</td>'
        '</tr>'
        for position, item in entries
    )


def city_narrative(city, summary, index):
    name = city["name"]
    angle = decimal_tr(city["bearing"])
    direction = direction_16(city["bearing"])
    low = summary["minimum_item"]
    high = summary["maximum_item"]
    variants = [
        f"{name} merkezinde gerçek kuzeyi başlangıç aldığınızda Kâbe yönü {angle}° açısında kalır. Bu değer pusula üzerinde {direction.lower()} doğrultusuna karşılık gelir.",
        f"{name} için il merkezi hesabı {angle}° sonucunu verir. Başka bir deyişle kıble, gerçek kuzeyden saat yönünde ölçüldüğünde {direction.lower()} tarafındadır.",
        f"Şehir merkezini esas alan hesaplamada {name} kıble açısı {angle}° bulunur. Haritadaki çizgi ve canlı pusula aynı {direction.lower()} doğrultusunu gösterir.",
        f"{name} merkez koordinatlarından Kâbe’ye uzanan başlangıç yönü {angle}°’dir. Bu açı günlük yön tarifiyle {direction.lower()} tarafına denk gelir.",
    ]
    district_text = (
        f"İlçeler arasında aynı sayıyı kullanmak doğru olmaz. {low['name']} için {decimal_tr(low['bearing'])}° olan açı, "
        f"{high['name']} için {decimal_tr(high['bearing'])}° değerine çıkar; iki uç arasında {decimal_tr(summary['spread'])}° fark vardır."
    )
    return variants[index % len(variants)], district_text


def render(template, values):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    unresolved = re.findall(r"\{\{([A-Z0-9_]+)\}\}", template)
    if unresolved:
        raise ValueError(f"Eksik şablon alanları: {unresolved}")
    return template


def footer(description, cities):
    city_links = "".join(
        f'<a href="/{city["slug"]}/">{html.escape(city["name"])} Kıble</a>'
        for city in sorted(cities, key=lambda item: item["name"])
    )
    return (
        '<footer><div class="container"><div class="footer-grid">\n'
        f'<div><strong>Kıble Yönü Hesapla</strong><p>{html.escape(description)}</p></div>\n'
        '<div><strong>Popüler şehirler</strong><a href="/istanbul-kible-yonu/">İstanbul</a>'
        '<a href="/ankara-kible-yonu/">Ankara</a><a href="/izmir-kible-yonu/">İzmir</a>'
        '<a href="/bursa-kible-yonu/">Bursa</a></div>\n'
        '<div><strong>Keşfet</strong><a href="/sehirler/">81 İl</a><a href="/blog/">Kıble Rehberi</a>'
        '<a href="/hakkimizda/">Hakkımızda</a><a href="/kullanim-sartlari/">Kullanım Şartları</a>'
        '<a href="/hesaplama-yontemi/">Hesaplama Yöntemi</a><a href="/iletisim/">İletişim</a>'
        '<a href="/gizlilik/">Gizlilik Politikası</a></div>\n</div>'
        '<div class="footer-cities"><strong>Türkiye genelinde kıble yönleri</strong>'
        f'<div class="footer-city-grid">{city_links}</div></div></div></footer>'
    )


def guide_sections(sections):
    blocks = []
    for section in sections:
        body = "".join(
            f'<p>{html.escape(text)}</p>' for text in section.get("paragraphs_before", [])
        )
        items = section.get("list_items", [])
        list_type = section.get("list_type", "none")
        if items and list_type in {"ordered", "unordered"}:
            tag = "ol" if list_type == "ordered" else "ul"
            body += f'<{tag}>' + "".join(f'<li>{html.escape(item)}</li>' for item in items) + f'</{tag}>'
        body += "".join(
            f'<p>{html.escape(text)}</p>' for text in section.get("paragraphs_after", [])
        )
        if section.get("tip"):
            body += f'<p class="tip-box">{html.escape(section["tip"])}</p>'
        if section.get("cta_label") and section.get("cta_url"):
            body += (
                f'<p><a class="btn btn-secondary" href="{html.escape(section["cta_url"], quote=True)}">'
                f'{html.escape(section["cta_label"])}</a></p>'
            )
        blocks.append(
            '<article class="content-block">'
            f'<h2>{html.escape(section["heading"])}</h2>{body}</article>'
        )
    return (
        '<section class="homepage-content" id="rehber">'
        '<div class="container content-stack">'
        + "".join(blocks)
        + '</div></section>'
    )


def update_homepage(home):
    path = DIST / "index.html"
    page = path.read_text(encoding="utf-8")

    replacements = [
        (r"<title>.*?</title>", f'<title>{html.escape(home["seo_title"])}</title>'),
        (
            r'<meta name="description" content="[^"]*">',
            f'<meta name="description" content="{html.escape(home["meta_description"], quote=True)}">',
        ),
        (
            r'<meta property="og:title" content="[^"]*">',
            f'<meta property="og:title" content="{html.escape(home["seo_title"], quote=True)}">',
        ),
        (
            r'<meta property="og:description" content="[^"]*">',
            f'<meta property="og:description" content="{html.escape(home["meta_description"], quote=True)}">',
        ),
        (r'<span class="eyebrow">.*?</span>', f'<span class="eyebrow">{html.escape(home["hero_eyebrow"])}</span>'),
        (r'<h1>.*?</h1>', f'<h1>{html.escape(home["h1"])}</h1>'),
        (r'<p class="lead">.*?</p>', f'<p class="lead">{html.escape(home["hero_lead"])}</p>'),
        (
            r'(<p id="statusMessage"[^>]*>).*?(</p>)',
            rf'\1{html.escape(home["status_message"])}\2',
        ),
        (
            r'(<p id="locationPrivacy"[^>]*>).*?(</p>)',
            rf'\1{html.escape(home["privacy_note"])}\2',
        ),
    ]
    for pattern, replacement in replacements:
        page, count = re.subn(pattern, replacement, page, count=1, flags=re.DOTALL)
        if count != 1:
            raise ValueError(f"Ana sayfa alanı bulunamadı: {pattern}")

    page, count = re.subn(
        r'<section class="homepage-content".*?</section>\s*(?=<section class="faq")',
        guide_sections(home["guide_sections"]) + "\n\n    ",
        page,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Ana sayfa rehber bölümü bulunamadı")

    faq_html = "".join(
        f'<details><summary><h3>{html.escape(item["question"])}</h3></summary>'
        f'<p>{html.escape(item["answer"])}</p></details>'
        for item in home["faqs"]
    )
    page, count = re.subn(
        r'(<div class="faq-list">).*?(</div>)', rf'\1{faq_html}\2', page, count=1, flags=re.DOTALL
    )
    if count != 1:
        raise ValueError("Ana sayfa SSS listesi bulunamadı")
    page, count = re.subn(
        r'(<section class="faq".*?<h2>).*?(</h2>)',
        rf'\1{html.escape(home["faq_heading"])}\2',
        page,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Ana sayfa SSS başlığı bulunamadı")
    page, count = re.subn(
        r'(<p class="closing-copy">).*?(</p>)',
        rf'\1{html.escape(home["closing_copy"])}\2',
        page,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Ana sayfa kapanış metni bulunamadı")

    schema_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, flags=re.DOTALL)
    if not schema_match:
        raise ValueError("Ana sayfa yapılandırılmış verisi bulunamadı")
    schema = json.loads(schema_match.group(1))
    for item in schema.get("@graph", []):
        if item.get("@type") == "FAQPage":
            item["mainEntity"] = [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": faq["answer"]},
                }
                for faq in home["faqs"]
            ]
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    page = page[: schema_match.start(1)] + "\n" + schema_text + "\n  " + page[schema_match.end(1) :]
    page = page.replace(
        "Canlı pusula, harita ve şehir bazlı kıble rehberleri.", home["footer_description"], 1
    )
    path.write_text(page, encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SRC / "site", DIST)

    city_data = json.loads((SRC / "data/cities.json").read_text(encoding="utf-8"))
    blog_data = json.loads((SRC / "data/blog.json").read_text(encoding="utf-8"))
    home = json.loads((SRC / "data/homepage.json").read_text(encoding="utf-8"))
    cities = city_data["cities"] if isinstance(city_data, dict) else city_data
    posts = blog_data["posts"] if isinstance(blog_data, dict) else blog_data
    if not cities or not posts:
        raise ValueError("Şehir ve blog listeleri boş bırakılamaz")

    update_homepage(home)
    footer_html = footer(home["footer_description"], cities)
    city_lookup = {city["slug"]: city for city in cities}
    city_template = (SRC / "templates/city.template.html").read_text(encoding="utf-8")
    city_index = (SRC / "templates/cities-index.template.html").read_text(encoding="utf-8")
    blog_index = (SRC / "templates/blog-index.template.html").read_text(encoding="utf-8")
    blog_post = (SRC / "templates/blog-post.template.html").read_text(encoding="utf-8")

    cards = []
    for index, city in enumerate(sorted(cities, key=lambda item: item["name"])):
        summary = district_summary(city)
        precise_direction = direction_16(city["bearing"])
        similar_cards, different_cards = angle_comparison_cards(city, cities)
        intro_text, district_text = city_narrative(city, summary, index)
        nearby = "".join(
            f'<a href="/{item["slug"]}/">{html.escape(item["name"])} kıble yönü'
            f'<span>Yaklaşık {tr(item["distance"])} km</span></a>'
            for item in city["nearby"]
        )
        selected_posts = [posts[(index + offset) % len(posts)] for offset in range(min(3, len(posts)))]
        blog_links = "".join(
            f'<a class="blog-mini-card" href="/blog/{post["slug"]}/"><span>REHBER</span>'
            f'<strong>{html.escape(post["title"])}</strong><p>{html.escape(post["excerpt"])}</p></a>'
            for post in selected_posts
        )
        values = {
            "CITY_NAME": city["name"],
            "CITY_NAME_UPPER": city["name"].upper(),
            "CITY_SLUG": city["slug"],
            "LAT": city["lat"],
            "LNG": city["lng"],
            "BEARING": city["bearing"],
            "BEARING_TR": decimal_tr(city["bearing"]),
            "BEARING_ROUNDED": round(city["bearing"]),
            "DIRECTION": precise_direction,
            "DIRECTION_LOWER": precise_direction.lower(),
            "DISTANCE": city["distance"],
            "DISTANCE_TR": tr(city["distance"]),
            "DISTRICT_COUNT": summary["count"],
            "MIN_BEARING_TR": decimal_tr(summary["minimum"]),
            "MAX_BEARING_TR": decimal_tr(summary["maximum"]),
            "AVG_BEARING_TR": decimal_tr(summary["average"]),
            "SPREAD_TR": decimal_tr(summary["spread"]),
            "MIN_DISTRICT": html.escape(summary["minimum_item"]["name"]),
            "MAX_DISTRICT": html.escape(summary["maximum_item"]["name"]),
            "CLOSEST_DISTRICT": html.escape(summary["closest_item"]["name"]),
            "CLOSEST_DISTRICT_BEARING_TR": decimal_tr(summary["closest_item"]["bearing"]),
            "DISTRICT_OPTIONS": district_options(city),
            "DISTRICT_ROWS": district_table(city),
            "NEARBY_COMPARISON_ROWS": city_comparison_rows(city, city_lookup),
            "SIMILAR_ANGLE_CARDS": similar_cards,
            "DIFFERENT_ANGLE_CARDS": different_cards,
            "GEOGRAPHIC_EXTREME_ROWS": geographic_extremes(city),
            "CITY_INTRO_TEXT": html.escape(intro_text),
            "DISTRICT_NARRATIVE": html.escape(district_text),
            "NEARBY_CITY_LINKS": nearby,
            "CITY_BLOG_LINKS": blog_links,
            "FOOTER": footer_html,
        }
        directory = DIST / city["slug"]
        directory.mkdir(parents=True)
        (directory / "index.html").write_text(render(city_template, values), encoding="utf-8")
        cards.append(
            f'<a href="/{city["slug"]}/"><strong>{html.escape(city["name"])}</strong>'
            f'<span>{decimal_tr(city["bearing"])}° · {html.escape(precise_direction)}</span></a>'
        )

    directory = DIST / "sehirler"
    directory.mkdir()
    (directory / "index.html").write_text(
        render(city_index, {"CITY_CARDS": "".join(cards), "FOOTER": footer_html}), encoding="utf-8"
    )

    blog_cards = []
    for post in posts:
        blog_cards.append(
            f'<a class="blog-card" href="/blog/{post["slug"]}/"><span class="meta">'
            f'{html.escape(post["reading_time"])} OKUMA</span><h2>{html.escape(post["title"])}</h2>'
            f'<p>{html.escape(post["excerpt"])}</p></a>'
        )
        content = "".join(
            f'<h2>{html.escape(section["heading"])}</h2>'
            + "".join(f'<p>{html.escape(paragraph)}</p>' for paragraph in section["paragraphs"])
            for section in post["sections"]
        )
        faq = "".join(
            f'<details><summary>{html.escape(item["question"])}</summary>'
            f'<p>{html.escape(item["answer"])}</p></details>'
            for item in post["faq"]
        )
        related = "".join(
            f'<a href="/blog/{item["slug"]}/">{html.escape(item["title"])}</a>'
            for item in posts
            if item["slug"] != post["slug"]
        )
        popular = "".join(
            f'<a href="/{slug}-kible-yonu/">{name} kıble yönü</a>'
            for name, slug in [("İstanbul", "istanbul"), ("Ankara", "ankara"), ("İzmir", "izmir"), ("Bursa", "bursa")]
        )
        schema = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": post["title"],
                "description": post["description"],
            },
            ensure_ascii=False,
        )
        values = {
            "TITLE": html.escape(post["title"]),
            "DESCRIPTION": html.escape(post["description"]),
            "SLUG": post["slug"],
            "READING_TIME": html.escape(post["reading_time"]),
            "ARTICLE_CONTENT": content,
            "RELATED_POSTS": related,
            "POPULAR_CITIES": popular,
            "FAQ_HTML": faq,
            "SCHEMA": schema,
            "FOOTER": footer_html,
        }
        directory = DIST / "blog" / post["slug"]
        directory.mkdir(parents=True)
        (directory / "index.html").write_text(render(blog_post, values), encoding="utf-8")

    directory = DIST / "blog"
    directory.mkdir(exist_ok=True)
    (directory / "index.html").write_text(
        render(blog_index, {"BLOG_CARDS": "".join(blog_cards), "FOOTER": footer_html}), encoding="utf-8"
    )

    urls = [
        "https://kibleyonuhesapla.com/",
        "https://kibleyonuhesapla.com/sehirler/",
        "https://kibleyonuhesapla.com/blog/",
        "https://kibleyonuhesapla.com/gizlilik/",
        "https://kibleyonuhesapla.com/hakkimizda/",
        "https://kibleyonuhesapla.com/kullanim-sartlari/",
    ]
    urls += [f'https://kibleyonuhesapla.com/{city["slug"]}/' for city in cities]
    urls += [f'https://kibleyonuhesapla.com/blog/{post["slug"]}/' for post in posts]
    urls += [
        "https://kibleyonuhesapla.com/hesaplama-yontemi/",
        "https://kibleyonuhesapla.com/iletisim/",
    ]
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"<url><loc>{url}</loc></url>" for url in urls)
        + "\n</urlset>",
        encoding="utf-8",
    )

    locations = []
    for city in cities:
        locations.append(
            {"name": city["name"], "parent": "", "type": "İl", "lat": city["lat"], "lng": city["lng"]}
        )
        locations.extend(
            {
                "name": district["name"],
                "parent": city["name"],
                "type": "İlçe",
                "lat": district["lat"],
                "lng": district["lng"],
            }
            for district in city.get("districts", [])
        )
    (DIST / "data" / "locations.json").write_text(
        json.dumps(locations, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    for path in DIST.rglob("*.html"):
        if path.parts[-2:] == ("admin", "index.html"):
            continue
        page = path.read_text(encoding="utf-8")
        if re.search(r"<footer\b.*?</footer>", page, flags=re.DOTALL):
            page = re.sub(r"<footer\b.*?</footer>", footer_html, page, count=1, flags=re.DOTALL)
        page = re.sub(r'/assets/css/style\.css(?:\?v=\d+)?', '/assets/css/style.css?v=31', page)
        page = re.sub(r'/assets/js/app\.js(?:\?v=\d+)?', '/assets/js/app.js?v=31', page)
        page = re.sub(r'/assets/js/qibla-map\.js(?:\?v=\d+)?', '/assets/js/qibla-map.js?v=31', page)
        if '/assets/js/nav.js' not in page:
            page = page.replace('</body>', '<script src="/assets/js/nav.js?v=31" defer></script>\n</body>')
        path.write_text(page, encoding="utf-8")
    print(f"Build tamamlandı: {len(cities)} il, {len(posts)} blog")


if __name__ == "__main__":
    main()
