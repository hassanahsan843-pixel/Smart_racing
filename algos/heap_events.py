"""Event Min-Heap Priority Queue with Lazy Deletion and Target Validation.

Maintains track and dynamic environmental events keyed deterministically by:
(trigger_time, priority, insertion_sequence, event).
"""

import heapq
from typing import List, Tuple, Set, Optional, Any
from core.models import Event
from core.graph import Graph
from core.counters import OpCounters


class EventQueue:
    """Deterministic event priority queue using binary min-heap.

    Order priority:
      1. trigger_time (ascending)
      2. priority (ascending, 1=highest priority)
      3. insertion_sequence (ascending deterministic tie-breaker)
    """

    def __init__(self, graph: Optional[Graph] = None, counters: Optional[OpCounters] = None):
        self.heap: List[Tuple[float, int, int, Event]] = []
        self.cancelled_ids: Set[str] = set()
        self.seq: int = 0
        self.graph: Optional[Graph] = graph
        self.counters: OpCounters = counters if counters is not None else OpCounters()

    def push(self, event: Event) -> bool:
        """Push an event to the queue after validating target existence.

        Complexity: O(log N)
        """
        # Target validation
        if self.graph is not None:
            if event.target_type == "edge":
                if event.target_id not in self.graph.edges:
                    return False
            elif event.target_type == "vertex":
                if event.target_id not in self.graph.vertices:
                    return False

        self.seq += 1
        heap_item = (event.trigger_time, event.priority, self.seq, event)
        heapq.heappush(self.heap, heap_item)
        self.counters.heap_pushes += 1
        return True

    def cancel(self, event_id: str) -> None:
        """Cancel an event via lazy deletion.

        Complexity: O(1)
        """
        self.cancelled_ids.add(event_id)

    def peek(self) -> Optional[Event]:
        """Examine the earliest due non-cancelled event without removing it.

        Complexity: O(1) amortized
        """
        while self.heap:
            t, p, s, evt = self.heap[0]
            if evt.id in self.cancelled_ids:
                heapq.heappop(self.heap)
                self.counters.heap_pops += 1
                continue
            return evt
        return None

    def pop_due(self, current_time: float) -> List[Event]:
        """Pop and return ALL events with trigger_time <= current_time in heap order.

        Complexity: O(k log N) where k is the number of due events.
        """
        due_events: List[Event] = []

        while self.heap:
            t, p, s, evt = self.heap[0]
            if t > current_time:
                break

            heapq.heappop(self.heap)
            self.counters.heap_pops += 1

            if evt.id in self.cancelled_ids:
                continue

            due_events.append(evt)

        return due_events

    def is_empty(self) -> bool:
        return self.peek() is None

    def __len__(self) -> int:
        return len([item for item in self.heap if item[3].id not in self.cancelled_ids])
