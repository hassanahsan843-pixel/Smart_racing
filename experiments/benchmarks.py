"""Algorithmic Complexity Benchmarking Experiments.

Runs comparative benchmarks for all 12 algorithm families:
  - BFS vs DFS vs Dijkstra vs A* (operational counts + wall-clock)
  - Dijkstra vs A* expanded-vertex advantage across circuit sizes
  - Merge Sort vs Quick Sort vs Heap Sort (n=10 to 10000)
  - Full-sort top-n vs bounded top-k heap (k = 1,3,5)
  - Knapsack DP vs Greedy vs Exhaustive (n=3..20)
  - Refuel DP state-space at fuel_unit=1.0 vs 0.1
  - Backtracking generator timing (n=12..22)

All results are saved to experiments/results/ as CSV files and
rendered to PNG charts via matplotlib.
"""

import os
import csv
import time
import random
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from core.models import Vertex, Edge, Racer, ChampionshipEntry
from core.graph import Graph
from core.cost import CircuitReferenceValues
from core.counters import OpCounters
from algos.bfs_dfs import bfs, dfs_traverse
from algos.dijkstra import dijkstra
from algos.astar import astar
from algos.mst import kruskal
from algos.knapsack import knapsack_dp, knapsack_value_only
from algos.greedy import greedy_knapsack, exhaustive_knapsack
from algos.sorting import merge_sort, quick_sort, heap_sort
from algos.topk import top_k_heap, full_sort_topk
from algos.refuel_dp import refuel_dp
from algos.backtrack_gen import generate_track
from algos.comparator import championship_sort_key
from algos.validator import validate_circuit
from data.circuits.loader import load_circuit_from_json

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────

def build_random_graph(n: int, edge_prob: float = 0.35, seed: int = 0) -> Graph:
    rng = random.Random(seed)
    g = Graph()
    for i in range(n):
        g.add_vertex(Vertex(id=i, x=rng.uniform(0, 500), y=rng.uniform(0, 400)))
    eid = 1
    for u in range(n):
        for v in range(u + 1, n):
            if rng.random() < edge_prob:
                eu = g.vertices[u]; ev = g.vertices[v]
                dist = max(1.0, ((eu.x - ev.x)**2 + (eu.y - ev.y)**2)**0.5)
                g.add_edge(Edge(id=eid, from_node=u, to_node=v,
                                distance=dist * rng.uniform(1.0, 1.4),
                                baseTime=max(1.0, dist / 25),
                                fuelCost=max(1.0, dist / 30),
                                difficulty=rng.randint(1, 5)))
                eid += 1
    return g


def build_random_entries(n: int, seed: int = 7) -> list:
    rng = random.Random(seed)
    entries = []
    for i in range(n):
        entries.append(ChampionshipEntry(
            racer_id=i, racer_name=f"R{i:04d}",
            total_points=rng.randint(0, 150),
            wins=rng.randint(0, 5),
            sum_positions=rng.randint(1, 20),
            best_fastest_lap=rng.uniform(60.0, 300.0),
        ))
    return entries


def write_csv(filename: str, header: list, rows: list) -> None:
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  Saved → {path}")


def save_fig(fig: plt.Figure, filename: str) -> None:
    path = os.path.join(RESULTS_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved → {path}")


# ───────────────────────────────────────────────────────────────────────────────
# Experiment 1: Graph Traversal — BFS / DFS operational counts vs vertex count
# ───────────────────────────────────────────────────────────────────────────────
def exp1_traversal_ops():
    print("\n[Exp 1] BFS vs DFS — Operational Counts vs |V|")
    sizes = list(range(5, 55, 5))
    rows = []
    bfs_visited, dfs_visited = [], []
    bfs_edges, dfs_edges = [], []

    for n in sizes:
        g = build_random_graph(n, edge_prob=0.4, seed=n)
        ref = CircuitReferenceValues.from_graph(g)

        cb = OpCounters()
        bfs(g, src=0, dst=n - 1, counters=cb)
        bfs_visited.append(cb.visited_vertices)
        bfs_edges.append(cb.examined_edges)

        cd = OpCounters()
        dfs_traverse(g, src=0, counters=cd)
        dfs_visited.append(cd.visited_vertices)
        dfs_edges.append(cd.examined_edges)

        rows.append([n, cb.visited_vertices, cb.examined_edges, cd.visited_vertices, cd.examined_edges])

    write_csv("exp1_traversal_ops.csv",
              ["n", "bfs_visited", "bfs_edges", "dfs_visited", "dfs_edges"], rows)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Exp 1: BFS vs DFS — Operational Counts", fontsize=14, fontweight="bold")

    ax1.plot(sizes, bfs_visited, "b-o", label="BFS Visited")
    ax1.plot(sizes, dfs_visited, "r-s", label="DFS Visited")
    ax1.set_xlabel("|V| (vertices)"); ax1.set_ylabel("Vertices Visited")
    ax1.set_title("Vertices Visited"); ax1.legend(); ax1.grid(alpha=0.3)

    ax2.plot(sizes, bfs_edges, "b-o", label="BFS Edges Examined")
    ax2.plot(sizes, dfs_edges, "r-s", label="DFS Edges Examined")
    ax2.set_xlabel("|V| (vertices)"); ax2.set_ylabel("Edges Examined")
    ax2.set_title("Edges Examined"); ax2.legend(); ax2.grid(alpha=0.3)

    save_fig(fig, "exp1_traversal_ops.png")


# ───────────────────────────────────────────────────────────────────────────────
# Experiment 2: Dijkstra vs A* — Expanded Vertices + Wall-Clock Time
# ───────────────────────────────────────────────────────────────────────────────
def exp2_dijkstra_vs_astar():
    print("\n[Exp 2] Dijkstra vs A* — Expanded Vertices and Timing")
    sizes = list(range(10, 65, 5))
    rows = []
    d_exp, a_exp = [], []
    d_time, a_time = [], []

    for n in sizes:
        g = build_random_graph(n, edge_prob=0.35, seed=n * 3)
        ref = CircuitReferenceValues.from_graph(g)
        src, dst = 0, n - 1

        cd = OpCounters()
        t0 = time.perf_counter()
        dijkstra(g, src=src, dst=dst, counters=cd, ref=ref)
        td = (time.perf_counter() - t0) * 1000

        ca = OpCounters()
        t0 = time.perf_counter()
        astar(g, src=src, dst=dst, counters=ca, ref=ref)
        ta = (time.perf_counter() - t0) * 1000

        d_exp.append(cd.visited_vertices)
        a_exp.append(ca.visited_vertices)
        d_time.append(round(td, 4))
        a_time.append(round(ta, 4))
        rows.append([n, cd.visited_vertices, ca.visited_vertices, round(td, 4), round(ta, 4)])

    write_csv("exp2_dijkstra_vs_astar.csv",
              ["n", "dijkstra_expanded", "astar_expanded", "dijkstra_ms", "astar_ms"], rows)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Exp 2: Dijkstra vs A* — Performance", fontsize=14, fontweight="bold")

    ax1.plot(sizes, d_exp, "b-o", label="Dijkstra Expanded")
    ax1.plot(sizes, a_exp, "g-s", label="A* Expanded")
    ax1.fill_between(sizes, d_exp, a_exp, alpha=0.15, color="orange", label="A* Advantage")
    ax1.set_xlabel("|V|"); ax1.set_ylabel("Vertices Expanded")
    ax1.set_title("Vertices Expanded (A* advantage area)"); ax1.legend(); ax1.grid(alpha=0.3)

    ax2.plot(sizes, d_time, "b-o", label="Dijkstra (ms)")
    ax2.plot(sizes, a_time, "g-s", label="A* (ms)")
    ax2.set_xlabel("|V|"); ax2.set_ylabel("Wall-clock time (ms)")
    ax2.set_title("Wall-Clock Time"); ax2.legend(); ax2.grid(alpha=0.3)

    save_fig(fig, "exp2_dijkstra_vs_astar.png")


# ───────────────────────────────────────────────────────────────────────────────
# Experiment 3: Sorting Algorithms — Comparison Count vs Array Size
# ───────────────────────────────────────────────────────────────────────────────
def exp3_sorting_comparison():
    print("\n[Exp 3] Sorting — Comparison Counts and Timing")
    sizes = [10, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    rows = []
    m_comps, q_comps, h_comps = [], [], []
    m_times, q_times, h_times = [], [], []

    rng = random.Random(99)
    for n in sizes:
        entries = build_random_entries(n, seed=n)
        key_fn = championship_sort_key

        cm = OpCounters()
        t0 = time.perf_counter()
        merge_sort(entries, key=key_fn, counters=cm)
        m_times.append((time.perf_counter() - t0) * 1000)

        cq = OpCounters()
        t0 = time.perf_counter()
        quick_sort(entries, key=key_fn, counters=cq)
        q_times.append((time.perf_counter() - t0) * 1000)

        ch = OpCounters()
        t0 = time.perf_counter()
        heap_sort(entries, key=key_fn, counters=ch)
        h_times.append((time.perf_counter() - t0) * 1000)

        m_comps.append(cm.comparisons)
        q_comps.append(cq.comparisons)
        h_comps.append(ch.comparisons)

        # Theoretical O(n log n)
        nlogn = n * (n.bit_length())
        rows.append([n, cm.comparisons, cq.comparisons, ch.comparisons,
                     round(m_times[-1], 3), round(q_times[-1], 3), round(h_times[-1], 3),
                     nlogn])

    write_csv("exp3_sorting.csv",
              ["n", "merge_comps", "quick_comps", "heap_comps",
               "merge_ms", "quick_ms", "heap_ms", "nlogn_theoretical"], rows)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Exp 3: Sorting Algorithms — Comparison Counts", fontsize=14, fontweight="bold")

    nlogn_theory = [n * (n.bit_length()) for n in sizes]

    ax1.plot(sizes, m_comps, "b-o", label="Merge Sort")
    ax1.plot(sizes, q_comps, "r-s", label="Quick Sort (3-way)")
    ax1.plot(sizes, h_comps, "g-^", label="Heap Sort")
    ax1.plot(sizes, nlogn_theory, "k--", alpha=0.5, label="O(n log n) theoretical")
    ax1.set_xlabel("Array Size (n)"); ax1.set_ylabel("Comparisons")
    ax1.set_title("Comparison Counts"); ax1.legend(); ax1.grid(alpha=0.3)

    ax2.plot(sizes, m_times, "b-o", label="Merge Sort")
    ax2.plot(sizes, q_times, "r-s", label="Quick Sort")
    ax2.plot(sizes, h_times, "g-^", label="Heap Sort")
    ax2.set_xlabel("Array Size (n)"); ax2.set_ylabel("Time (ms)")
    ax2.set_title("Wall-Clock Time"); ax2.legend(); ax2.grid(alpha=0.3)

    save_fig(fig, "exp3_sorting.png")


# ───────────────────────────────────────────────────────────────────────────────
# Experiment 4: Top-K Bounded Heap vs Full Sort — Wall-clock time
# ───────────────────────────────────────────────────────────────────────────────
def exp4_topk_vs_fullsort():
    print("\n[Exp 4] Top-K Heap vs Full Sort — Timing for varying k")
    n = 10000
    k_vals = [1, 5, 10, 50, 100, 500, 1000, 5000, 10000]
    rows = []
    topk_times, full_times = [], []

    entries = build_random_entries(n, seed=42)
    key_fn = championship_sort_key

    for k in k_vals:
        t0 = time.perf_counter()
        for _ in range(20):
            top_k_heap(entries, k=k, key=key_fn)
        topk_ms = (time.perf_counter() - t0) * 1000 / 20

        t1 = time.perf_counter()
        for _ in range(20):
            full_sort_topk(entries, k=k, key=key_fn)
        full_ms = (time.perf_counter() - t1) * 1000 / 20

        topk_times.append(round(topk_ms, 3))
        full_times.append(round(full_ms, 3))
        rows.append([n, k, round(topk_ms, 3), round(full_ms, 3)])

    write_csv("exp4_topk_vs_fullsort.csv",
              ["n", "k", "topk_heap_ms", "full_sort_ms"], rows)

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle(f"Exp 4: Top-K Heap vs Full Sort (n={n})", fontsize=14, fontweight="bold")
    ax.plot(k_vals, topk_times, "g-o", label="top_k_heap O(n log k)")
    ax.plot(k_vals, full_times, "r-s", label="full_sort O(n log n)")
    ax.axhline(y=full_times[-1], color="gray", linestyle="--", alpha=0.5, label="Full sort flat baseline")
    ax.set_xlabel("k"); ax.set_ylabel("Time (ms)")
    ax.set_title(f"Top-K Selection Performance (n={n})"); ax.legend(); ax.grid(alpha=0.3)
    ax.set_xscale("log")

    save_fig(fig, "exp4_topk_vs_fullsort.png")


# ───────────────────────────────────────────────────────────────────────────────
# Experiment 5: Knapsack DP vs Greedy — Value Gap and Timing
# ───────────────────────────────────────────────────────────────────────────────
def exp5_knapsack():
    print("\n[Exp 5] Knapsack DP vs Greedy — Value Gap")
    item_counts = list(range(3, 21))
    rows = []
    dp_vals, gr_vals, gaps = [], [], []
    dp_times, gr_times = [], []
    gap_cases = 0

    rng = random.Random(42)
    for n in item_counts:
        budget = n * 5
        items = [{"id": i, "cost": rng.randint(1, 10), "value": round(rng.uniform(5, 50), 1)} for i in range(n)]

        t0 = time.perf_counter()
        dp_v, _, _ = knapsack_dp(items, budget)
        dp_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        gr_v, _ = greedy_knapsack(items, budget)
        gr_times.append((time.perf_counter() - t0) * 1000)

        gap = dp_v - gr_v
        dp_vals.append(dp_v)
        gr_vals.append(gr_v)
        gaps.append(gap)
        if gap > 0:
            gap_cases += 1
        rows.append([n, budget, round(dp_v, 1), round(gr_v, 1), round(gap, 1),
                     round(dp_times[-1], 4), round(gr_times[-1], 4)])

    write_csv("exp5_knapsack.csv",
              ["n_items", "budget", "dp_value", "greedy_value", "gap", "dp_ms", "greedy_ms"], rows)

    print(f"  Greedy suboptimal in {gap_cases}/{len(item_counts)} cases")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Exp 5: Knapsack DP vs Greedy", fontsize=14, fontweight="bold")

    ax1.plot(item_counts, dp_vals, "g-o", label="DP Optimal")
    ax1.plot(item_counts, gr_vals, "r-s", label="Greedy")
    ax1.fill_between(item_counts, gr_vals, dp_vals, alpha=0.2, color="orange", label="Greedy Deficit")
    ax1.set_xlabel("Item Count (n)"); ax1.set_ylabel("Selected Value")
    ax1.set_title("Selected Value (DP vs Greedy)"); ax1.legend(); ax1.grid(alpha=0.3)

    ax2.bar([x - 0.2 for x in item_counts], dp_times, 0.4, color="steelblue", label="DP (ms)")
    ax2.bar([x + 0.2 for x in item_counts], gr_times, 0.4, color="tomato", label="Greedy (ms)")
    ax2.set_xlabel("Item Count (n)"); ax2.set_ylabel("Time (ms)")
    ax2.set_title("Execution Time"); ax2.legend(); ax2.grid(alpha=0.3)

    save_fig(fig, "exp5_knapsack.png")


# ───────────────────────────────────────────────────────────────────────────────
# Experiment 6: Refuel DP — State Space at fuel_unit=1.0 vs 0.1
# ───────────────────────────────────────────────────────────────────────────────
def exp6_refuel_dp_state_space():
    print("\n[Exp 6] Refuel DP — State Space at fuel_unit=1.0 vs 0.1")
    rows = []

    for m_legs in range(1, 9):
        stops = [Vertex(id=i, x=i * 10, y=0,
                        type="station" if i % 3 == 0 else "regular",
                        active=True) for i in range(m_legs + 1)]
        demands = [8.0] * m_legs

        # State space: (m+1) * (capacity / fuel_unit + 1)
        states_coarse = (m_legs + 1) * (100 // 1 + 1)   # fuel_unit=1.0
        states_fine = (m_legs + 1) * (100 // 1 * 10 + 1)  # fuel_unit=0.1 (10x)

        t0 = time.perf_counter()
        refuel_dp(stops, demands, capacity=100.0, start_fuel=50.0, fuel_unit=1.0)
        t_coarse = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        refuel_dp(stops, demands, capacity=100.0, start_fuel=50.0, fuel_unit=0.1)
        t_fine = (time.perf_counter() - t0) * 1000

        rows.append([m_legs, states_coarse, states_fine, round(t_coarse, 3), round(t_fine, 3)])

    write_csv("exp6_refuel_dp.csv",
              ["m_legs", "states_coarse(unit=1)", "states_fine(unit=0.1)",
               "time_coarse_ms", "time_fine_ms"], rows)

    m_vals = [r[0] for r in rows]
    s_coarse = [r[1] for r in rows]
    s_fine = [r[2] for r in rows]
    t_coarse_v = [r[3] for r in rows]
    t_fine_v = [r[4] for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Exp 6: Refuel DP — fuel_unit State Space Impact", fontsize=14, fontweight="bold")

    ax1.plot(m_vals, s_coarse, "b-o", label="unit=1.0 (coarse)")
    ax1.plot(m_vals, s_fine, "r-s", label="unit=0.1 (fine, 10x)")
    ax1.set_xlabel("Route Legs (m)"); ax1.set_ylabel("DP State Count")
    ax1.set_title("State Space Size"); ax1.legend(); ax1.grid(alpha=0.3)

    ax2.plot(m_vals, t_coarse_v, "b-o", label="unit=1.0")
    ax2.plot(m_vals, t_fine_v, "r-s", label="unit=0.1")
    ax2.set_xlabel("Route Legs (m)"); ax2.set_ylabel("Time (ms)")
    ax2.set_title("Execution Time"); ax2.legend(); ax2.grid(alpha=0.3)

    save_fig(fig, "exp6_refuel_dp.png")


# ───────────────────────────────────────────────────────────────────────────────
# Experiment 7: Backtracking Generator — Timing and Pruning Statistics
# ───────────────────────────────────────────────────────────────────────────────
def exp7_generator_timing():
    print("\n[Exp 7] Backtracking Generator — Timing and Pruning Stats")
    sizes = list(range(12, 25, 2))
    rows = []
    gen_times, prune_counts = [], []

    for n in sizes:
        t0 = time.perf_counter()
        graph, log = generate_track(seed=42, n_vertices=n)
        elapsed = (time.perf_counter() - t0) * 1000
        gen_times.append(round(elapsed, 2))
        total_prune = sum(log.values())
        prune_counts.append(total_prune)
        success = graph is not None
        rows.append([n, round(elapsed, 2), total_prune, 1 if success else 0,
                     log.get("pruned_max_degree", 0),
                     log.get("pruned_station_spacing", 0),
                     log.get("pruned_obstacle_spacing", 0)])
        print(f"  n={n}: {elapsed:.1f}ms | pruned={total_prune} | success={success}")

    write_csv("exp7_generator.csv",
              ["n_vertices", "gen_ms", "total_pruned", "success",
               "pruned_max_degree", "pruned_station_spacing", "pruned_obstacle_spacing"], rows)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Exp 7: Backtracking Circuit Generator", fontsize=14, fontweight="bold")

    ax1.bar(sizes, gen_times, color="steelblue", width=1.2)
    ax1.set_xlabel("Vertices (n)"); ax1.set_ylabel("Generation Time (ms)")
    ax1.set_title("Generation Time"); ax1.grid(alpha=0.3, axis="y")

    ax2.bar(sizes, prune_counts, color="salmon", width=1.2)
    ax2.set_xlabel("Vertices (n)"); ax2.set_ylabel("Pruning Events Count")
    ax2.set_title("Total Pruning Events"); ax2.grid(alpha=0.3, axis="y")

    save_fig(fig, "exp7_generator.png")


# ───────────────────────────────────────────────────────────────────────────────
# Experiment 8: MST — Edge count in spanning tree and tree weight
# ───────────────────────────────────────────────────────────────────────────────
def exp8_mst():
    print("\n[Exp 8] MST Kruskal — Spanning Tree Properties")
    sizes = list(range(5, 55, 5))
    rows = []
    mst_edges_count, total_weights = [], []

    for n in sizes:
        g = build_random_graph(n, edge_prob=0.5, seed=n * 7)
        vertices = list(g.vertices.values())
        edges = list(g.edges.values())

        mst_e, connected, weight = kruskal(vertices, edges)
        mst_edges_count.append(len(mst_e))
        total_weights.append(round(weight, 1))
        rows.append([n, len(edges), len(mst_e), round(weight, 1), 1 if connected else 0])

    write_csv("exp8_mst.csv",
              ["n", "total_edges", "mst_edges", "mst_weight", "connected"], rows)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Exp 8: Kruskal MST Properties", fontsize=14, fontweight="bold")

    ax1.plot(sizes, [n - 1 for n in sizes], "k--", alpha=0.5, label="V-1 (theoretical MST edges)")
    ax1.plot(sizes, mst_edges_count, "b-o", label="MST edges (actual)")
    ax1.set_xlabel("Vertices (n)"); ax1.set_ylabel("Edge Count")
    ax1.set_title("MST Edge Count"); ax1.legend(); ax1.grid(alpha=0.3)

    ax2.plot(sizes, total_weights, "g-s")
    ax2.set_xlabel("Vertices (n)"); ax2.set_ylabel("Total MST Weight")
    ax2.set_title("MST Total Edge Weight"); ax2.grid(alpha=0.3)

    save_fig(fig, "exp8_mst.png")


# ───────────────────────────────────────────────────────────────────────────────
# Master Runner
# ───────────────────────────────────────────────────────────────────────────────
def run_all_experiments():
    print("=" * 70)
    print("SMART RACING CHAMPIONSHIP — ALGORITHMIC EXPERIMENTS")
    print("=" * 70)
    exp1_traversal_ops()
    exp2_dijkstra_vs_astar()
    exp3_sorting_comparison()
    exp4_topk_vs_fullsort()
    exp5_knapsack()
    exp6_refuel_dp_state_space()
    exp7_generator_timing()
    exp8_mst()
    print("\n" + "=" * 70)
    print(f"All experiments complete. Results in: {RESULTS_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    run_all_experiments()
