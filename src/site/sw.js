const CACHE = "kible-v17-qibla-map";
const CORE = [
  "/",
  "/sehirler/",
  "/assets/css/style.css",
  "/assets/js/qibla.js",
  "/assets/js/app.js",
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
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(CORE))),
);
self.addEventListener("activate", (event) =>
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
      ),
  ),
);
self.addEventListener("fetch", (event) => {
  if (
    event.request.method !== "GET" ||
    new URL(event.request.url).pathname.startsWith("/admin/")
  )
    return;
  event.respondWith(
    caches.match(event.request).then(
      (cached) =>
        cached ||
        fetch(event.request)
          .then((response) => {
            if (!response || response.status !== 200 || response.type === "opaque")
              return response;
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(event.request, copy));
            return response;
          })
          .catch(() =>
            event.request.mode === "navigate" ? caches.match("/") : undefined,
          ),
    ),
  );
});
