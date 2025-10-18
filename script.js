(() => {
  const statusEl = document.getElementById("status");
  const newGameBtn = document.getElementById("new-game");
  const cardDesignSelect = document.getElementById("card-design");
  const backgroundSelect = document.getElementById("background-design");
  const controlsPanel = document.querySelector(".controls");

  const infoElements = {
    stock: document.getElementById("stock-count"),
    waste: document.getElementById("waste-count"),
    foundations: document.getElementById("foundation-count"),
    moves: document.getElementById("move-count")
  };

  const cardThemeClasses = ["card-theme-classic", "card-theme-vintage", "card-theme-midnight"];
  const backgroundThemeClasses = [
    "background-classic",
    "background-forest",
    "background-deepsea"
  ];

  const uiState = {
    menuOpen: true,
    statusMessage: "",
    counts: {
      stock: 0,
      waste: 0,
      foundations: "0/52",
      moves: 0
    }
  };

  function setStatusMessage(message) {
    uiState.statusMessage = message ?? "";
    if (!statusEl) return;
    if (uiState.statusMessage.trim().length === 0) {
      statusEl.textContent = "";
      statusEl.removeAttribute("data-state");
      return;
    }
    statusEl.textContent = uiState.statusMessage;
    statusEl.setAttribute("data-state", "active");
  }

  function clearStatusMessage() {
    setStatusMessage("");
  }

  function toggleMenuVisibility(forceState) {
    if (!controlsPanel) return;
    const shouldOpen =
      typeof forceState === "boolean" ? forceState : !uiState.menuOpen;
    uiState.menuOpen = shouldOpen;

    controlsPanel.dataset.state = shouldOpen ? "open" : "closed";
    if (shouldOpen) {
      controlsPanel.removeAttribute("hidden");
    } else {
      controlsPanel.setAttribute("hidden", "");
    }

    document.body?.classList.toggle("menu-open", shouldOpen);

    if (statusEl) {
      const message = shouldOpen ? "Controls menu opened." : "Controls menu collapsed.";
      setStatusMessage(message);
    }
  }

  function normalizeFoundationValue(value) {
    if (typeof value === "string") return value;
    if (typeof value === "number") {
      const clamped = Math.max(0, Math.min(52, value));
      return `${clamped}/52`;
    }
    if (Array.isArray(value)) {
      const total = value.reduce((sum, count) => sum + Number(count || 0), 0);
      return `${Math.max(0, Math.min(52, total))}/52`;
    }
    return uiState.counts.foundations;
  }

  function updateInfoCounts(partialCounts = {}) {
    uiState.counts = {
      stock:
        typeof partialCounts.stock === "number"
          ? Math.max(0, partialCounts.stock)
          : uiState.counts.stock,
      waste:
        typeof partialCounts.waste === "number"
          ? Math.max(0, partialCounts.waste)
          : uiState.counts.waste,
      foundations: normalizeFoundationValue(partialCounts.foundations),
      moves:
        typeof partialCounts.moves === "number"
          ? Math.max(0, partialCounts.moves)
          : uiState.counts.moves
    };

    if (infoElements.stock) {
      infoElements.stock.textContent = uiState.counts.stock.toString();
    }
    if (infoElements.waste) {
      infoElements.waste.textContent = uiState.counts.waste.toString();
    }
    if (infoElements.foundations) {
      infoElements.foundations.textContent = uiState.counts.foundations;
    }
    if (infoElements.moves) {
      infoElements.moves.textContent = uiState.counts.moves.toString();
    }
  }

  function applyCardTheme(theme) {
    if (!document.body) return;
    document.body.classList.remove(...cardThemeClasses);
    document.body.classList.add(`card-theme-${theme}`);
  }

  function applyBackgroundTheme(theme) {
    if (!document.body) return;
    document.body.classList.remove(...backgroundThemeClasses);
    document.body.classList.add(`background-${theme}`);
  }

  function bindEventHandlers() {
    if (newGameBtn) {
      newGameBtn.addEventListener("click", () => {
        setStatusMessage("New game setup coming soon.");
        updateInfoCounts({ stock: 0, waste: 0, foundations: "0/52", moves: 0 });
      });
    }

    if (cardDesignSelect) {
      cardDesignSelect.addEventListener("change", (event) => {
        const { value } = event.target;
        applyCardTheme(value);
        setStatusMessage(`Card design updated to ${value}.`);
      });
    }

    if (backgroundSelect) {
      backgroundSelect.addEventListener("change", (event) => {
        const { value } = event.target;
        applyBackgroundTheme(value);
        setStatusMessage(`Background updated to ${value}.`);
      });
    }

    document.addEventListener("keydown", (event) => {
      if (event.key.toLowerCase() === "m") {
        toggleMenuVisibility();
      }
    });
  }

  function initializeUI() {
    updateInfoCounts(uiState.counts);
    clearStatusMessage();
    if (cardDesignSelect) {
      applyCardTheme(cardDesignSelect.value);
    }
    if (backgroundSelect) {
      applyBackgroundTheme(backgroundSelect.value);
    }
    toggleMenuVisibility(true);
  }

  bindEventHandlers();
  initializeUI();

  window.solitaireUI = {
    toggleMenuVisibility,
    setStatusMessage,
    clearStatusMessage,
    updateInfoCounts
  };
})();
