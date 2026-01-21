(() => {
  const root = document.body;
  const statusEls = Array.from(document.querySelectorAll(".life-pill"));
  const feedUrl = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTf9LEUBGvKLUj21scsKLQtDQ-ucL0RccRz-eNfB76MNM2U_hz-RuJe3reKNU22XtR-8xX8HpC63ol3/pub?gid=663029337&single=true&output=csv";
  const modal = document.getElementById("life-modal");
  const triggers = Array.from(document.querySelectorAll(".life-trigger"));
  const closeBtn = document.querySelector(".life-modal-close");
  const navLinks = Array.from(document.querySelectorAll(".nav-links a[href^=\"#\"]"));
  const sections = Array.from(document.querySelectorAll("main section[id]"));
  const hero = document.querySelector(".hero");

  const update = () => {
    if (!hero) {
      if (window.scrollY > 10) {
        root.classList.add("content-revealed");
        root.classList.add("pill-visible");
      } else {
        root.classList.remove("content-revealed");
        root.classList.remove("pill-visible");
      }
      return;
    }

    const heroRect = hero.getBoundingClientRect();
    const revealPoint = heroRect.height * 0.5;

    if (heroRect.bottom <= revealPoint) {
      root.classList.add("content-revealed");
    } else {
      root.classList.remove("content-revealed");
    }

    if (heroRect.bottom <= 0) {
      root.classList.add("pill-visible");
    } else {
      root.classList.remove("pill-visible");
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

  const setHeartRateAnimation = (bpm) => {
    const hearts = Array.from(document.querySelectorAll(".life-heart"));
    if (!hearts.length || !bpm) {
      return;
    }
    const seconds = Math.min(2, Math.max(0.4, 60 / bpm));
    hearts.forEach((heart) => {
      heart.style.animationDuration = `${seconds}s`;
      heart.style.setProperty("--pulse-speed", `${seconds}s`);
    });
  };
  const refreshStatus = async () => {
    if (!statusEls.length) {
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
        statusEls.forEach((el) => {
          el.textContent = statusForBpm(bpm);
        });
        setHeartRateAnimation(bpm);
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

  if (triggers.length) {
    triggers.forEach((trigger) => trigger.addEventListener("click", openModal));
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
