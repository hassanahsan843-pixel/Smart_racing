"""Normalized scalar edge cost computation and preset evaluation.

Ensures that the cost evaluated by routing algorithms (Dijkstra, A*)
is identical to the cost presented to the user on GUI dashboards.
"""

from typing import Dict, Optional, List
import statistics
from core.models import Edge
from core.graph import Graph
from core.config import COST_PRESETS


class CircuitReferenceValues:
    """Stores reference normalizers computed from a circuit's edge metrics.

    Typically the median value of each metric across all edges in the circuit.
    """
    def __init__(self, d_ref: float = 1.0, t_ref: float = 1.0, f_ref: float = 1.0,
                 r_ref: float = 1.0, o_ref: float = 1.0):
        self.d_ref = max(d_ref, 1e-6)
        self.t_ref = max(t_ref, 1e-6)
        self.f_ref = max(f_ref, 1e-6)
        self.r_ref = max(r_ref, 1e-6)
        self.o_ref = max(o_ref, 1e-6)

    @classmethod
    def from_graph(cls, graph: Graph) -> "CircuitReferenceValues":
        """Compute reference values as the medians of edge attributes."""
        if not graph.edges:
            return cls()

        distances: List[float] = [e.distance for e in graph.edges.values()]
        times: List[float] = [e.baseTime for e in graph.edges.values()]
        fuels: List[float] = [e.fuelCost for e in graph.edges.values()]
        difficulties: List[float] = [float(e.difficulty) for e in graph.edges.values()]

        d_med = statistics.median(distances) if distances else 1.0
        t_med = statistics.median(times) if times else 1.0
        f_med = statistics.median(fuels) if fuels else 1.0
        r_med = statistics.median(difficulties) if difficulties else 1.0

        return cls(d_ref=d_med, t_ref=t_med, f_ref=f_med, r_ref=r_med, o_ref=1.0)


def calculate_effective_time(edge: Edge) -> float:
    """Calculate effective traversal time considering speed restrictions."""
    if edge.effective_speed_cap is not None and edge.effective_speed_cap > 0:
        base_speed = edge.distance / max(edge.baseTime, 1e-6)
        eff_speed = min(base_speed, edge.effective_speed_cap)
        return edge.distance / max(eff_speed, 1e-6)
    return edge.baseTime


def calculate_effective_difficulty(edge: Edge) -> int:
    """Calculate effective difficulty capped between 1 and 5."""
    return min(5, max(1, edge.difficulty + edge.effective_difficulty_penalty))


def edge_cost(edge: Edge, preset: str = "Balanced",
              ref: Optional[CircuitReferenceValues] = None) -> float:
    """Calculate scalar cost for an edge using normalized preset weights.

    Formula:
      cost(e) = w_d*(D/D_ref) + w_t*(T/T_ref) + w_f*(F/F_ref) + w_r*(R/R_ref) + w_o*(O/O_ref)

    Complexity: O(1)
    """
    if preset not in COST_PRESETS:
        preset = "Balanced"

    weights = COST_PRESETS[preset]
    w_d = weights["D"]
    w_t = weights["T"]
    w_f = weights["F"]
    w_r = weights["R"]
    w_o = weights["O"]

    # Invariant: weights must be non-negative and sum to 1.0
    assert w_d >= 0.0 and w_t >= 0.0 and w_f >= 0.0 and w_r >= 0.0 and w_o >= 0.0, "Weights must be non-negative"
    assert abs((w_d + w_t + w_f + w_r + w_o) - 1.0) < 1e-4, "Weights must sum to 1.0"

    if ref is None:
        ref = CircuitReferenceValues()

    d_val = edge.distance
    t_val = calculate_effective_time(edge)
    f_val = edge.fuelCost
    r_val = float(calculate_effective_difficulty(edge))
    o_val = 1.0 if edge.status == "Restricted" else 0.0

    cost = (
        w_d * (d_val / ref.d_ref)
        + w_t * (t_val / ref.t_ref)
        + w_f * (f_val / ref.f_ref)
        + w_r * (r_val / ref.r_ref)
        + w_o * (o_val / ref.o_ref)
    )

    return max(0.0, float(cost))
