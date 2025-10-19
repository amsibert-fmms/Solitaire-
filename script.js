(() => {
  const statusEl = document.getElementById("status");
  const newGameBtn = document.getElementById("new-game");
  const cardDesignSelect = document.getElementById("card-design");
  const backgroundSelect = document.getElementById("background-design");
  const exportAttemptsBtn = document.getElementById("export-attempts");
  const controlsPanel = document.querySelector(".controls");

  const infoElements = {
    stock: document.getElementById("stock-count"),
    waste: document.getElementById("waste-count"),
    foundations: document.getElementById("foundation-count"),
    moves: document.getElementById("move-count"),
    handTag: document.getElementById("hand-tag-value"),
    seed: document.getElementById("seed-value")
  };

  const cardThemes = ["classic", "vintage", "midnight"];
  const cardThemeClasses = cardThemes.map((theme) => `card-theme-${theme}`);
  const backgroundThemes = ["classic", "forest", "deepsea"];
  const backgroundThemeClasses = backgroundThemes.map(
    (theme) => `background-${theme}`
  );

  const attemptLog = [];
  const storage = {
    key: "solitaire.attemptLog.v1",
    available: null,
    isAvailable() {
      if (this.available !== null) {
        return this.available;
      }
      try {
        if (typeof window === "undefined" || !window.localStorage) {
          this.available = false;
          return this.available;
        }
        const testKey = "__solitaire_storage_test__";
        window.localStorage.setItem(testKey, "1");
        window.localStorage.removeItem(testKey);
        this.available = true;
        return this.available;
      } catch (error) {
        this.available = false;
        return this.available;
      }
    },
    load() {
      if (!this.isAvailable()) return [];
      try {
        const raw = window.localStorage.getItem(this.key);
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) return [];
        return parsed
          .map((entry) => {
            try {
              return normaliseAttempt(entry);
            } catch (error) {
              return null;
            }
          })
          .filter(Boolean);
      } catch (error) {
        return [];
      }
    },
    save(entries) {
      if (!this.isAvailable()) return;
      try {
        const payload = JSON.stringify(entries);
        window.localStorage.setItem(this.key, payload);
      } catch (error) {
        // Silently ignore persistence issues so UI behaviour remains unaffected.
      }
    }
  };

  const uiState = {
    menuOpen: true,
    statusMessage: "",
    counts: {
      stock: 0,
      waste: 0,
      foundations: "0/52",
      moves: 0
    },
    metadata: {
      handTag: "—",
      seed: "—"
    }
  };

  function updateExportButtonState() {
    if (!exportAttemptsBtn) return;
    if (attemptLog.length === 0) {
      exportAttemptsBtn.setAttribute("disabled", "");
    } else {
      exportAttemptsBtn.removeAttribute("disabled");
    }
    exportAttemptsBtn.setAttribute(
      "aria-label",
      attemptLog.length === 0
        ? "Export attempts (disabled, no attempts yet)"
        : `Export ${attemptLog.length} attempts as CSV`
    );
  }

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

  function formatMetadataValue(value, fallback) {
    if (value === null || value === undefined) return fallback;
    if (typeof value === "number") {
      if (!Number.isFinite(value)) return fallback;
      return value.toString();
    }
    if (typeof value === "string") {
      const trimmed = value.trim();
      return trimmed.length > 0 ? trimmed : fallback;
    }
    return fallback;
  }

  function updateRunMetadata(partialMetadata = {}) {
    const defaults = uiState.metadata;
    const nextState = {
      handTag: formatMetadataValue(partialMetadata.handTag, defaults.handTag),
      seed: formatMetadataValue(partialMetadata.seed, defaults.seed)
    };

    uiState.metadata = nextState;

    if (infoElements.handTag) {
      infoElements.handTag.textContent = uiState.metadata.handTag;
    }
    if (infoElements.seed) {
      infoElements.seed.textContent = uiState.metadata.seed;
    }
  }

  function applyCardTheme(theme) {
    if (!document.body) return cardThemes[0];
    const safeTheme = cardThemes.includes(theme) ? theme : cardThemes[0];
    document.body.classList.remove(...cardThemeClasses);
    document.body.classList.add(`card-theme-${safeTheme}`);
    return safeTheme;
  }

  function applyBackgroundTheme(theme) {
    if (!document.body) return backgroundThemes[0];
    const safeTheme = backgroundThemes.includes(theme) ? theme : backgroundThemes[0];
    document.body.classList.remove(...backgroundThemeClasses);
    document.body.classList.add(`background-${safeTheme}`);
    return safeTheme;
  }

  function toSafeString(value, fallback = "") {
    if (value === null || value === undefined) return fallback;
    if (typeof value === "string") {
      const trimmed = value.trim();
      return trimmed.length > 0 ? trimmed : fallback;
    }
    if (typeof value === "number" || typeof value === "bigint") {
      if (!Number.isFinite(Number(value))) {
        return fallback;
      }
      return value.toString();
    }
    if (value instanceof Date) {
      if (Number.isNaN(value.getTime())) {
        return fallback;
      }
      return value.toISOString();
    }
    return fallback;
  }

  function toNonNegativeInteger(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      if (value < 0) return undefined;
      return Math.round(value);
    }
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (!trimmed) return undefined;
      const parsed = Number.parseInt(trimmed, 10);
      if (!Number.isNaN(parsed) && parsed >= 0) {
        return parsed;
      }
    }
    return undefined;
  }

  function toIsoTimestamp(value) {
    if (value instanceof Date) {
      if (!Number.isNaN(value.getTime())) {
        return value.toISOString();
      }
      return new Date().toISOString();
    }
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (!trimmed) {
        return new Date().toISOString();
      }
      const parsed = new Date(trimmed);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed.toISOString();
      }
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      const parsed = new Date(value);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed.toISOString();
      }
    }
    return new Date().toISOString();
  }

  function normaliseAttempt(attempt = {}) {
    const tag = toSafeString(attempt.tag, "untagged");
    const seed = toSafeString(
      attempt.seed ?? attempt.seedValue ?? attempt.shuffleSeed,
      ""
    );
    const result = toSafeString(attempt.result, "unknown").toLowerCase();
    const moves = toNonNegativeInteger(attempt.moves);
    const durationMs = toNonNegativeInteger(
      attempt.durationMs ?? attempt.duration_ms
    );
    const timestamp = toIsoTimestamp(
      attempt.timestampUtc ?? attempt.timestamp_utc ?? attempt.timestamp
    );
    const notes = toSafeString(attempt.notes, "");

    return {
      tag,
      seed,
      result,
      moves: moves ?? "",
      duration_ms: durationMs ?? "",
      timestamp_utc: timestamp,
      notes
    };
  }

  function escapeCsvValue(value) {
    if (value === null || value === undefined) return "";
    const stringValue = String(value);
    if (/[",\n\r]/.test(stringValue)) {
      return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
  }

  function buildAttemptCsv(entries) {
    const headers = [
      "tag",
      "seed",
      "result",
      "moves",
      "duration_ms",
      "timestamp_utc",
      "notes"
    ];
    const rows = entries.map((entry) =>
      headers.map((key) => escapeCsvValue(entry[key])).join(",")
    );
    return [headers.join(","), ...rows].join("\r\n");
  }

  function logAttempt(attempt = {}) {
    const normalised = normaliseAttempt(attempt);
    attemptLog.push(normalised);
    storage.save(attemptLog);
    updateExportButtonState();
    return normalised;
  }

  function clearAttemptLog() {
    attemptLog.splice(0, attemptLog.length);
    storage.save(attemptLog);
    updateExportButtonState();
  }

  function exportAttempts() {
    if (attemptLog.length === 0) {
      setStatusMessage("No attempts to export yet.");
      return;
    }

    const csvContent = buildAttemptCsv(attemptLog);
    const blob = new Blob([csvContent], {
      type: "text/csv;charset=utf-8;"
    });
    const url = URL.createObjectURL(blob);

    const timestamp = new Date().toISOString().replace(/[:T]/g, "-").split(".")[0];
    const filename = `solitaire_attempts_${timestamp}.csv`;

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.setAttribute("hidden", "");
    document.body?.appendChild(link);
    link.click();
    requestAnimationFrame(() => {
      link.remove();
      URL.revokeObjectURL(url);
    });

    setStatusMessage(`Exported ${attemptLog.length} attempts as CSV.`);
  }

  function bindEventHandlers() {
    if (newGameBtn) {
      newGameBtn.addEventListener("click", () => {
        setStatusMessage("New game setup coming soon.");
        updateInfoCounts({ stock: 0, waste: 0, foundations: "0/52", moves: 0 });
        updateRunMetadata({ handTag: "—", seed: "—" });
      });
    }

    if (exportAttemptsBtn) {
      exportAttemptsBtn.addEventListener("click", exportAttempts);
    }

    if (cardDesignSelect) {
      cardDesignSelect.addEventListener("change", (event) => {
        const { value } = event.target;
        const appliedTheme = applyCardTheme(value);
        if (appliedTheme !== value) {
          cardDesignSelect.value = appliedTheme;
        }
        setStatusMessage(`Card design updated to ${appliedTheme}.`);
      });
    }

    if (backgroundSelect) {
      backgroundSelect.addEventListener("change", (event) => {
        const { value } = event.target;
        const appliedTheme = applyBackgroundTheme(value);
        if (appliedTheme !== value) {
          backgroundSelect.value = appliedTheme;
        }
        setStatusMessage(`Background updated to ${appliedTheme}.`);
      });
    }

    document.addEventListener("keydown", (event) => {
      if (event.key.toLowerCase() === "m") {
        toggleMenuVisibility();
      }
    });
  }

  function initializeUI() {
    const storedAttempts = storage.load();
    if (storedAttempts.length > 0) {
      attemptLog.push(...storedAttempts);
      storage.save(attemptLog);
    }
    updateInfoCounts(uiState.counts);
    updateRunMetadata(uiState.metadata);
    clearStatusMessage();
    if (cardDesignSelect) {
      cardDesignSelect.value = applyCardTheme(cardDesignSelect.value);
    }
    if (backgroundSelect) {
      backgroundSelect.value = applyBackgroundTheme(backgroundSelect.value);
    }
    toggleMenuVisibility(true);
    updateExportButtonState();
  }

  bindEventHandlers();
  initializeUI();

  window.solitaireUI = {
    toggleMenuVisibility,
    setStatusMessage,
    clearStatusMessage,
    updateInfoCounts,
    updateRunMetadata,
    logAttempt,
    clearAttemptLog,
    getAttemptLog() {
      return attemptLog.slice();
    },
    exportAttempts,
    setHandTag(handTag) {
      updateRunMetadata({ handTag });
    },
    setSeed(seed) {
      updateRunMetadata({ seed });
    }
  };

  window.solitaireHandTag = function solitaireHandTag() {
    return uiState.metadata.handTag;
  };

  window.solitaireSeed = function solitaireSeed() {
    return uiState.metadata.seed;
  };
})();
