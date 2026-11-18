"""Greedy Knapsack Heuristic and Exhaustive Search Baseline.

Demonstrates that greedy benefit-to-cost ratio selection is suboptimal
for 0/1 integer knapsack problems compared to dynamic programming.
"""

from typing import List, Dict, Tuple, Any, Optional
from core.counters import OpCounters


def greedy_knapsack(items: List[Dict[str, Any]], budget: int,
                    counters: Optional[OpCounters] = None) -> Tuple[float, List[Any]]:
    """Greedy approximation for 0/1 knapsack using benefit-to-cost ratio.

    Complexity:
      - Time: O(n log n) sorting + O(n) selection.
      - Space: O(n)
    Why Greedy Fails:
      In 0/1 knapsack, items cannot be divided. An item with high value/cost ratio
      may leave empty capacity that could have been filled by multiple items of
      higher combined value.
    """
    if counters is None:
        counters = OpCounters()

    if budget <= 0 or not items:
        return 0.0, []

    selected_ids: List[Any] = []
    total_val = 0.0
    remaining_budget = budget

    # 1. Take all zero-cost positive-benefit items
    regular_items: List[Dict[str, Any]] = []
    for item in items:
        cost = int(item.get("cost", item.get("weight", 0)))
        val = float(item.get("value", item.get("benefit", 0.0)))
        item_id = item.get("id")

        if cost == 0:
            if val > 0:
                total_val += val
                selected_ids.append(item_id)
            # Skip zero-cost zero/negative benefit
        else:
            if cost > 0:
                regular_items.append(item)

    # 2. Sort remaining items by ratio (val / cost) descending, tie-break by lower ID
    def sort_key(itm: Dict[str, Any]):
        cost = int(itm.get("cost", itm.get("weight", 1)))
        val = float(itm.get("value", itm.get("benefit", 0.0)))
        ratio = val / cost
        itm_id = itm.get("id", 0)
        # Use negative ratio for descending sort, positive itm_id for ascending tie-break
        return (-ratio, itm_id)

    regular_items.sort(key=sort_key)
    counters.comparisons += len(regular_items) * 2

    # 3. Select greedily while they fit
    for item in regular_items:
        cost = int(item.get("cost", item.get("weight", 0)))
        val = float(item.get("value", item.get("benefit", 0.0)))
        item_id = item.get("id")

        if cost <= remaining_budget:
            remaining_budget -= cost
            total_val += val
            selected_ids.append(item_id)

    return total_val, selected_ids


def exhaustive_knapsack(items: List[Dict[str, Any]], budget: int) -> Tuple[float, List[Any]]:
    """Exact exhaustive search evaluating all 2^n subsets (for n <= 20).

    Complexity:
      - Time: O(2^n)
      - Space: O(n)
    """
    n = len(items)
    assert n <= 20, f"Exhaustive search only feasible for n <= 20, got n={n}"

    best_val = 0.0
    best_subset: List[Any] = []

    num_subsets = 1 << n
    for mask in range(num_subsets):
        current_weight = 0
        current_val = 0.0
        current_ids: List[Any] = []

        valid = True
        for i in range(n):
            if (mask >> i) & 1:
                cost = int(items[i].get("cost", items[i].get("weight", 0)))
                val = float(items[i].get("value", items[i].get("benefit", 0.0)))
                current_weight += cost
                if current_weight > budget:
                    valid = False
                    break
                current_val += val
                current_ids.append(items[i].get("id", i))

        if valid and current_val > best_val:
            best_val = current_val
            best_subset = list(current_ids)

    return best_val, best_subset
