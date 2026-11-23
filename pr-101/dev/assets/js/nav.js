// The groups of the sidebar open and close, and which of them you closed is remembered for the next page. Whatever holds the page you
// are on stays open. Without this script the sidebar still works: every group starts open, and the sections open for the current page.
(function () {
  "use strict";
  var KEY = "alto-docs-nav";
  var groups = document.querySelectorAll("details[data-nav-group]");
  if (!groups.length) { return; }
  var closed = {};
  try { closed = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { closed = {}; }

  Array.prototype.forEach.call(groups, function (group) {
    var name = group.getAttribute("data-nav-group");
    var holdsCurrent = !!group.querySelector('[aria-current="page"]');
    if (closed[name] && !holdsCurrent) { group.open = false; }
    group.addEventListener("toggle", function () {
      if (group.open) { delete closed[name]; } else { closed[name] = true; }
      try { localStorage.setItem(KEY, JSON.stringify(closed)); } catch (e) { /* not remembered; the sidebar still works */ }
    });
  });
})();
