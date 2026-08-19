(() => {
  const header = document.querySelector(".site-header .header-inner");
  if (!header) return;
  let nav = header.querySelector("nav");
  if (!nav) {
    nav = document.createElement("nav");
    nav.setAttribute("aria-label", "Ana menü");
    nav.innerHTML = '<a href="/">Kıble Bul</a><a href="/sehirler/">81 İl</a><a href="/blog/">Rehber</a><a href="/#sss">SSS</a><a href="/iletisim/">İletişim</a>';
    header.appendChild(nav);
  }
  nav.classList.add("site-nav");
  if (!nav.id) nav.id = "siteNavigation";
  const button = document.createElement("button");
  button.className = "nav-toggle";
  button.type = "button";
  button.setAttribute("aria-controls", nav.id);
  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-label", "Menüyü aç");
  button.innerHTML = '<span class="nav-toggle-lines" aria-hidden="true"></span>';
  header.insertBefore(button, nav);
  const close = () => {
    nav.classList.remove("is-open");
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-label", "Menüyü aç");
  };
  button.addEventListener("click", () => {
    const open = !nav.classList.contains("is-open");
    nav.classList.toggle("is-open", open);
    button.setAttribute("aria-expanded", String(open));
    button.setAttribute("aria-label", open ? "Menüyü kapat" : "Menüyü aç");
  });
  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
  document.addEventListener("click", (event) => {
    if (!header.contains(event.target)) close();
  });
})();
