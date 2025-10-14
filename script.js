(() => {
  const suits = [
    { name: "spades", symbol: "♠", color: "black" },
    { name: "hearts", symbol: "♥", color: "red" },
    { name: "diamonds", symbol: "♦", color: "red" },
    { name: "clubs", symbol: "♣", color: "black" }
  ];
  const ranks = [
    { label: "A", value: 1 },
    { label: "2", value: 2 },
    { label: "3", value: 3 },
    { label: "4", value: 4 },
    { label: "5", value: 5 },
    { label: "6", value: 6 },
    { label: "7", value: 7 },
    { label: "8", value: 8 },
    { label: "9", value: 9 },
    { label: "10", value: 10 },
    { label: "J", value: 11 },
    { label: "Q", value: 12 },
    { label: "K", value: 13 }
  ];

  function getTableauSpacing() {
    return parseInt(
      getComputedStyle(document.documentElement).getPropertyValue("--tableau-gap"),
      10
    );
  }

  const piles = {
    stock: document.querySelector('[data-pile="stock"]'),
    waste: document.querySelector('[data-pile="waste"]'),
    foundations: [
      document.querySelector('[data-pile="foundation-0"]'),
      document.querySelector('[data-pile="foundation-1"]'),
      document.querySelector('[data-pile="foundation-2"]'),
      document.querySelector('[data-pile="foundation-3"]')
    ],
    tableaus: [
      document.querySelector('[data-pile="tableau-0"]'),
      document.querySelector('[data-pile="tableau-1"]'),
      document.querySelector('[data-pile="tableau-2"]'),
      document.querySelector('[data-pile="tableau-3"]'),
      document.querySelector('[data-pile="tableau-4"]'),
      document.querySelector('[data-pile="tableau-5"]'),
      document.querySelector('[data-pile="tableau-6"]')
    ]
  };

  const statusEl = document.getElementById("status");
  const newGameBtn = document.getElementById("new-game");
  const cardDesignSelect = document.getElementById("card-design");
  const backgroundSelect = document.getElementById("background-design");
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

  const state = {
    stock: [],
    waste: [],
    foundations: [[], [], [], []],
    tableaus: [[], [], [], [], [], [], []],
    moveCount: 0
  };

  let dragState = null;

  function createDeck() {
    const deck = [];
    suits.forEach((suit) => {
      ranks.forEach((rank) => {
        const card = {
          suit,
          rank,
          color: suit.color,
          faceUp: false,
          element: null,
          pile: "stock"
        };
        card.element = createCardElement(card);
        deck.push(card);
      });
    });
    return deck;
  }

  function shuffle(deck) {
    for (let i = deck.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }
  }

  function createCardElement(card) {
    const el = document.createElement("div");
    el.className = "card face-down";
    el.classList.add(card.color === "red" ? "red" : "black");
    el.innerHTML = `
      <div class="rank">${card.rank.label}</div>
      <div class="suit">${card.suit.symbol}</div>
    `;
    el.setAttribute("role", "img");
    el.setAttribute(
      "aria-label",
      `${card.rank.label} of ${card.suit.name[0].toUpperCase()}${card.suit.name.slice(1)}`
    );

    el.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      onCardPointerDown(event, card);
    });

    el.addEventListener("dblclick", () => {
      tryAutoMove(card);
    });

    return el;
  }

  function attachPlaceholders() {
    document.querySelectorAll(".pile").forEach((pile) => {
      const placeholder = document.createElement("div");
      placeholder.className = "placeholder";
      pile.appendChild(placeholder);
    });
  }

  function startNewGame() {
    resetState();
    const deck = createDeck();
    shuffle(deck);

    // deal tableau
    for (let pileIndex = 0; pileIndex < 7; pileIndex += 1) {
      for (let cardIndex = 0; cardIndex <= pileIndex; cardIndex += 1) {
        const card = deck.shift();
        state.tableaus[pileIndex].push(card);
        card.pile = `tableau-${pileIndex}`;
        if (cardIndex === pileIndex) {
          setCardFace(card, true);
        }
      }
    }

    // remaining deck to stock
    while (deck.length) {
      const card = deck.shift();
      state.stock.push(card);
      card.pile = "stock";
      setCardFace(card, false);
    }

    state.moveCount = 0;
    render();
    updateStatus("Good luck!");
  }

  function applyCardTheme(theme) {
    document.body.classList.remove(...cardThemeClasses);
    document.body.classList.add(`card-theme-${theme}`);
  }

  function applyBackgroundTheme(theme) {
    document.body.classList.remove(...backgroundThemeClasses);
    document.body.classList.add(`background-${theme}`);
  }

  function resetState() {
    state.stock.length = 0;
    state.waste.length = 0;
    state.foundations.forEach((f) => f.splice(0));
    state.tableaus.forEach((t) => t.splice(0));
  }

  function setCardFace(card, faceUp) {
    card.faceUp = faceUp;
    card.element.classList.toggle("face-down", !faceUp);
    card.element.style.cursor = faceUp ? "grab" : "default";
  }

  function render() {
    renderStock();
    renderWaste();
    renderFoundations();
    renderTableau();
    updateInfoPanel();
  }

  function clearPileElement(pileEl) {
    Array.from(pileEl.querySelectorAll(".card")).forEach((el) => {
      el.remove();
    });
  }

  function togglePlaceholder(pileEl, show) {
    const placeholder = pileEl.querySelector(".placeholder");
    if (placeholder) {
      placeholder.style.display = show ? "block" : "none";
    }
  }

  function renderStock() {
    const pileEl = piles.stock;
    clearPileElement(pileEl);
    state.stock.forEach((card, index) => {
      setCardFace(card, false);
      card.pile = "stock";
      card.element.style.top = "0px";
      card.element.style.left = "0px";
      card.element.style.transform = "";
      card.element.style.zIndex = index;
      pileEl.appendChild(card.element);
    });
    togglePlaceholder(pileEl, state.stock.length === 0);
  }

  function renderWaste() {
    const pileEl = piles.waste;
    clearPileElement(pileEl);
    state.waste.forEach((card, index) => {
      setCardFace(card, true);
      card.pile = "waste";
      card.element.style.top = "0px";
      card.element.style.left = "0px";
      card.element.style.transform = "";
      card.element.style.zIndex = index;
      pileEl.appendChild(card.element);
    });
    togglePlaceholder(pileEl, state.waste.length === 0);
  }

  function renderFoundations() {
    state.foundations.forEach((foundation, index) => {
      const pileEl = piles.foundations[index];
      clearPileElement(pileEl);
      foundation.forEach((card, cardIndex) => {
        setCardFace(card, true);
        card.pile = `foundation-${index}`;
        card.element.style.top = "0px";
        card.element.style.left = "0px";
        card.element.style.transform = "";
        card.element.style.zIndex = cardIndex;
        pileEl.appendChild(card.element);
      });
      togglePlaceholder(pileEl, foundation.length === 0);
    });
  }

  function renderTableau() {
    state.tableaus.forEach((pile, index) => {
      const pileEl = piles.tableaus[index];
      clearPileElement(pileEl);
      const spacing = getTableauSpacing();
      pile.forEach((card, cardIndex) => {
        card.pile = `tableau-${index}`;
        card.element.style.left = "0px";
        card.element.style.top = `${cardIndex * spacing}px`;
        card.element.style.transform = "";
        card.element.style.zIndex = cardIndex;
        pileEl.appendChild(card.element);
      });
      togglePlaceholder(pileEl, pile.length === 0);
    });
  }

  function getPileArray(pileId) {
    if (pileId === "stock") return state.stock;
    if (pileId === "waste") return state.waste;
    if (pileId.startsWith("foundation")) {
      const index = Number(pileId.split("-")[1]);
      return state.foundations[index];
    }
    if (pileId.startsWith("tableau")) {
      const index = Number(pileId.split("-")[1]);
      return state.tableaus[index];
    }
    return null;
  }

  function onCardPointerDown(event, card) {
    if (!card.faceUp) {
      const pileArray = getPileArray(card.pile);
      const indexInPile = pileArray ? pileArray.indexOf(card) : -1;
      if (card.pile.startsWith("tableau") && indexInPile === pileArray.length - 1) {
        setCardFace(card, true);
      }
      return;
    }

    if (card.pile === "stock") {
      return;
    }

    const pileArray = getPileArray(card.pile);
    const indexInPile = pileArray.indexOf(card);
    if (card.pile.startsWith("waste") && indexInPile !== pileArray.length - 1) {
      return;
    }
    if (card.pile.startsWith("foundation") && indexInPile !== pileArray.length - 1) {
      return;
    }

    const cardsToDrag = pileArray.slice(indexInPile);
    dragState = {
      cards: cardsToDrag,
      originPile: card.pile,
      originIndex: indexInPile,
      startX: event.clientX,
      startY: event.clientY,
      pointerId: event.pointerId
    };

    cardsToDrag.forEach((c, idx) => {
      if (idx === 0) {
        c.element.setPointerCapture(event.pointerId);
      }
      c.element.style.transition = "none";
      c.element.classList.add("dragging");
      c.element.style.zIndex = 2000 + idx;
    });

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp, { once: true });
    window.addEventListener("pointercancel", onPointerCancel, { once: true });
  }

  function onPointerMove(event) {
    if (!dragState) return;
    const dx = event.clientX - dragState.startX;
    const dy = event.clientY - dragState.startY;
    dragState.cards.forEach((card) => {
      card.element.style.transform = `translate(${dx}px, ${dy}px)`;
    });
  }

  function onPointerUp(event) {
    if (!dragState) return;
    const target = document
      .elementsFromPoint(event.clientX, event.clientY)
      .find((el) => el.classList && el.classList.contains("pile"));

    const { cards, originPile, originIndex } = dragState;
    dragState.cards.forEach((card, idx) => {
      card.element.style.transition = "";
      card.element.classList.remove("dragging");
      card.element.style.transform = "";
      if (idx === 0) {
        card.element.releasePointerCapture(dragState.pointerId);
      }
    });

    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointercancel", onPointerCancel);

    if (!target) {
      render();
      dragState = null;
      return;
    }

    const targetPileId = target.getAttribute("data-pile");
    if (!targetPileId || targetPileId === "stock" || targetPileId === originPile) {
      render();
      dragState = null;
      return;
    }

    const destinationArray = getPileArray(targetPileId);
    const originArray = getPileArray(originPile);

    if (!destinationArray || !originArray) {
      render();
      dragState = null;
      return;
    }

    const canDrop = validateMove(cards, targetPileId);

    if (canDrop) {
      originArray.splice(originIndex, cards.length);
      cards.forEach((card) => {
        destinationArray.push(card);
        card.pile = targetPileId;
      });

      if (originPile.startsWith("tableau")) {
        const newTop = originArray[originArray.length - 1];
        if (newTop && !newTop.faceUp) {
          setCardFace(newTop, true);
        }
      }
      state.moveCount += 1;
      render();
      checkWin();
    } else {
      render();
    }

    dragState = null;
  }

  function onPointerCancel() {
    if (!dragState) return;
    dragState.cards.forEach((card, idx) => {
      card.element.style.transition = "";
      card.element.classList.remove("dragging");
      card.element.style.transform = "";
      if (idx === 0) {
        card.element.releasePointerCapture(dragState.pointerId);
      }
    });
    window.removeEventListener("pointermove", onPointerMove);
    render();
    dragState = null;
  }

  function validateMove(cards, targetPileId) {
    const targetPile = getPileArray(targetPileId);
    const topCard = targetPile[targetPile.length - 1];
    const movingCard = cards[0];

    if (targetPileId.startsWith("foundation")) {
      if (cards.length !== 1) return false;
      if (!topCard) {
        return movingCard.rank.value === 1;
      }
      return (
        topCard.suit.name === movingCard.suit.name &&
        topCard.rank.value + 1 === movingCard.rank.value
      );
    }

    if (targetPileId.startsWith("tableau")) {
      if (!topCard) {
        return movingCard.rank.value === 13;
      }
      if (!topCard.faceUp) return false;
      return (
        topCard.color !== movingCard.color &&
        topCard.rank.value === movingCard.rank.value + 1
      );
    }

    return false;
  }

  function tryAutoMove(card) {
    if (!card.faceUp) return;
    const sourceArray = getPileArray(card.pile);
    if (!sourceArray || sourceArray[sourceArray.length - 1] !== card) {
      return;
    }
    for (let i = 0; i < state.foundations.length; i += 1) {
      if (validateMove([card], `foundation-${i}`)) {
        moveCardsToFoundation(card, i);
        return;
      }
    }
  }

  function moveCardsToFoundation(card, index) {
    const targetId = `foundation-${index}`;
    const sourceId = card.pile;
    const sourceArray = getPileArray(sourceId);
    const cardIndex = sourceArray.indexOf(card);
    if (cardIndex === -1) return;
    sourceArray.splice(cardIndex, 1);
    state.foundations[index].push(card);
    card.pile = targetId;
    if (sourceId.startsWith("tableau")) {
      const newTop = sourceArray[sourceArray.length - 1];
      if (newTop && !newTop.faceUp) {
        setCardFace(newTop, true);
      }
    }
    state.moveCount += 1;
    render();
    checkWin();
  }

  function handleStockClick() {
    if (state.stock.length === 0) {
      if (state.waste.length === 0) return;
      while (state.waste.length) {
        const card = state.waste.pop();
        setCardFace(card, false);
        state.stock.push(card);
        card.pile = "stock";
      }
      updateStatus(`Recycled waste back to stock. Moves: ${state.moveCount}`);
      render();
      return;
    }
    const card = state.stock.pop();
    setCardFace(card, true);
    state.waste.push(card);
    card.pile = "waste";
    state.moveCount += 1;
    render();
    checkWin();
  }

  function checkWin() {
    const complete = state.foundations.every((foundation) => foundation.length === 13);
    if (complete) {
      updateStatus(`You win! Moves: ${state.moveCount}`);
    } else {
      updateStatus(`Moves: ${state.moveCount}`);
    }
  }

  function updateStatus(message) {
    statusEl.textContent = message;
  }

  function updateInfoPanel() {
    if (!infoElements.stock) return;
    infoElements.stock.textContent = state.stock.length;
    infoElements.waste.textContent = state.waste.length;
    const foundationCount = state.foundations.reduce(
      (total, foundation) => total + foundation.length,
      0
    );
    infoElements.foundations.textContent = `${foundationCount}/52`;
    infoElements.moves.textContent = state.moveCount;
  }

  function setupEventListeners() {
    piles.stock.addEventListener("click", handleStockClick);
    newGameBtn.addEventListener("click", startNewGame);
    if (cardDesignSelect) {
      cardDesignSelect.addEventListener("change", (event) => {
        applyCardTheme(event.target.value);
      });
    }
    if (backgroundSelect) {
      backgroundSelect.addEventListener("change", (event) => {
        applyBackgroundTheme(event.target.value);
      });
    }
  }

  attachPlaceholders();
  setupEventListeners();
  if (cardDesignSelect) {
    applyCardTheme(cardDesignSelect.value);
  }
  if (backgroundSelect) {
    applyBackgroundTheme(backgroundSelect.value);
  }
  startNewGame();
})();
