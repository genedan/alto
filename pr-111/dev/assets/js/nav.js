// Category links navigate normally. Their adjacent buttons control only the named list.
(function () {
  "use strict";
  const key = "alto-docs-nav";
  let closed = {};
  try { closed = JSON.parse(localStorage.getItem(key)) || {}; } catch (e) { /* Use the default state. */ }

  document.querySelectorAll(".nav-toggle").forEach(button => {
    const list = document.getElementById(button.getAttribute("aria-controls"));
    const name = button.dataset.category;
    const holdsCurrent = button.closest(".nav-group")?.querySelector('[aria-current="page"]');

    function setOpen(open) {
      list.hidden = !open;
      button.setAttribute("aria-expanded", String(open));
      button.setAttribute("aria-label", (open ? "Collapse " : "Expand ") + name);
    }

    setOpen(!closed[name] || !!holdsCurrent);
    button.hidden = false;
    button.addEventListener("click", () => {
      setOpen(list.hidden);
      if (list.hidden) closed[name] = true;
      else delete closed[name];
      try { localStorage.setItem(key, JSON.stringify(closed)); } catch (e) { /* The control still works. */ }
    });
  });
})();
