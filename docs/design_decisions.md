# Design Decisions and Frozen Rules

This document records the frozen architectural, algorithmic, and simulation decisions for the **Smart Racing Championship** project in accordance with the DAA specification.

---

## 1. Cost Function & Preset Weights

The cost of traversing edge $e$ is normalized by circuit reference values:
$$\text{cost}(e) = w_d \cdot \frac{D}{D_{\text{ref}}} + w_t \cdot \frac{T}{T_{\text{ref}}} + w_f \cdot \frac{F}{F_{\text{ref}}} + w_r \cdot \frac{R}{R_{\text{ref}}} + w_o \cdot \frac{O}{O_{\text{ref}}}$$

Where:
- $D$: Edge distance.
- $T$: Effective travel time (accounting for active speed restrictions or nitro bonuses).
- $F$: Edge base fuel cost.
- $R$: Edge difficulty (1 to 5), representing risk.
- $O$: Obstacle penalty (0 for clear/standard edges, 1.0 for restricted/oil spills).
- Reference values $(D_{\text{ref}}, T_{\text{ref}}, F_{\text{ref}}, R_{\text{ref}}, O_{\text{ref}})$ are the medians over all edges in the circuit. If any median is 0, reference is set to 1.0 to avoid division by zero.
- Weights are non-negative and sum to 1.0:
  - **Balanced**: $w_d=0.25, w_t=0.25, w_f=0.20, w_r=0.15, w_o=0.15$
  - **Speed**: $w_d=0.20, w_t=0.50, w_f=0.10, w_r=0.10, w_o=0.10$
  - **Economy**: $w_d=0.20, w_t=0.15, w_f=0.50, w_r=0.10, w_o=0.05$
  - **Safety**: $w_d=0.10, w_t=0.15, w_f=0.15, w_r=0.30, w_o=0.30$

Single Source of Truth: The scalar cost computed by this formula is the exact cost evaluated by Dijkstra, A*, and displayed on the UI.

---

## 2. Resource Management

- **Fuel**:
  - Maximum tank capacity: $C = 100.0$ units.
  - Fuel consumed per edge: $\text{fuelCost} \times (1.0 + 0.1 \times (\text{difficulty} - 1))$.
  - When nitro is active, fuel consumption rate is multiplied by $2.0$.
  - Service station capacity: Sells up to $40.0$ units per stop.
  - Fixed stop penalty: $3.0\text{ s}$ when purchasing $> 0$ units. Zero extra time if $0$ units purchased.
  - Refuel threshold for opponents: $\le 25\%$ remaining tank capacity.
- **Nitro**:
  - Maximum charges: 3 charges per racer per race.
  - Duration per charge: $4.0\text{ s}$.
  - Speed multiplier: $1.5\times$ base speed while active (travel time divided by 1.5).
  - Collecting nitro pickups: Passing an active nitro vertex restores 1 charge (up to max 3).

---

## 3. Laps, Checkpoints, and Recovery Policy

- **Lap Validation**:
  - Championship: 3 laps. Quick race: 2 laps.
  - Checkpoint-ordered routing: A lap only counts if all mandatory checkpoints ($CP_1, CP_2, \dots, CP_k$) are visited strictly in ascending sequence before crossing the lap boundary (finish/start line).
- **Recovery Policy**:
  - When a road closure or blockage renders the planned path invalid, the racer waits at its current vertex and retries rerouting after every event batch.
  - Waiting time is accumulated in `totalTime`.
  - If no valid path is found within $60.0\text{ s}$ of waiting time, the racer receives a Did Not Finish (**DNF**).
- **Race Finish and Time Limit**:
  - Max simulation time: $600.0\text{ s}$.
  - Racers exceeding the time limit or DNF are ranked after finished racers by: laps completed (descending), checkpoints completed (descending), elapsed time (ascending), racer ID (ascending). DNF racers receive 0 championship points.

---

## 4. Scoring Table & Championship Rankings

- **Points System**:
  - Positions 1 to 10: `[25, 18, 15, 12, 10, 8, 6, 4, 2, 1]`.
  - Bonus points: $0$ (field maintained in schema).
- **Championship Total Order Comparator**:
  Rankings are decided strictly in the following priority order:
  1. Higher `totalPoints`
  2. More `wins` (1st place finishes)
  3. Lower `sumOfFinishPositions`
  4. Lower `bestFastestLap`
  5. Lower `racerId` (deterministic tie-breaker)
  This identical comparator is used by Merge Sort, Quick Sort (3-way), Heap Sort, and the Top-$K$ priority queue.

---

## 5. A* Heuristic Design

- Consistent and Admissible Heuristic:
  $$h(u, v) = \text{EuclideanDistance}(u, v) \times \min_{e \in E} \left(\frac{\text{cost}(e)}{\text{distance}(e)}\right)$$
  - If the minimum ratio is 0 or no edges exist, $h(u, v) = 0$.
  - Triangle inequality $h(u, v) \le \text{cost}(u, w) + h(w, v)$ holds because Euclidean distance satisfies metric properties and scaling by the minimum possible cost-per-distance ensures $h$ is a lower bound on the true shortest path cost.
  - Verified by `check_consistency(graph)`.

---

## 6. Determinism & Randomness

- Every stochastic component (track generator, initial race positions, event generation) accepts a seeded `random.Random(seed)` instance.
- Tie-breaking: All priority queues, heap events, and sorts break ties using unique IDs (e.g. vertex ID, racer ID, insertion sequence).
- Event min-heap tuple: `(triggerTime, priority, insertionSequence, event)`.

---

## 7. Dynamic Graph & In-Place Effects

- Edges and vertices are never deleted or rebuilt on updates; state transitions modify status flags (`Open`, `Blocked`, `Restricted`) and active effects maps in-place.
- Multiple simultaneous effects on an edge (e.g. oil spill + speed restriction) are tracked independently with separate expiries. The effective state recomputes:
  - Max difficulty penalty among active effects.
  - Strictest (minimum) speed cap among active effects.
  - Status is `Blocked` if any blocking effect is active; otherwise `Restricted` if restrictions exist; otherwise `Open`.
