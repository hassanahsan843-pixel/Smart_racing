"""Total-Order Comparator for Championship Standings and Top-K Analytics.

Section 4.6 Single Source of Truth for racer rankings:
  1. Higher totalPoints
  2. More wins (1st place finishes)
  3. Lower sumOfFinishPositions
  4. Lower bestFastestLap
  5. Lower racerId (deterministic tie-breaker)
"""

from typing import Tuple, Any
from core.models import ChampionshipEntry


def championship_sort_key(entry: ChampionshipEntry) -> Tuple[int, int, int, float, int]:
    """Generate a total-order comparison tuple where smaller means ranked higher."""
    return (
        -entry.total_points,
        -entry.wins,
        entry.sum_positions,
        entry.best_fastest_lap,
        entry.racer_id,
    )


def compare_entries(a: ChampionshipEntry, b: ChampionshipEntry) -> int:
    """Compare two ChampionshipEntry instances according to the total-order rules.

    Returns:
      -1 if a ranks strictly ahead of b
      +1 if b ranks strictly ahead of a
       0 if completely tied (only possible if identical racer_id)
    """
    key_a = championship_sort_key(a)
    key_b = championship_sort_key(b)
    if key_a < key_b:
        return -1
    elif key_a > key_b:
        return 1
    return 0
