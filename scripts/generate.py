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


def render(template, values):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    unresolved = re.findall(r"\{\{([A-Z0-9_]+)\}\}", template)
    if unresolved:
        raise ValueError(f"Eksik şablon alanları: {unresolved}")
    return template


def footer(description):
    return (
        '<footer><div class="container footer-grid">\n'
        f'<div><strong>Kıble Yönü Hesapla</strong><p>{html.escape(description)}</p></div>\n'
        '<div><strong>Popüler şehirler</strong><a href="/istanbul-kible-yonu/">İstanbul</a>'
        '<a href="/ankara-kible-yonu/">Ankara</a><a href="/izmir-kible-yonu/">İzmir</a>'
        '<a href="/bursa-kible-yonu/">Bursa</a></div>\n'
        '<div><strong>Keşfet</strong><a href="/sehirler/">81 İl</a><a href="/blog/">Kıble Rehberi</a>'
        '<a href="/hakkimizda/">Hakkımızda</a><a href="/kullanim-sartlari/">Kullanım Şartları</a>'
        '<a href="/gizlilik/">Gizlilik Politikası</a></div>\n</div></footer>'
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
    footer_html = footer(home["footer_description"])
    city_template = (SRC / "templates/city.template.html").read_text(encoding="utf-8")
    city_index = (SRC / "templates/cities-index.template.html").read_text(encoding="utf-8")
    blog_index = (SRC / "templates/blog-index.template.html").read_text(encoding="utf-8")
    blog_post = (SRC / "templates/blog-post.template.html").read_text(encoding="utf-8")

    cards = []
    for index, city in enumerate(sorted(cities, key=lambda item: item["name"])):
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
            "BEARING_TR": str(city["bearing"]).replace(".", ","),
            "DIRECTION": city["direction"],
            "DIRECTION_LOWER": city["direction"].lower(),
            "DISTANCE": city["distance"],
            "DISTANCE_TR": tr(city["distance"]),
            "NEARBY_CITY_LINKS": nearby,
            "CITY_BLOG_LINKS": blog_links,
            "FOOTER": footer_html,
        }
        directory = DIST / city["slug"]
        directory.mkdir(parents=True)
        (directory / "index.html").write_text(render(city_template, values), encoding="utf-8")
        cards.append(
            f'<a href="/{city["slug"]}/"><strong>{html.escape(city["name"])}</strong>'
            f'<span>{str(city["bearing"]).replace(".", ",")}° · {html.escape(city["direction"])}</span></a>'
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
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"<url><loc>{url}</loc></url>" for url in urls)
        + "\n</urlset>",
        encoding="utf-8",
    )
    print(f"Build tamamlandı: {len(cities)} il, {len(posts)} blog")


if __name__ == "__main__":
    main()
