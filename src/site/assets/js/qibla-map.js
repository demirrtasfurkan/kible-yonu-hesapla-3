(() => {
  const KAABA_MAP = { lat: 21.422487, lng: 39.826206 };
  const ASSETS = {
    leafletCss: "/assets/vendor/leaflet/leaflet.css",
    leafletJs: "/assets/vendor/leaflet/leaflet.js",
  };
  const el = {
    mapEl: document.getElementById("qibla-map"),
    mapStage: document.getElementById("mapPanel"),
    btnStreet: document.getElementById("btn-layer-street"),
    btnSat: document.getElementById("btn-layer-sat"),
    districtSelect: document.getElementById("districtSelect"),
  };
  if (!el.mapEl) return;

  const cityPage = document.body.dataset.cityPage === "true";
  const state = {
    lat: cityPage ? Number(document.body.dataset.cityLat) : null,
    lng: cityPage ? Number(document.body.dataset.cityLng) : null,
    name: cityPage ? document.body.dataset.cityName : "Konumunuz",
    qibla: null,
    leafletPromise: null,
    map: null,
    streetLayer: null,
    satLayer: null,
    marker: null,
    kaabaMarker: null,
    line: null,
  };
  if (Number.isFinite(state.lat) && Number.isFinite(state.lng)) {
    state.qibla = calculateQiblaBearing(state.lat, state.lng);
  }

  function mapVisible() {
    if (el.mapStage && el.mapStage.hidden) return false;
    return el.mapEl.offsetParent !== null && el.mapEl.clientHeight > 40;
  }

  function invalidateMap() {
    if (!state.map) return;
    const run = () => {
      state.map.invalidateSize({ animate: false });
      drawMap(true);
    };
    requestAnimationFrame(() => {
      run();
      setTimeout(run, 50);
      setTimeout(run, 200);
      setTimeout(run, 450);
    });
  }

  function loadCss(href) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`link[href="${href}"]`);
      if (existing) {
        resolve();
        return;
      }
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.dataset.kbLeaflet = "1";
      link.onload = () => resolve();
      link.onerror = () => reject(new Error("Leaflet CSS yüklenemedi"));
      document.head.appendChild(link);
    });
  }

  function loadJs(src) {
    return new Promise((resolve, reject) => {
      if (typeof window.L !== "undefined") {
        resolve();
        return;
      }
      const existing = document.querySelector('script[data-kb-leaflet="1"]');
      if (existing) {
        existing.addEventListener("load", () => resolve(), { once: true });
        existing.addEventListener(
          "error",
          () => reject(new Error("Leaflet JS")),
          { once: true },
        );
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.dataset.kbLeaflet = "1";
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Leaflet JS yüklenemedi"));
      document.head.appendChild(script);
    });
  }

  function ensureLeaflet() {
    if (typeof window.L !== "undefined") return Promise.resolve();
    if (!state.leafletPromise) {
      state.leafletPromise = Promise.all([
        loadCss(ASSETS.leafletCss),
        loadJs(ASSETS.leafletJs),
      ]).then(
        () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
      );
    }
    return state.leafletPromise;
  }

  async function initMap() {
    if (state.map) {
      invalidateMap();
      return;
    }
    if (!Number.isFinite(state.lat) || !Number.isFinite(state.lng)) return;
    try {
      await ensureLeaflet();
    } catch (error) {
      console.error(error);
      return;
    }
    if (state.map || typeof window.L === "undefined") return;
    if (el.mapStage && el.mapStage.hidden) return;
    if (el.mapEl.clientHeight < 40) {
      await new Promise((resolve) => setTimeout(resolve, 30));
      if (el.mapEl.clientHeight < 40) return;
    }

    state.map = window.L.map(el.mapEl, {
      zoomControl: true,
      attributionControl: true,
      scrollWheelZoom: true,
    });
    state.streetLayer = window.L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
        detectRetina: true,
      },
    );
    state.satLayer = window.L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        maxZoom: 19,
        attribution: "Tiles &copy; Esri",
        detectRetina: true,
      },
    );
    state.streetLayer.addTo(state.map);
    drawMap(false);
    invalidateMap();
  }

  function setLayer(kind) {
    if (!state.map) return;
    if (kind === "sat") {
      if (state.map.hasLayer(state.streetLayer)) state.map.removeLayer(state.streetLayer);
      if (!state.map.hasLayer(state.satLayer)) state.satLayer.addTo(state.map);
      el.btnSat?.classList.add("active");
      el.btnStreet?.classList.remove("active");
    } else {
      if (state.map.hasLayer(state.satLayer)) state.map.removeLayer(state.satLayer);
      if (!state.map.hasLayer(state.streetLayer)) state.streetLayer.addTo(state.map);
      el.btnStreet?.classList.add("active");
      el.btnSat?.classList.remove("active");
    }
  }

  function drawMap(keepView) {
    if (!state.map) return;
    const here = [state.lat, state.lng];
    const there = [KAABA_MAP.lat, KAABA_MAP.lng];

    if (state.marker) state.map.removeLayer(state.marker);
    if (state.kaabaMarker) state.map.removeLayer(state.kaabaMarker);
    if (state.line) state.map.removeLayer(state.line);

    const cityIcon = window.L.divIcon({
      className: "kb-marker",
      html: '<span class="kb-pin kb-pin-city" aria-hidden="true"></span>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
    const kaabaIcon = window.L.divIcon({
      className: "kb-marker",
      html: '<span class="kb-pin kb-pin-kaaba" aria-hidden="true"></span>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });

    state.marker = window.L.marker(here, {
      icon: cityIcon,
      title: state.name,
      alt: `${state.name} konumu`,
      keyboard: true,
    })
      .addTo(state.map)
      .bindPopup(`<strong>${state.name}</strong><br>Kıble: ${Math.round(state.qibla)}°`);
    state.marker.getElement()?.setAttribute("aria-label", `${state.name} konumu`);

    state.kaabaMarker = window.L.marker(there, {
      icon: kaabaIcon,
      title: "Kabe",
      alt: "Kabe, Mekke",
      keyboard: true,
    })
      .addTo(state.map)
      .bindPopup("<strong>Kabe</strong><br>Mekke");
    state.kaabaMarker.getElement()?.setAttribute("aria-label", "Kabe, Mekke");

    state.line = window.L.polyline([here, there], {
      color: "#c9a24e",
      weight: 3,
      opacity: 0.95,
      dashArray: "10 8",
    }).addTo(state.map);

    if (!keepView) {
      state.map.fitBounds(window.L.latLngBounds(here, there).pad(0.18));
    }
  }

  function updateLocation(detail) {
    if (!detail || !Number.isFinite(detail.lat) || !Number.isFinite(detail.lng)) return;
    state.lat = detail.lat;
    state.lng = detail.lng;
    state.name = detail.name || "Konumunuz";
    state.qibla = Number.isFinite(detail.qibla)
      ? detail.qibla
      : calculateQiblaBearing(state.lat, state.lng);
    if (state.map) drawMap(false);
    else if (mapVisible()) initMap();
  }

  function onDistrictChange() {
    const option = el.districtSelect?.selectedOptions?.[0];
    if (!option?.dataset.lat || !option?.dataset.lng) return;
    updateLocation({
      lat: Number(option.dataset.lat),
      lng: Number(option.dataset.lng),
      name: option.dataset.name,
      qibla: Number(option.dataset.bearing),
    });
  }

  (function lazyCityMap() {
    if (el.mapStage || !cityPage) return;
    const boot = () => {
      if (mapVisible()) initMap();
    };
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            observer.disconnect();
            if ("requestIdleCallback" in window) {
              requestIdleCallback(boot, { timeout: 2000 });
            } else {
              setTimeout(boot, 300);
            }
          }
        },
        { rootMargin: "120px" },
      );
      observer.observe(el.mapEl);
    } else {
      setTimeout(boot, 500);
    }
  })();

  window.addEventListener("qibla:location", (event) => updateLocation(event.detail));
  window.addEventListener("qibla:map-visible", () => {
    requestAnimationFrame(() => initMap().then(() => invalidateMap()));
  });
  window.addEventListener("qibla:map-fit", () => {
    if (state.map) {
      drawMap(false);
      invalidateMap();
    } else {
      initMap();
    }
  });
  el.btnStreet?.addEventListener("click", () => setLayer("street"));
  el.btnSat?.addEventListener("click", () => setLayer("sat"));
  el.districtSelect?.addEventListener("change", onDistrictChange);
  window.addEventListener("resize", () => {
    if (state.map && mapVisible()) invalidateMap();
  });
})();
