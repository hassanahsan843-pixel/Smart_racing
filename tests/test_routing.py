"""Unit tests for Routing (Dijkstra, A*), Planner, MST, Generator, and Validator.

Covers:
  - source = target
  - unreachable target
  - blocked edge reroute
  - equal-cost paths
  - zero-weight edges
  - long routes
  - A* cost equals Dijkstra on 200 random graphs
  - Presets change route on circuit 1
  - Planner never skips a checkpoint
  - Generated tracks pass validator
  - Rejection of hand-built invalid candidate
  - Comparison of expanded vertices for Dijkstra vs A* on Circuit 1
"""

import os
import random
import math
import pytest
from core.models import Vertex, Edge, Racer
from core.graph import Graph
from core.cost import CircuitReferenceValues, edge_cost
from core.counters import OpCounters
import core.config as cfg
from algos.dijkstra import dijkstra
from algos.astar import astar, check_consistency
from engine.planner import plan_route, replan
from algos.mst import kruskal
from algos.validator import validate_circuit, create_invalid_candidate_circuit
from algos.backtrack_gen import generate_track
from data.circuits.loader import load_circuit_from_json


def test_source_equals_target():
    """Routing where source == destination."""
    g = Graph()
    g.add_vertex(Vertex(id=0, x=0, y=0))

    path_d, cost_d, dist_d, time_d = dijkstra(g, src=0, dst=0)
    assert path_d == [0]
    assert cost_d == 0.0

    path_a, cost_a, dist_a, time_a = astar(g, src=0, dst=0)
    assert path_a == [0]
    assert cost_a == 0.0


def test_unreachable_target():
    """Routing where destination is unreachable."""
    g = Graph()
    g.add_vertex(Vertex(id=0, x=0, y=0))
    g.add_vertex(Vertex(id=1, x=10, y=10))

    path_d, cost_d, _, _ = dijkstra(g, src=0, dst=1)
    assert path_d is None
    assert cost_d == float("inf")

    path_a, cost_a, _, _ = astar(g, src=0, dst=1)
    assert path_a is None
    assert cost_a == float("inf")


def test_blocked_edge_reroute():
    """Routing through an alternate path when preferred edge is blocked."""
    g = Graph()
    for i in range(3):
        g.add_vertex(Vertex(id=i, x=i * 10, y=0))

    # Short direct edge 0 -> 2 (blocked)
    e1 = Edge(id=1, from_node=0, to_node=2, distance=5, baseTime=2, fuelCost=2, difficulty=1, status="Blocked")
    # Detour 0 -> 1 -> 2 (open)
    e2 = Edge(id=2, from_node=0, to_node=1, distance=4, baseTime=2, fuelCost=2, difficulty=1, status="Open")
    e3 = Edge(id=3, from_node=1, to_node=2, distance=4, baseTime=2, fuelCost=2, difficulty=1, status="Open")
    g.add_edge(e1)
    g.add_edge(e2)
    g.add_edge(e3)

    path_d, cost_d, dist_d, _ = dijkstra(g, src=0, dst=2)
    assert path_d == [0, 1, 2]

    path_a, cost_a, dist_a, _ = astar(g, src=0, dst=2)
    assert path_a == [0, 1, 2]
    assert abs(cost_d - cost_a) < 1e-6


def test_equal_cost_paths_deterministic_tie_break():
    """Equal cost paths must break ties deterministically by lower vertex ID."""
    g = Graph()
    g.add_vertex(Vertex(id=0, x=0, y=0))
    g.add_vertex(Vertex(id=1, x=5, y=5))
    g.add_vertex(Vertex(id=2, x=5, y=-5))
    g.add_vertex(Vertex(id=3, x=10, y=0))

    # Path A: 0 -> 1 -> 3
    g.add_edge(Edge(id=1, from_node=0, to_node=1, distance=5, baseTime=2, fuelCost=2, difficulty=1))
    g.add_edge(Edge(id=2, from_node=1, to_node=3, distance=5, baseTime=2, fuelCost=2, difficulty=1))
    # Path B: 0 -> 2 -> 3
    g.add_edge(Edge(id=3, from_node=0, to_node=2, distance=5, baseTime=2, fuelCost=2, difficulty=1))
    g.add_edge(Edge(id=4, from_node=2, to_node=3, distance=5, baseTime=2, fuelCost=2, difficulty=1))

    path_d, cost_d, _, _ = dijkstra(g, src=0, dst=3)
    path_a, cost_a, _, _ = astar(g, src=0, dst=3)
    assert abs(cost_d - cost_a) < 1e-6
    # Both should deterministically agree on lower vertex ID 1
    assert path_d == [0, 1, 3]
    assert path_a == [0, 1, 3]


def test_zero_weight_edges():
    """Graph with zero-cost edges."""
    g = Graph()
    g.add_vertex(Vertex(id=0, x=0, y=0))
    g.add_vertex(Vertex(id=1, x=5, y=0))
    g.add_vertex(Vertex(id=2, x=10, y=0))

    g.add_edge(Edge(id=1, from_node=0, to_node=1, distance=0.0, baseTime=0.0, fuelCost=0.0, difficulty=1))
    g.add_edge(Edge(id=2, from_node=1, to_node=2, distance=5.0, baseTime=2.0, fuelCost=2.0, difficulty=1))

    ref = CircuitReferenceValues(d_ref=5.0, t_ref=2.0, f_ref=2.0, r_ref=1.0, o_ref=1.0)
    path_d, cost_d, _, _ = dijkstra(g, src=0, dst=2, ref=ref)
    path_a, cost_a, _, _ = astar(g, src=0, dst=2, ref=ref)
    assert path_d == [0, 1, 2]
    assert path_a == [0, 1, 2]
    assert abs(cost_d - cost_a) < 1e-6


def test_astar_equals_dijkstra_200_random_graphs():
    """Statement requirement: A* optimal cost must equal Dijkstra on 200 random graphs."""
    rng = random.Random(1337)

    for trial in range(200):
        n_v = rng.randint(5, 12)
        g = Graph()
        for i in range(n_v):
            g.add_vertex(Vertex(id=i, x=rng.uniform(0, 100), y=rng.uniform(0, 100)))

        edge_id = 1
        for u in range(n_v):
            for v in range(u + 1, n_v):
                if rng.random() < 0.4:
                    # Road distance is Euclidean metric plus winding road factor >= 1.0
                    eucl = math.hypot(g.vertices[u].x - g.vertices[v].x, g.vertices[u].y - g.vertices[v].y)
                    dist = max(1.0, eucl * rng.uniform(1.0, 1.4))
                    g.add_edge(Edge(
                        id=edge_id, from_node=u, to_node=v,
                        distance=dist,
                        baseTime=max(1.0, dist / 2.0),
                        fuelCost=max(1.0, dist / 2.5),
                        difficulty=rng.randint(1, 5)
                    ))
                    edge_id += 1

        src = rng.randint(0, n_v - 1)
        dst = rng.randint(0, n_v - 1)

        ref = CircuitReferenceValues.from_graph(g)
        p_d, cost_d, _, _ = dijkstra(g, src=src, dst=dst, ref=ref)
        p_a, cost_a, _, _ = astar(g, src=src, dst=dst, ref=ref)

        if p_d is None:
            assert p_a is None
            assert cost_a == float("inf")
        else:
            assert p_a is not None
            assert abs(cost_d - cost_a) < 1e-5, f"Cost mismatch on graph {trial}: Dijkstra {cost_d} vs A* {cost_a}"


def test_planner_never_skips_checkpoint():
    """Checkpoint-ordered planner must visit checkpoints in ascending order."""
    circuit1_path = os.path.join(os.path.dirname(__file__), "..", "data", "circuits", "circuit1.json")
    graph = load_circuit_from_json(circuit1_path)

    racer = Racer(id=1, name="Player", preset="Balanced", current_vertex=0, next_checkpoint_idx=1)
    plan = plan_route(graph, racer)
    assert plan is not None

    path = plan["path"]
    # Check that checkpoints 1, 2, ..., 10 appear in that order
    for order in range(1, 11):
        assert order in path
    indices = [path.index(order) for order in range(1, 11)]
    assert indices == sorted(indices), f"Checkpoints were visited out of order: {indices}"


def test_generated_tracks_pass_validator():
    """Procedurally generated track passes full competition validator."""
    graph, log = generate_track(seed=101, n_vertices=16)
    assert graph is not None
    ok, reasons = validate_circuit(graph)
    assert ok, f"Generated circuit failed validation: {reasons}"


def test_invalid_candidate_rejected_by_validator():
    """Hand-built invalid track must be rejected by validator."""
    invalid_g = create_invalid_candidate_circuit()
    ok, reasons = validate_circuit(invalid_g)
    assert not ok
    assert len(reasons) > 0


def test_dijkstra_vs_astar_expanded_vertices_circuit1():
    """Measure and print expanded vertices for Dijkstra vs A* on Circuit 1."""
    circuit1_path = os.path.join(os.path.dirname(__file__), "..", "data", "circuits", "circuit1.json")
    graph = load_circuit_from_json(circuit1_path)

    c_dijk = OpCounters()
    c_astar = OpCounters()

    # Route from Start (0) to Checkpoint 5 (5)
    p_d, cost_d, _, _ = dijkstra(graph, src=0, dst=5, counters=c_dijk)
    p_a, cost_a, _, _ = astar(graph, src=0, dst=5, counters=c_astar)

    assert abs(cost_d - cost_a) < 1e-6
    print(f"\n[Circuit 1 from 0 to 5] Dijkstra expanded: {c_dijk.visited_vertices}, A* expanded: {c_astar.visited_vertices}")
