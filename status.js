(() => {
  const root = document.body;
  const statusEl = document.querySelector(".life-pill");
  const feedUrl = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTf9LEUBGvKLUj21scsKLQtDQ-ucL0RccRz-eNfB76MNM2U_hz-RuJe3reKNU22XtR-8xX8HpC63ol3/pub?gid=663029337&single=true&output=csv";
  const modal = document.getElementById("life-modal");
  const trigger = document.querySelector(".life-bar-chip");
  const closeBtn = document.querySelector(".life-modal-close");
  const navLinks = Array.from(document.querySelectorAll(".nav-links a[href^=\"#\"]"));
  const sections = Array.from(document.querySelectorAll("main section[id]"));

  const update = () => {
    if (window.scrollY > 10) {
      root.classList.add("scrolled");
    } else {
      root.classList.remove("scrolled");
    }
  };

  const parseBpm = (csvText) => {
    const lines = csvText.trim().split("\n").filter(Boolean);
    if (!lines.length) {
      return null;
    }
    const firstRow = lines[0].split(",").map((cell) => cell.replace(/\"/g, "").trim());
    const bpm = Number(firstRow[1] || firstRow[0]);
    return Number.isFinite(bpm) ? bpm : null;
  };

  const statusForBpm = (bpm) => {
    if (bpm < 40) {
      return `Someone should check on our boy - ${bpm} bpm`
    }
    if (bpm < 50) {
      return `He's Probably fine? - ${bpm} bpm`
    }
    if (bpm < 60) {
      return `Alive - Probably Asleep - ${bpm} bpm`
    }
    if (bpm < 75) {
      return `Alive - Seems to be relaxed - ${bpm} bpm`;
    }
    if (bpm >= 90) {
      return `Alive - Probably Checking on the chickens - ${bpm} bpm`;
    }
    return `Alive - Cruising | ${bpm} bpm`;
  };
  const refreshStatus = async () => {
    if (!statusEl) {
      return;
    }
    try {
      const response = await fetch(feedUrl, { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const csvText = await response.text();
      const bpm = parseBpm(csvText);
      if (bpm) {
        statusEl.textContent = statusForBpm(bpm);
      }
    } catch (error) {
      // Keep fallback text when the feed is unavailable.
    }
  };

  const openModal = () => {
    if (!modal) {
      return;
    }
    modal.removeAttribute("hidden");
    document.body.style.overflow = "hidden";
  };

  const closeModal = () => {
    if (!modal) {
      return;
    }
    modal.setAttribute("hidden", "");
    document.body.style.overflow = "";
  };

  const setActiveLink = (id) => {
    navLinks.forEach((link) => {
      const target = link.getAttribute("href");
      if (target === `#${id}`) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });
  };

  update();
  refreshStatus();
  window.addEventListener("scroll", update, { passive: true });
  setInterval(refreshStatus, 30000);

  if (sections.length && navLinks.length) {
    navLinks.forEach((link) => {
      link.addEventListener("click", () => {
        const target = link.getAttribute("href");
        if (target && target.startsWith("#")) {
          setActiveLink(target.slice(1));
        }
      });
    });

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) {
          setActiveLink(visible[0].target.id);
        }
      },
      {
        rootMargin: "-35% 0px -55% 0px",
        threshold: [0.2, 0.4, 0.6],
      }
    );

    sections.forEach((section) => observer.observe(section));
  }

  if (trigger) {
    trigger.addEventListener("click", openModal);
  }
  if (closeBtn) {
    closeBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      closeModal();
    });
  }
  if (modal) {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeModal();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !modal.hasAttribute("hidden")) {
        closeModal();
      }
    });
  }
})();
