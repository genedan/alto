// Folder titles navigate. Only their adjacent buttons toggle the child list.
(function () {
  "use strict";
  const key = "alto-docs-nav";
  let closed = {};
  try { closed = JSON.parse(localStorage.getItem(key)) || {}; } catch (e) { /* Use the default state. */ }

  document.querySelectorAll(".nav-toggle").forEach(button => {
    const list = document.getElementById(button.getAttribute("aria-controls"));
    const name = button.dataset.category;
    const row = button.parentElement;
    const title = row.querySelector("a");
    const category = row.classList.contains("nav-head");
    const stateKey = category ? name : list.id;
    const holdsCurrent = list.querySelector('[aria-current="page"]');

    function setOpen(open) {
      list.hidden = !open;
      button.setAttribute("aria-expanded", String(open));
      button.setAttribute("aria-label", (open ? "Collapse " : "Expand ") + name);
    }

    function remember() {
      closed[stateKey] = list.hidden;
      try { localStorage.setItem(key, JSON.stringify(closed)); } catch (e) { /* Navigation still works. */ }
    }

    const defaultOpen = category || title?.hasAttribute("aria-current");
    setOpen(!!holdsCurrent || (stateKey in closed ? !closed[stateKey] : !!defaultOpen));
    button.hidden = false;
    // If a closed folder's title is followed, keep it closed on its overview.
    title?.addEventListener("click", remember);
    button.addEventListener("click", () => {
      setOpen(list.hidden);
      remember();
    });
  });
})();
