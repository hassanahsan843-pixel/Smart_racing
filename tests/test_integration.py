"""Integration tests for Headless Race Simulation and Multi-Circuit Championship.

Covers:
  - Complete race with multiple laps and ordered checkpoints
  - Skipped-checkpoint lap not counted
  - Insufficient fuel causing DNF when no refuel route exists
  - Road closure triggering dynamic replan without restart
  - Exact determinism across runs with the same seed
  - Full 3-circuit championship execution
"""

import os
import pytest
from core.models import Racer, Vertex, Edge, Event
from core.graph import Graph
import core.config as cfg
from engine.race import Race
from engine.opponents import create_standard_opponents
from engine.championship import run_championship
from data.circuits.loader import load_circuit_from_json


def test_complete_race_multiple_laps_and_checkpoints():
    """Verify that a race completes multiple laps with ordered checkpoints."""
    circuit1_path = os.path.join(os.path.dirname(__file__), "..", "data", "circuits", "circuit1.json")
    graph = load_circuit_from_json(circuit1_path)

    human = Racer(id=1, name="Human", preset="Balanced", strategy="human")
    opponents = create_standard_opponents()
    racers = [human] + opponents

    race = Race(graph=graph, racers=racers, laps=2, seed=42)
    results = race.run()

    assert len(results) == 4
    # All non-DNF racers completed 2 laps
    for r in results:
        if not r.dnf:
            assert r.completed_laps == 2
            assert r.completed_checkpoints >= 20  # 10 CPs per lap * 2 laps


def test_skipped_checkpoint_lap_not_counted():
    """Crossing finish line without visiting all mandatory checkpoints must NOT count as a lap."""
    circuit1_path = os.path.join(os.path.dirname(__file__), "..", "data", "circuits", "circuit1.json")
    graph = load_circuit_from_json(circuit1_path)

    # Hand-craft a cheat racer that directly paths start(0) -> checkpoint 10 -> start(0),
    # skipping checkpoints 1..9
    cheater = Racer(id=99, name="Cheater", preset="Balanced", strategy="human")
    cheater.planned_route = [0, 10, 0]

    race = Race(graph=graph, racers=[cheater], laps=1, seed=42)
    # Step simulation until racer returns to 0
    while len(cheater.planned_route) > 0 and not race.is_finished():
        race.step()

    # Completed laps must be 0 because checkpoints 1..9 were skipped!
    assert cheater.completed_laps == 0


def test_insufficient_fuel_causes_dnf():
    """Racer with insufficient fuel and no reachable fuel station results in DNF."""
    circuit1_path = os.path.join(os.path.dirname(__file__), "..", "data", "circuits", "circuit1.json")
    graph = load_circuit_from_json(circuit1_path)

    # Deactivate all fuel stations
    for v in graph.vertices.values():
        if v.type == "station":
            graph.set_vertex_active(v.id, False)

    # Racer starts with almost zero fuel (1.0 unit)
    stranded_racer = Racer(id=77, name="Stranded", preset="Balanced", fuel=1.0)
    race = Race(graph=graph, racers=[stranded_racer], laps=2, seed=42)
    results = race.run()

    assert len(results) == 1
    assert results[0].dnf is True


def test_road_closure_replan_without_restart():
    """Mid-race road blockage causes racer to dynamically replan route without restart."""
    circuit1_path = os.path.join(os.path.dirname(__file__), "..", "data", "circuits", "circuit1.json")
    graph = load_circuit_from_json(circuit1_path)

    racer = Racer(id=1, name="Human", preset="Speed", strategy="human")
    race = Race(graph=graph, racers=[racer], laps=1, seed=42)

    # Schedule a road blockage event on edge 1 (0 -> 16) at t=0.5s
    block_evt = Event(id="blk_1", event_type="blockage", target_type="edge", target_id=1, trigger_time=0.5, priority=1)
    race.event_queue.push(block_evt)

    results = race.run()
    assert len(results) == 1
    # Racer should have rerouted successfully and completed the race without crashing
    assert results[0].completed_laps == 1


def test_deterministic_identical_runs():
    """Two runs with the identical seed produce bitwise identical outcomes."""
    circuit1_path = os.path.join(os.path.dirname(__file__), "..", "data", "circuits", "circuit1.json")

    def run_sim(seed_val: int):
        graph = load_circuit_from_json(circuit1_path)
        racers = [Racer(id=1, name="H", preset="Balanced")] + create_standard_opponents()
        r = Race(graph=graph, racers=racers, laps=1, seed=seed_val)
        return r.run()

    res1 = run_sim(42)
    res2 = run_sim(42)

    assert len(res1) == len(res2)
    for r1, r2 in zip(res1, res2):
        assert r1.racer_id == r2.racer_id
        assert r1.finish_position == r2.finish_position
        assert abs(r1.total_time - r2.total_time) < 1e-6


def test_full_championship_execution():
    """Run full 3-circuit championship season and declare champion."""
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "circuits")
    circuits = [
        os.path.join(base_dir, "circuit1.json"),
        os.path.join(base_dir, "circuit2.json"),
        os.path.join(base_dir, "circuit3.json"),
    ]

    standings, champion = run_championship(circuits, human_preset="Balanced", laps=1)
    assert len(standings) == 4
    assert champion is not None
    assert champion.racer_id == standings[0].racer_id
    assert champion.total_points >= standings[1].total_points
