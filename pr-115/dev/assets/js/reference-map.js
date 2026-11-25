(() => {
  const map = document.querySelector(".reference-map");
  const components = JSON.parse(map.querySelector('script[type="application/json"]').textContent);
  const screen = map.querySelector("select");
  const modes = map.querySelector("fieldset");
  const image = map.querySelector("img");
  const markers = map.querySelector(".reference-map-markers");
  const key = map.querySelector(".reference-map-key");
  const detail = map.querySelector(".reference-map-detail");
  let selected = components[0];

  function showComponent(component) {
    selected = component;
    for (const button of map.querySelectorAll("[data-component]")) {
      button.setAttribute("aria-pressed", String(button.dataset.component === component.name));
    }

    const title = document.createElement("strong");
    title.textContent = component.name;
    const explanation = document.createElement("p");
    explanation.textContent = component.detail;
    const colors = document.createElement("div");
    colors.className = "reference-map-values";
    for (const mode of ["light", "dark"]) {
      const value = document.createElement("span");
      const swatch = document.createElement("span");
      swatch.className = "reference-swatch";
      swatch.style.backgroundColor = component[mode];
      const hex = document.createElement("code");
      hex.textContent = component[mode];
      value.append(swatch, mode === "light" ? "Light " : "Dark ", hex);
      colors.append(value);
    }
    detail.replaceChildren(title, explanation, colors);
  }

  function drawScreen() {
    const dark = modes.querySelector(":checked").value === "dark";
    const items = components.filter(component => component.screen === screen.value);
    image.src = map.dataset.imageRoot + screen.value + (dark ? "-dark.png" : ".png");
    image.alt = screen.selectedOptions[0].textContent + " in Default " + (dark ? "Dark" : "Light");
    key.replaceChildren();
    markers.replaceChildren();
    items.forEach((component, index) => {
      const [x, y] = component.points[dark ? 1 : 0];
      const number = index + 1;
      const marker = document.createElement("button");
      marker.type = "button";
      marker.className = "reference-map-pin";
      // The tip of each marker points to a sampled pixel in the 1100 × 720 reference.
      marker.style.left = ((x + 0.5) / 1100 * 100) + "%";
      marker.style.top = ((y + 0.5) / 720 * 100) + "%";
      marker.classList.toggle("pin-below", y < 100);
      const label = number + ". " + component.name;
      marker.textContent = number;
      marker.title = label;
      marker.setAttribute("aria-label", label);
      markers.append(marker);

      const entry = document.createElement("button");
      entry.type = "button";
      entry.textContent = label;
      key.append(entry);
      for (const button of [marker, entry]) {
        button.dataset.component = component.name;
        button.addEventListener("click", () => showComponent(component));
      }
    });
    showComponent(items.includes(selected) ? selected : items[0]);
  }

  screen.addEventListener("change", drawScreen);
  modes.addEventListener("change", drawScreen);
  for (const link of document.querySelectorAll("[data-map-row]")) {
    link.addEventListener("click", () => {
      selected = components[Number(link.dataset.mapRow)];
      screen.value = selected.screen;
      drawScreen();
      markers.querySelector('[aria-pressed="true"]').focus({preventScroll: true});
    });
  }
  map.querySelector(".reference-map-controls").hidden = false;
  drawScreen();
})();
