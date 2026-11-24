// Keep the control outside the pre so selections and clipboard text contain only the snippet.
(function () {
  "use strict";

  function addCopyButtons(root) {
    root.querySelectorAll("pre").forEach(pre => {
      const block = document.createElement("div");
      block.className = "code-snippet";
      const button = document.createElement("button");
      button.type = "button";
      button.title = "Copy code";
      button.setAttribute("aria-label", "Copy code");
      button.innerHTML = '<svg class="i" aria-hidden="true" focusable="false"><use href="#i-copy"/></svg>';
      const icon = button.querySelector("use");
      const status = document.createElement("span");
      status.setAttribute("role", "status");
      let reset;

      pre.before(block);
      block.append(pre, button, status);
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
