"""Dynamic Programming for Optimal Pit Stop Refuelling.

Minimizes extra race pit stop time while guaranteeing fuel never drops below zero.
Computes the exact optimal fuel purchase at each accessible fuel station.
"""

from typing import List, Dict, Tuple, Optional, Any
import math


def refuel_dp(route_stops: List[Any],
              demands: List[float],
              capacity: float = 100.0,
              start_fuel: float = 100.0,
              max_purchase: float = 40.0,
              stop_time: float = 3.0,
              fuel_unit: float = 1.0) -> Tuple[Optional[Dict[int, float]], float, str]:
    """Refuelling DP per the recurrence:

      dp[j][f] = min extra stop time on arrival at stop j with f units;
      transition if f + a >= d_j to dp[j+1][f + a - d_j];
      stopTime(0) = 0, fixed stop time if a > 0;
      no purchase at destination.

    State-space effect:
      The state space at each stop j is determined by fuel_unit:
      Number of discrete fuel states = floor(capacity / fuel_unit) + 1.
      Using whole units (fuel_unit=1.0) yields 101 states per stop.
      Using tenths (fuel_unit=0.1) yields 1,001 states per stop (a 10x state expansion).
    Complexity:
      - Time: O(m * (capacity / fuel_unit) * (max_purchase / fuel_unit))
      - Space: O(m * (capacity / fuel_unit))
    Returns:
      (plan: Dict[stop_id, purchase_amount], total_extra_time, reason_or_status)
    """
    m = len(demands)
    if len(route_stops) < m + 1:
        return None, float("inf"), "Infeasible: route stops count does not match leg demands."

    # Discretize capacity and fuel levels
    num_states = int(round(capacity / fuel_unit)) + 1
    start_state = min(num_states - 1, max(0, int(round(start_fuel / fuel_unit))))

    # dp[j][state] = min extra stop time
    dp: List[List[float]] = [[float("inf")] * num_states for _ in range(m + 1)]
    parent: List[List[Optional[Tuple[int, float]]]] = [[None] * num_states for _ in range(m + 1)]

    dp[0][start_state] = 0.0

    max_p_steps = int(round(max_purchase / fuel_unit))

    for j in range(m):
        stop = route_stops[j]
        # Check if stop j is an active refueling station
        is_station = False
        if hasattr(stop, "type") and stop.type == "station":
            is_station = getattr(stop, "active", True)
        elif isinstance(stop, dict) and stop.get("type") == "station":
            is_station = stop.get("active", True)

        d_steps = int(math.ceil(demands[j] / fuel_unit))

        for f_idx in range(num_states):
            curr_time = dp[j][f_idx]
            if curr_time == float("inf"):
                continue

            # Determine available purchase steps
            if is_station:
                max_avail = min(num_states - 1 - f_idx, max_p_steps)
                allowed_purchases = range(0, max_avail + 1)
            else:
                allowed_purchases = [0]

            for a_step in allowed_purchases:
                f_after = f_idx + a_step
                if f_after >= d_steps:
                    f_next = f_after - d_steps
                    cost_inc = stop_time if a_step > 0 else 0.0
                    new_time = curr_time + cost_inc

                    if new_time < dp[j + 1][f_next]:
                        dp[j + 1][f_next] = new_time
                        a_amount = a_step * fuel_unit
                        parent[j + 1][f_next] = (f_idx, a_amount)

    # Destination stop m
    best_time = min(dp[m])
    if best_time == float("inf"):
        return None, float("inf"), "Infeasible: racer runs out of fuel before reaching destination."

    best_final_state = dp[m].index(best_time)

    # Reconstruct plan: map stop vertex id -> purchase amount
    plan: Dict[int, float] = {}
    curr_state = best_final_state
    for j in range(m, 0, -1):
        prev = parent[j][curr_state]
        if prev is not None:
            prev_state, purchase = prev
            stop_obj = route_stops[j - 1]
            stop_id = getattr(stop_obj, "id", stop_obj.get("id") if isinstance(stop_obj, dict) else stop_obj)
            if purchase > 0:
                plan[stop_id] = round(purchase, 2)
            curr_state = prev_state

    return plan, best_time, "Feasible"
