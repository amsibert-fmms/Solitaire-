# Solitaire-

This repository hosts the source code for a Solitaire web experience. The project now includes a browser-playable Klondike Solitaire implementation that supports dragging cards, recycling the stock pile, and automatically sending eligible cards to the foundations.

## Running the game locally

1. Start a lightweight static server from the repository root—for example:
   ```bash
   python -m http.server 8000
   ```
2. Visit [http://localhost:8000](http://localhost:8000) in your browser.
3. Interact with `index.html` to play Klondike Solitaire. Use the **New Game** button to redeal the deck at any time.

## Working with this repository

* Clone the repository locally or open it in a development container.
* Make iterative changes to the code, assets, or documentation as needed.
* Use standard Git workflows (`git status`, `git add`, `git commit`, `git push`) to collaborate and track history.

As an AI assistant operating inside this environment I can apply code changes directly to the repository—adding new files, updating existing ones, and running tooling—before committing the results for review.

## Fingerprinting a Solitaire configuration

To count how many Klondike hands are winnable you need a way to identify when two states represent the same configuration. A practical approach is to serialize the complete game state into a canonical byte string and then hash the result. One encoding strategy is:

1. **Normalize the card order.** Assign every card an index from 0–51 using a fixed mapping (e.g., `index = suit * 13 + rank`).
2. **Capture tableau piles.** For each of the seven tableau columns, record the cards from bottom to top. Store the boundary between face-down and face-up sections so the representation can be reconstructed.
3. **Encode stock and waste.** Record the remaining facedown stock in draw order followed by the face-up waste pile from bottom to top.
4. **Encode foundations.** For each suit, record the highest rank currently placed on the foundation.
5. **Serialize.** Concatenate the structured data above into a deterministic sequence of integers. Converting the sequence into bytes (e.g., using variable-length integers or fixed-width bytes per card) produces a compact canonical representation.
6. **Hash for the fingerprint.** Apply a cryptographic hash (SHA-256, BLAKE3, etc.) to the serialized bytes. The hash acts as a fingerprint that uniquely identifies the configuration for deduplication or lookup in a transposition table.

With this scheme any logically identical configuration yields the same fingerprint even if the user arrived there through different sequences of moves. That makes it possible to maintain a global database of observed hands and track which configurations ultimately lead to a win.
