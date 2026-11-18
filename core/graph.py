"""Graph representation with dynamic in-place updates.

Implements adjacency lists supporting directed and undirected edges,
in-place edge blocking/unblocking, service vertex activation toggling,
and independent overlapping active effects without graph rebuilds.
"""

from typing import Dict, List, Tuple, Optional, Any, Iterator
import copy
from core.models import Vertex, Edge
from core.config import OIL_SPILL_DIFFICULTY_PENALTY, OIL_SPILL_SPEED_CAP


class NeighborEdge:
    """Wrapper that behaves simultaneously as a 2-tuple (neighbor_id, edge)

    and as an Edge proxy oriented towards the neighbor vertex.
    This guarantees compatibility with both unpacked `for nxt, e in neighbors(v)`
    and direct `for e in neighbors(v): e.to_node`.
    """
    __slots__ = ("neighbor_id", "edge")

    def __init__(self, neighbor_id: int, edge: Edge):
        self.neighbor_id = neighbor_id
        self.edge = edge

    def __iter__(self):
        return iter((self.neighbor_id, self.edge))

    def __getitem__(self, index: int):
        return (self.neighbor_id, self.edge)[index]

    def __len__(self) -> int:
        return 2

    @property
    def target(self) -> int:
        return self.neighbor_id

    @property
    def to_node(self) -> int:
        return self.neighbor_id

    @property
    def to(self) -> int:
        return self.neighbor_id

    @property
    def u(self) -> int:
        return self.edge.u

    @property
    def v(self) -> int:
        return self.neighbor_id

    def __getattr__(self, name: str) -> Any:
        return getattr(self.edge, name)

    def __repr__(self) -> str:
        return f"NeighborEdge(to={self.neighbor_id}, edge_id={self.edge.id})"


class Graph:
    """Adjacency-list based dynamic graph.

    Complexity:
      - Space: O(V + E)
      - neighbors(v): O(deg(v))
      - block_edge / unblock_edge: O(1) in-place
      - add_effect / remove_effect: O(k) where k is active effects on that edge
    """

    def __init__(self):
        self.vertices: Dict[int, Vertex] = {}
        self.edges: Dict[int, Edge] = {}
        self.adj: Dict[int, List[Tuple[int, Edge]]] = {}
        self.edge_effects: Dict[int, Dict[str, Dict[str, Any]]] = {}
        self.base_statuses: Dict[int, str] = {}

    def add_vertex(self, vertex: Vertex) -> None:
        """Add a vertex to the graph."""
        self.vertices[vertex.id] = vertex
        if vertex.id not in self.adj:
            self.adj[vertex.id] = []

    def add_edge(self, edge: Edge) -> None:
        """Add an edge.

        Undirected edges are registered in both directions.
        Directed edges are registered only in the forward direction.
        """
        self.edges[edge.id] = edge
        self.base_statuses[edge.id] = edge.status
        self.edge_effects[edge.id] = {}

        u, v = edge.from_node, edge.to_node
        if u not in self.adj:
            self.adj[u] = []
        if v not in self.adj:
            self.adj[v] = []

        self.adj[u].append((v, edge))
        if not edge.directed:
            self.adj[v].append((u, edge))

    def neighbors(self, vertex_id: int) -> Iterator[NeighborEdge]:
        """Yield non-blocked edges connected to vertex_id.

        Skips any edge whose status is 'Blocked'.
        Restricted edges are yielded with their modified effective state.
        """
        if vertex_id not in self.adj:
            return

        for neighbor_id, edge in self.adj[vertex_id]:
            # If target vertex is inactive, treat edge as not traversable
            tgt_v = self.vertices.get(neighbor_id)
            if tgt_v and not tgt_v.active and tgt_v.type in ("station", "nitro"):
                # Notice: service vertices can have their service toggled active/inactive,
                # but track vertices themselves stay passable unless blocked.
                pass

            if edge.status != "Blocked":
                yield NeighborEdge(neighbor_id, edge)

    def block_edge(self, edge_id: int) -> None:
        """Mark an edge as Blocked in-place."""
        if edge_id in self.edges:
            self.edges[edge_id].status = "Blocked"

    def unblock_edge(self, edge_id: int) -> None:
        """Unblock an edge in-place and restore its effective state."""
        if edge_id in self.edges:
            edge = self.edges[edge_id]
            # Remove any explicit blockage effect if present
            if "blockage" in self.edge_effects.get(edge_id, {}):
                del self.edge_effects[edge_id]["blockage"]
            self.effective_edge_state(edge)

    def set_vertex_active(self, vertex_id: int, active: bool) -> None:
        """Toggle active state of a vertex (e.g. service station / nitro)."""
        if vertex_id in self.vertices:
            self.vertices[vertex_id].active = active

    def add_effect(self, edge_id: int, effect_id: str, effect: Dict[str, Any]) -> None:
        """Add an active effect to an edge and recompute its effective state.

        Never triggers a full graph rebuild.
        """
        if edge_id not in self.edges:
            return
        if edge_id not in self.edge_effects:
            self.edge_effects[edge_id] = {}
        self.edge_effects[edge_id][effect_id] = effect
        self.effective_edge_state(self.edges[edge_id])

    def remove_effect(self, edge_id: int, effect_id: str) -> None:
        """Remove an active effect and recompute effective state in-place."""
        if edge_id in self.edge_effects and effect_id in self.edge_effects[edge_id]:
            del self.edge_effects[edge_id][effect_id]
            if edge_id in self.edges:
                self.effective_edge_state(self.edges[edge_id])

    def effective_edge_state(self, edge: Edge) -> Edge:
        """Recompute effective difficulty, speed cap, and status from all active effects.

        Rules:
          - Strictest (minimum) speed cap.
          - Max difficulty penalty (difficulty capped at 5).
          - Status: Blocked if any effect causes blockage; else Restricted if any effect imposes restriction;
            otherwise base status.
        """
        effects = self.edge_effects.get(edge.id, {})
        base_status = self.base_statuses.get(edge.id, "Open")

        has_blockage = False
        has_restriction = False
        strictest_speed_cap: Optional[float] = None
        max_diff_penalty = 0

        for eff_id, eff in effects.items():
            eff_type = eff.get("type", "")
            if eff_type == "blockage" or eff.get("blocks", False):
                has_blockage = True

            diff_pen = eff.get("difficulty_penalty", 0)
            if eff_type == "oil_spill":
                diff_pen = max(diff_pen, OIL_SPILL_DIFFICULTY_PENALTY)
                has_restriction = True
                speed_cap = eff.get("speed_cap", OIL_SPILL_SPEED_CAP)
                if strictest_speed_cap is None or speed_cap < strictest_speed_cap:
                    strictest_speed_cap = speed_cap

            if eff_type == "speed_restriction":
                has_restriction = True
                speed_cap = eff.get("speed_cap", 15.0)
                if strictest_speed_cap is None or speed_cap < strictest_speed_cap:
                    strictest_speed_cap = speed_cap

            if diff_pen > max_diff_penalty:
                max_diff_penalty = diff_pen

        edge.effective_difficulty_penalty = max_diff_penalty
        edge.effective_speed_cap = strictest_speed_cap

        if has_blockage:
            edge.status = "Blocked"
        elif has_restriction or base_status == "Restricted":
            edge.status = "Restricted"
        else:
            edge.status = base_status

        return edge

    def get_edge(self, edge_id: int) -> Optional[Edge]:
        return self.edges.get(edge_id)

    def find_edge(self, u: int, v: int) -> Optional[Edge]:
        """Find the edge connecting u and v, if one exists."""
        if u in self.adj:
            for neighbor_id, edge in self.adj[u]:
                if neighbor_id == v:
                    return edge
        return None

    def clone(self) -> "Graph":
        """Create a deep copy of the graph for simulations or sandboxes."""
        return copy.deepcopy(self)
