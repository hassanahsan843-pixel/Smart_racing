"""Core domain models and dataclasses for Smart Racing Championship.

Defines Vertex, Edge, Racer, RaceResult, ChampionshipEntry, and Event
strictly matching the DAA project specification.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class Vertex:
    """Represents a node in the racing graph.

    Types:
      - 'start': starting grid / finish line
      - 'checkpoint': mandatory checkpoint with checkpointOrder (1..k)
      - 'station': fuel refuelling station
      - 'nitro': nitro booster pickup
      - 'intersection': junction of multiple track branches
      - 'dead_end': termination vertex requiring reversing / turnaround
      - 'regular': standard track vertex
    """
    id: int
    x: float
    y: float
    type: str = "regular"
    checkpointOrder: Optional[int] = None
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "type": self.type,
            "checkpointOrder": self.checkpointOrder,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vertex":
        return cls(
            id=int(data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            type=str(data.get("type", "regular")),
            checkpointOrder=int(data["checkpointOrder"]) if data.get("checkpointOrder") is not None else None,
            active=bool(data.get("active", True)),
        )


@dataclass
class Edge:
    """Represents a directed or undirected road segment between vertices.

    Fields:
      - id: unique edge identifier
      - from_node: source vertex id (alias: u, from)
      - to_node: destination vertex id (alias: v, to)
      - distance: Euclidean or track length
      - baseTime: base traversal time in seconds
      - fuelCost: base fuel units consumed
      - difficulty: risk/hazard rating (1 to 5)
      - status: 'Open', 'Blocked', or 'Restricted'
      - isShortcut: whether this edge represents an optional high-risk/reward shortcut
      - directed: True for one-way roads, False for two-way roads
    """
    id: int
    from_node: int
    to_node: int
    distance: float
    baseTime: float
    fuelCost: float
    difficulty: int
    status: str = "Open"  # 'Open', 'Blocked', 'Restricted'
    isShortcut: bool = False
    directed: bool = False
    effective_speed_cap: Optional[float] = None
    effective_difficulty_penalty: int = 0

    @property
    def u(self) -> int:
        return self.from_node

    @property
    def v(self) -> int:
        return self.to_node

    @property
    def to(self) -> int:
        return self.to_node

    def __getattr__(self, name: str) -> Any:
        if name == "from":
            return self.from_node
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from": self.from_node,
            "to": self.to_node,
            "distance": self.distance,
            "baseTime": self.baseTime,
            "fuelCost": self.fuelCost,
            "difficulty": self.difficulty,
            "status": self.status,
            "isShortcut": self.isShortcut,
            "directed": self.directed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        from_val = data.get("from", data.get("from_node", data.get("u")))
        to_val = data.get("to", data.get("to_node", data.get("v")))
        return cls(
            id=int(data["id"]),
            from_node=int(from_val),
            to_node=int(to_val),
            distance=float(data["distance"]),
            baseTime=float(data["baseTime"]),
            fuelCost=float(data["fuelCost"]),
            difficulty=int(data["difficulty"]),
            status=str(data.get("status", "Open")),
            isShortcut=bool(data.get("isShortcut", False)),
            directed=bool(data.get("directed", False)),
        )


@dataclass
class Racer:
    """Represents a racing car participant in the championship."""
    id: int
    name: str
    preset: str = "Balanced"  # 'Balanced', 'Speed', 'Economy', 'Safety'
    strategy: str = "human"   # 'human', 'fixed_detour', 'shortcut_fallback', 'min_distance_recompute'
    current_vertex: int = 0
    fuel: float = 100.0
    nitro_charges: int = 3
    nitro_active_timer: float = 0.0
    next_checkpoint_idx: int = 1
    lap: int = 1
    distance_traveled: float = 0.0
    total_time: float = 0.0
    waiting_time: float = 0.0
    dnf: bool = False
    finished: bool = False
    planned_route: List[int] = field(default_factory=list)
    current_edge: Optional[Edge] = None
    edge_progress: float = 0.0
    fastest_lap: float = float("inf")
    lap_start_time: float = 0.0
    completed_laps: int = 0
    completed_checkpoints: int = 0
    refuel_plan: Dict[int, float] = field(default_factory=dict)  # stop_vertex -> purchase amount
    current_pit_stop_timer: float = 0.0


@dataclass
class RaceResult:
    """Final outcome and statistics for a single race."""
    racer_id: int
    racer_name: str
    finish_position: int
    total_time: float
    completed_laps: int
    completed_checkpoints: int
    fastest_lap: float
    dnf: bool = False
    points: int = 0


@dataclass
class ChampionshipEntry:
    """Aggregated championship standings across a multi-circuit season."""
    racer_id: int
    racer_name: str
    total_points: int = 0
    wins: int = 0
    sum_positions: int = 0
    best_fastest_lap: float = float("inf")
    race_results: List[RaceResult] = field(default_factory=list)


@dataclass
class Event:
    """Dynamic track event scheduled or dispatched in the race event queue.

    Keyed for min-heap as (trigger_time, priority, insertion_sequence, event).
    """
    id: str
    event_type: str       # 'blockage', 'unblock', 'shortcut_toggle', 'oil_spill', 'speed_restriction', 'fuel_station', 'nitro_booster'
    target_type: str      # 'edge' or 'vertex'
    target_id: int        # edge_id or vertex_id
    trigger_time: float
    priority: int         # 1 (highest) to 6 (lowest)
    duration: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
