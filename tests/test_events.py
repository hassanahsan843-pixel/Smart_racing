"""Unit tests for Event Min-Heap and Dynamic Effects Dispatcher.

Covers:
  - Simultaneous events ordered by priority then insertion sequence
  - Cancelled event ignored via lazy deletion
  - Missing target edge/vertex rejection
  - Two overlapping effects on one edge where first expiry leaves second active
"""

import pytest
from core.models import Vertex, Edge, Event
from core.graph import Graph
from algos.heap_events import EventQueue
from engine.effects import apply_event


def test_event_heap_simultaneous_and_deterministic_ties():
    """Events at same trigger_time ordered by priority then insertion sequence."""
    eq = EventQueue()

    # Two events with same trigger_time and same priority
    e1 = Event(id="evt1", event_type="blockage", target_type="edge", target_id=1, trigger_time=10.0, priority=2)
    e2 = Event(id="evt2", event_type="shortcut_toggle", target_type="edge", target_id=2, trigger_time=10.0, priority=2)
    # Event with higher priority (1 < 2) at same time
    e3 = Event(id="evt3", event_type="blockage", target_type="edge", target_id=3, trigger_time=10.0, priority=1)

    eq.push(e1)  # seq 1
    eq.push(e2)  # seq 2
    eq.push(e3)  # seq 3, but priority 1

    due = eq.pop_due(10.0)
    assert len(due) == 3
    # e3 has priority 1 -> popped first
    assert due[0].id == "evt3"
    # e1 and e2 have same priority 2 -> broken by insertion sequence (seq 1 before seq 2)
    assert due[1].id == "evt1"
    assert due[2].id == "evt2"


def test_event_cancellation_lazy_deletion():
    """Cancelled events are ignored when popped."""
    eq = EventQueue()
    e1 = Event(id="evt_cancel", event_type="blockage", target_type="edge", target_id=1, trigger_time=5.0, priority=1)
    e2 = Event(id="evt_stay", event_type="oil_spill", target_type="edge", target_id=1, trigger_time=6.0, priority=3)

    eq.push(e1)
    eq.push(e2)

    eq.cancel("evt_cancel")
    due = eq.pop_due(10.0)

    assert len(due) == 1
    assert due[0].id == "evt_stay"


def test_missing_target_rejection():
    """Pushing an event whose target edge or vertex does not exist is rejected."""
    g = Graph()
    g.add_vertex(Vertex(id=0, x=0, y=0))
    eq = EventQueue(graph=g)

    # Valid vertex target
    ev_valid = Event(id="e_valid", event_type="fuel_station", target_type="vertex", target_id=0, trigger_time=1.0, priority=5)
    assert eq.push(ev_valid) is True

    # Missing vertex target 999
    ev_bad_v = Event(id="e_bad_v", event_type="fuel_station", target_type="vertex", target_id=999, trigger_time=1.0, priority=5)
    assert eq.push(ev_bad_v) is False

    # Missing edge target 555
    ev_bad_e = Event(id="e_bad_e", event_type="oil_spill", target_type="edge", target_id=555, trigger_time=1.0, priority=3)
    assert eq.push(ev_bad_e) is False


def test_overlapping_effects_expiry_preservation():
    """Two overlapping effects on one edge: first expiry leaves second active."""
    g = Graph()
    g.add_vertex(Vertex(id=0, x=0, y=0))
    g.add_vertex(Vertex(id=1, x=10, y=0))
    edge = Edge(id=1, from_node=0, to_node=1, distance=10, baseTime=5, fuelCost=5, difficulty=1, status="Open")
    g.add_edge(edge)

    eq = EventQueue(graph=g)

    # Effect 1: Oil spill at t=5.0 with duration 20s (expires at t=25.0)
    # Adds difficulty penalty +2 and speed cap 12.0
    ev_oil = Event(id="oil_1", event_type="oil_spill", target_type="edge", target_id=1,
                   trigger_time=5.0, priority=3, duration=20.0)
    apply_event(g, ev_oil, eq)

    assert edge.status == "Restricted"
    assert edge.effective_difficulty_penalty == 2
    assert edge.effective_speed_cap == 12.0

    # Effect 2: Speed restriction at t=10.0 with duration 30s (expires at t=40.0)
    # Stricter speed cap 8.0
    ev_speed = Event(id="speed_1", event_type="speed_restriction", target_type="edge", target_id=1,
                     trigger_time=10.0, priority=4, duration=30.0,
                     parameters={"speed_cap": 8.0})
    apply_event(g, ev_speed, eq)

    # Both active: speed cap should be 8.0 (strictest), difficulty penalty 2
    assert edge.effective_speed_cap == 8.0
    assert edge.effective_difficulty_penalty == 2

    # Advance time to t=26.0 (oil spill expires)
    due_at_26 = eq.pop_due(26.0)
    assert len(due_at_26) == 1
    assert due_at_26[0].id == "exp_oil_1"
    apply_event(g, due_at_26[0], eq)

    # Oil spill expired, but speed restriction MUST STILL BE ACTIVE!
    assert edge.status == "Restricted"
    assert edge.effective_speed_cap == 8.0  # speed restriction preserved!
    assert edge.effective_difficulty_penalty == 0  # oil difficulty penalty cleared

    # Advance time to t=41.0 (speed restriction expires)
    due_at_41 = eq.pop_due(41.0)
    assert len(due_at_41) == 1
    assert due_at_41[0].id == "exp_speed_1"
    apply_event(g, due_at_41[0], eq)

    # Both expired: back to original open state
    assert edge.status == "Open"
    assert edge.effective_speed_cap is None
    assert edge.effective_difficulty_penalty == 0
