"""0/1 Knapsack Dynamic Programming with Table Reconstruction.

Solves the optimal selection of bonus pickups and resource bundles within
a scalar budget constraint.
"""

from typing import List, Dict, Tuple, Any, Optional
from core.counters import OpCounters, StepCallback


def knapsack_dp(items: List[Dict[str, Any]], budget: int,
                counters: Optional[OpCounters] = None,
                on_step: StepCallback = None) -> Tuple[float, List[Any], int]:
    """0/1 Knapsack algorithm using dynamic programming with full back-tracing.

    Complexity:
      - Time: O(n * B) where n = len(items), B = budget
      - Space: O(n * B) for DP table
    Recurrence:
      dp[i][b] = dp[i-1][b]                               if cost_i > b
      dp[i][b] = max(dp[i-1][b], dp[i-1][b - cost_i] + val_i) otherwise
    Returns:
      (best_value, selected_item_ids, state_count)
    """
    if counters is None:
        counters = OpCounters()

    n = len(items)
    # Filter non-positive budget or empty items
    if budget <= 0 or n == 0:
        return 0.0, [], 0

    # DP table: (n + 1) x (budget + 1)
    dp: List[List[float]] = [[0.0] * (budget + 1) for _ in range(n + 1)]
    state_count = (n + 1) * (budget + 1)

    for i in range(1, n + 1):
        item = items[i - 1]
        cost_i = int(item.get("cost", item.get("weight", 0)))
        val_i = float(item.get("value", item.get("benefit", 0.0)))

        for b in range(budget + 1):
            counters.comparisons += 1
            if cost_i > b:
                dp[i][b] = dp[i - 1][b]
            else:
                without_item = dp[i - 1][b]
                with_item = dp[i - 1][b - cost_i] + val_i
                if with_item > without_item:
                    dp[i][b] = with_item
                else:
                    dp[i][b] = without_item

        if on_step:
            on_step({"action": "knapsack_row", "item_index": i, "item": item,
                     "best_at_budget": dp[i][budget]})

    # Traceback to reconstruct selected items
    selected_ids: List[Any] = []
    curr_b = budget
    for i in range(n, 0, -1):
        item = items[i - 1]
        cost_i = int(item.get("cost", item.get("weight", 0)))
        val_i = float(item.get("value", item.get("benefit", 0.0)))

        if cost_i <= curr_b and dp[i][curr_b] != dp[i - 1][curr_b]:
            selected_ids.append(item.get("id", i - 1))
            curr_b -= cost_i

    selected_ids.reverse()
    best_value = dp[n][budget]
    return best_value, selected_ids, state_count


def knapsack_value_only(items: List[Dict[str, Any]], budget: int) -> float:
    """Space-optimized 0/1 knapsack returning optimal value with O(B) space."""
    if budget <= 0 or not items:
        return 0.0

    dp = [0.0] * (budget + 1)
    for item in items:
        cost = int(item.get("cost", item.get("weight", 0)))
        val = float(item.get("value", item.get("benefit", 0.0)))
        for b in range(budget, cost - 1, -1):
            if dp[b - cost] + val > dp[b]:
                dp[b] = dp[b - cost] + val

    return dp[budget]
