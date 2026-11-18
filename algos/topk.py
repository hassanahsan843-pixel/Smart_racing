"""Top-K Priority Queue Selection vs Full Sort.

Computes the top-k highest ranked competitors in O(n log k) time using a
bounded heap, avoiding the full O(n log n) sorting cost when k << n.
"""

import heapq
from typing import List, Callable, Any, Optional
from core.counters import OpCounters


class _InvertedItem:
    """Wrapper to invert comparisons so heapq (min-heap) acts as a max-heap."""
    __slots__ = ("key_val", "item")

    def __init__(self, key_val: Any, item: Any):
        self.key_val = key_val
        self.item = item

    def __lt__(self, other: "_InvertedItem") -> bool:
        # Inverted: larger key value is treated as smaller so it sits at heap root
        return self.key_val > other.key_val


def top_k_heap(entries: List[Any], k: int,
               key: Optional[Callable[[Any], Any]] = None,
               counters: Optional[OpCounters] = None) -> List[Any]:
    """Select the top-k best entries using a bounded size-k heap.

    Complexity:
      - Time: O(n log k)
      - Space: O(k)
    Correctness Idea:
      Maintains a max-heap of size at most k storing the k best (smallest key)
      elements seen so far. If an incoming element has a smaller key than the
      heap's maximum (root), the root is replaced. At termination, the heap
      contains exactly the k best elements.
    """
    if counters is None:
        counters = OpCounters()
    if key is None:
        key = lambda x: x

    if k <= 0 or not entries:
        return []

    k = min(k, len(entries))
    heap: List[_InvertedItem] = []

    for entry in entries:
        k_val = key(entry)
        wrapped = _InvertedItem(k_val, entry)

        if len(heap) < k:
            heapq.heappush(heap, wrapped)
            counters.heap_pushes += 1
        else:
            counters.comparisons += 1
            # Root of inverted heap is the worst among the current top-k
            if k_val < heap[0].key_val:
                heapq.heapreplace(heap, wrapped)
                counters.heap_pushes += 1
                counters.heap_pops += 1

    # Extract all elements from heap and sort in ascending order (best first)
    result = [w.item for w in heap]
    result.sort(key=key)
    return result


def full_sort_topk(entries: List[Any], k: int,
                   key: Optional[Callable[[Any], Any]] = None,
                   counters: Optional[OpCounters] = None) -> List[Any]:
    """Baseline top-k selector using full sort of all entries.

    Complexity:
      - Time: O(n log n)
      - Space: O(n)
    """
    if counters is None:
        counters = OpCounters()
    if key is None:
        key = lambda x: x

    from algos.sorting import merge_sort
    sorted_all = merge_sort(entries, key=key, counters=counters)
    return sorted_all[:k]
