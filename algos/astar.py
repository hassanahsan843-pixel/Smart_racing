"""A* Search Algorithm with Admissible and Consistent Heuristic.

Finds the optimal path matching Dijkstra's cost while focusing the search
using a Euclidean-based lower-bound heuristic.
"""

import math
import heapq
from typing import Dict, List, Tuple, Optional, Any
from core.graph import Graph
from core.cost import CircuitReferenceValues, edge_cost, calculate_effective_time
from core.counters import OpCounters, StepCallback


def compute_min_cost_per_distance(graph: Graph, preset: str = "Balanced",
                                  ref: Optional[CircuitReferenceValues] = None) -> float:
    """Calculate the minimum ratio of scalar edge cost to geometric distance across all edges."""
    min_ratio = float("inf")
    for edge in graph.edges.values():
        if edge.distance > 0:
            c = edge_cost(edge, preset=preset, ref=ref)
            ratio = c / edge.distance
            if ratio < min_ratio:
                min_ratio = ratio

    if min_ratio == float("inf") or min_ratio < 0:
        return 0.0
    return min_ratio


def euclidean_distance(graph: Graph, u: int, v: int) -> float:
    """Compute straight-line Euclidean distance between two vertices."""
    v_u = graph.vertices.get(u)
    v_v = graph.vertices.get(v)
    if not v_u or not v_v:
        return 0.0
    return math.hypot(v_u.x - v_v.x, v_u.y - v_v.y)


def check_consistency(graph: Graph, preset: str = "Balanced",
                      ref: Optional[CircuitReferenceValues] = None) -> Tuple[bool, List[str]]:
    """Verify that heuristic satisfies triangle inequality h(u) <= cost(u, v) + h(v) for all edges."""
    min_ratio = compute_min_cost_per_distance(graph, preset=preset, ref=ref)
    violations: List[str] = []

    # Pick a dummy destination to verify consistency across the graph
    dest_candidates = list(graph.vertices.keys())
    if not dest_candidates:
        return True, []
    dst = dest_candidates[0]

    for u in graph.vertices:
        h_u = euclidean_distance(graph, u, dst) * min_ratio
        for v, edge in graph.neighbors(u):
            c_uv = edge_cost(edge, preset=preset, ref=ref)
            h_v = euclidean_distance(graph, v, dst) * min_ratio
            if h_u > c_uv + h_v + 1e-6:
                violations.append(f"Inconsistency at edge {u}->{v}: h(u)={h_u:.4f} > cost={c_uv:.4f} + h(v)={h_v:.4f}")

    return len(violations) == 0, violations


def astar(graph: Graph, src: int, dst: int,
          preset: str = "Balanced",
          ref: Optional[CircuitReferenceValues] = None,
          counters: Optional[OpCounters] = None,
          on_step: StepCallback = None) -> Tuple[Optional[List[int]], float, float, float]:
    """Find the minimum scalar cost path from src to dst using A* search.

    Complexity:
      - Worst-case Time: O((V + E) log V)
      - Space: O(V)
    Correctness Idea:
      The heuristic h(v) = euclid(v, dst) * min_cost_per_distance is a true lower bound
      on the remaining cost to dst because no path can travel faster/cheaper per unit
      distance than min_cost_per_distance, and no track distance can be shorter than straight line.
      Hence h is admissible and consistent, ensuring A* returns the optimal cost identical to Dijkstra.
    """
    if counters is None:
        counters = OpCounters()

    if ref is None:
        ref = CircuitReferenceValues.from_graph(graph)

    if src == dst:
        return [src], 0.0, 0.0, 0.0

    if src not in graph.vertices or dst not in graph.vertices:
        return None, float("inf"), float("inf"), float("inf")

    min_ratio = compute_min_cost_per_distance(graph, preset=preset, ref=ref)

    def h(v: int) -> float:
        return euclidean_distance(graph, v, dst) * min_ratio

    g_score: Dict[int, float] = {src: 0.0}
    parent: Dict[int, Tuple[int, Any]] = {}
    closed_set: set = set()

    # Heap contains (f_score, g_score, vertex_id)
    initial_f = h(src)
    heap: List[Tuple[float, float, int]] = [(initial_f, 0.0, src)]
    counters.heap_pushes += 1

    if on_step:
        on_step({"action": "astar_init", "src": src, "dst": dst, "f_score": initial_f})

    while heap:
        f_u, g_u, u = heapq.heappop(heap)
        counters.heap_pops += 1

        # Skip stale heap entries
        if g_u > g_score.get(u, float("inf")):
            continue

        if u in closed_set:
            continue

        closed_set.add(u)
        counters.visited_vertices += 1

        if on_step:
            on_step({"action": "astar_expand", "u": u, "g_score": g_u, "f_score": f_u})

        if u == dst:
            break

        for v, edge in graph.neighbors(u):
            counters.examined_edges += 1

            tentative_g = g_u + edge_cost(edge, preset=preset, ref=ref)

            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                f_v = tentative_g + h(v)
                parent[v] = (u, edge)
                # If v was previously closed, reopen it to handle any inconsistent heuristic steps
                if v in closed_set:
                    closed_set.remove(v)

                heapq.heappush(heap, (f_v, tentative_g, v))
                counters.heap_pushes += 1
                counters.relaxations += 1

                if on_step:
                    on_step({"action": "astar_relax", "from": u, "to": v,
                             "g_score": tentative_g, "f_score": f_v, "edge_id": edge.id})

    if dst not in g_score:
        return None, float("inf"), float("inf"), float("inf")

    # Reconstruct path
    path: List[int] = []
    edges_traversed = []
    curr = dst
    while curr in parent:
        p_node, edge = parent[curr]
        path.append(curr)
        edges_traversed.append(edge)
        curr = p_node
    path.append(src)
    path.reverse()
    edges_traversed.reverse()

    total_cost = g_score[dst]
    total_dist = sum(e.distance for e in edges_traversed)
    total_time = sum(calculate_effective_time(e) for e in edges_traversed)

    return path, total_cost, total_dist, total_time
