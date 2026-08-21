(() => {
  const $ = (id) => document.getElementById(id),
    e = {
      locationButton: $("locationButton"),
      searchForm: $("searchForm"),
      locationSearch: $("locationSearch"),
      searchResults: $("searchResults"),
      status: $("statusMessage"),
      result: $("resultSection"),
      resultTitle: $("resultTitle"),
      bearing: $("bearingValue") || $("previewBearing"),
      direction: $("directionValue") || $("previewDirection"),
      distance: $("distanceValue") || $("previewDistance"),
      accuracy: $("accuracyValue") || $("previewAccuracy"),
      place: $("placeValue") || $("previewPlace"),
      heading: $("headingValue"),
      needle: $("qiblaNeedle"),
      previewNeedle: $("previewNeedle") || $("qiblaNeedle"),
      previewPlace: $("previewPlace"),
      previewBearing: $("previewBearing"),
      previewDirection: $("previewDirection"),
      previewDistance: $("previewDistance"),
      previewAccuracy: $("previewAccuracy"),
      compassButton: $("compassButton"),
      compassStatus: $("compassStatus"),
      alignment: $("alignmentMessage"),
      fitMapButton: $("fitMapButton"),
      shareButton: $("shareButton"),
      compassViewButton: $("compassViewButton"),
      mapViewButton: $("mapViewButton"),
      compassPanel: $("compassPanel"),
      mapPanel: $("mapPanel"),
      mapLayerButtons: document.querySelectorAll(".map-layers button"),
    };
  let s = {
    lat: null,
    lng: null,
    bearing: null,
    place: "",
    vibrated: false,
    locations: [],
    leafletPromise: null,
    map: null,
    userMarker: null,
    kaabaMarker: null,
    routeLine: null,
    streetLayer: null,
    satelliteLayer: null,
    mapResizeObserver: null,
  };
  function track(action, params = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: "custom_event",
      event_category: "qibla_tool",
      event_action: action,
      ...params,
    });
  }
  function status(m, err = false) {
    if (!e.status) return;
    e.status.textContent = m;
    e.status.classList.toggle("error", err);
  }
  function fmt(v, d = 0) {
    return v.toLocaleString("tr-TR", {
      minimumFractionDigits: d,
      maximumFractionDigits: d,
    });
  }
  function normText(v) {
    return String(v || "")
      .toLocaleLowerCase("tr-TR")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }
  async function loadLocations() {
    try {
      s.locations = await fetch("/data/locations.json").then((r) => r.json());
    } catch {
      s.locations = [];
    }
  }
  function loadLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (s.leafletPromise) return s.leafletPromise;

    if (!document.getElementById("leafletStyles")) {
      const link = document.createElement("link");
      link.id = "leafletStyles";
      link.rel = "stylesheet";
      link.href = "/assets/vendor/leaflet/leaflet.css";
      document.head.appendChild(link);
    }

    s.leafletPromise = new Promise((resolve, reject) => {
      const existing = document.getElementById("leafletScript"),
        script = existing || document.createElement("script"),
        complete = () =>
          window.L
            ? resolve(window.L)
            : reject(new Error("Harita kütüphanesi yüklenemedi."));

      script.addEventListener("load", complete, { once: true });
      script.addEventListener(
        "error",
        () => reject(new Error("Harita kütüphanesi yüklenemedi.")),
        { once: true },
      );

      if (!existing) {
        script.id = "leafletScript";
        script.src = "/assets/vendor/leaflet/leaflet.js";
        document.head.appendChild(script);
      }
    }).catch((error) => {
      s.leafletPromise = null;
      throw error;
    });

    return s.leafletPromise;
  }
  function createMapIcon(L, type) {
    return L.divIcon({
      className: "qibla-map-div-icon",
      html: `<span class="qibla-map-pin ${type}" aria-hidden="true"></span>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
  }
  function mapElements() {
    const frame = document.getElementById("mapFrame"),
      placeholder = document.getElementById("mapPlaceholder"),
      root =
        document.getElementById("map") ||
        frame?.closest(".city-map-shell") ||
        frame?.parentElement;
    return { frame, placeholder, root };
  }
  function mapVisible(root = mapElements().root) {
    return Boolean(root && root.offsetParent !== null && root.clientHeight > 40);
  }
  function escapeMapText(value) {
    const element = document.createElement("span");
    element.textContent = String(value || "");
    return element.innerHTML;
  }
  function drawMap(keepView = false) {
    if (!s.map || !window.L || s.lat === null || s.lng === null) return;
    const L = window.L,
      here = [s.lat, s.lng],
      there = [KAABA.lat, KAABA.lng];

    if (s.userMarker) s.map.removeLayer(s.userMarker);
    if (s.kaabaMarker) s.map.removeLayer(s.kaabaMarker);
    if (s.routeLine) s.map.removeLayer(s.routeLine);

    s.userMarker = L.marker(here, {
      icon: createMapIcon(L, "user"),
      title: s.place || "Konumunuz",
      alt: `${s.place || "Konumunuz"} konumu`,
      keyboard: true,
    })
      .addTo(s.map)
      .bindPopup(
        `<strong>${escapeMapText(s.place || "Konumunuz")}</strong><br>Kıble: ${Math.round(s.bearing)}°`,
      );
    s.userMarker
      .getElement()
      ?.setAttribute("aria-label", `${s.place || "Konumunuz"} konumu`);

    s.kaabaMarker = L.marker(there, {
      icon: createMapIcon(L, "kaaba"),
      title: "Kâbe",
      alt: "Kâbe, Mekke",
      keyboard: true,
    })
      .addTo(s.map)
      .bindPopup("<strong>Kâbe</strong><br>Mekke");
    s.kaabaMarker.getElement()?.setAttribute("aria-label", "Kâbe, Mekke");

    s.routeLine = L.polyline([here, there], {
      color: "#c9a24e",
      weight: 3,
      opacity: 0.95,
      dashArray: "10 8",
    }).addTo(s.map);

    if (!keepView) s.map.fitBounds(L.latLngBounds(here, there).pad(0.18));
  }
  function invalidateMap() {
    if (!s.map) return;
    const run = () => {
      if (!mapVisible()) return;
      s.map.invalidateSize({ animate: false });
      drawMap(true);
    };
    requestAnimationFrame(() => {
      run();
      setTimeout(run, 50);
      setTimeout(run, 200);
      setTimeout(run, 450);
    });
  }
  async function ensureMap() {
    const { frame, placeholder, root } = mapElements();
    if (!root || !mapVisible(root)) return null;

    const L = await loadLeaflet();
    if (!mapVisible(root)) return null;
    let canvas = document.getElementById("mapCanvas");
    if (!canvas) {
      canvas = document.createElement("div");
      canvas.id = "mapCanvas";
      canvas.className = "qibla-map-canvas";
      canvas.setAttribute("role", "region");
      canvas.setAttribute(
        "aria-label",
        "Konumunuzdan Kâbe'ye uzanan kıble yönü haritası",
      );
      root.insertBefore(canvas, placeholder || root.firstChild);
    }

    root.classList.add("qibla-map-ready");
    if (frame) {
      frame.hidden = true;
      frame.removeAttribute("src");
    }
    if (placeholder) placeholder.hidden = true;
    root.querySelector(".map-route-card")?.setAttribute("hidden", "");

    if (!s.map) {
      s.map = L.map(canvas, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: true,
      });
      s.streetLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
        detectRetina: true,
      });
      s.satelliteLayer = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 19,
          attribution: "Tiles &copy; Esri",
          detectRetina: true,
        },
      );
      s.streetLayer.addTo(s.map);

      if ("ResizeObserver" in window) {
        s.mapResizeObserver = new ResizeObserver(([entry]) => {
          if (entry.contentRect.width > 0 && entry.contentRect.height > 40)
            invalidateMap();
        });
        s.mapResizeObserver.observe(canvas);
      }
    }

    return { L, map: s.map, root };
  }
  async function updateMap({ refit = true } = {}) {
    if (s.lat === null || s.lng === null) return;
    const placeholder = document.getElementById("mapPlaceholder");
    if (placeholder) {
      placeholder.hidden = false;
      const title = placeholder.querySelector("span"),
        copy = placeholder.querySelector("small");
      if (title) title.textContent = "Harita yükleniyor…";
      if (copy)
        copy.textContent =
          "Konumunuz ile Kâbe arasındaki gerçek doğrultu hazırlanıyor.";
    }

    try {
      const mapContext = await ensureMap();
      if (!mapContext) return;
      drawMap(!refit);
      invalidateMap();
    } catch (error) {
      if (placeholder) {
        placeholder.hidden = false;
        const title = placeholder.querySelector("span"),
          copy = placeholder.querySelector("small");
        if (title) title.textContent = "Harita yüklenemedi";
        if (copy)
          copy.textContent =
            "Bağlantını kontrol edip Haritayı yenile düğmesine basabilirsin.";
      }
      console.error(error);
    }
  }
  function fitMap() {
    if (s.map && s.routeLine) {
      drawMap(false);
      invalidateMap();
    } else updateMap();
  }
  async function setMapLayer(kind) {
    if (!s.map) await updateMap();
    if (!s.map || !s.streetLayer || !s.satelliteLayer) return;
    const satellite = kind === "satellite";
    if (satellite) {
      if (s.map.hasLayer(s.streetLayer)) s.map.removeLayer(s.streetLayer);
      if (!s.map.hasLayer(s.satelliteLayer)) s.satelliteLayer.addTo(s.map);
    } else {
      if (s.map.hasLayer(s.satelliteLayer)) s.map.removeLayer(s.satelliteLayer);
      if (!s.map.hasLayer(s.streetLayer)) s.streetLayer.addTo(s.map);
    }
    e.mapLayerButtons.forEach((button, index) =>
      button.classList.toggle("active", satellite ? index === 1 : index === 0),
    );
    invalidateMap();
  }
  function render({
    lat,
    lng,
    accuracy = null,
    place = "Mevcut konum",
    source = "gps",
    scrollResult = false,
    updateMapFrame = true,
  }) {
    s.lat = lat;
    s.lng = lng;
    s.place = place;
    s.bearing = calculateQiblaBearing(lat, lng);
    const distance = calculateDistanceToKaaba(lat, lng),
      deg = `${fmt(s.bearing, 1)}°`,
      dir = getDirectionName(s.bearing),
      dist = `${fmt(Math.round(distance))} km`,
      acc = accuracy ? `±${fmt(Math.round(accuracy))} m` : "Merkez koordinatı";
    e.bearing.textContent = deg;
    e.direction.textContent = dir;
    e.distance.textContent = dist;
    e.accuracy.textContent = acc;
    e.place.textContent = place;
    e.heading.textContent = "Bekleniyor";
    if (e.resultTitle) e.resultTitle.textContent = `${place} için kıble yönü`;
    e.needle.style.transform = `translate(-50%,-100%) rotate(${s.bearing}deg)`;
    if (e.previewNeedle) e.previewNeedle.style.transform = `translate(-50%,-100%) rotate(${s.bearing}deg)`;
    if (e.previewPlace) e.previewPlace.textContent = place;
    if (e.previewBearing) e.previewBearing.textContent = deg;
    if (e.previewDirection) e.previewDirection.textContent = dir;
    if (e.previewDistance) e.previewDistance.textContent = dist;
    if (e.previewAccuracy) e.previewAccuracy.textContent = acc;
    document.getElementById("quickCompass")?.classList.add("is-calculated");
    if (e.result) e.result.hidden = false;
    if (e.shareButton) e.shareButton.hidden = false;
    if (updateMapFrame && mapVisible()) updateMap();
    status("Kıble yönü başarıyla hesaplandı.");
    track("qibla_calculated", {
      calculation_source: source,
      qibla_bearing: Number(s.bearing.toFixed(1)),
      place_name: place,
    });
    if (scrollResult && e.result) {
      setTimeout(() => {
        const y = e.result.getBoundingClientRect().top + window.scrollY - 78;
        window.scrollTo({ top: y, behavior: "smooth" });
      }, 120);
    }
  }
  e.locationButton?.addEventListener("click", async () => {
    track("location_permission_requested");
    if (!navigator.geolocation) {
      status("Tarayıcın konum özelliğini desteklemiyor.", true);
      return;
    }
    let orientationPermission = "not-required";
    if (
      typeof DeviceOrientationEvent !== "undefined" &&
      typeof DeviceOrientationEvent.requestPermission === "function"
    ) {
      try {
        orientationPermission = await DeviceOrientationEvent.requestPermission();
      } catch {
        orientationPermission = "denied";
      }
    }
    e.locationButton.disabled = true;
    e.locationButton.textContent = "Konum alınıyor…";
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const { latitude, longitude, accuracy } = p.coords;
        render({
          lat: latitude,
          lng: longitude,
          accuracy,
          place: "Mevcut konum",
          source: "gps",
        });
        if (orientationPermission !== "denied") startCompass(true);
        e.locationButton.disabled = false;
        e.locationButton.textContent = "Konumu yeniden hesapla";
        track("location_permission_granted");
      },
      (err) => {
        const m = {
          1: "Konum izni verilmedi. Şehir veya ilçe aramasını kullanabilirsin.",
          2: "Konum bilgisi alınamadı.",
          3: "Konum isteği zaman aşımına uğradı.",
        };
        status(m[err.code] || "Konum alınamadı.", true);
        e.locationButton.disabled = false;
        e.locationButton.textContent = "Tekrar dene";
        track("location_permission_denied", { error_code: err.code });
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 },
    );
  });
  async function remoteSearch(q) {
    const u = new URL("https://nominatim.openstreetmap.org/search");
    u.searchParams.set("format", "jsonv2");
    u.searchParams.set("limit", "5");
    u.searchParams.set("countrycodes", "tr");
    u.searchParams.set("accept-language", "tr");
    u.searchParams.set("q", q);
    const r = await fetch(u, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error();
    return r.json();
  }
  function localSearch(q) {
    const n = normText(q);
    return s.locations
      .filter((x) => normText(`${x.name} ${x.parent}`).includes(n))
      .slice(0, 5)
      .map((x) => ({
        lat: x.lat,
        lon: x.lng,
        name: x.name,
        display_name: [x.name, x.parent, x.type].filter(Boolean).join(", "),
      }));
  }
  function showResults(rs) {
    e.searchResults.innerHTML = "";
    if (!rs.length) {
      e.searchResults.innerHTML =
        '<div class="search-result">Sonuç bulunamadı.</div>';
      e.searchResults.hidden = false;
      return;
    }
    rs.forEach((i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "search-result";
      const t = i.name || i.display_name.split(",")[0];
      b.innerHTML = `<strong>${t}</strong><small>${i.display_name}</small>`;
      b.onclick = () => {
        render({ lat: +i.lat, lng: +i.lon, place: t, source: "manual_search" });
        e.locationSearch.value = i.display_name;
        e.searchResults.hidden = true;
      };
      e.searchResults.appendChild(b);
    });
    e.searchResults.hidden = false;
  }
  e.searchForm?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const q = e.locationSearch.value.trim();
    if (q.length < 2) {
      status("En az iki karakter yazmalısın.", true);
      return;
    }
    status("Konum aranıyor…");
    track("manual_search", { search_term: q });
    let rs = localSearch(q);
    try {
      if (!rs.length) rs = await remoteSearch(q);
      showResults(rs);
      status(rs.length ? "Bir konum seç." : "Sonuç bulunamadı.", !rs.length);
    } catch {
      showResults(rs);
      status(
        rs.length ? "Bir konum seç." : "Konum araması şu anda kullanılamıyor.",
        !rs.length,
      );
    }
  });
  e.locationSearch?.addEventListener("input", () => {
    const q = e.locationSearch.value.trim();
    if (q.length < 2) {
      e.searchResults.hidden = true;
      return;
    }
    const rs = localSearch(q);
    if (rs.length) showResults(rs);
  });
  document.addEventListener("click", (ev) => {
    if (e.searchForm && !e.searchForm.contains(ev.target)) e.searchResults.hidden = true;
  });
  document.querySelectorAll(".city-card").forEach((b) =>
    b.addEventListener("click", () => {
      track("popular_city_clicked", { city_name: b.dataset.place });
      render({
        lat: +b.dataset.lat,
        lng: +b.dataset.lng,
        place: b.dataset.place,
        source: "popular_city",
      });
    }),
  );
  function useDistrict(element, source) {
    const option = element.selectedOptions
      ? element.selectedOptions[0]
      : element;
    if (!option || !option.dataset.lat || !option.dataset.lng) return;
    render({
      lat: Number(option.dataset.lat),
      lng: Number(option.dataset.lng),
      place: option.dataset.name,
      source,
    });
  }
  const districtSelect = document.getElementById("districtSelect");
  if (districtSelect) {
    districtSelect.addEventListener("change", () => {
      if (districtSelect.value) useDistrict(districtSelect, "district_select");
    });
  }
  document.querySelectorAll(".district-use").forEach((button) => {
    button.addEventListener("click", () => useDistrict(button, "district_table"));
  });
  function getHeading(ev) {
    if (typeof ev.webkitCompassHeading === "number")
      return ev.webkitCompassHeading;
    if (typeof ev.alpha === "number") return normalizeDegree(360 - ev.alpha);
    return null;
  }
  function orient(ev) {
    if (s.bearing === null) return;
    const h = getHeading(ev);
    if (h === null) return;
    const rel = normalizeDegree(s.bearing - h),
      diff = angularDifference(h, s.bearing);
    e.needle.style.transform = `translate(-50%,-100%) rotate(${rel}deg)`;
    if (e.previewNeedle) e.previewNeedle.style.transform = `translate(-50%,-100%) rotate(${rel}deg)`;
    e.heading.textContent = `${fmt(h, 0)}°`;
    e.compassStatus.textContent =
      diff <= 4
        ? "Kıble doğrultusundasınız."
        : `Kıbleye fark: ${fmt(diff, 0)}°`;
    document
      .querySelector(".compass-face")
      .classList.toggle("aligned", diff <= 4);
    e.alignment.hidden = diff > 4;
    if (diff <= 4 && !s.vibrated && navigator.vibrate) {
      navigator.vibrate(120);
      s.vibrated = true;
      track("qibla_aligned");
    } else if (diff > 7) s.vibrated = false;
  }
  async function startCompass(permissionAlreadyRequested = false) {
    if (s.bearing === null) {
      status("Önce konumunu hesapla.", true);
      return;
    }
    try {
      if (
        typeof DeviceOrientationEvent !== "undefined" &&
        typeof DeviceOrientationEvent.requestPermission === "function" &&
        !permissionAlreadyRequested
      ) {
        const p = await DeviceOrientationEvent.requestPermission();
        if (p !== "granted") throw new Error("Sensör izni verilmedi.");
      }
      if (typeof DeviceOrientationEvent === "undefined")
        throw new Error("Bu cihazda yön sensörü bulunamadı.");
      window.addEventListener("deviceorientationabsolute", orient, true);
      window.addEventListener("deviceorientation", orient, true);
      if (e.compassButton) {
        e.compassButton.textContent = "Canlı pusula aktif";
        e.compassButton.disabled = true;
      }
      e.compassStatus.textContent = "Canlı pusula aktif. Telefonu düz tutup yavaşça döndür.";
      track("compass_started");
    } catch (err) {
      e.compassStatus.textContent = err.message;
    }
  }
  e.compassButton?.addEventListener("click", () => startCompass(false));
  e.fitMapButton?.addEventListener("click", () => {
    fitMap();
    track("map_opened");
  });
  e.mapLayerButtons.forEach((button, index) =>
    button.addEventListener("click", () =>
      setMapLayer(index === 1 ? "satellite" : "street"),
    ),
  );
  function setToolView(view) {
    if (!e.compassPanel || !e.mapPanel) return;
    const showMap = view === "map";
    e.compassPanel.hidden = showMap;
    e.mapPanel.hidden = !showMap;
    e.compassViewButton?.classList.toggle("active", !showMap);
    e.mapViewButton?.classList.toggle("active", showMap);
    e.compassViewButton?.setAttribute("aria-selected", String(!showMap));
    e.mapViewButton?.setAttribute("aria-selected", String(showMap));
    if (showMap && s.lat !== null)
      requestAnimationFrame(() => updateMap().then(() => invalidateMap()));
    track(showMap ? "map_view_selected" : "compass_view_selected");
  }
  e.compassViewButton?.addEventListener("click", () => setToolView("compass"));
  e.mapViewButton?.addEventListener("click", () => setToolView("map"));
  e.shareButton?.addEventListener("click", async () => {
    if (s.bearing === null) return;
    const text = `${s.place} için kıble açısı ${fmt(s.bearing, 1)}° (${getDirectionName(s.bearing)}).`;
    try {
      if (navigator.share)
        await navigator.share({
          title: "Kıble Yönü Hesapla",
          text,
          url: location.origin,
        });
      else {
        await navigator.clipboard.writeText(`${text} ${location.origin}`);
        e.shareButton.textContent = "Kopyalandı";
      }
      track("share_result");
    } catch {}
  });
  document.querySelectorAll(".faq-list details").forEach((d) =>
    d.addEventListener("toggle", () => {
      if (d.open)
        track("faq_opened", {
          faq_question: d.querySelector("summary").textContent,
        });
    }),
  );
  let sent75 = false,
    sent100 = false;
  window.addEventListener("scroll", () => {
    const h = document.documentElement.scrollHeight - innerHeight,
      p = h > 0 ? scrollY / h : 0;
    if (p >= 0.75 && !sent75) {
      sent75 = true;
      track("scroll_75");
    }
    if (p >= 0.98 && !sent100) {
      sent100 = true;
      track("scroll_100");
    }
  });
  window.addEventListener("resize", () => {
    if (s.map && mapVisible()) invalidateMap();
  });
  loadLocations();
  const cityPage = document.body.dataset.cityPage === "true";
  if (cityPage) {
    const lat = Number(document.body.dataset.cityLat),
      lng = Number(document.body.dataset.cityLng),
      name = document.body.dataset.cityName;
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      setTimeout(
        () =>
          render({
            lat,
            lng,
            place: name,
            source: "city_page",
            scrollResult: false,
            updateMapFrame: true,
          }),
        80,
      );
    }
  }
  if ("serviceWorker" in navigator)
    window.addEventListener("load", () =>
      navigator.serviceWorker.register("/sw.js?v=29").catch(() => {}),
    );
})();
