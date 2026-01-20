(() => {
  const root = document.body;
  const toggle = document.querySelector(".theme-toggle");
  const media = window.matchMedia("(prefers-color-scheme: dark)");

  const applyTheme = (mode) => {
    if (mode === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    if (toggle) {
      const toLight = mode === "dark";
      const label = toLight ? "Switch to light mode" : "Switch to dark mode";
      toggle.setAttribute("aria-pressed", mode === "dark" ? "true" : "false");
      toggle.setAttribute("aria-label", label);
      toggle.setAttribute("title", label);
    }
    document.querySelectorAll("[data-src-light][data-src-dark]").forEach((embed) => {
      const next = mode === "dark" ? embed.dataset.srcDark : embed.dataset.srcLight;
      if (next && embed.getAttribute("src") !== next) {
        embed.setAttribute("src", next);
      }
    });
  };

  const stored = localStorage.getItem("theme");
  applyTheme(stored || (media.matches ? "dark" : "light"));

  if (!stored) {
    media.addEventListener("change", (event) => {
      applyTheme(event.matches ? "dark" : "light");
    });
  }

  if (toggle) {
    toggle.addEventListener("click", () => {
      const isDark = root.classList.toggle("dark");
      localStorage.setItem("theme", isDark ? "dark" : "light");
      applyTheme(isDark ? "dark" : "light");
    });
  }
})();
