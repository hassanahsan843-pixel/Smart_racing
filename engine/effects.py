"""Dynamic Track Effects and Event Dispatcher.

Handles edge hazards, speed restrictions, blockages, service vertex toggles,
and automatic expiry scheduling with independent overlapping effect preservation.
"""

from typing import Optional, Dict, Any
from core.models import Event
from core.graph import Graph
import core.config as cfg


def apply_event(graph: Graph, event: Event, event_queue: Any = None) -> Optional[Event]:
    """Apply an event to the graph and schedule any automatic expiry event.

    Overlapping effects on an edge are keyed by unique effect_id so expiring
    one effect leaves all other concurrent effects active.

    Complexity:
      - O(1) in-place effect modification and state recomputation.
    """
    evt_type = event.event_type
    target_id = event.target_id
    expiry_event: Optional[Event] = None

    if evt_type == "blockage":
        graph.block_edge(target_id)
        # Store as blockage effect
        graph.add_effect(target_id, f"block_{event.id}", {
            "type": "blockage",
            "blocks": True,
        })
        if event.duration is not None and event.duration > 0:
            expiry_event = Event(
                id=f"exp_{event.id}",
                event_type="unblock",
                target_type="edge",
                target_id=target_id,
                trigger_time=event.trigger_time + event.duration,
                priority=event.priority,
            )

    elif evt_type == "unblock":
        graph.remove_effect(target_id, f"block_{event.parameters.get('source_event_id', event.id)}")
        graph.unblock_edge(target_id)

    elif evt_type == "shortcut_toggle":
        edge = graph.get_edge(target_id)
        if edge:
            if edge.status == "Blocked":
                graph.unblock_edge(target_id)
            else:
                graph.block_edge(target_id)

    elif evt_type == "oil_spill":
        duration = event.duration if event.duration is not None else cfg.DURATION_OIL_SPILL
        effect_id = f"oil_{event.id}"
        graph.add_effect(target_id, effect_id, {
            "type": "oil_spill",
            "difficulty_penalty": event.parameters.get("difficulty_penalty", cfg.OIL_SPILL_DIFFICULTY_PENALTY),
            "speed_cap": event.parameters.get("speed_cap", cfg.OIL_SPILL_SPEED_CAP),
        })
        expiry_event = Event(
            id=f"exp_{event.id}",
            event_type="clear_effect",
            target_type="edge",
            target_id=target_id,
            trigger_time=event.trigger_time + duration,
            priority=event.priority,
            parameters={"effect_id": effect_id},
        )

    elif evt_type == "speed_restriction":
        duration = event.duration if event.duration is not None else cfg.DURATION_SPEED_RESTRICTION
        effect_id = f"speed_{event.id}"
        graph.add_effect(target_id, effect_id, {
            "type": "speed_restriction",
            "speed_cap": event.parameters.get("speed_cap", cfg.DEFAULT_SPEED_RESTRICTION_CAP),
        })
        expiry_event = Event(
            id=f"exp_{event.id}",
            event_type="clear_effect",
            target_type="edge",
            target_id=target_id,
            trigger_time=event.trigger_time + duration,
            priority=event.priority,
            parameters={"effect_id": effect_id},
        )

    elif evt_type == "fuel_station":
        duration = event.duration if event.duration is not None else cfg.DURATION_FUEL_STATION
        make_active = event.parameters.get("active", False)
        graph.set_vertex_active(target_id, make_active)
        expiry_event = Event(
            id=f"exp_{event.id}",
            event_type="toggle_vertex",
            target_type="vertex",
            target_id=target_id,
            trigger_time=event.trigger_time + duration,
            priority=event.priority,
            parameters={"active": not make_active},
        )

    elif evt_type == "nitro_booster":
        duration = event.duration if event.duration is not None else cfg.DURATION_NITRO_BOOSTER
        make_active = event.parameters.get("active", False)
        graph.set_vertex_active(target_id, make_active)
        expiry_event = Event(
            id=f"exp_{event.id}",
            event_type="toggle_vertex",
            target_type="vertex",
            target_id=target_id,
            trigger_time=event.trigger_time + duration,
            priority=event.priority,
            parameters={"active": not make_active},
        )

    elif evt_type == "clear_effect":
        effect_id = event.parameters.get("effect_id", "")
        graph.remove_effect(target_id, effect_id)

    elif evt_type == "toggle_vertex":
        active_val = event.parameters.get("active", True)
        graph.set_vertex_active(target_id, active_val)

    if expiry_event is not None and event_queue is not None:
        event_queue.push(expiry_event)

    return expiry_event
