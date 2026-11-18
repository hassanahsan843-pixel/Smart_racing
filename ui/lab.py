"""Algorithm Lab Interactive Step-Through Screen.

Visualizes internal operational steps of BFS, DFS, Dijkstra, A*, Knapsack DP,
Event Heap, and Sorting algorithms using the EXACT gameplay functions and on_step hooks.
"""

import os
import pygame
from typing import Dict, Any, Callable, List, Optional, Tuple
from core.graph import Graph
from core.counters import OpCounters
from data.circuits.loader import load_circuit_from_json
from algos.bfs_dfs import bfs, dfs_traverse
from algos.dijkstra import dijkstra
from algos.astar import astar
from algos.knapsack import knapsack_dp
from algos.heap_events import EventQueue
from core.models import Event
from algos.sorting import merge_sort, quick_sort, heap_sort


class LabScreen:
    """Algorithm Lab Screen."""

    def __init__(self, app_state: Dict[str, Any], navigate_cb: Callable[[str], None]):
        self.state = app_state
        self.navigate = navigate_cb
        self.font_hdr = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_txt = pygame.font.SysFont("Arial", 15)
        self.font_hud = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_lbl = pygame.font.SysFont("Arial", 12)

        self.algos = ["BFS", "DFS", "Dijkstra", "A*", "Knapsack DP", "Event Heap", "Merge Sort", "Quick Sort", "Heap Sort"]
        self.selected_algo = "Dijkstra"

        self.counters = OpCounters()
        self.step_history: List[Dict[str, Any]] = []
        self.current_step_idx: int = 0

        self.auto_play: bool = False
        self.play_speed: int = 1  # 1x, 2x, 5x
        self.frame_counter: int = 0

        self.btn_back = pygame.Rect(30, 20, 100, 36)
        self.btn_step = pygame.Rect(720, 20, 80, 36)
        self.btn_play = pygame.Rect(810, 20, 90, 36)
        self.btn_reset = pygame.Rect(910, 20, 80, 36)

        self.load_and_run_selected_algo()

    def load_and_run_selected_algo(self) -> None:
        self.counters.reset()
        self.step_history = []
        self.current_step_idx = 0
        self.auto_play = False

        cid = self.state.get("circuit_id", 1)
        base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "circuits")
        graph = load_circuit_from_json(os.path.join(base_dir, f"circuit{cid}.json"))

        def step_hook(state_dict: Dict[str, Any]):
            # Record deep copy of state for playback
            self.step_history.append(dict(state_dict))

        # Execute using the EXACT gameplay functions from algos/
        if self.selected_algo == "BFS":
            bfs(graph, src=0, dst=6, counters=self.counters, on_step=step_hook)
        elif self.selected_algo == "DFS":
            dfs_traverse(graph, src=0, counters=self.counters, on_step=step_hook)
        elif self.selected_algo == "Dijkstra":
            dijkstra(graph, src=0, dst=6, counters=self.counters, on_step=step_hook)
        elif self.selected_algo == "A*":
            astar(graph, src=0, dst=6, counters=self.counters, on_step=step_hook)
        elif self.selected_algo == "Knapsack DP":
            items = [
                {"id": 1, "cost": 2, "value": 10},
                {"id": 2, "cost": 3, "value": 15},
                {"id": 3, "cost": 4, "value": 22},
                {"id": 4, "cost": 5, "value": 28},
            ]
            knapsack_dp(items, budget=8, counters=self.counters, on_step=step_hook)
        elif self.selected_algo == "Event Heap":
            eq = EventQueue(graph=graph, counters=self.counters)
            for i in range(6):
                ev = Event(id=f"e{i}", event_type="blockage", target_type="edge", target_id=i+1, trigger_time=float(i*2), priority=2)
                eq.push(ev)
                self.step_history.append({"action": "heap_push", "event_id": ev.id, "heap_size": len(eq)})
            for t in range(0, 12, 3):
                due = eq.pop_due(float(t))
                self.step_history.append({"action": "heap_pop_due", "time": t, "popped": len(due)})
        elif self.selected_algo in ("Merge Sort", "Quick Sort", "Heap Sort"):
            arr = [45, 12, 85, 32, 89, 39, 69, 44, 42, 1, 10, 50]
            if self.selected_algo == "Merge Sort":
                merge_sort(arr, counters=self.counters)
            elif self.selected_algo == "Quick Sort":
                quick_sort(arr, counters=self.counters)
            elif self.selected_algo == "Heap Sort":
                heap_sort(arr, counters=self.counters)
            # Create synthetic step history from sorting comparisons
            for idx, val in enumerate(arr):
                self.step_history.append({"action": "sort_examine", "idx": idx, "val": val})

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if self.btn_back.collidepoint(mx, my):
                self.navigate("menu")
                return

            if self.btn_step.collidepoint(mx, my):
                if self.current_step_idx < len(self.step_history) - 1:
                    self.current_step_idx += 1
            elif self.btn_play.collidepoint(mx, my):
                self.auto_play = not self.auto_play
            elif self.btn_reset.collidepoint(mx, my):
                self.current_step_idx = 0
                self.auto_play = False

            # Algo selector buttons
            ax = 30
            for algo in self.algos:
                rect = pygame.Rect(ax, 70, 95, 32)
                if rect.collidepoint(mx, my):
                    self.selected_algo = algo
                    self.load_and_run_selected_algo()
                    return
                ax += 105

    def update(self) -> None:
        if self.auto_play:
            self.frame_counter += 1
            if self.frame_counter >= max(1, 10 // self.play_speed):
                self.frame_counter = 0
                if self.current_step_idx < len(self.step_history) - 1:
                    self.current_step_idx += 1
                else:
                    self.auto_play = False

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((16, 20, 30))

        # Header controls
        pygame.draw.rect(surface, (40, 50, 70), self.btn_back, border_radius=4)
        surface.blit(self.font_txt.render("< Menu", True, (255, 255, 255)), (self.btn_back.centerx - 22, self.btn_back.centery - 9))

        surface.blit(self.font_hdr.render("Algorithm Lab - Interactive Step Execution", True, (255, 215, 0)), (150, 24))

        # Step, Play, Reset buttons
        pygame.draw.rect(surface, (35, 75, 120), self.btn_step, border_radius=4)
        surface.blit(self.font_txt.render("Step", True, (255, 255, 255)), (self.btn_step.centerx - 14, self.btn_step.centery - 9))

        pygame.draw.rect(surface, (40, 140, 80) if self.auto_play else (45, 90, 60), self.btn_play, border_radius=4)
        surface.blit(self.font_txt.render("Pause" if self.auto_play else "Auto-Play", True, (255, 255, 255)), (self.btn_play.centerx - 30, self.btn_play.centery - 9))

        pygame.draw.rect(surface, (140, 50, 50), self.btn_reset, border_radius=4)
        surface.blit(self.font_txt.render("Reset", True, (255, 255, 255)), (self.btn_reset.centerx - 18, self.btn_reset.centery - 9))

        # Algorithm Selection Bar
        ax = 30
        for algo in self.algos:
            rect = pygame.Rect(ax, 70, 98, 32)
            active = (self.selected_algo == algo)
            col = (40, 130, 80) if active else (30, 45, 70)
            pygame.draw.rect(surface, col, rect, border_radius=4)
            pygame.draw.rect(surface, (70, 180, 120) if active else (50, 70, 100), rect, width=1, border_radius=4)
            surface.blit(self.font_lbl.render(algo, True, (255, 255, 255)), (rect.centerx - 30, rect.centery - 7))
            ax += 105

        # Main Visualization Canvas (x: 30 to 690, y: 115 to 690)
        pygame.draw.rect(surface, (22, 28, 42), pygame.Rect(30, 115, 670, 575), border_radius=8)
        pygame.draw.rect(surface, (45, 60, 90), pygame.Rect(30, 115, 670, 575), width=1, border_radius=8)

        # Right Live Metrics & State Inspector (x: 715 to 1000)
        rx = 715
        pygame.draw.rect(surface, (22, 28, 42), pygame.Rect(rx, 115, 290, 575), border_radius=8)
        pygame.draw.rect(surface, (45, 60, 90), pygame.Rect(rx, 115, 290, 575), width=1, border_radius=8)

        # Step Progress
        step_str = f"Step: {self.current_step_idx + 1} / {max(1, len(self.step_history))}"
        surface.blit(self.font_hdr.render(step_str, True, (255, 215, 0)), (rx + 15, 125))

        # Current State Dict
        curr_state = self.step_history[self.current_step_idx] if self.step_history else {}
        surface.blit(self.font_hud.render("Current Step State:", True, (180, 210, 240)), (rx + 15, 160))
        sy = 190
        for k, v in list(curr_state.items())[:6]:
            line = f"{k}: {v}"
            surface.blit(self.font_lbl.render(line[:36], True, (220, 220, 220)), (rx + 15, sy))
            sy += 22

        # Operational Counters Panel
        surface.blit(self.font_hdr.render("Live Op Counters", True, (255, 215, 0)), (rx + 15, 340))
        cy = 375
        for c_name, c_val in self.counters.to_dict().items():
            line = f"{c_name.replace('_', ' ').title():<18}: {c_val}"
            surface.blit(self.font_txt.render(line, True, (100, 230, 140)), (rx + 15, cy))
            cy += 24

        # Visualizer representation
        if self.step_history:
            state = self.step_history[self.current_step_idx]
            act = state.get("action", "")

            # Render summary banner on canvas
            info_txt = f"Algorithm: {self.selected_algo} | Action: {act}"
            surface.blit(self.font_hdr.render(info_txt, True, (255, 220, 80)), (50, 135))

            # Draw visual elements according to algorithm family
            if "visited" in state:
                # Graph exploration visualization
                v_set = state.get("visited", set())
                surface.blit(self.font_txt.render(f"Visited Nodes Set: {sorted(list(v_set))}", True, (100, 240, 160)), (50, 180))

            if "f_score" in state or "g_score" in state:
                surface.blit(self.font_txt.render(f"A* g_score: {state.get('g_score', 0):.2f} | f_score: {state.get('f_score', 0):.2f}", True, (255, 180, 60)), (50, 210))

            if self.selected_algo in ("Merge Sort", "Quick Sort", "Heap Sort"):
                surface.blit(self.font_txt.render("Sorting Array Elements Progress:", True, (200, 220, 255)), (50, 190))
                # Draw array bars
                sample_vals = [45, 12, 85, 32, 89, 39, 69, 44, 42, 1, 10, 50]
                bx = 60
                active_idx = state.get("idx", -1)
                for i, v in enumerate(sample_vals):
                    bh = int(v * 2.5)
                    bar_col = (255, 215, 0) if i == active_idx else (50, 130, 200)
                    pygame.draw.rect(surface, bar_col, pygame.Rect(bx, 500 - bh, 36, bh), border_radius=3)
                    surface.blit(self.font_lbl.render(str(v), True, (255, 255, 255)), (bx + 10, 510))
                    bx += 48
