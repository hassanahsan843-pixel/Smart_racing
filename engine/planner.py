"""Route Planner and Checkpoint Sequence Chainer.

Plans complete racer paths by chaining optimal legs through mandatory checkpoints
in strictly ascending order: current_vertex -> next_cp -> ... -> CP_k -> finish.
Guarantees checkpoints cannot be skipped.
"""

from typing import Dict, List, Tuple, Optional, Any
from core.graph import Graph
from core.models import Racer, Vertex
from core.cost import CircuitReferenceValues
import core.config as cfg
from algos.astar import astar
from algos.dijkstra import dijkstra


def get_ordered_checkpoints(graph: Graph) -> List[Vertex]:
    """Retrieve all mandatory checkpoints sorted strictly by checkpointOrder."""
    cps = [v for v in graph.vertices.values() if v.checkpointOrder is not None]
    cps.sort(key=lambda v: v.checkpointOrder)
    return cps


def get_finish_vertex(graph: Graph) -> int:
    """Identify the lap finish / start line vertex."""
    for v in graph.vertices.values():
        if v.type == "start":
            return v.id
    # Default fallback to vertex 0
    return 0


def plan_route(graph: Graph, racer: Racer, preset: Optional[str] = None,
               ref: Optional[CircuitReferenceValues] = None,
               algorithm: str = "astar") -> Optional[Dict[str, Any]]:
    """Chain shortest-path legs through ordered checkpoints.

    Current vertex -> CP_m -> CP_{m+1} -> ... -> CP_k -> Finish.

    Complexity:
      - O(k * (V + E) log V) where k is the number of remaining checkpoints.
    Returns:
      Dict with 'path', 'legs', 'total_cost', 'total_distance', 'total_time'
      or None if any mandatory leg is disconnected/unreachable.
    """
    if preset is None:
        preset = racer.preset
    if ref is None:
        ref = CircuitReferenceValues.from_graph(graph)

    ordered_cps = get_ordered_checkpoints(graph)
    finish_vid = get_finish_vertex(graph)

    # Determine remaining checkpoints to visit
    remaining_targets: List[int] = []

    # If fuel is critically low (<= 25%), find nearest active refueling station
    if racer.fuel <= 50.0:
        active_stations = [v.id for v in graph.vertices.values() if v.type == "station" and v.active]
        if active_stations:
            # Find nearest reachable station from current vertex
            routing_fn_temp = astar if algorithm == "astar" else dijkstra
            best_station = None
            best_cost = float("inf")
            for st_id in active_stations:
                st_path, st_cost, _, _ = routing_fn_temp(graph, src=racer.current_vertex, dst=st_id, preset=preset, ref=ref)
                if st_path is not None and st_cost < best_cost:
                    best_cost = st_cost
                    best_station = st_id
            if best_station is not None and best_station != racer.current_vertex:
                remaining_targets.append(best_station)

    for cp in ordered_cps:
        if cp.checkpointOrder is not None and cp.checkpointOrder >= racer.next_checkpoint_idx:
            remaining_targets.append(cp.id)

    # After last checkpoint, route to the finish line
    remaining_targets.append(finish_vid)

    full_path: List[int] = [racer.current_vertex]
    legs_info: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_distance = 0.0
    total_time = 0.0

    current_node = racer.current_vertex
    routing_fn = astar if algorithm == "astar" else dijkstra

    for target in remaining_targets:
        if current_node == target:
            continue

        leg_path, leg_cost, leg_dist, leg_time = routing_fn(
            graph, src=current_node, dst=target, preset=preset, ref=ref
        )

        if leg_path is None or len(leg_path) == 0:
            # Checkpoint is unreachable under current graph state
            return None

        legs_info.append({
            "from": current_node,
            "to": target,
            "path": leg_path,
            "cost": leg_cost,
            "distance": leg_dist,
            "time": leg_time,
        })

        total_cost += leg_cost
        total_distance += leg_dist
        total_time += leg_time

        # Append path vertices avoiding duplicate junction vertices
        full_path.extend(leg_path[1:])
        current_node = target

    return {
        "path": full_path,
        "legs": legs_info,
        "total_cost": total_cost,
        "total_distance": total_distance,
        "total_time": total_time,
    }


def replan(graph: Graph, racer: Racer, preset: Optional[str] = None,
           ref: Optional[CircuitReferenceValues] = None) -> bool:
    """Reroute a racer from its current position following dynamic graph changes.

    Updates racer.planned_route in-place.
    Returns True if a valid route was found, False if unreachable.
    """
    result = plan_route(graph, racer, preset=preset, ref=ref)
    if result is not None:
        racer.planned_route = result["path"]
        return True
    return False
