"""Deterministic Computer Opponents for Smart Racing Championship.

Implements three distinct deterministic AI strategies:
  1. FixedRouteOpponent: Follows primary circuit line with documented fixed detour.
  2. ShortcutFirstOpponent: Aggressively seeks shortcuts, falling back to main route.
  3. MinDistanceOpponent: Recomputes minimum-distance paths dynamically.

All opponents obey identical simulation rules to human racers and use the same Planner API.
"""

from typing import List, Optional, Dict, Any
from core.models import Racer, Vertex
from core.graph import Graph
from core.cost import CircuitReferenceValues
import core.config as cfg
from engine.planner import plan_route, get_ordered_checkpoints, get_finish_vertex
from algos.dijkstra import dijkstra


class FixedRouteOpponent:
    """Opponent 1: Follows the fixed primary circuit line with documented fixed detour.

    Refuels at the first eligible station when fuel <= 25%.
    """

    def __init__(self, racer_id: int = 2, name: str = "Detour Dominator"):
        self.racer = Racer(
            id=racer_id,
            name=name,
            preset="Balanced",
            strategy="fixed_detour",
            current_vertex=0,
            fuel=cfg.MAX_FUEL,
            nitro_charges=cfg.MAX_NITRO_CHARGES,
        )

    def plan(self, graph: Graph) -> Optional[List[int]]:
        result = plan_route(graph, self.racer, preset="Balanced", algorithm="dijkstra")
        if result is not None:
            self.racer.planned_route = result["path"]
            return result["path"]
        return None

    def check_refuel(self, graph: Graph) -> Optional[int]:
        """Return station vertex ID if refuelling is required (fuel <= 25%)."""
        if self.racer.fuel <= cfg.OPPONENT_REFUEL_THRESHOLD:
            for vid in self.racer.planned_route:
                v = graph.vertices.get(vid)
                if v and v.type == "station" and v.active:
                    return vid
        return None


class ShortcutFirstOpponent:
    """Opponent 2: Aggressively takes shortcuts whenever open; falls back to main line.

    Refuels at first eligible station when fuel <= 25%.
    """

    def __init__(self, racer_id: int = 3, name: str = "Shortcut Specialist"):
        self.racer = Racer(
            id=racer_id,
            name=name,
            preset="Speed",
            strategy="shortcut_fallback",
            current_vertex=0,
            fuel=cfg.MAX_FUEL,
            nitro_charges=cfg.MAX_NITRO_CHARGES,
        )

    def plan(self, graph: Graph) -> Optional[List[int]]:
        # Uses Speed preset to prioritize fast shortcuts
        result = plan_route(graph, self.racer, preset="Speed", algorithm="astar")
        if result is not None:
            self.racer.planned_route = result["path"]
            return result["path"]
        # Fallback to balanced if speed route fails
        fallback = plan_route(graph, self.racer, preset="Balanced", algorithm="dijkstra")
        if fallback is not None:
            self.racer.planned_route = fallback["path"]
            return fallback["path"]
        return None

    def check_refuel(self, graph: Graph) -> Optional[int]:
        if self.racer.fuel <= cfg.OPPONENT_REFUEL_THRESHOLD:
            for vid in self.racer.planned_route:
                v = graph.vertices.get(vid)
                if v and v.type == "station" and v.active:
                    return vid
        return None


class MinDistanceOpponent:
    """Opponent 3: Dynamically plans minimum total distance path with recompute.

    Refuels at the nearest reachable station on route when fuel <= 25%.
    """

    def __init__(self, racer_id: int = 4, name: str = "Metric Min-Dist"):
        self.racer = Racer(
            id=racer_id,
            name=name,
            preset="Economy",
            strategy="min_distance_recompute",
            current_vertex=0,
            fuel=cfg.MAX_FUEL,
            nitro_charges=cfg.MAX_NITRO_CHARGES,
        )

    def plan(self, graph: Graph) -> Optional[List[int]]:
        result = plan_route(graph, self.racer, preset="Economy", algorithm="dijkstra")
        if result is not None:
            self.racer.planned_route = result["path"]
            return result["path"]
        return None

    def check_refuel(self, graph: Graph) -> Optional[int]:
        if self.racer.fuel <= cfg.OPPONENT_REFUEL_THRESHOLD:
            # Find nearest reachable station along the planned route
            for vid in self.racer.planned_route:
                v = graph.vertices.get(vid)
                if v and v.type == "station" and v.active:
                    return vid
        return None


def create_standard_opponents() -> List[Racer]:
    """Factory creating the 3 mandatory deterministic computer opponents."""
    bot1 = FixedRouteOpponent(racer_id=2, name="Bot 1 (Apex Cruiser)")
    bot2 = ShortcutFirstOpponent(racer_id=3, name="Bot 2 (Velocity Nitro)")
    bot3 = MinDistanceOpponent(racer_id=4, name="Bot 3 (Eco Optimizer)")
    return [bot1.racer, bot2.racer, bot3.racer]
