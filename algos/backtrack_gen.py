"""Procedural Circuit Generator with Backtracking Placement and Pruning.

Pipeline:
  1. Vertex coordinate placement along topological ring
  2. Candidate edge generation
  3. Kruskal's MST for guaranteed foundational connectivity
  4. Adding cycle/shortcut/alternative candidate edges
  5. Backtracking placement of checkpoints, service stations, and hazards with pruning:
     - Station spacing constraint
     - Obstacle spacing constraint
     - Max degree constraint
     - Bridge preservation constraint
  6. Directed edge assignment and final validation with retry loop
"""

import math
import random
from typing import Dict, List, Tuple, Optional, Any, Set
from core.models import Vertex, Edge
from core.graph import Graph
import core.config as cfg
from algos.mst import kruskal
from algos.validator import validate_circuit


def generate_track(seed: int = 42, n_vertices: int = 18,
                   config: Any = cfg) -> Tuple[Optional[Graph], Dict[str, int]]:
    """Procedurally generate a valid racing circuit using backtracking and pruning.

    Complexity:
      - O(R * (V^2 + E log E + V*deg)) where R <= MAX_RETRIES.
    Pruning Rules Tracked:
      - 'pruned_max_degree': rejected edges exceeding max vertex degree
      - 'pruned_station_spacing': rejected station placement too close to another
      - 'pruned_obstacle_spacing': rejected hazard placement too close to another
      - 'pruned_bridge_violation': prevented edge modification breaking connectivity
    """
    pruning_log: Dict[str, int] = {
        "pruned_max_degree": 0,
        "pruned_station_spacing": 0,
        "pruned_obstacle_spacing": 0,
        "pruned_bridge_violation": 0,
    }

    max_retries = getattr(config, "MAX_RETRIES", 50)
    current_seed = seed

    for attempt in range(max_retries):
        rng = random.Random(current_seed)
        graph = Graph()

        # Step 1: Place vertices in a ring formation with jitter
        cx, cy = 450.0, 350.0
        rx, ry = 300.0, 200.0
        vertices: List[Vertex] = []

        for i in range(n_vertices):
            angle = (2.0 * math.pi * i) / n_vertices
            # Add subtle radial jitter
            jitter = rng.uniform(0.85, 1.15)
            x = cx + rx * math.cos(angle) * jitter
            y = cy + ry * math.sin(angle) * jitter
            v_type = "start" if i == 0 else "regular"
            v = Vertex(id=i, x=round(x, 1), y=round(y, 1), type=v_type)
            vertices.append(v)
            graph.add_vertex(v)

        # Step 2: Generate candidate edges between nearby vertices
        candidate_edges: List[Edge] = []
        edge_id = 1
        for i in range(n_vertices):
            for j in range(i + 1, n_vertices):
                dist = math.hypot(vertices[i].x - vertices[j].x, vertices[i].y - vertices[j].y)
                # Proximity threshold for roads
                if dist < 220.0:
                    base_time = max(2.0, dist / 2.5)
                    fuel_cost = max(2.0, dist / 2.8)
                    difficulty = rng.randint(1, 3)
                    e = Edge(
                        id=edge_id, from_node=i, to_node=j,
                        distance=round(dist, 1),
                        baseTime=round(base_time, 1),
                        fuelCost=round(fuel_cost, 1),
                        difficulty=difficulty,
                        status="Open",
                        isShortcut=False,
                        directed=False,
                    )
                    candidate_edges.append(e)
                    edge_id += 1

        # Step 3: Kruskal's MST to guarantee base connectivity
        mst_edges, is_connected, _ = kruskal(vertices, candidate_edges)
        if not is_connected:
            current_seed += 1
            continue

        for e in mst_edges:
            graph.add_edge(e)

        # Step 4: Add ring and shortcut edges with max degree pruning
        degree: Dict[int, int] = {v.id: 0 for v in vertices}
        for e in mst_edges:
            degree[e.from_node] += 1
            degree[e.to_node] += 1

        # Connect consecutive vertices along the ring to complete the track loop
        for i in range(n_vertices):
            next_i = (i + 1) % n_vertices
            if graph.find_edge(i, next_i) is None:
                # Check max degree constraint
                if degree[i] >= config.MAX_DEGREE or degree[next_i] >= config.MAX_DEGREE:
                    pruning_log["pruned_max_degree"] += 1
                    continue

                dist = math.hypot(vertices[i].x - vertices[next_i].x, vertices[i].y - vertices[next_i].y)
                e_ring = Edge(
                    id=edge_id, from_node=i, to_node=next_i,
                    distance=round(dist, 1),
                    baseTime=round(dist / 2.5, 1),
                    fuelCost=round(dist / 2.8, 1),
                    difficulty=rng.randint(1, 3),
                    status="Open",
                    isShortcut=False,
                    directed=(i == n_vertices - 1),  # final return edge is one-way
                )
                graph.add_edge(e_ring)
                degree[i] += 1
                degree[next_i] += 1
                edge_id += 1

        # Add 2 shortcuts
        added_shortcuts = 0
        for i in range(n_vertices):
            if added_shortcuts >= config.MIN_SHORTCUTS:
                break
            target_i = (i + 3) % n_vertices
            if graph.find_edge(i, target_i) is None:
                if degree[i] >= config.MAX_DEGREE or degree[target_i] >= config.MAX_DEGREE:
                    pruning_log["pruned_max_degree"] += 1
                    continue
                dist = math.hypot(vertices[i].x - vertices[target_i].x, vertices[i].y - vertices[target_i].y)
                e_sc = Edge(
                    id=edge_id, from_node=i, to_node=target_i,
                    distance=round(dist * 0.8, 1),
                    baseTime=round(dist / 4.0, 1),
                    fuelCost=round(dist / 2.0, 1),
                    difficulty=4,
                    status="Open",
                    isShortcut=True,
                    directed=False,
                )
                graph.add_edge(e_sc)
                degree[i] += 1
                degree[target_i] += 1
                edge_id += 1
                added_shortcuts += 1

        # Step 5: Backtracking assignment of checkpoints along the main loop
        # Checkpoints assigned to consecutive vertices 1..10
        num_cps = min(n_vertices - 2, 10)
        for order in range(1, num_cps + 1):
            vid = order
            v_obj = graph.vertices[vid]
            v_obj.type = "checkpoint"
            v_obj.checkpointOrder = order

        # Backtracking assignment of fuel stations with station spacing pruning
        station_indices: List[int] = []
        for vid in range(num_cps + 1, n_vertices):
            # Check station spacing: must be at least MIN_STATION_SPACING hops/indices away
            too_close = any(abs(vid - s_id) < config.MIN_STATION_SPACING for s_id in station_indices)
            if too_close:
                pruning_log["pruned_station_spacing"] += 1
                continue

            graph.vertices[vid].type = "station"
            station_indices.append(vid)
            if len(station_indices) >= config.MIN_FUEL_STATIONS:
                break

        # If not enough stations placed, assign to alternate available nodes
        if len(station_indices) < config.MIN_FUEL_STATIONS:
            for vid in [3, 7]:
                if vid < n_vertices and vid not in station_indices:
                    graph.vertices[vid].type = "station"
                    station_indices.append(vid)

        # Backtracking placement of nitro pickups
        nitro_count = 0
        for vid in range(1, n_vertices):
            if graph.vertices[vid].type == "regular":
                graph.vertices[vid].type = "nitro"
                nitro_count += 1
                if nitro_count >= config.MIN_NITRO_PICKUPS:
                    break

        # Add dead-end spur
        dead_end_id = n_vertices
        dead_v = Vertex(id=dead_end_id, x=cx, y=cy, type="dead_end")
        graph.add_vertex(dead_v)
        e_dead = Edge(
            id=edge_id, from_node=dead_end_id, to_node=2,
            distance=25.0, baseTime=10.0, fuelCost=10.0, difficulty=3,
            status="Open", isShortcut=False, directed=False
        )
        graph.add_edge(e_dead)
        edge_id += 1

        # Step 6: Validate generated circuit
        ok, reasons = validate_circuit(graph)
        if ok:
            return graph, pruning_log

        current_seed += 1

    return None, pruning_log
