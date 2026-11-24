// Search the current build and leave result links usable with ordinary browser navigation.
(function () {
  "use strict";
  const search = document.querySelector(".docs-search");
  if (!search) return;
  const input = search.querySelector("input");
  const panel = search.querySelector(".search-results");
  const status = panel.querySelector('[role="status"]');
  const list = panel.querySelector("ul");
  const indexURL = new URL(search.dataset.index, location.href);
  let entries;
  let loading;
  let dismissed = false;
  let titlesOnly = false;

  function findMatches(query) {
    query = query.toLowerCase();
    const terms = query.split(/\s+/);
    const matches = [];
    for (const {entry, title, heading, headingWords, text} of entries) {
      if (!terms.every(term => title.includes(term) || heading.includes(term) || text.includes(term))) continue;
      if (entry.section && !terms.some(term => heading.includes(term) || text.includes(term))) continue;
      let score = terms.filter(term => heading.includes(term)).length;
      score += terms.filter(term => headingWords.includes(term)).length;
      if (heading.includes(query)) score += 2;
      if (heading.startsWith(query)) score += 1;
      if (heading === query) score += 4;
      matches.push({entry, score});
    }
    matches.sort((a, b) => b.score - a.score);
    return matches.map(match => match.entry);
  }

  function resultItem(entry) {
    const link = document.createElement("a");
    link.href = new URL(entry.url, indexURL).href;
    link.textContent = entry.section || entry.title;
    if (entry.section) {
      const page = document.createElement("small");
      page.textContent = entry.title;
      link.appendChild(page);
    }
    const item = document.createElement("li");
    item.appendChild(link);
    return item;
  }

  function showResults() {
    const query = input.value.trim();
    panel.hidden = !query || dismissed || !search.contains(document.activeElement);
    if (panel.hidden) return;
    list.replaceChildren();
    if (!entries) {
      status.textContent = "Searching…";
      return;
    }
    const matches = findMatches(query);
    const shown = matches.slice(0, 20);
    const count = shown.length === matches.length ? "" : `Showing ${shown.length} of ${matches.length} results.`;
    status.textContent = [titlesOnly ? "Searching page titles only." : "", matches.length ? count : "No results found."].filter(Boolean).join(" ");
    list.append(...shown.map(resultItem));
  }

  function loadIndex() {
    if (loading) return loading;
    loading = fetch(indexURL).then(response => {
      if (!response.ok) throw new Error("Search index unavailable");
      return response.json();
    }).catch(() => {
      // Plain Jekyll previews can still search the page titles in the sidebar.
      titlesOnly = true;
      return Array.from(document.querySelectorAll(".sidebar nav a[href]"), link => ({
        title: link.textContent.trim(), section: "", text: "", url: link.href
      }));
    }).then(data => {
      // Normalize the index once so typing only compares the query with existing strings.
      entries = data.map(entry => {
        const title = entry.title.toLowerCase();
        const heading = entry.section.toLowerCase() || title;
        return {entry, title, heading, headingWords: heading.split(/[^\p{L}\p{N}_]+/u), text: entry.text.toLowerCase()};
      });
      showResults();
    });
    return loading;
  }

  function update() {
    dismissed = false;
    showResults();
    if (input.value.trim()) loadIndex();
  }

  search.hidden = false;
  input.addEventListener("input", update);
  input.addEventListener("focus", update);
  input.addEventListener("click", () => { if (panel.hidden) update(); });
  search.addEventListener("focusout", event => {
    if (!search.contains(event.relatedTarget)) panel.hidden = true;
  });
  document.addEventListener("pointerdown", event => {
    if (!search.contains(event.target)) {
      dismissed = true;
      panel.hidden = true;
    }
  });
  search.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      event.preventDefault();
      input.focus();
      dismissed = true;
      panel.hidden = true;
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      dismissed = false;
      if (panel.hidden) showResults();
      const links = Array.from(list.querySelectorAll("a"));
      if (panel.hidden || !links.length) return;
      event.preventDefault();
      const index = links.indexOf(document.activeElement);
      const next = index < 0 ? (event.key === "ArrowDown" ? 0 : links.length - 1)
        : (index + (event.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
      links[next].focus();
    }
  });
  list.addEventListener("click", () => {
    dismissed = true;
    panel.hidden = true;
  });

  const resultsPage = document.getElementById("search-page");
  if (resultsPage) {
    const query = (new URLSearchParams(location.search).get("q") || "").trim();
    const summary = resultsPage.querySelector('[role="status"]');
    input.value = query;
    if (!query) {
      summary.textContent = "Enter a search term in the search bar.";
      return;
    }
    summary.textContent = "Searching…";
    loadIndex().then(() => {
      const matches = findMatches(query);
      const count = matches.length === 1 ? "1 result" : `${matches.length} results`;
      summary.textContent = `${matches.length ? count : "No results"} for “${query}”.`;
      if (titlesOnly) summary.textContent += " Searching page titles only.";
      const terms = query.toLowerCase().split(/\s+/);
      const items = matches.map(entry => {
        const item = resultItem(entry);
        if (entry.text) {
          const text = entry.text.toLowerCase();
          const term = terms.find(word => text.includes(word));
          const at = term ? text.indexOf(term) : 0;
          const start = entry.text.lastIndexOf(" ", Math.max(0, at - 48)) + 1;
          const end = start + 170;
          const excerpt = document.createElement("p");
          excerpt.textContent = (start ? "…" : "") + entry.text.slice(start, end).trim() + (end < entry.text.length ? "…" : "");
          item.appendChild(excerpt);
        }
        return item;
      });
      resultsPage.querySelector("ol").append(...items);
    });
  }
})();
