"""Unit tests for Sorting Algorithms, Top-K Priority Queue, and Comparator.

Covers:
  - Empty, single, random, sorted, reverse, and duplicate-heavy input arrays
  - Merge Sort, Quick Sort (3-way), and Heap Sort agreement across all inputs
  - Top-K heap equivalence to first k of full sort
  - Championship total-order comparator tie-break chain
  - Deterministic tie-breaking on identical scores using racer ID
"""

import random
import pytest
from core.models import ChampionshipEntry
from algos.comparator import championship_sort_key, compare_entries
from algos.sorting import merge_sort, quick_sort, heap_sort
from algos.topk import top_k_heap, full_sort_topk


def test_sorting_input_variants_agreement():
    """All three sorts (Merge, Quick, Heap) agree on empty, single, sorted, reverse, duplicate."""
    rng = random.Random(42)

    test_cases = [
        [],  # empty
        [42],  # single
        [1, 2, 3, 4, 5, 6, 7, 8],  # already sorted
        [8, 7, 6, 5, 4, 3, 2, 1],  # reverse sorted
        [3, 1, 3, 1, 3, 2, 2, 1, 3, 2, 1],  # duplicate-heavy
        [rng.randint(-100, 100) for _ in range(50)],  # random
    ]

    for arr in test_cases:
        res_m = merge_sort(arr)
        res_q = quick_sort(arr)
        res_h = heap_sort(arr)
        expected = sorted(arr)

        assert res_m == expected, f"Merge sort failed on {arr}"
        assert res_q == expected, f"Quick sort failed on {arr}"
        assert res_h == expected, f"Heap sort failed on {arr}"


def test_topk_heap_equals_first_k_of_full_sort():
    """Top-K priority queue returns identical results to first k elements of full sort."""
    rng = random.Random(99)
    data = [rng.randint(1, 500) for _ in range(100)]

    for k in [1, 5, 10, 50, 100]:
        topk_res = top_k_heap(data, k=k)
        full_res = full_sort_topk(data, k=k)

        assert topk_res == full_res
        assert topk_res == sorted(data)[:k]


def test_championship_comparator_tie_break_chain():
    """Verify total-order comparator tie-break hierarchy:

    1. Points -> 2. Wins -> 3. Sum of positions -> 4. Fastest lap -> 5. Racer ID
    """
    # Base entry
    e1 = ChampionshipEntry(racer_id=10, racer_name="A", total_points=50, wins=2, sum_positions=5, best_fastest_lap=12.5)

    # 1. Higher points beats everything
    e2 = ChampionshipEntry(racer_id=20, racer_name="B", total_points=51, wins=1, sum_positions=10, best_fastest_lap=15.0)
    assert compare_entries(e2, e1) < 0  # e2 ranks ahead

    # 2. Equal points: More wins beats fewer wins
    e3 = ChampionshipEntry(racer_id=30, racer_name="C", total_points=50, wins=3, sum_positions=10, best_fastest_lap=15.0)
    assert compare_entries(e3, e1) < 0  # e3 ranks ahead

    # 3. Equal points & wins: Lower sum of positions wins
    e4 = ChampionshipEntry(racer_id=40, racer_name="D", total_points=50, wins=2, sum_positions=4, best_fastest_lap=15.0)
    assert compare_entries(e4, e1) < 0  # e4 ranks ahead

    # 4. Equal points, wins, & sum of positions: Lower best fastest lap wins
    e5 = ChampionshipEntry(racer_id=50, racer_name="E", total_points=50, wins=2, sum_positions=5, best_fastest_lap=11.0)
    assert compare_entries(e5, e1) < 0  # e5 ranks ahead

    # 5. Equal points, wins, sum, & fastest lap: Lower racer ID wins (racer-ID tie break!)
    e6 = ChampionshipEntry(racer_id=5, racer_name="F", total_points=50, wins=2, sum_positions=5, best_fastest_lap=12.5)
    assert compare_entries(e6, e1) < 0  # e6 has racer_id=5 < 10, so e6 ranks ahead


def test_sorts_with_championship_entries():
    """All three sorting algorithms produce identical championship standings."""
    entries = [
        ChampionshipEntry(racer_id=4, racer_name="Delta", total_points=35, wins=1, sum_positions=8, best_fastest_lap=14.2),
        ChampionshipEntry(racer_id=1, racer_name="Alpha", total_points=50, wins=2, sum_positions=4, best_fastest_lap=12.0),
        ChampionshipEntry(racer_id=3, racer_name="Gamma", total_points=40, wins=1, sum_positions=6, best_fastest_lap=13.1),
        ChampionshipEntry(racer_id=2, racer_name="Beta", total_points=50, wins=2, sum_positions=4, best_fastest_lap=12.0),
    ]

    # Note: Alpha and Beta have identical points, wins, sum_positions, and fastest lap.
    # Alpha has racer_id=1, Beta has racer_id=2 -> Alpha must rank ahead of Beta!
    sm = merge_sort(entries, key=championship_sort_key)
    sq = quick_sort(entries, key=championship_sort_key)
    sh = heap_sort(entries, key=championship_sort_key)

    assert [e.racer_id for e in sm] == [1, 2, 3, 4]
    assert [e.racer_id for e in sq] == [1, 2, 3, 4]
    assert [e.racer_id for e in sh] == [1, 2, 3, 4]
