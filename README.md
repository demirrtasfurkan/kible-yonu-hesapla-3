# V14.1 — Redirect Loop Fix

Bu sürüm, kurumsal sayfalardaki trailing-slash yönlendirme döngüsünü giderir.

Canonical URL standardı:

- `/gizlilik/`
- `/hakkimizda/`
- `/kullanim-sartlari/`

Yönlendirmeler:

- Slash olmayan URL → slash olan URL (`301`)
- `.html` URL → slash olan URL (`301`)

`/sayfa/ → /sayfa` kuralları kaldırılmıştır. Cloudflare Static Assets için `html_handling: force-trailing-slash` açıkça tanımlanmıştır.

Commit mesajı:

`Fix institutional page redirect loops`
