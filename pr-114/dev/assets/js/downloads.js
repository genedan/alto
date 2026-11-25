// Choose the initial operating system for downloads and Getting started in the browser.
// A manual guide selection goes in the URL so the reader can reload or share that view.
(function () {
  "use strict";
  var picker = document.getElementById("os-picker");
  if (picker) {
    var choices = Array.from(picker.querySelectorAll("input"));
    var address = new URL(location.href);
    var detected = detect();
    var preferred = choices.find(choice => choice.value === address.searchParams.get("os"))
      || choices.find(choice => choice.value === detected) || choices[0];
    preferred.checked = true;

    function revealTarget() {
      var target = document.getElementById(location.hash.slice(1));
      var group = target && target.closest("[data-platforms]");
      if (!group) return;
      var platforms = group.dataset.platforms.split(" ");
      if (!platforms.includes(picker.querySelector(":checked").value)) {
        choices.find(choice => platforms.includes(choice.value)).checked = true;
        target.scrollIntoView();
      }
    }
    revealTarget();
    window.addEventListener("hashchange", revealTarget);
    picker.addEventListener("change", function (event) {
      var url = new URL(location.href);
      url.searchParams.set("os", event.target.value);
      var target = document.getElementById(url.hash.slice(1));
      if (target && !target.getClientRects().length) url.hash = "";
      history.replaceState(history.state, "", url);
    });
    return;
  }
  var root = document.getElementById("download");
  var slot = document.getElementById("dl-main");
  if (!root || !slot) { return; }
  var source = root.getAttribute("data-source");
  var systems = {};
  Array.prototype.forEach.call(root.querySelectorAll(".dl-os"), function (row) {
    systems[row.getAttribute("data-os")] = {
      row: row,
      name: row.getAttribute("data-name"),
      file: row.getAttribute("data-file"),
      req: row.getAttribute("data-req"),
      url: row.getAttribute("data-url"),
      logo: { windows: "os-windows", linux: "os-linux", macos: "os-apple" }[row.getAttribute("data-os")]
    };
  });

  // Which system the visitor is on: "windows", "linux", "macos", "phone" (a phone or tablet) or "other" (anything Alto has no download
  // for, such as Linux on an ARM processor, which has no package yet).
  function detect() {
    var data = navigator.userAgentData;
    var ua = navigator.userAgent || "";
    var platform = (data && data.platform) || navigator.platform || "";
    if ((data && data.mobile) || /Android|iPhone|iPad|iPod/i.test(ua) || (/Mac/i.test(platform) && navigator.maxTouchPoints > 1)) { return "phone"; }
    if (/Win/i.test(platform)) { return "windows"; }
    if (/Mac/i.test(platform)) { return "macos"; }
    if (/CrOS/i.test(ua)) { return "other"; }
    if (/Linux|X11/i.test(platform + " " + ua)) { return /aarch64|armv\d|\barm\b|i[3-6]86/i.test(ua + " " + platform) ? "other" : "linux"; }
    return "other";
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text) { node.textContent = text; }
    return node;
  }
  // Every icon has its size written on it, so that a page whose stylesheet is old or has not loaded never shows one at the browser's
  // default size, which is huge.
  function logo(id, size) {
    var span = el("span", "dl-logo");
    span.setAttribute("aria-hidden", "true");
    span.innerHTML = '<svg viewBox="0 0 24 24" width="' + size + '" height="' + size + '"><use href="#' + id + '"/></svg>';
    return span;
  }
  function icon(id) {
    var span = document.createElement("span");
    span.innerHTML = '<svg class="i" width="18" height="18" aria-hidden="true"><use href="#' + id + '"/></svg>';
    return span.firstChild;
  }

  var os = detect();
  var main;
  if (os === "windows" || os === "linux") {
    var s = systems[os];
    main = { logo: s.logo, title: "Download for " + s.name, note: s.file + " · " + s.req, url: s.url };
  } else if (os === "macos") {
    main = { logo: "os-apple", title: "Run Alto on macOS", note: "No installer yet · run it from source", url: systems.macos.url || source };
  } else {
    main = { logo: "os-computer", title: "Get Alto on a computer", note: "Linux, Windows or macOS · pick yours below", url: "#dl-all" };
  }
  if (systems[os]) {
    var you = el("span", "dl-you", "Your system");
    systems[os].row.querySelector(".dl-name").appendChild(you);
  }

  var split = el("div", "dl-split");
  var button = el("a", "dl-solid");
  button.href = main.url;
  button.appendChild(logo(main.logo, 32));
  var text = el("span", "dl-txt");
  text.appendChild(el("span", "dl-t1", main.title));
  text.appendChild(el("span", "dl-t2", main.note));
  button.appendChild(text);
  split.appendChild(button);

  var arrow = el("button", "dl-arrow");
  arrow.type = "button";
  arrow.id = "dl-arrow";
  arrow.setAttribute("aria-haspopup", "menu");
  arrow.setAttribute("aria-expanded", "false");
  arrow.setAttribute("aria-controls", "dl-menu");
  arrow.setAttribute("aria-label", "Downloads for other systems");
  arrow.appendChild(icon("i-chev"));
  split.appendChild(arrow);

  var menu = el("div", "dl-menu");
  menu.id = "dl-menu";
  menu.setAttribute("role", "menu");
  menu.hidden = true;
  var links = [];
  Object.keys(systems).forEach(function (key) {
    var item = systems[key];
    var link = el("a");
    link.href = item.url || source;
    link.setAttribute("role", "menuitem");
    var tile = el("span", "dl-tile");
    tile.appendChild(logo(item.logo, 20));
    var words = document.createElement("span");
    words.appendChild(el("b", null, item.name));
    words.appendChild(el("small", null, item.file ? item.file : "No installer yet, run it from source"));
    link.appendChild(tile);
    link.appendChild(words);
    menu.appendChild(link);
    links.push(link);
  });
  split.appendChild(menu);
  slot.appendChild(split);

  function open(isOpen) {
    menu.hidden = !isOpen;
    arrow.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (isOpen && links.length) { links[0].focus(); }
  }
  arrow.addEventListener("click", function () { open(menu.hidden); });
  document.addEventListener("click", function (event) { if (!menu.hidden && !split.contains(event.target)) { open(false); } });
  document.addEventListener("keydown", function (event) {
    if (menu.hidden) { return; }
    if (event.key === "Escape") { open(false); arrow.focus(); }
    var at = links.indexOf(document.activeElement);
    if (event.key === "ArrowDown") { event.preventDefault(); links[(at + 1) % links.length].focus(); }
    if (event.key === "ArrowUp") { event.preventDefault(); links[(at + links.length - 1) % links.length].focus(); }
  });
})();
