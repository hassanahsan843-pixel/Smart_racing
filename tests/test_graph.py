"""Unit tests for Graph data structures, Cost functions, Circuit loader, and BFS/DFS.

Covers single vertex, disconnected, cyclic, branching, dead ends,
directed/undirected, unreachable targets, S-T edge-count vs distance test,
and brute-force BFS comparison on random graphs.
"""

import os
import random
from typing import List, Optional
import pytest
from core.models import Vertex, Edge
from core.graph import Graph
from core.cost import CircuitReferenceValues, edge_cost
from core.counters import OpCounters
from algos.bfs_dfs import (
    bfs, dfs_traverse, detect_cycle, connected_components,
    find_dead_ends, alternative_routes
)
from data.circuits.loader import load_circuit_from_json


def test_single_vertex():
    """Graph with a single isolated vertex."""
    g = Graph()
    v0 = Vertex(id=0, x=0, y=0, type="start")
    g.add_vertex(v0)

    visited, parent, path = bfs(g, src=0, dst=0)
    assert 0 in visited
    assert path == [0]

    # Traversal and components
    assert dfs_traverse(g, 0) == [0]
    comps = connected_components(g)
    assert comps == [{0}]
    has_cycle, _ = detect_cycle(g)
    assert not has_cycle


def test_disconnected_graph():
    """Graph with two disconnected components."""
    g = Graph()
    g.add_vertex(Vertex(id=0, x=0, y=0))
    g.add_vertex(Vertex(id=1, x=10, y=0))
    g.add_vertex(Vertex(id=2, x=20, y=0))
    g.add_edge(Edge(id=1, from_node=0, to_node=1, distance=10, baseTime=5, fuelCost=5, difficulty=1))

    # Vertex 2 is isolated
    comps = connected_components(g)
    assert len(comps) == 2
    assert {0, 1} in comps
    assert {2} in comps

    # Unreachable target must return None and not hang
    visited, parent, path = bfs(g, src=0, dst=2)
    assert 2 not in visited
    assert path is None


def test_cyclic_graph():
    """Graph with a cycle."""
    g = Graph()
    for i in range(3):
        g.add_vertex(Vertex(id=i, x=i * 10, y=0))

    g.add_edge(Edge(id=1, from_node=0, to_node=1, distance=5, baseTime=2, fuelCost=2, difficulty=1, directed=True))
    g.add_edge(Edge(id=2, from_node=1, to_node=2, distance=5, baseTime=2, fuelCost=2, difficulty=1, directed=True))
    g.add_edge(Edge(id=3, from_node=2, to_node=0, distance=5, baseTime=2, fuelCost=2, difficulty=1, directed=True))

    has_cycle, cycle = detect_cycle(g)
    assert has_cycle
    assert len(cycle) >= 3


def test_branching_and_alternative_routes():
    """Graph with branching paths."""
    g = Graph()
    for i in range(5):
        g.add_vertex(Vertex(id=i, x=i * 10, y=0))

    # Path 1: 0 -> 1 -> 4
    g.add_edge(Edge(id=1, from_node=0, to_node=1, distance=5, baseTime=2, fuelCost=2, difficulty=1))
    g.add_edge(Edge(id=2, from_node=1, to_node=4, distance=5, baseTime=2, fuelCost=2, difficulty=1))
    # Path 2: 0 -> 2 -> 3 -> 4
    g.add_edge(Edge(id=3, from_node=0, to_node=2, distance=5, baseTime=2, fuelCost=2, difficulty=1))
    g.add_edge(Edge(id=4, from_node=2, to_node=3, distance=5, baseTime=2, fuelCost=2, difficulty=1))
    g.add_edge(Edge(id=5, from_node=3, to_node=4, distance=5, baseTime=2, fuelCost=2, difficulty=1))

    main_route = [0, 1, 4]
    alts = alternative_routes(g, start=0, finish=4, main_route=main_route, max_routes=5)
    assert [0, 2, 3, 4] in alts


def test_dead_end_detection():
    """Graph with a dead end vertex that cannot reach finish without reversing."""
    g = Graph()
    g.add_vertex(Vertex(id=0, x=0, y=0, type="start"))
    g.add_vertex(Vertex(id=1, x=10, y=0, type="checkpoint", checkpointOrder=1))
    g.add_vertex(Vertex(id=2, x=20, y=0, type="checkpoint", checkpointOrder=2))
    g.add_vertex(Vertex(id=99, x=10, y=10, type="dead_end"))

    # Track from 0 -> 1 -> 2 -> 0 (directed loop)
    g.add_edge(Edge(id=1, from_node=0, to_node=1, distance=10, baseTime=5, fuelCost=5, difficulty=1, directed=True))
    g.add_edge(Edge(id=2, from_node=1, to_node=2, distance=10, baseTime=5, fuelCost=5, difficulty=1, directed=True))
    g.add_edge(Edge(id=3, from_node=2, to_node=0, distance=10, baseTime=5, fuelCost=5, difficulty=1, directed=True))

    # Spur 1 -> 99 (one-way into dead end)
    g.add_edge(Edge(id=4, from_node=1, to_node=99, distance=5, baseTime=2, fuelCost=2, difficulty=1, directed=True))

    dead_ends = find_dead_ends(g, finish_vertex=0)
    assert 99 in dead_ends


def test_st_example_bfs_minimizes_edges_not_distance():
    """Statement requirement: S-T example.

    Direct edge S->T of length 10 vs S-A-B-T with 3 edges of length 2 each.
    Total distance S-T is 10; total distance S-A-B-T is 6.
    BFS MUST pick direct path [S, T] because it has fewer edges (1 edge vs 3 edges).
    """
    g = Graph()
    # S=0, A=1, B=2, T=3
    g.add_vertex(Vertex(id=0, x=0, y=0))
    g.add_vertex(Vertex(id=1, x=2, y=1))
    g.add_vertex(Vertex(id=2, x=4, y=1))
    g.add_vertex(Vertex(id=3, x=10, y=0))

    # Long direct edge S -> T (1 edge, dist=10)
    g.add_edge(Edge(id=1, from_node=0, to_node=3, distance=10.0, baseTime=10.0, fuelCost=10.0, difficulty=1))
    # Detour S -> A -> B -> T (3 edges, total dist=6)
    g.add_edge(Edge(id=2, from_node=0, to_node=1, distance=2.0, baseTime=2.0, fuelCost=2.0, difficulty=1))
    g.add_edge(Edge(id=3, from_node=1, to_node=2, distance=2.0, baseTime=2.0, fuelCost=2.0, difficulty=1))
    g.add_edge(Edge(id=4, from_node=2, to_node=3, distance=2.0, baseTime=2.0, fuelCost=2.0, difficulty=1))

    _, _, path = bfs(g, src=0, dst=3)
    assert path == [0, 3], f"BFS should have chosen [0, 3] with 1 edge, but chose {path}"


def test_bfs_vs_brute_force_random_graphs():
    """Verify BFS min-edge count matches brute-force search on random graphs."""
    rng = random.Random(42)

    for trial in range(10):
        num_v = rng.randint(5, 12)
        g = Graph()
        for i in range(num_v):
            g.add_vertex(Vertex(id=i, x=float(i), y=float(i)))

        edge_id = 1
        for u in range(num_v):
            for v in range(u + 1, num_v):
                if rng.random() < 0.35:
                    g.add_edge(Edge(id=edge_id, from_node=u, to_node=v,
                                    distance=rng.uniform(1.0, 20.0),
                                    baseTime=rng.uniform(1.0, 10.0),
                                    fuelCost=rng.uniform(1.0, 10.0),
                                    difficulty=rng.randint(1, 5)))
                    edge_id += 1

        src, dst = 0, num_v - 1

        # BFS result
        _, _, bfs_path = bfs(g, src=src, dst=dst)

        # Brute-force all simple paths to find min edge count
        all_paths: List[List[int]] = []

        def _find_all(curr: int, path: List[int], visited: set):
            if curr == dst:
                all_paths.append(list(path))
                return
            for nxt, _ in g.neighbors(curr):
                if nxt not in visited:
                    visited.add(nxt)
                    path.append(nxt)
                    _find_all(nxt, path, visited)
                    path.pop()
                    visited.remove(nxt)

        _find_all(src, [src], {src})

        if not all_paths:
            assert bfs_path is None
        else:
            min_hops = min(len(p) - 1 for p in all_paths)
            assert bfs_path is not None
            assert len(bfs_path) - 1 == min_hops


def test_circuit1_presets_pick_different_routes():
    """Verify Circuit 1: Speed, Economy, and Safety presets pick different routes."""
    circuit1_path = os.path.join(os.path.dirname(__file__), "..", "data", "circuits", "circuit1.json")
    graph = load_circuit_from_json(circuit1_path)
    ref = CircuitReferenceValues.from_graph(graph)

    # 3 branches between Start (0) and CP1 (1):
    # Branch 1 via 16 (Speed): fast time, high fuel, diff 4
    # Branch 2 via 17 (Economy): low fuel, slow time, diff 2
    # Branch 3 via 18 (Safety): diff 1, moderate time/fuel

    def branch_cost(mid_node: int, preset: str) -> float:
        e1 = graph.find_edge(0, mid_node)
        e2 = graph.find_edge(mid_node, 1)
        assert e1 is not None and e2 is not None
        return edge_cost(e1, preset=preset, ref=ref) + edge_cost(e2, preset=preset, ref=ref)

    # Under Speed preset, branch 16 must be cheapest
    cost_speed_16 = branch_cost(16, "Speed")
    cost_speed_17 = branch_cost(17, "Speed")
    cost_speed_18 = branch_cost(18, "Speed")
    assert cost_speed_16 < cost_speed_17 and cost_speed_16 < cost_speed_18

    # Under Economy preset, branch 17 must be cheapest
    cost_eco_16 = branch_cost(16, "Economy")
    cost_eco_17 = branch_cost(17, "Economy")
    cost_eco_18 = branch_cost(18, "Economy")
    assert cost_eco_17 < cost_eco_16 and cost_eco_17 < cost_eco_18

    # Under Safety preset, branch 18 must be cheapest
    cost_safe_16 = branch_cost(16, "Safety")
    cost_safe_17 = branch_cost(17, "Safety")
    cost_safe_18 = branch_cost(18, "Safety")
    assert cost_safe_18 < cost_safe_16 and cost_safe_18 < cost_safe_17
