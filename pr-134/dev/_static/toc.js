// "On this page": a list of the page's headings (the h2 and h3 in the article), with the one you are reading marked. It sits beside the
// text on wide screens and in a box above it on narrower ones. It is made here, from the page, so no page has to list its own headings.
// A page with fewer than two headings gets none. Without this script the page reads as before.
(function () {
  "use strict";
  var article = document.querySelector(".page-grid article");
  var rail = document.getElementById("toc");
  var grid = document.getElementById("page-grid");
  if (!article || !rail || !grid) { return; }
  if (grid.hasAttribute("data-no-toc")) { return; }  // a page can opt out with `toc: false` in its front matter

  var heads = Array.prototype.slice.call(article.querySelectorAll("h2, h3, dl.py.method > dt.sig[id]")).filter(function (h) {
    return !h.classList.contains("no-toc") && !h.parentElement.matches("section.no-toc");  // a heading can opt out with `{: .no-toc}` under it
  });
  if (heads.length < 2) { return; }

  var labels = heads.map(function (h) {
    var method = h.querySelector(".sig-name");
    return method ? method.textContent : h.textContent;
  });
  var used = {};
  function slug(text) {
    var base = text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "section";
    var name = base, n = 2;
    while (used[name] || (document.getElementById(name) && document.getElementById(name).tagName.charAt(0) !== "H")) { name = base + "-" + n; n += 1; }
    used[name] = true;
    return name;
  }
  var targets = heads.map(function (h) {
    // Sphinx puts the fragment on the enclosing section. Jekyll puts it on the heading.
    var section = h.parentElement;
    var id = h.id || (section.matches("section[id]") && section.firstElementChild === h && section.id);
    if (!id) { h.id = id = slug(h.textContent); }
    used[id] = true;
    return id;
  });

  function links() {
    var list = document.createElement("ul");
    heads.forEach(function (h, i) {
      var item = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#" + targets[i];
      a.textContent = labels[i];
      if (h.tagName === "H3") { a.className = "sub"; }
      a.setAttribute("data-toc-for", targets[i]);
      item.appendChild(a);
      list.appendChild(item);
    });
    return list;
  }

  var cap = document.createElement("div");
  cap.className = "toc-cap";
  cap.textContent = "On this page";
  rail.appendChild(cap);
  rail.appendChild(links());
  rail.hidden = false;

  var inline = document.createElement("details");
  inline.className = "toc-inline";
  var summary = document.createElement("summary");
  summary.innerHTML = '<svg class="i chev" width="14" height="14" aria-hidden="true"><use href="#i-chev-d"/></svg>';
  summary.appendChild(document.createTextNode("On this page"));
  var here = document.createElement("span");
  here.className = "here";
  summary.appendChild(here);
  inline.appendChild(summary);
  inline.appendChild(links());
  var first = article.querySelector("h1");
  var anchor = first ? (first.closest(".hero") || first) : null;  // on the home page the title is inside the hero
  anchor = article.querySelector(".os-picker") || anchor;
  if (anchor) { anchor.after(inline); } else { article.prepend(inline); }
  inline.addEventListener("click", function (event) { if (event.target.closest("a")) { inline.open = false; } });

  grid.classList.add("has-toc");

  var pending = false;
  function update() {
    pending = false;
    var current = 0;
    heads.forEach(function (h, i) { if (h.getBoundingClientRect().top <= 96) { current = i; } });
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) { current = heads.length - 1; }
    Array.prototype.forEach.call(document.querySelectorAll("[data-toc-for]"), function (a) {
      a.classList.toggle("on", a.getAttribute("data-toc-for") === targets[current]);
    });
    here.textContent = labels[current];
  }
  window.addEventListener("scroll", function () { if (!pending) { pending = true; window.requestAnimationFrame(update); } }, { passive: true });
  window.addEventListener("resize", update);
  update();
})();
