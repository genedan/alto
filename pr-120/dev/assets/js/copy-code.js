// Keep the control outside the pre so selections and clipboard text contain only the snippet.
(function () {
  "use strict";

  function highlightSourceLines(grid) {
    const lines = grid.querySelector(".view-source-lines").children;
    // The gutter and highlighted Python share a line height. Keep the code
    // in one selectable block while painting the row under the pointer.
    grid.addEventListener("pointermove", event => {
      if (event.pointerType === "touch") return;
      const first = lines[0].getBoundingClientRect();
      const index = Math.floor((event.clientY - first.top) / first.height);
      if (lines[index]) grid.style.setProperty("--hover-line", lines[index].offsetTop + "px");
      else grid.style.removeProperty("--hover-line");
    });
    grid.addEventListener("pointerleave", () => grid.style.removeProperty("--hover-line"));
    grid.addEventListener("focusin", event => {
      if (event.target.matches(".view-source-lines a")) {
        grid.style.removeProperty("--hover-line");
        grid.style.setProperty("--focus-line", event.target.offsetTop + "px");
      }
    });
    grid.addEventListener("focusout", () => grid.style.removeProperty("--focus-line"));
  }

  function addCopyButtons(root) {
    root.querySelectorAll("pre").forEach(pre => {
      const header = pre.closest(".view-source")?.querySelector(".view-source-header");
      const button = document.createElement("button");
      button.type = "button";
      button.title = "Copy code";
      button.setAttribute("aria-label", "Copy code");
      button.innerHTML = '<svg class="i" aria-hidden="true" focusable="false"><use href="#i-copy"/></svg>';
      const icon = button.querySelector("use");
      const status = document.createElement("span");
      status.setAttribute("role", "status");
      let reset;

      if (header) {
        header.append(button, status);
      } else {
        const block = document.createElement("div");
        block.className = "code-snippet";
        pre.before(block);
        block.append(pre, button, status);
      }
      button.addEventListener("click", async () => {
        clearTimeout(reset);
        try {
          await navigator.clipboard.writeText(pre.textContent);
          icon.setAttribute("href", "#i-check");
          status.classList.remove("copy-help");
          status.textContent = "Code copied to clipboard.";
          reset = setTimeout(() => {
            icon.setAttribute("href", "#i-copy");
            status.textContent = "";
          }, 2000);
        } catch {
          const range = document.createRange();
          range.selectNodeContents(pre);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          icon.setAttribute("href", "#i-copy");
          status.classList.add("copy-help");
          status.textContent = "Code selected. Use your device’s Copy command.";
        }
      });
    });
  }

  const article = document.querySelector("main article");
  if (!article) return;
  article.querySelectorAll(".view-source-grid").forEach(highlightSourceLines);
  addCopyButtons(article);
  // Plugin detail pages load their README after the rest of the page.
  const details = article.querySelector("#plugin-details");
  if (details && !details.querySelector(".plugin-readme")) {
    const observer = new MutationObserver(() => {
      const readme = details.querySelector(".plugin-readme");
      if (readme) {
        observer.disconnect();
        addCopyButtons(readme);
      }
    });
    observer.observe(details, {childList: true, subtree: true});
  }
})();
