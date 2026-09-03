#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import html
import json
import re
import shutil
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"


def last_modified(*paths):
    """Return the last real source-change date used to produce a URL."""
    relative_paths = [str(Path(path).resolve().relative_to(ROOT)) for path in paths]
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", *relative_paths],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", result.stdout.strip()):
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        pass
    latest = max(Path(path).stat().st_mtime for path in paths if Path(path).exists())
    return datetime.fromtimestamp(latest, timezone.utc).date().isoformat()


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


INLINE_LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")
SITE_HOSTS = {"kibleyonuhesapla.com", "www.kibleyonuhesapla.com"}


def safe_link_target(value):
    value = value.strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    if value.startswith("#"):
        return value
    if value.startswith("kibleyonuhesapla.com") or value.startswith("www.kibleyonuhesapla.com"):
        value = f"https://{value}"
    if value.startswith("https://"):
        parsed = urlsplit(value)
        if parsed.hostname and parsed.hostname.lower() in SITE_HOSTS:
            target = parsed.path or "/"
            if parsed.query:
                target += f"?{parsed.query}"
            if parsed.fragment:
                target += f"#{parsed.fragment}"
            return target
        return value
    if value.startswith("mailto:") and re.fullmatch(r"mailto:[^\s@]+@[^\s@]+(?:\?[^\s]*)?", value):
        return value
    return None


def render_inline_text(value):
    value = html.escape(value)
    value = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", value)
    return value


def render_inline(value):
    """Render safe links and basic emphasis while escaping raw HTML."""
    output = []
    cursor = 0
    for match in INLINE_LINK_RE.finditer(value):
        output.append(render_inline_text(value[cursor : match.start()]))
        label, target = match.groups()
        safe_target = safe_link_target(target)
        if safe_target:
            output.append(
                f'<a href="{html.escape(safe_target, quote=True)}">'
                f'{render_inline_text(label)}</a>'
            )
        else:
            output.append(render_inline_text(match.group(0)))
        cursor = match.end()
    output.append(render_inline_text(value[cursor:]))
    return "".join(output)


def plain_text(value):
    """Remove supported Markdown syntax for metadata and structured data."""
    value = INLINE_LINK_RE.sub(lambda match: match.group(1), value)
    return value.replace("**", "").replace("*", "").strip()


def footer(description, cities):
    city_links = "".join(
        f'<a href="/{city["slug"]}/">{html.escape(city["name"])} Kıble</a>'
        for city in sorted(cities, key=lambda item: item["name"])
    )
    return (
        '<footer><div class="container"><div class="footer-grid">\n'
        f'<div><strong>Kıble Yönü Hesapla</strong><p>{html.escape(description)}</p>'
        '<nav class="social-links" aria-label="Sosyal medya hesaplarımız">'
        '<a href="https://x.com/kibleyonuhesap" target="_blank" rel="noopener noreferrer" '
        'aria-label="Kıble Yönü Hesapla X profili">'
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.657l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z"/></svg>'
        '<span class="sr-only">X</span></a>'
        '<a href="https://www.linkedin.com/company/k%C4%B1ble-y%C3%B6n%C3%BC-hesapla" target="_blank" '
        'rel="noopener noreferrer" aria-label="Kıble Yönü Hesapla LinkedIn sayfası">'
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.047c.475-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286h-.002ZM5.337 7.433a2.062 2.062 0 1 1 0-4.124 2.062 2.062 0 0 1 0 4.124ZM7.119 20.452H3.555V9h3.564v11.452Z"/></svg>'
        '<span class="sr-only">LinkedIn</span></a>'
        '<a href="https://bsky.app/profile/kibleyonuhesapla.bsky.social" target="_blank" '
        'rel="noopener noreferrer" aria-label="Kıble Yönü Hesapla Bluesky profili">'
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364-4.648.69-8.775 2.383-3.362 8.409 5.956 6.173 8.165-1.324 8.355-2.836.19 1.512 2.399 9.009 8.355 2.836 5.413-6.026 1.286-7.72-3.362-8.409 2.67.296 5.568-.628 6.383-3.364.246-.829.624-5.79.624-6.479 0-.69-.139-1.86-.902-2.203-.659-.299-1.664-.62-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8Z"/></svg>'
        '<span class="sr-only">Bluesky</span></a></nav></div>\n'
        '<div><strong>Popüler şehirler</strong><a href="/istanbul-kible-yonu/">İstanbul</a>'
        '<a href="/ankara-kible-yonu/">Ankara</a><a href="/izmir-kible-yonu/">İzmir</a>'
        '<a href="/bursa-kible-yonu/">Bursa</a></div>\n'
        '<div><strong>Keşfet</strong><a href="/sehirler/">81 İl</a><a href="/blog/">Kıble Rehberi</a>'
        '<a href="/hakkimizda/">Hakkımızda</a><a href="/kullanim-sartlari/">Kullanım Şartları</a>'
        '<a href="/hesaplama-yontemi/">Hesaplama Yöntemi</a><a href="/iletisim/">İletişim</a>'
        '<a href="/gizlilik/">Gizlilik Politikası</a></div>\n'
        '<div><strong>Hızlı yardım</strong><a href="/sikca-sorulan-sorular/">Kıble Ne Tarafta?</a>'
        '<a href="/#arac">GPS ile Kıble Bul</a><a href="/#arac">Canlı Kıble Pusulası</a>'
        '<a href="/blog/telefon-kible-pusulasi-dogru-mu/">Pusula Doğruluğu</a>'
        '<a href="/blog/pusulasiz-kible-bulma-yontemleri/">Pusulasız Kıble Bulma</a></div>\n</div>'
        '<div class="footer-cities"><strong>Türkiye genelinde kıble yönleri</strong>'
        f'<div class="footer-city-grid">{city_links}</div></div></div></footer>'
    )


def guide_sections(sections):
    blocks = []
    for section in sections:
        body = "".join(
            f'<p>{render_inline(text)}</p>' for text in section.get("paragraphs_before", [])
        )
        items = section.get("list_items", [])
        list_type = section.get("list_type", "none")
        if items and list_type in {"ordered", "unordered"}:
            tag = "ol" if list_type == "ordered" else "ul"
            body += f'<{tag}>' + "".join(f'<li>{render_inline(item)}</li>' for item in items) + f'</{tag}>'
        body += "".join(
            f'<p>{render_inline(text)}</p>' for text in section.get("paragraphs_after", [])
        )
        if section.get("tip"):
            body += f'<p class="tip-box">{render_inline(section["tip"])}</p>'
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


def content_sections(sections):
    blocks = []
    for section in sections:
        body = "".join(f'<p>{render_inline(text)}</p>' for text in section.get("paragraphs", []))
        if section.get("cta_label") and section.get("cta_url"):
            body += (
                f'<p><a class="btn btn-primary" href="{html.escape(section["cta_url"], quote=True)}">'
                f'{html.escape(section["cta_label"])}</a></p>'
            )
        blocks.append(f'<section><h2>{html.escape(section["heading"])}</h2>{body}</section>')
    return "".join(blocks)


def page_schema(slug, page, page_type="WebPage"):
    url = f"https://kibleyonuhesapla.com/{slug}/"
    return json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": page_type,
                    "@id": f"{url}#webpage",
                    "url": url,
                    "name": page["seo_title"],
                    "description": page["meta_description"],
                    "inLanguage": "tr-TR",
                    "breadcrumb": {"@id": f"{url}#breadcrumb"},
                },
                {
                    "@type": "BreadcrumbList",
                    "@id": f"{url}#breadcrumb",
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": 1,
                            "name": "Ana Sayfa",
                            "item": "https://kibleyonuhesapla.com/",
                        },
                        {
                            "@type": "ListItem",
                            "position": 2,
                            "name": page["h1"],
                            "item": url,
                        },
                    ],
                },
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def write_content_page(slug, page, template, footer_html, breadcrumb, page_type="WebPage"):
    aside_items = "".join(f'<li>{render_inline(item)}</li>' for item in page["aside_items"])
    cta = ""
    if page.get("cta_label") and page.get("cta_url"):
        cta = (
            f'<a class="btn btn-primary full" href="{html.escape(page["cta_url"], quote=True)}">'
            f'{html.escape(page["cta_label"])}</a>'
        )
    values = {
        "TITLE": html.escape(page["seo_title"]),
        "DESCRIPTION": html.escape(page["meta_description"], quote=True),
        "SLUG": slug,
        "BREADCRUMB": html.escape(breadcrumb),
        "EYEBROW": html.escape(page["eyebrow"]),
        "H1": html.escape(page["h1"]),
        "LEAD": html.escape(page["lead"]),
        "SECTIONS": content_sections(page["sections"]),
        "ASIDE_TITLE": html.escape(page["aside_title"]),
        "ASIDE_ITEMS": aside_items,
        "CTA": cta,
        "SCHEMA": page_schema(slug, page, page_type),
        "FOOTER": footer_html,
    }
    directory = DIST / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.html").write_text(render(template, values), encoding="utf-8")


def write_faq_page(page, template, footer_html):
    slug = "sikca-sorulan-sorular"
    url = f"https://kibleyonuhesapla.com/{slug}/"
    faq_entities = [
        {
            "@type": "Question",
            "name": item["question"],
            "acceptedAnswer": {"@type": "Answer", "text": plain_text(item["answer"])},
        }
        for item in page["faqs"]
    ]
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "FAQPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": page["seo_title"],
                "description": page["meta_description"],
                "inLanguage": "tr-TR",
                "mainEntity": faq_entities,
                "breadcrumb": {"@id": f"{url}#breadcrumb"},
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Ana Sayfa",
                        "item": "https://kibleyonuhesapla.com/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Sık Sorulan Sorular",
                        "item": url,
                    },
                ],
            },
        ],
    }
    values = {
        "TITLE": html.escape(page["seo_title"]),
        "DESCRIPTION": html.escape(page["meta_description"], quote=True),
        "EYEBROW": html.escape(page["eyebrow"]),
        "H1": html.escape(page["h1"]),
        "LEAD": html.escape(page["lead"]),
        "INTRO_SECTIONS": content_sections(page["intro_sections"]),
        "FAQ_HEADING": html.escape(page["faq_heading"]),
        "FAQ_HTML": "".join(
            f'<details><summary><h3>{html.escape(item["question"])}</h3></summary>'
            f'<p>{render_inline(item["answer"])}</p></details>'
            for item in page["faqs"]
        ),
        "ASIDE_TITLE": html.escape(page["aside_title"]),
        "ASIDE_ITEMS": "".join(f'<li>{render_inline(item)}</li>' for item in page["aside_items"]),
        "CTA_LABEL": html.escape(page["cta_label"]),
        "CTA_URL": html.escape(page["cta_url"], quote=True),
        "SCHEMA": json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
        "FOOTER": footer_html,
    }
    directory = DIST / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.html").write_text(render(template, values), encoding="utf-8")


def popular_cities_section(cities):
    featured_names = [
        "İstanbul",
        "Ankara",
        "İzmir",
        "Bursa",
        "Antalya",
        "Konya",
        "Adana",
        "Gaziantep",
        "Kayseri",
        "Eskişehir",
        "Diyarbakır",
        "Samsun",
    ]
    city_lookup = {city["name"]: city for city in cities}
    missing = [name for name in featured_names if name not in city_lookup]
    if missing:
        raise ValueError(f"Popüler şehir verileri eksik: {', '.join(missing)}")

    city_links = "".join(
        (
            f'<a class="popular-city-chip" href="/{city_lookup[name]["slug"]}/" '
            f'aria-label="{html.escape(name)} kıble yönü '
            f'{decimal_tr(city_lookup[name]["bearing"])} derece">'
            f'<strong>{html.escape(name)}</strong>'
            f'<span>{decimal_tr(city_lookup[name]["bearing"])}°</span>'
            "</a>"
        )
        for name in featured_names
    )
    return (
        '<section class="cities" id="sehirler">\n'
        '  <div class="container">\n'
        '    <div class="popular-cities-head">\n'
        '      <div>\n'
        '        <span class="section-label">HIZLI ERİŞİM</span>\n'
        '        <h2>En Çok Aranan Şehirler</h2>\n'
        '      </div>\n'
        '      <a class="btn btn-secondary popular-cities-all" href="/sehirler/">Tüm şehirler</a>\n'
        '    </div>\n'
        f'    <div class="popular-city-list">{city_links}</div>\n'
        '  </div>\n'
        '</section>'
    )


def update_homepage(home, cities):
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
        f'<p>{render_inline(item["answer"])}</p></details>'
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
        rf'\1{render_inline(home["closing_copy"])}\2',
        page,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Ana sayfa kapanış metni bulunamadı")

    page, count = re.subn(
        r'<section class="cities" id="sehirler">.*?</section>',
        popular_cities_section(cities),
        page,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Ana sayfa popüler şehirler bölümü bulunamadı")

    schema_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, flags=re.DOTALL)
    if not schema_match:
        raise ValueError("Ana sayfa yapılandırılmış verisi bulunamadı")
    schema = json.loads(schema_match.group(1))
    for item in schema.get("@graph", []):
        if item.get("@type") == "WebSite":
            item["name"] = home["seo_title"]
            item["description"] = home["meta_description"]
        if item.get("@type") == "WebApplication":
            item["description"] = home["meta_description"]
        if item.get("@type") == "FAQPage":
            item["mainEntity"] = [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": plain_text(faq["answer"])},
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

    update_homepage(home, cities)
    footer_html = footer(home["footer_description"], cities)
    content_page_template = (SRC / "templates/content-page.template.html").read_text(encoding="utf-8")
    faq_page_template = (SRC / "templates/faq-page.template.html").read_text(encoding="utf-8")
    content_page_config = {
        "hakkimizda": ("Kıble Yönü Hesapla hakkında", "AboutPage"),
        "gizlilik": ("Gizlilik Politikası", "WebPage"),
        "kullanim-sartlari": ("Kullanım Şartları", "WebPage"),
        "iletisim": ("İletişim", "ContactPage"),
        "hesaplama-yontemi": ("Hesaplama Yöntemi", "WebPage"),
    }
    for slug, (breadcrumb, page_type) in content_page_config.items():
        page = json.loads((SRC / f"data/pages/{slug}.json").read_text(encoding="utf-8"))
        write_content_page(
            slug, page, content_page_template, footer_html, breadcrumb, page_type
        )
    faq_page = json.loads(
        (SRC / "data/pages/sikca-sorulan-sorular.json").read_text(encoding="utf-8")
    )
    write_faq_page(faq_page, faq_page_template, footer_html)
    city_lookup = {city["slug"]: city for city in cities}
    city_template = (SRC / "templates/city.template.html").read_text(encoding="utf-8")
    city_index = (SRC / "templates/cities-index.template.html").read_text(encoding="utf-8")
    blog_index = (SRC / "templates/blog-index.template.html").read_text(encoding="utf-8")
    blog_post = (SRC / "templates/blog-post.template.html").read_text(encoding="utf-8")
    shared_city_lastmod = last_modified(
        SRC / "data/cities.json", SRC / "templates/city.template.html", Path(__file__)
    )

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
            "CITY_LASTMOD": shared_city_lastmod,
            "CITY_LASTMOD_TR": datetime.strptime(shared_city_lastmod, "%Y-%m-%d").strftime("%d.%m.%Y"),
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
            + "".join(f'<p>{render_inline(paragraph)}</p>' for paragraph in section["paragraphs"])
            for section in post["sections"]
        )
        faq = "".join(
            f'<details><summary>{html.escape(item["question"])}</summary>'
            f'<p>{render_inline(item["answer"])}</p></details>'
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

    base = "https://kibleyonuhesapla.com"
    generator_source = Path(__file__)
    entries = [
        (f"{base}/", last_modified(SRC / "site/index.html", SRC / "data/homepage.json", generator_source)),
        (f"{base}/sehirler/", last_modified(SRC / "templates/cities-index.template.html", SRC / "data/cities.json", generator_source)),
        (f"{base}/blog/", last_modified(SRC / "templates/blog-index.template.html", SRC / "data/blog.json", generator_source)),
    ]
    for slug in ["gizlilik", "hakkimizda", "kullanim-sartlari", "hesaplama-yontemi", "iletisim"]:
        entries.append(
            (
                f"{base}/{slug}/",
                last_modified(
                    SRC / f"data/pages/{slug}.json",
                    SRC / "templates/content-page.template.html",
                    generator_source,
                ),
            )
        )
    entries.append(
        (
            f"{base}/sikca-sorulan-sorular/",
            last_modified(
                SRC / "data/pages/sikca-sorulan-sorular.json",
                SRC / "templates/faq-page.template.html",
                generator_source,
            ),
        )
    )
    entries += [(f'{base}/{city["slug"]}/', shared_city_lastmod) for city in cities]
    blog_lastmod = last_modified(SRC / "data/blog.json", SRC / "templates/blog-post.template.html", generator_source)
    entries += [(f'{base}/blog/{post["slug"]}/', blog_lastmod) for post in posts]
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(
            f"  <url><loc>{html.escape(url)}</loc><lastmod>{modified}</lastmod></url>"
            for url, modified in entries
        )
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
    (DIST / "data").mkdir(parents=True, exist_ok=True)
    (DIST / "data" / "locations.json").write_text(
        json.dumps(locations, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    for path in DIST.rglob("*.html"):
        if path.parts[-2:] == ("admin", "index.html"):
            continue
        page = path.read_text(encoding="utf-8")
        if re.search(r"<footer\b.*?</footer>", page, flags=re.DOTALL):
            page = re.sub(r"<footer\b.*?</footer>", footer_html, page, count=1, flags=re.DOTALL)
        page = re.sub(r'/assets/css/style\.css(?:\?v=\d+)?', '/assets/css/style.css?v=35', page)
        page = re.sub(r'/assets/js/app\.js(?:\?v=\d+)?', '/assets/js/app.js?v=35', page)
        page = re.sub(r'/assets/js/qibla-map\.js(?:\?v=\d+)?', '/assets/js/qibla-map.js?v=35', page)
        page = re.sub(r'/assets/js/nav\.js(?:\?v=\d+)?', '/assets/js/nav.js?v=35', page)
        if '/assets/js/nav.js' not in page:
            page = page.replace('</body>', '<script src="/assets/js/nav.js?v=35" defer></script>\n</body>')
        path.write_text(page, encoding="utf-8")
    print(f"Build tamamlandı: {len(cities)} il, {len(posts)} blog")


if __name__ == "__main__":
    main()
