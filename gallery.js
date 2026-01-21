(() => {
  const galleries = document.querySelectorAll("[data-gallery]");
  galleries.forEach((gallery) => {
    const mainImg = gallery.querySelector(".gallery-main img");
    const caption = gallery.querySelector(".gallery-caption");
    const buttons = Array.from(gallery.querySelectorAll(".gallery-thumb"));
    if (!mainImg || !buttons.length) {
      return;
    }

    const setActive = (button) => {
      buttons.forEach((btn) => btn.classList.toggle("active", btn === button));
      const full = button.dataset.full;
      const alt = button.dataset.alt || "";
      const cap = button.dataset.caption || "";
      if (full) {
        mainImg.src = full;
      }
      mainImg.alt = alt;
      if (caption) {
        caption.textContent = cap;
      }
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => setActive(button));
    });

    setActive(buttons[0]);
  });
})();
