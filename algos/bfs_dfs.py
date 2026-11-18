"""Breadth-First Search (BFS) and Depth-First Search (DFS) algorithms.

Includes reachability, min-hop paths, cycle detection, connected components,
dead-end identification, and bounded alternative route enumeration.
All routines accept `counters` (OpCounters) and `on_step` callbacks.
"""

from collections import deque
from typing import Dict, List, Set, Tuple, Optional, Any
from core.graph import Graph
from core.counters import OpCounters, StepCallback


def bfs(graph: Graph, src: int, dst: Optional[int] = None,
        counters: Optional[OpCounters] = None,
        on_step: StepCallback = None) -> Tuple[Set[int], Dict[int, Optional[int]], Optional[List[int]]]:
    """Breadth-First Search from source vertex.

    Complexity:
      - Time: O(V + E)
      - Space: O(V) for queue, visited set, and parent map.
    Correctness Idea:
      BFS explores vertices in non-decreasing order of edge count (hops) from `src`.
      Because each edge contributes exactly 1 hop to path length, the first time `dst`
      is discovered, the path stored in `parent` is guaranteed to have the minimum
      number of edges, regardless of edge distance or time weights.
    """
    if counters is None:
        counters = OpCounters()

    visited: Set[int] = set()
    parent: Dict[int, Optional[int]] = {src: None}
    queue: deque[int] = deque([src])
    visited.add(src)
    counters.visited_vertices += 1

    if on_step:
        on_step({"action": "bfs_start", "current": src, "visited": set(visited), "queue": list(queue)})

    reached = False
    while queue:
        u = queue.popleft()

        if dst is not None and u == dst:
            reached = True
            break

        for v, edge in graph.neighbors(u):
            counters.examined_edges += 1
            if v not in visited:
                visited.add(v)
                parent[v] = u
                counters.visited_vertices += 1
                queue.append(v)
                if on_step:
                    on_step({"action": "bfs_visit", "from": u, "to": v, "edge": edge.id,
                             "visited": set(visited), "queue": list(queue)})

    min_edge_path: Optional[List[int]] = None
    if dst is not None and (reached or dst in visited):
        path: List[int] = []
        curr: Optional[int] = dst
        while curr is not None:
            path.append(curr)
            curr = parent.get(curr)
        path.reverse()
        min_edge_path = path

    return visited, parent, min_edge_path


def dfs_traverse(graph: Graph, src: int,
                 counters: Optional[OpCounters] = None,
                 on_step: StepCallback = None) -> List[int]:
    """Depth-First Search traversal returning the vertex discovery order.

    Complexity:
      - Time: O(V + E)
      - Space: O(V) recursion/call stack.
    Correctness Idea:
      Follows each path as deep as possible before backtracking, visiting every
      reachable vertex in the component.
    """
    if counters is None:
        counters = OpCounters()

    visited: Set[int] = set()
    traversal_order: List[int] = []

    def _dfs(u: int) -> None:
        visited.add(u)
        traversal_order.append(u)
        counters.visited_vertices += 1
        if on_step:
            on_step({"action": "dfs_visit", "current": u, "order": list(traversal_order)})

        for v, edge in graph.neighbors(u):
            counters.examined_edges += 1
            if v not in visited:
                _dfs(v)

    if src in graph.vertices:
        _dfs(src)

    return traversal_order


def detect_cycle(graph: Graph,
                 counters: Optional[OpCounters] = None,
                 on_step: StepCallback = None) -> Tuple[bool, List[int]]:
    """Detect if the graph contains any cycle using 3-color DFS.

    Colors:
      0 = UNVISITED (White)
      1 = VISITING / in active recursion stack (Gray)
      2 = VISITED / finished (Black)

    Complexity:
      - Time: O(V + E)
      - Space: O(V)
    Correctness Idea:
      A back-edge pointing to a vertex currently in the active recursion call stack (Gray)
      proves the existence of a directed or undirected cycle.
    """
    if counters is None:
        counters = OpCounters()

    color: Dict[int, int] = {v: 0 for v in graph.vertices}
    parent: Dict[int, Optional[int]] = {v: None for v in graph.vertices}
    cycle_nodes: List[int] = []

    def _dfs_cycle(u: int) -> bool:
        color[u] = 1  # Gray
        counters.visited_vertices += 1

        for v, edge in graph.neighbors(u):
            counters.examined_edges += 1
            if color[v] == 1:
                # Cycle found! If undirected edge directly to parent, ignore trivial back-link
                if not edge.directed and parent[u] == v:
                    continue
                # Reconstruct cycle path
                cycle_nodes.append(v)
                curr = u
                while curr is not None and curr != v:
                    cycle_nodes.append(curr)
                    curr = parent.get(curr)
                cycle_nodes.append(v)
                cycle_nodes.reverse()
                return True

            elif color[v] == 0:
                parent[v] = u
                if _dfs_cycle(v):
                    return True

        color[u] = 2  # Black
        return False

    for vertex_id in sorted(graph.vertices.keys()):
        if color[vertex_id] == 0:
            if _dfs_cycle(vertex_id):
                return True, cycle_nodes

    return False, []


def connected_components(graph: Graph,
                         counters: Optional[OpCounters] = None,
                         on_step: StepCallback = None) -> List[Set[int]]:
    """Compute connected components of the graph (considering traversable non-blocked edges).

    Complexity:
      - Time: O(V + E)
      - Space: O(V)
    """
    if counters is None:
        counters = OpCounters()

    visited: Set[int] = set()
    components: List[Set[int]] = []

    for vertex_id in sorted(graph.vertices.keys()):
        if vertex_id not in visited:
            comp: Set[int] = set()
            queue = deque([vertex_id])
            visited.add(vertex_id)
            comp.add(vertex_id)
            counters.visited_vertices += 1

            while queue:
                u = queue.popleft()
                for v, _ in graph.neighbors(u):
                    counters.examined_edges += 1
                    if v not in visited:
                        visited.add(v)
                        comp.add(v)
                        counters.visited_vertices += 1
                        queue.append(v)

            components.append(comp)

    return components


def find_dead_ends(graph: Graph, finish_vertex: int = 0,
                   counters: Optional[OpCounters] = None,
                   on_step: StepCallback = None) -> List[int]:
    """Find non-mandatory vertices from which the finish cannot be reached without reversing.

    Dead ends represent tactical traps or dead-end spurs on the circuit.

    Complexity:
      - Time: O(V + E)
      - Space: O(V)
    """
    if counters is None:
        counters = OpCounters()

    dead_ends: List[int] = []

    for vid, v in graph.vertices.items():
        # Checkpoint and start nodes are mandatory race vertices, not dead ends
        if v.type in ("start", "checkpoint") or v.checkpointOrder is not None:
            continue

        # Check reachability to finish_vertex from vid
        reachable, _, _ = bfs(graph, src=vid, dst=finish_vertex, counters=counters)
        if finish_vertex not in reachable:
            dead_ends.append(vid)

    return sorted(dead_ends)


def alternative_routes(graph: Graph, start: int, finish: int,
                       main_route: List[int],
                       max_routes: int = 5,
                       max_len: int = 30,
                       counters: Optional[OpCounters] = None,
                       on_step: StepCallback = None) -> List[List[int]]:
    """Bounded enumeration of simple alternative paths between start and finish.

    Bounded by max_routes and max_len to prevent combinatorial explosion.
    Must differ from main_route by at least one edge.

    Complexity:
      - Time: O(max_routes * max_len * deg_max) bounded
      - Space: O(max_len)
    """
    if counters is None:
        counters = OpCounters()

    main_edge_set = set()
    if len(main_route) >= 2:
        for i in range(len(main_route) - 1):
            main_edge_set.add((main_route[i], main_route[i + 1]))

    routes: List[List[int]] = []

    def _backtrack(curr: int, path: List[int], visited: Set[int]) -> None:
        if len(routes) >= max_routes:
            return
        if len(path) > max_len:
            return

        if curr == finish:
            # Check if this route differs from main route by at least one edge
            differs = False
            if len(path) != len(main_route):
                differs = True
            else:
                for i in range(len(path) - 1):
                    if (path[i], path[i + 1]) not in main_edge_set:
                        differs = True
                        break

            if differs and path not in routes:
                routes.append(list(path))
            return

        for nxt, edge in graph.neighbors(curr):
            counters.examined_edges += 1
            if nxt not in visited:
                visited.add(nxt)
                path.append(nxt)
                counters.visited_vertices += 1

                _backtrack(nxt, path, visited)

                path.pop()
                visited.remove(nxt)

                if len(routes) >= max_routes:
                    return

    _backtrack(start, [start], {start})
    return routes
