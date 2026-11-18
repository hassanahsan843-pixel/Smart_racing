"""Sorting Algorithms for Championship Standings.

Implements Merge Sort (stable), Quick Sort (3-way partition, median-of-three pivot),
and Heap Sort (in-place binary heap), all driven by the single total-order comparator.
"""

from typing import List, Callable, Any, Optional
from core.counters import OpCounters


def _default_key(x: Any) -> Any:
    return x


def merge_sort(items: List[Any], key: Optional[Callable[[Any], Any]] = None,
               counters: Optional[OpCounters] = None) -> List[Any]:
    """Stable Merge Sort implementation.

    Complexity:
      - Time: O(n log n) in all cases (worst, best, average).
      - Space: O(n) auxiliary array allocations.
    Correctness Idea:
      Divides list into two equal halves, recursively sorts each half, and merges
      them by always selecting the smaller leading element. Stability is preserved
      because equal elements from the left subarray are always chosen first.
    """
    if counters is None:
        counters = OpCounters()
    if key is None:
        key = _default_key

    n = len(items)
    if n <= 1:
        return list(items)

    mid = n // 2
    left = merge_sort(items[:mid], key=key, counters=counters)
    right = merge_sort(items[mid:], key=key, counters=counters)

    # Merge step
    merged: List[Any] = []
    i = j = 0
    len_l, len_r = len(left), len(right)

    while i < len_l and j < len_r:
        counters.comparisons += 1
        # <= guarantees stability
        if key(left[i]) <= key(right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def quick_sort(items: List[Any], key: Optional[Callable[[Any], Any]] = None,
               counters: Optional[OpCounters] = None) -> List[Any]:
    """Quick Sort with Median-of-Three pivot selection and 3-Way Partitioning.

    Complexity:
      - Time: O(n log n) expected; O(n) for all-duplicate arrays.
      - Space: O(log n) recursion call stack.
    Pivot Rule:
      Median-of-three: examines first, middle, and last elements to choose
      the median as pivot, mitigating quadratic degradation on presorted inputs.
    3-Way Partition (Dutch National Flag):
      Divides array into three segments:
      [ elements < pivot | elements == pivot | elements > pivot ]
      Drastically reduces recursion depth when duplicate keys exist.
    """
    if counters is None:
        counters = OpCounters()
    if key is None:
        key = _default_key

    arr = list(items)

    def _qsort(low: int, high: int) -> None:
        if low >= high:
            return

        # Median-of-three pivot selection
        mid = (low + high) // 2
        # Sort low, mid, high
        candidates = [(key(arr[low]), low), (key(arr[mid]), mid), (key(arr[high]), high)]
        counters.comparisons += 3
        candidates.sort(key=lambda t: t[0])
        pivot_idx = candidates[1][1]
        # Place pivot at low
        arr[low], arr[pivot_idx] = arr[pivot_idx], arr[low]
        pivot_key = key(arr[low])

        # 3-Way partition
        # arr[low..lt-1] < pivot, arr[lt..gt] == pivot, arr[gt+1..high] > pivot
        lt = low
        gt = high
        i = low + 1

        while i <= gt:
            counters.comparisons += 1
            curr_k = key(arr[i])
            if curr_k < pivot_key:
                arr[lt], arr[i] = arr[i], arr[lt]
                lt += 1
                i += 1
            elif curr_k > pivot_key:
                arr[i], arr[gt] = arr[gt], arr[i]
                gt -= 1
            else:
                i += 1

        _qsort(low, lt - 1)
        _qsort(gt + 1, high)

    if len(arr) > 1:
        _qsort(0, len(arr) - 1)
    return arr


def heap_sort(items: List[Any], key: Optional[Callable[[Any], Any]] = None,
              counters: Optional[OpCounters] = None) -> List[Any]:
    """Heap Sort using in-place binary max-heap.

    Complexity:
      - Time: O(n log n) guaranteed.
      - Space: O(1) auxiliary space (in-place).
    Correctness Idea:
      Transforms the array into a max-heap in O(n) using sift-down operations,
      then repeatedly extracts the maximum element and moves it to the back
      of the array in O(n log n) time.
    """
    if counters is None:
        counters = OpCounters()
    if key is None:
        key = _default_key

    arr = list(items)
    n = len(arr)

    def _sift_down(start: int, end: int) -> None:
        root = start
        while True:
            child = 2 * root + 1
            if child > end:
                break
            counters.comparisons += 1
            if child + 1 <= end and key(arr[child]) < key(arr[child + 1]):
                child += 1
            counters.comparisons += 1
            if key(arr[root]) < key(arr[child]):
                arr[root], arr[child] = arr[child], arr[root]
                root = child
            else:
                break

    # Build max heap (heapify)
    for start in range((n - 2) // 2, -1, -1):
        _sift_down(start, n - 1)

    # Extract elements from heap one by one
    for end in range(n - 1, 0, -1):
        arr[0], arr[end] = arr[end], arr[0]
        _sift_down(0, end - 1)

    return arr
