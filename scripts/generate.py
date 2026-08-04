#!/usr/bin/env python3
from pathlib import Path
import json, shutil, re, html
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/'src'; DIST=ROOT/'dist'
def tr(v): return f"{int(v):,}".replace(',','.')
def render(t,v):
 for k,x in v.items(): t=t.replace('{{'+k+'}}',str(x))
 u=re.findall(r'\{\{([A-Z0-9_]+)\}\}',t)
 if u: raise ValueError(u)
 return t
def footer():
 return '<footer><div class="container footer-grid">\n<div><strong>Kıble Yönü Hesapla</strong><p>Canlı pusula, harita ve şehir bazlı kıble rehberleri.</p></div>\n<div><strong>Popüler şehirler</strong><a href="/istanbul-kible-yonu/">İstanbul</a><a href="/ankara-kible-yonu/">Ankara</a><a href="/izmir-kible-yonu/">İzmir</a><a href="/bursa-kible-yonu/">Bursa</a></div>\n<div><strong>Keşfet</strong><a href="/sehirler/">81 İl</a><a href="/blog/">Kıble Rehberi</a><a href="/hakkimizda/">Hakkımızda</a><a href="/kullanim-sartlari/">Kullanım Şartları</a><a href="/gizlilik/">Gizlilik Politikası</a></div>\n</div></footer>'
def main():
 if DIST.exists(): shutil.rmtree(DIST)
 shutil.copytree(SRC/'site',DIST)
 cities=json.loads((SRC/'data/cities.json').read_text(encoding='utf-8')); posts=json.loads((SRC/'data/blog.json').read_text(encoding='utf-8'))
 ct=(SRC/'templates/city.template.html').read_text(encoding='utf-8'); ci=(SRC/'templates/cities-index.template.html').read_text(encoding='utf-8'); bi=(SRC/'templates/blog-index.template.html').read_text(encoding='utf-8'); bp=(SRC/'templates/blog-post.template.html').read_text(encoding='utf-8')
 cards=[]
 for i,c in enumerate(sorted(cities,key=lambda x:x['name'])):
  near=''.join(f'<a href="/{n["slug"]}/">{html.escape(n["name"])} kıble yönü<span>Yaklaşık {tr(n["distance"])} km</span></a>' for n in c['nearby'])
  sel=[posts[(i+j)%len(posts)] for j in range(3)]; blogs=''.join(f'<a class="blog-mini-card" href="/blog/{p["slug"]}/"><span>REHBER</span><strong>{html.escape(p["title"])}</strong><p>{html.escape(p["excerpt"])}</p></a>' for p in sel)
  vals={'CITY_NAME':c['name'],'CITY_NAME_UPPER':c['name'].upper(),'CITY_SLUG':c['slug'],'LAT':c['lat'],'LNG':c['lng'],'BEARING':c['bearing'],'BEARING_TR':str(c['bearing']).replace('.',','),'DIRECTION':c['direction'],'DIRECTION_LOWER':c['direction'].lower(),'DISTANCE':c['distance'],'DISTANCE_TR':tr(c['distance']),'NEARBY_CITY_LINKS':near,'CITY_BLOG_LINKS':blogs,'FOOTER':footer()}
  d=DIST/c['slug']; d.mkdir(parents=True); (d/'index.html').write_text(render(ct,vals),encoding='utf-8'); cards.append(f'<a href="/{c["slug"]}/"><strong>{html.escape(c["name"])}</strong><span>{str(c["bearing"]).replace(".",",")}° · {html.escape(c["direction"])}</span></a>')
 d=DIST/'sehirler'; d.mkdir(); (d/'index.html').write_text(ci.replace('{{CITY_CARDS}}',''.join(cards)),encoding='utf-8')
 bc=[]
 for p in posts:
  bc.append(f'<a class="blog-card" href="/blog/{p["slug"]}/"><span class="meta">{p["reading_time"]} OKUMA</span><h2>{html.escape(p["title"])}</h2><p>{html.escape(p["excerpt"])}</p></a>')
  content=''.join(f'<h2>{html.escape(h)}</h2>'+''.join(f'<p>{html.escape(x)}</p>' for x in ps) for h,ps in p['sections']); faq=''.join(f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q,a in p['faq']); rel=''.join(f'<a href="/blog/{x["slug"]}/">{html.escape(x["title"])}</a>' for x in posts if x['slug']!=p['slug']); pop=''.join(f'<a href="/{s}-kible-yonu/">{n} kıble yönü</a>' for n,s in [('İstanbul','istanbul'),('Ankara','ankara'),('İzmir','izmir'),('Bursa','bursa')]); schema=json.dumps({'@context':'https://schema.org','@type':'Article','headline':p['title'],'description':p['description']},ensure_ascii=False)
  vals={'TITLE':html.escape(p['title']),'DESCRIPTION':html.escape(p['description']),'SLUG':p['slug'],'READING_TIME':p['reading_time'],'ARTICLE_CONTENT':content,'RELATED_POSTS':rel,'POPULAR_CITIES':pop,'FAQ_HTML':faq,'SCHEMA':schema,'FOOTER':footer()}; d=DIST/'blog'/p['slug']; d.mkdir(parents=True); (d/'index.html').write_text(render(bp,vals),encoding='utf-8')
 d=DIST/'blog'; d.mkdir(exist_ok=True); (d/'index.html').write_text(render(bi,{'BLOG_CARDS':''.join(bc),'FOOTER':footer()}),encoding='utf-8')
 urls=['https://kibleyonuhesapla.com/','https://kibleyonuhesapla.com/sehirler/','https://kibleyonuhesapla.com/blog/','https://kibleyonuhesapla.com/gizlilik/','https://kibleyonuhesapla.com/hakkimizda/','https://kibleyonuhesapla.com/kullanim-sartlari/']+[f'https://kibleyonuhesapla.com/{c["slug"]}/' for c in cities]+[f'https://kibleyonuhesapla.com/blog/{p["slug"]}/' for p in posts]
 (DIST/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+'\n'.join(f'<url><loc>{u}</loc></url>' for u in urls)+'\n</urlset>',encoding='utf-8'); print(f'Build tamamlandı: {len(cities)} il, {len(posts)} blog')
if __name__=='__main__': main()
