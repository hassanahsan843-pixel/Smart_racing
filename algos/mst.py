"""Minimum Spanning Tree (MST) using Kruskal's algorithm and Union-Find.

Uses path compression and union by rank. Used in procedural circuit generation
to guarantee foundational connectivity before cycles and shortcuts are added.
"""

from typing import Dict, List, Tuple, Optional
from core.models import Vertex, Edge
from core.counters import OpCounters


class UnionFind:
    """Disjoint-set data structure with path compression and union by rank."""

    def __init__(self, elements: List[int]):
        self.parent: Dict[int, int] = {x: x for x in elements}
        self.rank: Dict[int, int] = {x: 0 for x in elements}
        self.num_sets: int = len(elements)

    def find(self, x: int) -> int:
        """Find representative with path compression."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        """Union two sets by rank. Returns True if sets were merged, False if already in same set."""
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return False

        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

        self.num_sets -= 1
        return True


def kruskal(vertices: List[Vertex], candidate_edges: List[Edge],
            counters: Optional[OpCounters] = None) -> Tuple[List[Edge], bool, float]:
    """Kruskal's algorithm for Minimum Spanning Tree / Forest.

    Complexity:
      - Time: O(E log E) sorting + O(E * alpha(V)) union-find operations.
      - Space: O(V + E)
    Correctness Idea:
      By the Cut Property of MSTs, the minimum-weight edge crossing any cut in a connected
      graph is always part of some MST. Kruskal greedily adds the cheapest available
      edge that does not form a cycle, guaranteeing an optimal spanning tree or forest.
    Returns:
      (mst_edges, is_connected_tree, total_weight)
    """
    if counters is None:
        counters = OpCounters()

    if not vertices:
        return [], True, 0.0

    # Deterministic sort by edge distance, breaking ties by lower edge ID
    # Counts comparisons
    def sort_key(edge: Edge) -> Tuple[float, int]:
        return (edge.distance, edge.id)

    sorted_edges = list(candidate_edges)
    sorted_edges.sort(key=sort_key)
    counters.comparisons += len(sorted_edges) * 2  # approximate O(E log E) comparisons

    vertex_ids = [v.id for v in vertices]
    uf = UnionFind(vertex_ids)

    mst_edges: List[Edge] = []
    total_weight = 0.0

    for edge in sorted_edges:
        counters.examined_edges += 1
        u, v = edge.from_node, edge.to_node
        if u not in uf.parent or v not in uf.parent:
            continue

        if uf.union(u, v):
            mst_edges.append(edge)
            total_weight += edge.distance
            if len(mst_edges) == len(vertices) - 1:
                break

    # If number of sets is 1, candidate graph was fully connected and forms a single tree.
    # Otherwise, it forms a spanning forest.
    is_connected = (uf.num_sets == 1) or (len(vertices) <= 1)
    return mst_edges, is_connected, total_weight
