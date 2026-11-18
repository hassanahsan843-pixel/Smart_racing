"""Headless Simulation Race Engine.

Executes a complete race simulation on a fixed dt=0.1s clock without GUI dependencies.
Enforces edge traversal physics, checkpoint verification, lap counting, nitro dynamics,
fuel consumption, in-flight event dispatching, dynamic rerouting, and DNF recovery timeouts.
"""

from typing import List, Dict, Optional, Any
import copy
from core.models import Racer, RaceResult, Edge, Event
from core.graph import Graph
from core.cost import CircuitReferenceValues, calculate_effective_time
import core.config as cfg
from algos.heap_events import EventQueue
from engine.effects import apply_event
from engine.planner import plan_route, replan, get_ordered_checkpoints, get_finish_vertex


class Race:
    """Headless simulation of a circuit race.

    Determinism:
      Uses seeded step progression and tie-breaking by lower racer ID.
    """

    def __init__(self, graph: Graph, racers: List[Racer],
                 config: Any = cfg,
                 seed: int = 42,
                 laps: int = cfg.CHAMPIONSHIP_LAPS,
                 event_queue: Optional[EventQueue] = None):
        self.graph: Graph = graph
        self.racers: List[Racer] = [copy.deepcopy(r) for r in racers]
        self.config: Any = config
        self.seed: int = seed
        self.target_laps: int = laps
        self.current_time: float = 0.0
        self.dt: float = getattr(config, "DT", 0.1)
        self.max_time: float = getattr(config, "MAX_SIM_TIME", 600.0)
        self.recovery_timeout: float = getattr(config, "RECOVERY_TIMEOUT", 60.0)

        self.ref_values = CircuitReferenceValues.from_graph(self.graph)
        self.ordered_cps = get_ordered_checkpoints(self.graph)
        self.finish_vid = get_finish_vertex(self.graph)
        self.total_checkpoints_per_lap = len(self.ordered_cps)

        self.event_queue: EventQueue = event_queue if event_queue is not None else EventQueue(graph=self.graph)
        self.event_log: List[str] = []

        # Initial path planning for all racers
        for racer in self.racers:
            racer.current_vertex = self.finish_vid
            racer.fuel = self.config.MAX_FUEL
            racer.nitro_charges = self.config.MAX_NITRO_CHARGES
            racer.next_checkpoint_idx = 1
            racer.lap = 1
            racer.lap_start_time = 0.0
            racer.fastest_lap = float("inf")
            racer.dnf = False
            racer.finished = False
            racer.waiting_time = 0.0
            racer.total_time = 0.0
            racer.edge_progress = 0.0
            racer.current_edge = None
            plan_res = plan_route(self.graph, racer, preset=racer.preset, ref=self.ref_values)
            if plan_res is not None:
                racer.planned_route = plan_res["path"]

    def step(self) -> None:
        """Advance simulation by dt seconds."""
        self.current_time += self.dt

        # 1. Process due events from EventQueue
        due_events = self.event_queue.pop_due(self.current_time)
        if due_events:
            for event in due_events:
                self.event_log.append(f"[{self.current_time:.1f}s] Event: {event.event_type} on {event.target_type} {event.target_id}")
                apply_event(self.graph, event, self.event_queue)

            # Replan any racer whose upcoming route is blocked
            for racer in self.racers:
                if racer.finished or racer.dnf:
                    continue
                # Check if route has blocked edges
                needs_replan = False
                for i in range(len(racer.planned_route) - 1):
                    u, v = racer.planned_route[i], racer.planned_route[i + 1]
                    e = self.graph.find_edge(u, v)
                    if e and e.status == "Blocked":
                        needs_replan = True
                        break

                if needs_replan:
                    ok = replan(self.graph, racer, preset=racer.preset, ref=self.ref_values)
                    if ok:
                        self.event_log.append(f"[{self.current_time:.1f}s] Racer {racer.id} successfully rerouted.")
                    else:
                        self.event_log.append(f"[{self.current_time:.1f}s] Racer {racer.id} found no route, waiting.")

        # 2. Advance each racer along its planned route
        for racer in self.racers:
            if racer.finished or racer.dnf:
                continue

            racer.total_time += self.dt

            # Handle pit stop timer
            if racer.current_pit_stop_timer > 0.0:
                racer.current_pit_stop_timer = max(0.0, racer.current_pit_stop_timer - self.dt)
                continue

            # Handle nitro timer
            nitro_active = False
            if racer.nitro_active_timer > 0.0:
                nitro_active = True
                racer.nitro_active_timer = max(0.0, racer.nitro_active_timer - self.dt)

            # Check if racer has a route
            if not racer.planned_route or len(racer.planned_route) < 2:
                # Try planning
                ok = replan(self.graph, racer, preset=racer.preset, ref=self.ref_values)
                if not ok:
                    racer.waiting_time += self.dt
                    if racer.waiting_time >= self.recovery_timeout:
                        racer.dnf = True
                        racer.finished = True
                        self.event_log.append(f"[{self.current_time:.1f}s] Racer {racer.id} declared DNF (waiting timeout).")
                    continue
                else:
                    racer.waiting_time = 0.0

            # Current edge to traverse
            u_node = racer.planned_route[0]
            v_node = racer.planned_route[1]
            edge = self.graph.find_edge(u_node, v_node)

            if edge is None or edge.status == "Blocked":
                # Route blocked: wait and retry replanning
                ok = replan(self.graph, racer, preset=racer.preset, ref=self.ref_values)
                if not ok:
                    racer.waiting_time += self.dt
                    if racer.waiting_time >= self.recovery_timeout:
                        racer.dnf = True
                        racer.finished = True
                    continue
                else:
                    racer.waiting_time = 0.0
                    u_node = racer.planned_route[0]
                    v_node = racer.planned_route[1]
                    edge = self.graph.find_edge(u_node, v_node)

            # Check fuel
            if racer.fuel <= 0.0:
                racer.waiting_time += self.dt
                if racer.waiting_time >= self.recovery_timeout:
                    racer.dnf = True
                    racer.finished = True
                    self.event_log.append(f"[{self.current_time:.1f}s] Racer {racer.id} declared DNF (fuel exhausted).")
                continue

            # Calculate speed and progression
            base_time = max(edge.baseTime, 1e-4)
            speed = edge.distance / base_time

            if edge.effective_speed_cap is not None:
                speed = min(speed, edge.effective_speed_cap)

            if nitro_active:
                speed *= cfg.NITRO_SPEED_MULTIPLIER

            progress_increment = (speed * self.dt) / max(edge.distance, 1e-4)
            racer.edge_progress += progress_increment

            # Consume fuel
            diff_factor = 1.0 + cfg.FUEL_DIFFICULTY_COEFF * (edge.difficulty - 1)
            fuel_rate = (edge.fuelCost * diff_factor) / base_time
            if nitro_active:
                fuel_rate *= cfg.NITRO_FUEL_MULTIPLIER

            racer.fuel = max(0.0, racer.fuel - fuel_rate * self.dt)
            racer.distance_traveled += speed * self.dt

            # When reaching the end of the edge
            if racer.edge_progress >= 1.0:
                racer.edge_progress = 0.0
                racer.current_vertex = v_node
                racer.planned_route.pop(0)

                v_obj = self.graph.vertices.get(v_node)

                # If fuel is low and no upcoming station is on current planned route, replan towards pit stop
                if racer.fuel <= 60.0 and (not v_obj or v_obj.type != "station"):
                    has_station = any(
                        self.graph.vertices.get(vid) and self.graph.vertices[vid].type == "station" and self.graph.vertices[vid].active
                        for vid in racer.planned_route
                    )
                    if not has_station:
                        replan(self.graph, racer, preset=racer.preset, ref=self.ref_values)

                # Checkpoint validation
                if v_obj and v_obj.checkpointOrder is not None:
                    if v_obj.checkpointOrder == racer.next_checkpoint_idx:
                        racer.completed_checkpoints += 1
                        racer.next_checkpoint_idx += 1

                # Nitro collection
                if v_obj and v_obj.type == "nitro" and v_obj.active:
                    if racer.nitro_charges < cfg.MAX_NITRO_CHARGES:
                        racer.nitro_charges += 1

                # Refuelling at station
                if v_obj and v_obj.type == "station" and v_obj.active:
                    should_refuel = False
                    if racer.strategy == "human":
                        should_refuel = (v_node in racer.refuel_plan) or (racer.fuel <= 60.0)
                    else:
                        should_refuel = (racer.fuel <= 60.0)

                    if should_refuel:
                        racer.current_pit_stop_timer = cfg.STATION_FIXED_STOP_TIME
                        racer.fuel = min(cfg.MAX_FUEL, racer.fuel + cfg.MAX_STATION_PURCHASE)
                        replan(self.graph, racer, preset=racer.preset, ref=self.ref_values)

                # Lap boundary crossing check
                if v_node == self.finish_vid:
                    # Only complete lap if all mandatory checkpoints were visited in order!
                    if racer.next_checkpoint_idx > self.total_checkpoints_per_lap:
                        racer.completed_laps += 1
                        lap_time = racer.total_time - racer.lap_start_time
                        if lap_time < racer.fastest_lap:
                            racer.fastest_lap = lap_time
                        racer.lap_start_time = racer.total_time
                        racer.lap += 1
                        racer.next_checkpoint_idx = 1

                        if racer.completed_laps >= self.target_laps:
                            racer.finished = True
                    else:
                        # Crossed finish line without completing all checkpoints: lap does NOT count!
                        pass

                # If planned route is exhausted but race not finished, replan next lap
                if not racer.finished and len(racer.planned_route) <= 1:
                    replan(self.graph, racer, preset=racer.preset, ref=self.ref_values)

    def is_finished(self) -> bool:
        """Check if all racers have finished (or DNF) or time limit expired."""
        if self.current_time >= self.max_time:
            return True
        return all(r.finished or r.dnf for r in self.racers)

    def run(self, until_finished: bool = True) -> List[RaceResult]:
        """Run the race simulation until completion."""
        while not self.is_finished():
            self.step()

        # Build final race results
        results: List[RaceResult] = []

        finished_racers = [r for r in self.racers if r.finished and not r.dnf]
        unfinished_racers = [r for r in self.racers if r.dnf or not r.finished]

        # Finished racers ranked by total_time ascending, tie-break by lower racer ID
        finished_racers.sort(key=lambda r: (r.total_time, r.id))

        # Unfinished racers ranked by: completed laps desc, checkpoints desc, time asc, racer ID asc
        unfinished_racers.sort(key=lambda r: (-r.completed_laps, -r.completed_checkpoints, r.total_time, r.id))

        ordered_racers = finished_racers + unfinished_racers

        for pos, racer in enumerate(ordered_racers, start=1):
            # Points awarded from config table; unfinished/DNF racers receive 0 points
            points = cfg.POINTS_TABLE[pos - 1] if pos <= len(cfg.POINTS_TABLE) and racer.finished and not racer.dnf else 0

            res = RaceResult(
                racer_id=racer.id,
                racer_name=racer.name,
                finish_position=pos,
                total_time=round(racer.total_time, 2),
                completed_laps=racer.completed_laps,
                completed_checkpoints=racer.completed_checkpoints,
                fastest_lap=round(racer.fastest_lap, 2) if racer.fastest_lap < float("inf") else 0.0,
                dnf=racer.dnf or (not racer.finished),
                points=points,
            )
            results.append(res)

        return results
