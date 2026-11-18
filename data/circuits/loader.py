"""Circuit JSON loader and serializer.

Loads track graphs from JSON, building Graph instances and validating
topological and domain constraints.
"""

import json
from typing import Dict, Any
from core.models import Vertex, Edge
from core.graph import Graph


def load_circuit_from_json(filepath: str) -> Graph:
    """Load a circuit JSON file and construct a Graph instance."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = Graph()

    for v_data in data.get("vertices", []):
        v = Vertex.from_dict(v_data)
        graph.add_vertex(v)

    for e_data in data.get("edges", []):
        e = Edge.from_dict(e_data)
        graph.add_edge(e)

    return graph


def save_circuit_to_json(graph: Graph, filepath: str, name: str = "Circuit") -> None:
    """Serialize a Graph instance to circuit JSON format."""
    data: Dict[str, Any] = {
        "name": name,
        "vertices": [v.to_dict() for v in graph.vertices.values()],
        "edges": [e.to_dict() for e in graph.edges.values()],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
