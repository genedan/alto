// The version dropdown of the Alto docs, and the banner on a page that is not the latest release.
//
// Every version of the docs loads this one file from the root of the site, and reads the list of versions from versions.json
// there, so a page of an old release still offers the newer ones, and a fix here reaches every version. A page that is not served
// from a site with that list (a local preview) keeps the plain text it was built with.
//
// A version's stylesheet is frozen with it, so this file brings its own styles (the `avs-` classes below) instead of relying on
// the page's. They use the page's colors where it defines them, with plain fallbacks, and the icons have their size written on them.
(function () {
  "use strict";
  var slot = document.getElementById("version-slot");
  if (!slot) { return; }
  var root = slot.getAttribute("data-root") || "";
  var current = slot.getAttribute("data-version") || "";

  function pageInVersion(version) {
    var prefix = root + "/" + current + "/";
    var rest = location.pathname.indexOf(prefix) === 0 ? location.pathname.slice(prefix.length) : "";
    return root + "/" + version + "/" + rest + location.search;
  }

  function go(version) {
    var target = pageInVersion(version);
    var home = root + "/" + version + "/";
    // Stay on the same page if that version has it; otherwise go to that version's home.
    fetch(target, { method: "HEAD" })
      .then(function (answer) { location.href = answer.ok ? target + location.hash : home; })
      .catch(function () { location.href = home; });
  }

  function banner(text, href, linkText) {
    var bar = document.createElement("div");
    bar.className = "version-banner";
    bar.setAttribute("role", "note");
    bar.appendChild(document.createTextNode(text + " "));
    if (href) {
      var link = document.createElement("a");
      link.href = href;
      link.textContent = linkText;
      bar.appendChild(link);
    }
    var layout = document.querySelector(".layout");
    if (layout && layout.parentNode) { layout.parentNode.insertBefore(bar, layout); }
  }

  // The icons are drawn here, so that this file works in a page of any version, whatever icons that page carries.
  var SVG = {
    tag: '<path d="M3 12.2V4h8.2L21 13.8 13.8 21z"/><circle cx="7.5" cy="8.5" r="1"/>',
    branch: '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 7v10M18 10c0 4-6 3-12 7"/>',
    chev: '<path d="M6 9l6 6 6-6"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>'
  };
  function icon(name, extra) {
    return '<svg class="' + (extra || "") + '" width="' + (extra === "avs-chev" ? 14 : extra === "avs-check" ? 16 : 18) + '" height="' + (extra === "avs-chev" ? 14 : extra === "avs-check" ? 16 : 18) +
      '" viewBox="0 0 24 24" aria-hidden="true">' + SVG[name] + "</svg>";
  }

  var STYLE = [
    ".avs { position: relative; }",
    ".avs svg { fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; flex: none; }",
    ".avs-btn { font: inherit; font-size: .92rem; color: var(--fg, #1d2326); background: var(--panel, #f1f2f1); border: 0; cursor: pointer;",
    "  display: inline-flex; align-items: center; gap: 7px; height: 36px; padding: 0 10px; border-radius: 8px; white-space: nowrap; }",
    ".avs-btn:hover, .avs-btn[aria-expanded=true] { background: var(--accent-soft, #e3eef8); }",
    ".avs-btn:focus-visible, .avs-item:focus-visible { outline: 2px solid var(--accent, #1f6fb5); outline-offset: 2px; }",
    ".avs .avs-chev { color: var(--muted, #5b676c); transition: transform .12s; }",
    ".avs-btn[aria-expanded=true] .avs-chev { transform: rotate(180deg); }",
    ".avs-menu { position: absolute; right: 0; top: calc(100% + 6px); z-index: 20; min-width: 296px; max-width: calc(100vw - 24px); padding: 6px;",
    "  display: flex; flex-direction: column; gap: 2px; background: var(--bg, #fbfbfa); border: 1px solid var(--line, #dadfe0);",
    "  border-radius: 10px; box-shadow: 0 8px 24px rgba(20, 30, 40, .16); }",
    ".avs-menu[hidden] { display: none; }",
    ".avs-item { font: inherit; font-size: .92rem; color: var(--fg, #1d2326); background: transparent; border: 0; cursor: pointer; text-align: left;",
    "  display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; width: 100%; }",
    ".avs-item:hover { background: var(--accent-soft, #e3eef8); }",
    ".avs-ico { width: 30px; height: 30px; border-radius: 7px; background: var(--panel, #f1f2f1); display: inline-flex; align-items: center; justify-content: center; flex: none; }",
    ".avs-item[aria-checked=true] .avs-ico { background: var(--accent-soft, #e3eef8); color: var(--accent, #1f6fb5); }",
    ".avs-item:hover .avs-ico { background: var(--bg, #fbfbfa); }",
    ".avs-text { flex: 1; min-width: 0; }",
    ".avs-text b { font-weight: 600; }",
    ".avs-text small { display: block; color: var(--muted, #5b676c); font-size: .78rem; line-height: 1.3; }",
    ".avs .avs-check { margin-left: auto; color: var(--accent, #1f6fb5); visibility: hidden; }",
    ".avs-item[aria-checked=true] .avs-check { visibility: visible; }",
    "@media (max-width: 480px) { .avs-menu { right: auto; left: 0; } }",
    "@media (prefers-reduced-motion: reduce) { .avs .avs-chev { transition: none; } }"
  ].join("\n");
  function addStyle() {
    if (document.getElementById("avs-style")) { return; }
    var style = document.createElement("style");
    style.id = "avs-style";
    style.textContent = STYLE;
    document.head.appendChild(style);
  }

  fetch(root + "/versions.json", { cache: "no-cache" })
    .then(function (answer) { return answer.json(); })
    .then(function (data) {
      addStyle();
      var latest = data.latest;
      var entries = [];
      if (latest) { entries.push({ value: "latest", name: "latest", note: latest + ", the newest release", ico: "tag", label: "latest (" + latest + ")" }); }
      // The releases, newest first as in the list, and the development version after them.
      var ordered = data.versions.filter(function (name) { return name !== "dev"; }).concat(data.versions.indexOf("dev") >= 0 ? ["dev"] : []);
      ordered.forEach(function (name) {
        var isDev = name === "dev";
        var label = isDev && /^[0-9a-f]{4,64}$/.test(data.dev_commit || "") ? "dev (" + data.dev_commit + ")" : name;
        entries.push({ value: name, name: label, note: isDev ? "changes not yet in a release" : "", ico: isDev ? "branch" : "tag", label: label });
      });
      var shown = entries.filter(function (entry) { return entry.value === current; })[0] || { label: current };

      var wrap = document.createElement("div");
      wrap.className = "avs";
      var button = document.createElement("button");
      button.type = "button";
      button.className = "avs-btn";
      button.id = "version-button";
      button.setAttribute("aria-haspopup", "menu");
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-label", "Version of the docs: " + shown.label);
      button.innerHTML = "<span>" + shown.label + "</span>" + icon("chev", "avs-chev");
      var menu = document.createElement("div");
      menu.className = "avs-menu";
      menu.setAttribute("role", "menu");
      menu.hidden = true;
      var items = entries.map(function (entry) {
        var item = document.createElement("button");
        item.type = "button";
        item.className = "avs-item";
        item.setAttribute("role", "menuitemradio");
        item.setAttribute("aria-checked", entry.value === current ? "true" : "false");
        item.innerHTML = '<span class="avs-ico">' + icon(entry.ico) + '</span><span class="avs-text"><b>' + entry.name + "</b>" +
          (entry.note ? "<small>" + entry.note + "</small>" : "") + "</span>" + icon("check", "avs-check");
        item.addEventListener("click", function () { setOpen(false); if (entry.value !== current) { go(entry.value); } });
        menu.appendChild(item);
        return item;
      });
      function setOpen(isOpen) {
        menu.hidden = !isOpen;
        button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        if (isOpen) { (menu.querySelector('[aria-checked="true"]') || items[0]).focus(); }
      }
      button.addEventListener("click", function () { setOpen(menu.hidden); });
      document.addEventListener("click", function (event) { if (!menu.hidden && !wrap.contains(event.target)) { setOpen(false); } });
      document.addEventListener("keydown", function (event) {
        if (menu.hidden) { return; }
        if (event.key === "Escape") { setOpen(false); button.focus(); }
        var at = items.indexOf(document.activeElement);
        if (event.key === "ArrowDown") { event.preventDefault(); items[(at + 1) % items.length].focus(); }
        if (event.key === "ArrowUp") { event.preventDefault(); items[(at + items.length - 1) % items.length].focus(); }
      });
      wrap.appendChild(button);
      wrap.appendChild(menu);
      slot.textContent = "";
      slot.appendChild(wrap);

      if (current === "dev") {
        banner("This is the development version, which has changes that are not in a release.", latest ? root + "/latest/" : "", "See the latest release.");
      } else if (current !== "latest" && latest && current !== latest) {
        banner("You are reading the docs for " + current + ", which is not the latest release.", pageInVersion("latest"), "See " + latest + ".");
      }
    })
    .catch(function () { /* no list: the page keeps the name of its version that it was built with */ });
})();
