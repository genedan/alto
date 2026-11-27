// Both pages use the shared registry. Only the details page requests data from a plugin author.
(async function () {
  "use strict";
  const table = document.getElementById("plugin-list");
  const details = document.getElementById("plugin-details");
  const container = table || details;
  if (!container) return;
  const status = document.getElementById("plugin-status");

  async function request(url, accept) {
    const response = await fetch(url, {
      headers: { Accept: accept }, cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer",
      signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) throw new Error("Could not read JSON");
    return response;
  }

  async function readJSON(url) {
    return (await request(url, "application/json")).json();
  }

  function httpsURL(value) {
    if (typeof value !== "string") return null;
    try {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
    } catch {
      return null;
    }
  }

  function element(tag, text) {
    const node = document.createElement(tag);
    node.textContent = text;
    return node;
  }

  function link(label, href) {
    const node = element("a", label);
    node.href = href;
    return node;
  }

  async function readREADME(repository) {
    const url = new URL(repository);
    const path = url.pathname.replace(/\/$/, "");
    if (url.hostname !== "github.com" || !/^\/[\w-]+\/[\w.-]+$/.test(path)) {
      throw new Error("Expected a GitHub repository");
    }
    const response = await request("https://api.github.com/repos" + path + "/readme", "application/vnd.github.html+json");
    const source = document.createElement("template");
    source.innerHTML = await response.text();
    const article = document.createElement("div");
    article.className = "plugin-readme";
    const tags = new Set("a article b blockquote br code dd del details div dl dt em h1 h2 h3 h4 h5 h6 hr i img kbd li ol p picture pre s samp source span strong sub summary sup table tbody td th thead tr ul".split(" "));

    function copy(parent, children) {
      for (const child of children) {
        if (child.nodeType === Node.TEXT_NODE) {
          parent.append(document.createTextNode(child.textContent));
          continue;
        }
        const tag = child.localName;
        if (!tags.has(tag) || (tag === "a" && child.classList.contains("anchor"))) continue;
        const node = document.createElement(tag === "h1" ? "h2" : tag);
        if (tag === "a" || tag === "img" || tag === "source") {
          const attr = tag === "a" ? "href" : tag === "img" ? "src" : "srcset";
          const value = child.getAttribute(attr)?.trim();
          const base = tag === "a" ? repository.replace(/\/$/, "") + "/blob/HEAD/" : "https://raw.githubusercontent.com" + path + "/HEAD/";
          if (value && (attr !== "srcset" || !/\s/.test(value))) {
            const target = value.startsWith("#")
              ? repository.replace(/\/$/, "") + value
              : URL.canParse(value, base) && httpsURL(new URL(value, base).href);
            if (target) node.setAttribute(attr, target);
          }
        }
        for (const attr of tag === "img" ? ["alt", "width", "height"] : tag === "source" ? ["media", "type"] : []) {
          if (child.hasAttribute(attr)) node.setAttribute(attr, child.getAttribute(attr));
        }
        if (tag === "img") {
          node.loading = "lazy";
          node.referrerPolicy = "no-referrer";
        }
        parent.append(node);
        copy(node, child.childNodes);
      }
    }

    copy(article, source.content.childNodes);
    return article;
  }

  let registry;
  try {
    registry = await readJSON(container.dataset.registry);
    if (!Array.isArray(registry)) throw new Error("Expected an array");
  } catch {
    status.textContent = "The plugin registry could not be loaded. Refresh to try again.";
    return;
  }

  if (table) {
    if (!registry.length) {
      status.textContent = "No plugins are registered yet.";
      return;
    }
    const rows = document.createDocumentFragment();
    for (const plugin of registry) {
      const row = document.createElement("tr");
      const url = new URL(table.dataset.details, location.href);
      url.searchParams.set("id", plugin.id);
      row.insertCell().append(link(plugin.name, url.href));
      row.insertCell().textContent = plugin.code;
      row.insertCell().textContent = plugin.description;
      rows.append(row);
    }
    table.tBodies[0].replaceChildren(rows);
    return;
  }

  const id = new URLSearchParams(location.search).get("id");
  const plugin = registry.find(entry => entry.id === id);
  if (!plugin) {
    status.textContent = "This plugin could not be found in the registry.";
    return;
  }
  document.querySelector("article h1").textContent = plugin.name;
  document.title = plugin.name + " · Alto";
  details.append(element("p", plugin.description));
  const code = element("div", "");
  code.className = "plugin-code";
  code.append(element("span", "Registration code"), element("strong", plugin.code));
  details.append(code);
  const repository = httpsURL(plugin.repository);
  if (repository) {
    const repoLink = link("Plugin repository", repository);
    repoLink.className = "plugin-repository";
    const icon = document.getElementById("plugin-github-icon");
    if (icon) repoLink.prepend(icon.content.cloneNode(true));
    details.append(repoLink);
    const readme = element("div", "Loading README…");
    readme.setAttribute("aria-live", "polite");
    details.append(readme);
    readREADME(repository).then(article => readme.replaceChildren(article)).catch(() => {
      readme.textContent = "The README is unavailable here. You can read it in the plugin repository.";
    });
  }

  status.textContent = "";
  if (!plugin.metadata) return;
  status.textContent = "Loading release information…";
  try {
    const url = httpsURL(plugin.metadata);
    if (!url) throw new Error("Invalid metadata URL");
    const info = await readJSON(url);
    if (!info || typeof info !== "object" || Array.isArray(info)) throw new Error("Expected an object");
    if (typeof info.about === "string" && info.about.trim()) details.append(element("p", info.about));
    const facts = document.createElement("dl");
    for (const [field, label] of [["version", "Plugin version"], ["compatible_alto", "Compatible Alto versions"]]) {
      if (typeof info[field] === "string" && info[field].trim()) {
        facts.append(element("dt", label), element("dd", info[field]));
      }
    }
    if (facts.children.length) details.append(facts);
    const links = document.createElement("ul");
    for (const [field, label] of [["documentation", "Plugin documentation"], ["download", "Download plugin"]]) {
      const href = httpsURL(info[field]);
      if (href) {
        const item = document.createElement("li");
        item.append(link(label, href));
        links.append(item);
      }
    }
    if (links.children.length) details.append(links);
    status.textContent = "";
  } catch {
    status.textContent = "Current release information is unavailable. Check the plugin repository for updates.";
  }
})();
