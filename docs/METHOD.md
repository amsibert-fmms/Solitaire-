Solitaire Research Project — Methodology

> Objective: determine which solitaire deals are theoretically solvable under varying rule sets, from the strictest classic rules to the most permissive, knowledge-rich versions.



---

1. Overview

This project explores the solvability space of Klondike-style solitaire.
Each unique 32-bit seed defines a complete shuffle and initial layout.
The solver evaluates that layout under a grid of rule profiles and draw sizes to answer a fundamental question:

> “Can this deal be won at least once, under some reasonable interpretation of the rules?”



The design captures both player realism and theoretical upper bounds.


---

2. Variants and Rule Profiles

Each seed is solved under multiple profiles, each reflecting a different philosophy of play.
Profiles form a monotonic ladder of increasing permissiveness—anything solvable under a stricter profile will also be solvable under all looser ones.

| Profile       | Description                                                                                                         | Intended Use                                                        |
|---------------|---------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| STANDARD      | Closest to “classic” Klondike rules (as found in physical decks and early PC versions).                             | Baseline reference for tradition-minded players.                    |
| FRIENDLY_APP  | Matches most modern mobile apps: free supermoves, unlimited passes, foundation takeback allowed.                    | Mirrors common user experience.                                     |
| MAX_RELAX     | Removes all play restrictions that don’t affect logical solvability: free supermoves, unlimited passes, foundation takeback, safe autoplay, no staging limits. | Estimates the maximum realistic solvable fraction for hidden-information play. |
| XRAY          | Identical to MAX_RELAX but with perfect information: the solver can see facedown cards.                             | Upper-bound theoretical solvability—used for research calibration.  |
2.1 Configurable dimensions

Each profile is parameterized by:

FieldMeaningTypical Values

drawCards drawn from stock at a time.1 or 3
passesAllowed stock recycles."unlimited" or integer
supermoveHow multi-card moves are treated."staged" or "free"
foundation_takebackWhether cards may return from foundation to tableau.true / false
peek_xrayWhether hidden cards are visible to solver.true / false
autoplay_safe_onlyWhether automatic plays avoid blocking builds.true / false
undo_unlimitedUndo limit (for interface parity; does not affect solvability).true


Each combination of (profile, draw) defines a rule instance.


---

3. What “Solvable” Means

A seed is solvable under a given rule instance if there exists at least one sequence of legal moves leading to four completed foundations.
All moves must obey the legality constraints of that rule set; X-ray only affects the solver’s information, not the legality of moves.


---

4. Legal Move Definition

Within any profile, the following constraints always hold:

1. Tableau building: descending rank, alternating color.


2. Face-down restriction: only fully face-up runs can move.


3. Empty column rule: only a King may occupy an empty tableau space.


4. Foundation order: same-suit, strictly ascending from Ace to King.


5. Stock/waste: only the top waste card may play; draw size = draw; stock may be recycled up to passes.


6. Uniqueness invariant: exactly 52 distinct cards across tableau, stock, waste, and foundations.


7. Auto-flip: any newly exposed face-down card must be turned up immediately.



Supermove and foundation-takeback options relax, but never violate, these core invariants.


---

5. Solver Logic Summary

1. Shuffler: deterministic 32-bit seed → unique layout.


2. State Encoding: compact bit representation with reversible moves.


3. Search: Iterative Deepening A* with heuristics prioritizing uncovering, safe foundation pushes, and tableau mobility.


4. Deadlock detection: repeated stock/waste cycles without net progress, blocked low ranks, or zero legal moves.


5. Termination: success (all foundations complete) or timeout.



---

6. Output Schema (excerpt)

| Field               | Type    | Description                                 |
|---------------------|---------|---------------------------------------------|
| seed                | uint32  | Shuffle seed.                               |
| profile             | str     | Rule profile name.                          |
| draw                | int     | Draw size (1 or 3).                         |
| peek_xray           | bool    | Whether X-ray information was enabled.      |
| solved              | bool    | True if a legal win sequence exists.        |
| solution_len        | int     | Number of moves in the minimal found sequence. |
| time_ms             | int     | Solver runtime.                             |
| nodes               | int     | Search nodes expanded.                      |
| reason_if_unsolved  | str     | Timeout, deadlock type, or unknown.         |
---

7. Interpretation

Comparing STANDARD → MAX_RELAX shows how much stricter play rules reduce solvability.

Comparing MAX_RELAX → XRAY isolates the impact of hidden information.

Aggregating across draw sizes lets players see whether 1-card or 3-card draw affects fairness or winnability.



---

8. Planned Extensions

Add other variants: Vegas, Limited-Pass, FreeCell, Spider(1-suit).

Integrate “supermove-capacity” experiments to mirror FreeCell-style constraints.

Release anonymized per-seed replay data for reproducibility.



---

9. Reproducibility Notes

Every result derives from a deterministic shuffle + rule profile pair.

Shuffler and rule logic are version-pinned (engine_version hash).

Golden seeds verify deterministic layout and solvability outcomes.
