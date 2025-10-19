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

  const pileElements = {
    stock: document.querySelector('[data-pile="stock"]'),
    waste: document.querySelector('[data-pile="waste"]'),
    foundations: Array.from(
      document.querySelectorAll('[data-pile^="foundation-"]')
    ),
    tableau: Array.from(document.querySelectorAll('[data-pile^="tableau-"]'))
  };

  const cardThemes = ["classic", "vintage", "midnight"];
  const cardThemeClasses = cardThemes.map((theme) => `card-theme-${theme}`);
  const backgroundThemes = ["classic", "forest", "deepsea"];
  const backgroundThemeClasses = backgroundThemes.map(
    (theme) => `background-${theme}`
  );

  const attemptLog = [];

  const DRAW_COUNT = 3;
  const TABLEAU_PILES = 7;
  const FOUNDATION_PILES = 4;
  const TABLEAU_VERTICAL_OFFSET = 28;
  const WASTE_HORIZONTAL_OFFSET = 18;

  const SUITS = [
    { id: "spades", symbol: "♠", color: "black" },
    { id: "hearts", symbol: "♥", color: "red" },
    { id: "clubs", symbol: "♣", color: "black" },
    { id: "diamonds", symbol: "♦", color: "red" }
  ];

  const RANKS = [
    { value: 1, label: "A" },
    { value: 2, label: "2" },
    { value: 3, label: "3" },
    { value: 4, label: "4" },
    { value: 5, label: "5" },
    { value: 6, label: "6" },
    { value: 7, label: "7" },
    { value: 8, label: "8" },
    { value: 9, label: "9" },
    { value: 10, label: "10" },
    { value: 11, label: "J" },
    { value: 12, label: "Q" },
    { value: 13, label: "K" }
  ];

  let gameState = null;
  let selectedStack = null;
  let currentSeed = null;
  let currentHandTag = "—";
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

  function createRng(seed) {
    let state = seed >>> 0;
    return () => {
      state += 0x6d2b79f5;
      let t = state;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function shuffleDeck(cards, rng) {
    for (let i = cards.length - 1; i > 0; i -= 1) {
      const j = Math.floor(rng() * (i + 1));
      [cards[i], cards[j]] = [cards[j], cards[i]];
    }
    return cards;
  }

  function describeCard(card) {
    return `${card.label}${card.suitSymbol}`;
  }

  function createDeck(seed) {
    const deck = [];
    let counter = 0;
    for (const suit of SUITS) {
      for (const rank of RANKS) {
        deck.push({
          id: `${rank.label}-${suit.id}-${counter}`,
          rank: rank.value,
          label: rank.label,
          suit: suit.id,
          suitSymbol: suit.symbol,
          color: suit.color,
          faceUp: false,
          location: null,
          element: null
        });
        counter += 1;
      }
    }
    const rng = createRng(seed);
    return shuffleDeck(deck, rng);
  }

  function clearExistingCards() {
    document.querySelectorAll(".card").forEach((el) => el.remove());
  }

  function ensureCardElement(card) {
    if (card.element) {
      return card.element;
    }
    const cardEl = document.createElement("div");
    cardEl.className = "card face-down";
    cardEl.dataset.cardId = card.id;
    const rankEl = document.createElement("div");
    rankEl.className = "rank";
    rankEl.textContent = card.label;
    const suitEl = document.createElement("div");
    suitEl.className = "suit";
    suitEl.textContent = card.suitSymbol;
    cardEl.append(rankEl, suitEl);
    cardEl.classList.add(card.color === "red" ? "red" : "black");
    cardEl.addEventListener("click", (event) => {
      event.stopPropagation();
      handleCardClick(card);
    });
    cardEl.addEventListener("dblclick", (event) => {
      event.stopPropagation();
      handleCardDoubleClick(card);
    });
    card.element = cardEl;
    return cardEl;
  }

  function updateCardFace(card) {
    const element = ensureCardElement(card);
    element.classList.toggle("face-down", !card.faceUp);
    element.setAttribute("data-face", card.faceUp ? "up" : "down");
    element.setAttribute(
      "aria-label",
      card.faceUp ? `${card.label} of ${card.suit}` : "Facedown card"
    );
  }

  function setCardLocation(card, type, index) {
    card.location = { type, index };
  }

  function getPileArray(type, index) {
    if (!gameState) return null;
    if (type === "stock") return gameState.stock;
    if (type === "waste") return gameState.waste;
    if (type === "tableau") return gameState.tableau[index] || null;
    if (type === "foundation") return gameState.foundations[index] || null;
    return null;
  }

  function refreshStockPile() {
    if (!gameState || !pileElements.stock) return;
    const container = pileElements.stock;
    const fragment = document.createDocumentFragment();
    gameState.stock.forEach((card, index) => {
      const element = ensureCardElement(card);
      updateCardFace(card);
      element.style.top = "0px";
      element.style.left = "0px";
      element.style.zIndex = (index + 1).toString();
      fragment.appendChild(element);
    });
    container.replaceChildren(fragment);
  }

  function refreshWastePile() {
    if (!gameState || !pileElements.waste) return;
    const container = pileElements.waste;
    const fragment = document.createDocumentFragment();
    const startIndex = Math.max(0, gameState.waste.length - 3);
    gameState.waste.forEach((card, index) => {
      const element = ensureCardElement(card);
      updateCardFace(card);
      const visualIndex = Math.max(0, index - startIndex);
      element.style.top = "0px";
      element.style.left = `${visualIndex * WASTE_HORIZONTAL_OFFSET}px`;
      element.style.zIndex = (index + 1).toString();
      fragment.appendChild(element);
    });
    container.replaceChildren(fragment);
  }

  function refreshTableauPile(pileIndex) {
    if (!gameState || !pileElements.tableau[pileIndex]) return;
    const container = pileElements.tableau[pileIndex];
    const fragment = document.createDocumentFragment();
    const cards = gameState.tableau[pileIndex];
    cards.forEach((card, index) => {
      const element = ensureCardElement(card);
      updateCardFace(card);
      element.style.left = "0px";
      element.style.top = `${index * TABLEAU_VERTICAL_OFFSET}px`;
      element.style.zIndex = (index + 1).toString();
      fragment.appendChild(element);
    });
    container.replaceChildren(fragment);
  }

  function refreshFoundationPile(pileIndex) {
    if (!gameState || !pileElements.foundations[pileIndex]) return;
    const container = pileElements.foundations[pileIndex];
    const fragment = document.createDocumentFragment();
    const cards = gameState.foundations[pileIndex];
    cards.forEach((card, index) => {
      const element = ensureCardElement(card);
      updateCardFace(card);
      element.style.left = "0px";
      element.style.top = "0px";
      element.style.zIndex = (index + 1).toString();
      fragment.appendChild(element);
    });
    container.replaceChildren(fragment);
  }

  function refreshAllPiles() {
    refreshStockPile();
    refreshWastePile();
    for (let i = 0; i < TABLEAU_PILES; i += 1) {
      refreshTableauPile(i);
    }
    for (let i = 0; i < FOUNDATION_PILES; i += 1) {
      refreshFoundationPile(i);
    }
  }

  function applySelection() {
    document.querySelectorAll(".card.selected").forEach((el) =>
      el.classList.remove("selected")
    );
    if (!selectedStack) return;
    selectedStack.cards.forEach((card) => {
      if (card.element) {
        card.element.classList.add("selected");
      }
    });
  }

  function clearSelection() {
    selectedStack = null;
    applySelection();
  }

  function selectStackFromCard(card) {
    if (!gameState || !card.location || !card.faceUp) return;
    const { type, index } = card.location;
    const pile = getPileArray(type, index);
    if (!pile) return;
    const cardIndex = pile.indexOf(card);
    if (cardIndex === -1) return;
    if (type !== "tableau" && cardIndex !== pile.length - 1) {
      return;
    }
    const stack = pile.slice(cardIndex);
    selectedStack = {
      cards: stack,
      from: { type, index }
    };
    applySelection();
    setStatusMessage(
      stack.length === 1
        ? `Selected ${describeCard(card)}.`
        : `Selected ${describeCard(card)} and ${stack.length - 1} card stack.`
    );
  }

  function isTopCard(card) {
    if (!gameState || !card.location) return false;
    const pile = getPileArray(card.location.type, card.location.index);
    if (!pile || pile.length === 0) return false;
    return pile[pile.length - 1] === card;
  }

  function canMoveStackToTableau(stack, destPile) {
    if (!stack.length) return false;
    const movingCard = stack[0];
    const destinationTop = destPile[destPile.length - 1];
    if (!destinationTop) {
      return movingCard.rank === 13;
    }
    if (!destinationTop.faceUp) return false;
    if (destinationTop.color === movingCard.color) return false;
    return destinationTop.rank === movingCard.rank + 1;
  }

  function canMoveCardToFoundation(card, destPile) {
    if (!card.faceUp) return false;
    if (destPile.length === 0) {
      return card.rank === 1;
    }
    const topCard = destPile[destPile.length - 1];
    return topCard.suit === card.suit && card.rank === topCard.rank + 1;
  }

  function updateBoardMetrics() {
    if (!gameState) return;
    const foundationCounts = gameState.foundations.map((pile) => pile.length);
    updateInfoCounts({
      stock: gameState.stock.length,
      waste: gameState.waste.length,
      foundations: foundationCounts,
      moves: gameState.moves
    });
  }

  function checkForWin() {
    if (!gameState) return;
    const total = gameState.foundations.reduce(
      (sum, pile) => sum + pile.length,
      0
    );
    if (total === 52) {
      setStatusMessage("Congratulations! You cleared all foundations.");
    }
  }

  function flipTopOfTableau(index) {
    if (!gameState) return;
    const pile = gameState.tableau[index];
    if (!pile || pile.length === 0) return;
    const topCard = pile[pile.length - 1];
    if (!topCard.faceUp) {
      topCard.faceUp = true;
      updateCardFace(topCard);
      refreshTableauPile(index);
    }
  }

  function performStackMove(stack, destinationType, destinationIndex, message) {
    if (!gameState || !stack.length) return false;
    const sourceLocation = stack[0].location;
    if (!sourceLocation) return false;
    const sourcePile = getPileArray(sourceLocation.type, sourceLocation.index);
    const destinationPile = getPileArray(destinationType, destinationIndex);
    if (!sourcePile || !destinationPile) return false;
    const startIndex = sourcePile.indexOf(stack[0]);
    if (startIndex === -1) return false;
    sourcePile.splice(startIndex, stack.length);
    stack.forEach((card) => {
      setCardLocation(card, destinationType, destinationIndex);
      destinationPile.push(card);
    });
    gameState.moves += 1;
    clearSelection();
    if (sourceLocation.type === "tableau") {
      flipTopOfTableau(sourceLocation.index);
    }
    refreshPile(sourceLocation.type, sourceLocation.index);
    refreshPile(destinationType, destinationIndex);
    updateBoardMetrics();
    if (message) {
      setStatusMessage(message);
    }
    checkForWin();
    return true;
  }

  function refreshPile(type, index) {
    if (type === "stock") {
      refreshStockPile();
    } else if (type === "waste") {
      refreshWastePile();
    } else if (type === "tableau") {
      refreshTableauPile(index);
    } else if (type === "foundation") {
      refreshFoundationPile(index);
    }
  }

  function tryMoveSelectedToDestination(type, index) {
    if (!selectedStack || !gameState) return false;
    const from = selectedStack.from;
    if (from.type === type && from.index === index) {
      return false;
    }
    if (type === "tableau") {
      const destinationPile = getPileArray("tableau", index);
      if (!destinationPile) return false;
      if (!canMoveStackToTableau(selectedStack.cards, destinationPile)) {
        return false;
      }
      const message =
        selectedStack.cards.length === 1
          ? `Moved ${describeCard(selectedStack.cards[0])} to tableau.`
          : `Moved stack starting with ${describeCard(
              selectedStack.cards[0]
            )} to tableau.`;
      return performStackMove(selectedStack.cards, "tableau", index, message);
    }
    if (type === "foundation") {
      if (selectedStack.cards.length !== 1) {
        return false;
      }
      const destinationPile = getPileArray("foundation", index);
      if (!destinationPile) return false;
      const card = selectedStack.cards[0];
      if (!canMoveCardToFoundation(card, destinationPile)) {
        return false;
      }
      const message = `Moved ${describeCard(card)} to foundation.`;
      return performStackMove([card], "foundation", index, message);
    }
    return false;
  }

  function autoMoveCardToFoundation(card) {
    if (!gameState || !card.location || !card.faceUp) return false;
    const { type } = card.location;
    if (type === "stock") return false;
    if (type !== "tableau" && type !== "waste" && type !== "foundation") {
      return false;
    }
    if (!isTopCard(card)) return false;
    for (let i = 0; i < FOUNDATION_PILES; i += 1) {
      const destinationPile = getPileArray("foundation", i);
      if (!destinationPile) continue;
      if (canMoveCardToFoundation(card, destinationPile)) {
        return performStackMove(
          [card],
          "foundation",
          i,
          `Auto-moved ${describeCard(card)} to foundation.`
        );
      }
    }
    return false;
  }

  function recycleWasteToStock() {
    if (!gameState) return false;
    if (gameState.waste.length === 0) return false;
    while (gameState.waste.length) {
      const card = gameState.waste.pop();
      if (!card) break;
      card.faceUp = false;
      setCardLocation(card, "stock", 0);
      gameState.stock.push(card);
    }
    gameState.passes = (gameState.passes || 0) + 1;
    refreshStockPile();
    refreshWastePile();
    updateBoardMetrics();
    setStatusMessage("Recycled waste into the stock.");
    return true;
  }

  function drawFromStock() {
    if (!gameState) return;
    clearSelection();
    if (gameState.stock.length === 0) {
      if (!recycleWasteToStock()) {
        setStatusMessage("No cards available to draw.");
      }
      return;
    }
    const drawCount = Math.min(DRAW_COUNT, gameState.stock.length);
    for (let i = 0; i < drawCount; i += 1) {
      const card = gameState.stock.pop();
      if (!card) continue;
      card.faceUp = true;
      setCardLocation(card, "waste", 0);
      gameState.waste.push(card);
    }
    gameState.moves += 1;
    refreshStockPile();
    refreshWastePile();
    updateBoardMetrics();
    setStatusMessage(
      drawCount === 1
        ? "Drew one card from the stock."
        : `Drew ${drawCount} cards from the stock.`
    );
  }

  function handleCardClick(card) {
    if (!gameState) return;
    if (card.location?.type === "stock") {
      drawFromStock();
      return;
    }
    if (card.location?.type === "tableau" && !card.faceUp) {
      if (isTopCard(card)) {
        card.faceUp = true;
        updateCardFace(card);
        refreshTableauPile(card.location.index);
        gameState.moves += 1;
        updateBoardMetrics();
        setStatusMessage(`Flipped ${describeCard(card)} face up.`);
      }
      return;
    }
    if (selectedStack && selectedStack.cards.includes(card)) {
      clearSelection();
      return;
    }
    if (selectedStack) {
      const destination = card.location;
      if (destination && tryMoveSelectedToDestination(destination.type, destination.index)) {
        return;
      }
      clearSelection();
      selectStackFromCard(card);
      return;
    }
    selectStackFromCard(card);
  }

  function handleCardDoubleClick(card) {
    autoMoveCardToFoundation(card);
  }

  function handleTableauBackgroundClick(index) {
    if (selectedStack) {
      if (!tryMoveSelectedToDestination("tableau", index)) {
        clearSelection();
      }
      return;
    }
    if (!gameState) return;
    const pile = gameState.tableau[index];
    if (pile && pile.length) {
      const topCard = pile[pile.length - 1];
      handleCardClick(topCard);
    }
  }

  function handleFoundationBackgroundClick(index) {
    if (selectedStack) {
      if (!tryMoveSelectedToDestination("foundation", index)) {
        clearSelection();
      }
      return;
    }
    if (!gameState) return;
    const pile = gameState.foundations[index];
    if (pile && pile.length) {
      const topCard = pile[pile.length - 1];
      handleCardClick(topCard);
    }
  }

  function serialiseLayout(state) {
    const encodeCard = (card) =>
      `${card.rank}:${card.suit}:${card.faceUp ? "U" : "D"}`;
    const tableau = state.tableau
      .map((pile) => pile.map(encodeCard).join("."))
      .join("|");
    const stock = state.stock.map(encodeCard).join(".");
    const waste = state.waste.map(encodeCard).join(".");
    const foundations = state.foundations
      .map((pile) => pile.map(encodeCard).join("."))
      .join("|");
    return `seed=${state.seed}|tableau=${tableau}|stock=${stock}|waste=${waste}|foundations=${foundations}`;
  }

  function fallbackHash(serialised) {
    let hash = 2166136261;
    for (let i = 0; i < serialised.length; i += 1) {
      hash ^= serialised.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  }

  async function computeHandTag(serialised) {
    try {
      if (window.crypto?.subtle?.digest) {
        const encoder = new TextEncoder();
        const data = encoder.encode(serialised);
        const digest = await window.crypto.subtle.digest("SHA-256", data);
        const bytes = Array.from(new Uint8Array(digest));
        return bytes.map((byte) => byte.toString(16).padStart(2, "0")).join("");
      }
    } catch (error) {
      // Fall back to a deterministic hash below.
    }
    return fallbackHash(serialised);
  }

  async function updateHandTagForCurrentDeal() {
    if (!gameState) return;
    const signature =
      gameState.initialSignature || serialiseLayout(gameState);
    currentHandTag = await computeHandTag(signature);
    updateRunMetadata({
      handTag: currentHandTag,
      seed: currentSeed !== null ? String(currentSeed) : "—"
    });
  }

  function generateSeed() {
    if (window.crypto?.getRandomValues) {
      const buffer = new Uint32Array(1);
      window.crypto.getRandomValues(buffer);
      return buffer[0];
    }
    return Math.floor(Math.random() * 0xffffffff);
  }

  function dealNewGame(seed) {
    clearExistingCards();
    gameState = {
      seed,
      stock: [],
      waste: [],
      tableau: Array.from({ length: TABLEAU_PILES }, () => []),
      foundations: Array.from({ length: FOUNDATION_PILES }, () => []),
      moves: 0,
      passes: 0,
      drawCount: DRAW_COUNT,
      initialSignature: ""
    };

    const deck = createDeck(seed);

    for (let column = 0; column < TABLEAU_PILES; column += 1) {
      for (let row = 0; row <= column; row += 1) {
        const card = deck.shift();
        if (!card) continue;
        card.faceUp = row === column;
        setCardLocation(card, "tableau", column);
        gameState.tableau[column].push(card);
      }
    }

    while (deck.length) {
      const card = deck.shift();
      if (!card) continue;
      card.faceUp = false;
      setCardLocation(card, "stock", 0);
      gameState.stock.push(card);
    }

    gameState.initialSignature = serialiseLayout(gameState);
    refreshAllPiles();
    updateBoardMetrics();
  }

  async function startNewGame(seedOverride) {
    clearSelection();
    currentSeed =
      typeof seedOverride === "number" && Number.isFinite(seedOverride)
        ? seedOverride >>> 0
        : generateSeed();
    updateRunMetadata({ handTag: "—", seed: String(currentSeed) });
    dealNewGame(currentSeed);
    await updateHandTagForCurrentDeal();
    setStatusMessage("New game ready. Good luck!");
  }

  function bindEventHandlers() {
    if (newGameBtn) {
      newGameBtn.addEventListener("click", () => {
        startNewGame().catch((error) => {
          console.error("Failed to start a new game", error);
          setStatusMessage("Unable to start a new game. Please try again.");
        });
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

    if (pileElements.stock) {
      pileElements.stock.addEventListener("click", (event) => {
        event.stopPropagation();
        drawFromStock();
      });
    }

    if (pileElements.waste) {
      pileElements.waste.addEventListener("click", (event) => {
        event.stopPropagation();
        const topCard = gameState?.waste[gameState.waste.length - 1];
        if (topCard) {
          handleCardClick(topCard);
        }
      });
    }

    pileElements.tableau.forEach((pile, index) => {
      pile.addEventListener("click", (event) => {
        event.stopPropagation();
        handleTableauBackgroundClick(index);
      });
    });

    pileElements.foundations.forEach((pile, index) => {
      pile.addEventListener("click", (event) => {
        event.stopPropagation();
        handleFoundationBackgroundClick(index);
      });
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (target instanceof Element && target.closest(".game-area")) {
        return;
      }
      clearSelection();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key.toLowerCase() === "m") {
        toggleMenuVisibility();
      }
    });
  }

  async function initializeUI() {
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
    try {
      await startNewGame();
    } catch (error) {
      console.error("Failed to initialise the first game", error);
      setStatusMessage("Unable to initialise the first game.");
    }
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
    startNewGame,
    drawFromStock,
    getAttemptLog() {
      return attemptLog.slice();
    },
    getStateSnapshot() {
      if (!gameState) {
        return null;
      }
      return {
        seed: currentSeed,
        handTag: currentHandTag,
        stock: gameState.stock.length,
        waste: gameState.waste.length,
        foundations: gameState.foundations.map((pile) => pile.length),
        moves: gameState.moves
      };
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
    return currentHandTag;
  };

  window.solitaireSeed = function solitaireSeed() {
    if (currentSeed !== null) {
      return String(currentSeed);
    }
    return uiState.metadata.seed;
  };
})();
