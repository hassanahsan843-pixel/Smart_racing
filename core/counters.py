"""Counters object and step-tracing hook for algorithmic complexity measurement.

Used across all 12 algorithms to measure exact operational counts:
- visited vertices
- examined edges
- relaxations
- heap pushes / pops
- comparisons
"""

from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any


@dataclass
class OpCounters:
    """Tracks operational steps and metrics during algorithm execution."""
    visited_vertices: int = 0
    examined_edges: int = 0
    relaxations: int = 0
    heap_pushes: int = 0
    heap_pops: int = 0
    comparisons: int = 0

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.visited_vertices = 0
        self.examined_edges = 0
        self.relaxations = 0
        self.heap_pushes = 0
        self.heap_pops = 0
        self.comparisons = 0

    def to_dict(self) -> Dict[str, int]:
        """Return counters as a serializable dictionary."""
        return {
            "visited_vertices": self.visited_vertices,
            "examined_edges": self.examined_edges,
            "relaxations": self.relaxations,
            "heap_pushes": self.heap_pushes,
            "heap_pops": self.heap_pops,
            "comparisons": self.comparisons,
        }

    def total_ops(self) -> int:
        """Sum of all operations for high-level aggregate comparison."""
        return (
            self.visited_vertices
            + self.examined_edges
            + self.relaxations
            + self.heap_pushes
            + self.heap_pops
            + self.comparisons
        )


StepCallback = Optional[Callable[[Dict[str, Any]], None]]
