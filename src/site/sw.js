const CACHE = "kible-v29-competitor-map";
const CORE = [
  "/",
  "/sehirler/",
  "/assets/css/style.css?v=29",
  "/assets/js/qibla.js",
  "/assets/js/app.js?v=29",
  "/assets/js/nav.js?v=29",
  "/assets/vendor/leaflet/leaflet.css",
  "/assets/vendor/leaflet/leaflet.js",
  "/data/locations.json",
  "/data/cities.json",
  "/manifest.webmanifest",
  "/gizlilik/",
  "/hakkimizda/",
  "/kullanim-sartlari/",
  "/hesaplama-yontemi/",
  "/iletisim/",
];
self.addEventListener("install", (event) =>
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(CORE)).then(() => self.skipWaiting()),
  ),
);
self.addEventListener("activate", (event) =>
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  ),
);
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (
    event.request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/admin/")
  )
    return;
  const freshFirst =
    event.request.mode === "navigate" ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".js");

  if (freshFirst) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200 && response.type !== "opaque") {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() =>
          caches.match(event.request).then((cached) =>
            cached || (event.request.mode === "navigate" ? caches.match("/") : undefined),
          ),
        ),
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request)),
  );
});
