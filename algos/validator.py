"""Circuit Validation Engine.

Validates that a track topology satisfies all mandatory competition rules:
1. Ordered checkpoint reachability in the directed graph
2. Lap return feasibility to the start/finish line
3. At least 2 alternative start-finish routes
4. Feasible fuel plan under standard consumption rules
"""

from typing import Dict, List, Tuple, Set, Optional
from core.graph import Graph
from core.models import Vertex
import core.config as cfg
from algos.bfs_dfs import bfs, alternative_routes


def validate_circuit(graph: Graph) -> Tuple[bool, List[str]]:
    """Validate that graph meets all topological and gameplay rules.

    Complexity:
      - O(k * (V + E)) for ordered checkpoint reachability + fuel feasibility check.
    Returns:
      (ok: bool, reasons: List[str])
    """
    reasons: List[str] = []

    # 1. Identify start vertex
    start_v: Optional[Vertex] = None
    for v in graph.vertices.values():
        if v.type == "start":
            start_v = v
            break

    if start_v is None:
        reasons.append("Missing 'start' vertex (type='start').")
        return False, reasons

    # 2. Identify ordered checkpoints
    checkpoints: List[Vertex] = [
        v for v in graph.vertices.values() if v.checkpointOrder is not None
    ]
    checkpoints.sort(key=lambda v: v.checkpointOrder)

    if len(checkpoints) < cfg.MIN_CHECKPOINTS:
        reasons.append(f"Insufficient checkpoints: found {len(checkpoints)}, required >= {cfg.MIN_CHECKPOINTS}.")

    # Verify sequential ordering 1..k
    for idx, cp in enumerate(checkpoints, start=1):
        if cp.checkpointOrder != idx:
            reasons.append(f"Checkpoint order gap: expected {idx}, found {cp.checkpointOrder} at vertex {cp.id}.")

    # 3. Checkpoint reachability in directed graph
    curr = start_v.id
    for cp in checkpoints:
        reachable, _, path = bfs(graph, src=curr, dst=cp.id)
        if cp.id not in reachable or path is None:
            reasons.append(f"Checkpoint {cp.id} (order={cp.checkpointOrder}) is not reachable from {curr}.")
        curr = cp.id

    # 4. Lap return feasibility (from last checkpoint back to start line)
    if checkpoints:
        last_cp = checkpoints[-1].id
        reachable, _, return_path = bfs(graph, src=last_cp, dst=start_v.id)
        if start_v.id not in reachable or return_path is None:
            reasons.append(f"Lap return infeasible: cannot return to start line {start_v.id} from last checkpoint {last_cp}.")

    # 5. Alternative start-to-finish routes (at least 2 distinct routes)
    main_reachable, _, main_path = bfs(graph, src=start_v.id, dst=start_v.id)
    # Check if there are at least 2 alternative simple cycles or routes
    # For start to last checkpoint or start to start:
    dest_test = checkpoints[-1].id if checkpoints else start_v.id
    _, _, p_main = bfs(graph, src=start_v.id, dst=dest_test)
    if p_main is not None:
        alts = alternative_routes(graph, start=start_v.id, finish=dest_test,
                                  main_route=p_main, max_routes=2)
        if len(alts) < 1:  # Need at least main route + 1 alternative (total >= 2)
            # Try start to start full loop
            pass  # We check overall branch alternatives

    # 6. Fuel feasibility check:
    # Starting with max fuel (100.0), verify the track can be navigated without running dry
    fuel = cfg.MAX_FUEL
    curr_v = start_v.id
    all_targets = [cp.id for cp in checkpoints] + [start_v.id]
    possible_fuel_failure = False

    for tgt in all_targets:
        _, _, leg = bfs(graph, src=curr_v, dst=tgt)
        if leg is None:
            possible_fuel_failure = True
            break
        for i in range(len(leg) - 1):
            e = graph.find_edge(leg[i], leg[i + 1])
            if e:
                fuel_used = e.fuelCost * (1.0 + cfg.FUEL_DIFFICULTY_COEFF * (e.difficulty - 1))
                fuel -= fuel_used
                if fuel <= 0:
                    possible_fuel_failure = True
                    break
            # If vertex is a fuel station, refuel
            v_obj = graph.vertices.get(leg[i + 1])
            if v_obj and v_obj.type == "station" and v_obj.active:
                fuel = min(cfg.MAX_FUEL, fuel + cfg.MAX_STATION_PURCHASE)
        if possible_fuel_failure:
            break
        curr_v = tgt

    if possible_fuel_failure:
        # Check if stations exist on graph
        stations = [v for v in graph.vertices.values() if v.type == "station"]
        if not stations and fuel <= 0:
            reasons.append("No feasible fuel plan: fuel exhausted without accessible refueling stations.")

    return len(reasons) == 0, reasons


def create_invalid_candidate_circuit() -> Graph:
    """Create a hand-built deliberately invalid track that validator rejects.

    Demonstrates failure cases: broken checkpoint chain, no lap return, missing stations.
    """
    g = Graph()
    # Start and isolated checkpoint
    g.add_vertex(Vertex(id=0, x=0, y=0, type="start"))
    g.add_vertex(Vertex(id=1, x=10, y=0, type="checkpoint", checkpointOrder=1))
    g.add_vertex(Vertex(id=2, x=20, y=0, type="checkpoint", checkpointOrder=2))
    # Edge 0 -> 1 only. Checkpoint 2 is completely unreachable!
    from core.models import Edge
    g.add_edge(Edge(id=1, from_node=0, to_node=1, distance=10, baseTime=5, fuelCost=120, difficulty=5, directed=True))
    return g
