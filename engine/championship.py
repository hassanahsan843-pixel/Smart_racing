"""Championship Season Manager and Standings Evaluator.

Executes a multi-round championship across all three circuits, accumulates
points and tie-break statistics, and evaluates the final champion.
"""

from typing import List, Dict, Tuple, Optional
from core.models import Racer, RaceResult, ChampionshipEntry
from core.graph import Graph
import core.config as cfg
from algos.comparator import championship_sort_key
from algos.sorting import merge_sort, quick_sort, heap_sort
from algos.topk import top_k_heap
from engine.race import Race
from engine.opponents import create_standard_opponents
from data.circuits.loader import load_circuit_from_json


def update_standings(standings: Dict[int, ChampionshipEntry],
                     results: List[RaceResult],
                     sort_algo: str = "merge") -> List[ChampionshipEntry]:
    """Incorporate single-race results into season standings and sort by total-order comparator.

    Complexity:
      - O(P log P) where P is the number of participants.
    """
    for res in results:
        rid = res.racer_id
        if rid not in standings:
            standings[rid] = ChampionshipEntry(
                racer_id=rid,
                racer_name=res.racer_name,
                total_points=0,
                wins=0,
                sum_positions=0,
                best_fastest_lap=float("inf"),
                race_results=[],
            )

        entry = standings[rid]
        entry.total_points += res.points
        if res.finish_position == 1 and not res.dnf:
            entry.wins += 1
        entry.sum_positions += res.finish_position
        if res.fastest_lap > 0 and res.fastest_lap < entry.best_fastest_lap:
            entry.best_fastest_lap = res.fastest_lap
        entry.race_results.append(res)

    entries = list(standings.values())

    # Switchable sorting algorithm (all using identical total-order comparator)
    if sort_algo == "quick":
        sorted_entries = quick_sort(entries, key=championship_sort_key)
    elif sort_algo == "heap":
        sorted_entries = heap_sort(entries, key=championship_sort_key)
    else:
        sorted_entries = merge_sort(entries, key=championship_sort_key)

    return sorted_entries


def run_championship(circuit_paths: List[str],
                     human_preset: str = "Balanced",
                     laps: int = cfg.CHAMPIONSHIP_LAPS,
                     seed: int = 42,
                     sort_algo: str = "merge") -> Tuple[List[ChampionshipEntry], ChampionshipEntry]:
    """Execute a complete 3-circuit championship season headless.

    Returns:
      (final_standings_list, champion_entry)
    """
    standings: Dict[int, ChampionshipEntry] = {}

    for round_idx, c_path in enumerate(circuit_paths, start=1):
        graph = load_circuit_from_json(c_path)

        # Create human racer + 3 standard opponents
        human = Racer(id=1, name="Player (Human)", preset=human_preset, strategy="human")
        opponents = create_standard_opponents()
        racers = [human] + opponents

        race = Race(graph=graph, racers=racers, config=cfg, seed=seed + round_idx, laps=laps)
        results = race.run()

        sorted_standings = update_standings(standings, results, sort_algo=sort_algo)

    champion = sorted_standings[0] if sorted_standings else None
    return sorted_standings, champion
