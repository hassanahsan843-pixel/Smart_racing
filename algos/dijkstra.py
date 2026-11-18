"""Dijkstra's shortest path algorithm with binary min-heap.

Computes the path with minimum normalized scalar cost from source to destination.
Supports operation counting and interactive step tracing for the Algorithm Lab.
"""

import heapq
from typing import Dict, List, Tuple, Optional
from core.graph import Graph
from core.cost import CircuitReferenceValues, edge_cost, calculate_effective_time
from core.counters import OpCounters, StepCallback


def dijkstra(graph: Graph, src: int, dst: int,
             preset: str = "Balanced",
             ref: Optional[CircuitReferenceValues] = None,
             counters: Optional[OpCounters] = None,
             on_step: StepCallback = None) -> Tuple[Optional[List[int]], float, float, float]:
    """Find the minimum scalar cost path from src to dst using Dijkstra's algorithm.

    Complexity:
      - Time: O((V + E) log V) with binary heap
      - Space: O(V) for heap and dist/parent tables.
    Correctness Idea:
      Because all edge costs are strictly non-negative (cost(e) >= 0), when a vertex u
      is extracted from the min-heap with minimal distance d[u], no future relaxation
      through unvisited vertices can produce a shorter path to u (subpath optimality).
    Returns:
      (path, total_cost, total_distance, total_time)
      or (None, inf, inf, inf) if unreachable.
    """
    if counters is None:
        counters = OpCounters()

    if ref is None:
        ref = CircuitReferenceValues.from_graph(graph)

    # Edge case: source equals destination
    if src == dst:
        return [src], 0.0, 0.0, 0.0

    if src not in graph.vertices or dst not in graph.vertices:
        return None, float("inf"), float("inf"), float("inf")

    dist: Dict[int, float] = {src: 0.0}
    parent: Dict[int, Tuple[int, Any]] = {}
    visited: set = set()

    # Heap contains (current_cost, vertex_id)
    # Tie-breaks deterministically by vertex_id
    heap: List[Tuple[float, int]] = [(0.0, src)]
    counters.heap_pushes += 1

    if on_step:
        on_step({"action": "dijkstra_init", "src": src, "dst": dst, "heap_size": 1})

    while heap:
        d_u, u = heapq.heappop(heap)
        counters.heap_pops += 1

        # Skip stale heap entries (lazy deletion)
        if u in visited or d_u > dist.get(u, float("inf")):
            continue

        visited.add(u)
        counters.visited_vertices += 1

        if on_step:
            on_step({"action": "dijkstra_expand", "u": u, "cost": d_u,
                     "visited_count": len(visited)})

        if u == dst:
            break

        for v, edge in graph.neighbors(u):
            counters.examined_edges += 1
            w = edge_cost(edge, preset=preset, ref=ref)
            new_cost = d_u + w

            if new_cost < dist.get(v, float("inf")):
                dist[v] = new_cost
                parent[v] = (u, edge)
                heapq.heappush(heap, (new_cost, v))
                counters.heap_pushes += 1
                counters.relaxations += 1

                if on_step:
                    on_step({"action": "dijkstra_relax", "from": u, "to": v,
                             "new_cost": new_cost, "edge_id": edge.id})

    if dst not in dist:
        return None, float("inf"), float("inf"), float("inf")

    # Reconstruct path and compute metric totals
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

    total_cost = dist[dst]
    total_dist = sum(e.distance for e in edges_traversed)
    total_time = sum(calculate_effective_time(e) for e in edges_traversed)

    return path, total_cost, total_dist, total_time
