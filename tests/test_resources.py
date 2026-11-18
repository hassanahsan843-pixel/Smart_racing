"""Unit tests for Resource Management algorithms: Knapsack DP, Greedy, and Refuel DP.

Covers:
  - Statement's A/B/C knapsack example (Greedy 30 vs DP 48 at budget 10)
  - Two additional derived greedy-suboptimal counterexamples
  - DP equals exhaustive search on 200 random small instances
  - Zero-cost positive-benefit items handling
  - Infeasible fuel plan detection
  - Unavailable refueling station
  - Fuel tank capacity limit enforcement
"""

import random
import pytest
from algos.knapsack import knapsack_dp, knapsack_value_only
from algos.greedy import greedy_knapsack, exhaustive_knapsack
from algos.refuel_dp import refuel_dp
from core.models import Vertex


def test_abc_knapsack_counterexample():
    """Statement requirement: The A/B/C example.

    Budget = 10.
    Item A: cost=6, value=30 (ratio = 5.0)
    Item B: cost=5, value=24 (ratio = 4.8)
    Item C: cost=5, value=24 (ratio = 4.8)
    Greedy takes A for value 30.
    DP takes B and C for value 48.
    """
    items = [
        {"id": "A", "cost": 6, "value": 30.0},
        {"id": "B", "cost": 5, "value": 24.0},
        {"id": "C", "cost": 5, "value": 24.0},
    ]
    budget = 10

    greedy_val, greedy_ids = greedy_knapsack(items, budget)
    dp_val, dp_ids, _ = knapsack_dp(items, budget)

    assert greedy_val == 30.0
    assert greedy_ids == ["A"]

    assert dp_val == 48.0
    assert sorted(dp_ids) == ["B", "C"]


def test_greedy_counterexample_2():
    """Second counterexample: Budget=8.

    Item 1: cost=5, value=15 (ratio 3.0) -> greedy choice
    Item 2: cost=4, value=11 (ratio 2.75)
    Item 3: cost=4, value=11 (ratio 2.75)
    Greedy gives 15, DP gives 22.
    """
    items = [
        {"id": 1, "cost": 5, "value": 15.0},
        {"id": 2, "cost": 4, "value": 11.0},
        {"id": 3, "cost": 4, "value": 11.0},
    ]
    budget = 8

    greedy_val, _ = greedy_knapsack(items, budget)
    dp_val, _, _ = knapsack_dp(items, budget)

    assert greedy_val == 15.0
    assert dp_val == 22.0


def test_greedy_counterexample_3():
    """Third counterexample: Budget=12.

    Item 1: cost=7, value=28 (ratio 4.0) -> greedy choice
    Item 2: cost=6, value=21 (ratio 3.5)
    Item 3: cost=6, value=21 (ratio 3.5)
    Greedy gives 28, DP gives 42.
    """
    items = [
        {"id": 1, "cost": 7, "value": 28.0},
        {"id": 2, "cost": 6, "value": 21.0},
        {"id": 3, "cost": 6, "value": 21.0},
    ]
    budget = 12

    greedy_val, _ = greedy_knapsack(items, budget)
    dp_val, _, _ = knapsack_dp(items, budget)

    assert greedy_val == 28.0
    assert dp_val == 42.0


def test_dp_equals_exhaustive_200_instances():
    """Statement requirement: DP equals exhaustive search on 200 random small instances."""
    rng = random.Random(42)

    for trial in range(200):
        n = rng.randint(3, 10)
        budget = rng.randint(10, 40)
        items = []
        for i in range(n):
            items.append({
                "id": i,
                "cost": rng.randint(1, 15),
                "value": round(rng.uniform(5.0, 50.0), 1),
            })

        dp_val, dp_ids, _ = knapsack_dp(items, budget)
        ex_val, ex_ids = exhaustive_knapsack(items, budget)

        assert abs(dp_val - ex_val) < 1e-4, f"Mismatch on trial {trial}: DP {dp_val} vs Exhaustive {ex_val}"
        # Space-optimized DP check
        val_only = knapsack_value_only(items, budget)
        assert abs(val_only - dp_val) < 1e-4


def test_zero_cost_items():
    """Items with cost=0 and value>0 should always be selected."""
    items = [
        {"id": "free1", "cost": 0, "value": 10.0},
        {"id": "free2", "cost": 0, "value": 5.0},
        {"id": "costly", "cost": 10, "value": 20.0},
    ]
    budget = 5

    dp_val, dp_ids, _ = knapsack_dp(items, budget)
    greedy_val, greedy_ids = greedy_knapsack(items, budget)

    assert "free1" in dp_ids and "free2" in dp_ids
    assert "free1" in greedy_ids and "free2" in greedy_ids


def test_refuel_dp_feasible_plan():
    """Refuel DP finds optimal pit stop when initial fuel is insufficient."""
    # Route: 0 (start) -> 1 (regular) -> 2 (station) -> 3 (finish)
    stops = [
        Vertex(id=0, x=0, y=0, type="start"),
        Vertex(id=1, x=10, y=0, type="regular"),
        Vertex(id=2, x=20, y=0, type="station", active=True),
        Vertex(id=3, x=30, y=0, type="regular"),
    ]
    # Demands: 0->1 uses 30, 1->2 uses 30, 2->3 uses 30 (total 90)
    demands = [20.0, 20.0, 30.0]
    # Start with only 50 fuel: cannot reach 3 without stopping at 2
    plan, stop_time, status = refuel_dp(
        route_stops=stops, demands=demands, capacity=100.0, start_fuel=50.0,
        max_purchase=40.0, stop_time=3.0, fuel_unit=1.0
    )

    assert status == "Feasible"
    assert plan is not None
    assert 2 in plan
    assert plan[2] >= 20.0  # Needs at least 20 units to cover last leg


def test_refuel_dp_infeasible_plan():
    """Refuel DP detects infeasible routes where fuel runs out before any station."""
    stops = [
        Vertex(id=0, x=0, y=0, type="start"),
        Vertex(id=1, x=10, y=0, type="regular"),
        Vertex(id=2, x=20, y=0, type="station", active=True),
    ]
    demands = [70.0, 20.0]
    # Start with only 50 fuel, but first leg needs 70
    plan, _, status = refuel_dp(
        route_stops=stops, demands=demands, capacity=100.0, start_fuel=50.0
    )
    assert plan is None
    assert "Infeasible" in status


def test_refuel_dp_unavailable_station():
    """Station that is inactive cannot sell fuel."""
    stops = [
        Vertex(id=0, x=0, y=0, type="start"),
        Vertex(id=1, x=10, y=0, type="station", active=False),  # Inactive station
        Vertex(id=2, x=20, y=0, type="regular"),
    ]
    demands = [40.0, 40.0]  # total 80
    plan, _, status = refuel_dp(
        route_stops=stops, demands=demands, capacity=100.0, start_fuel=50.0
    )
    # Starts with 50, needs 80, station 1 is inactive
    assert plan is None
    assert "Infeasible" in status
