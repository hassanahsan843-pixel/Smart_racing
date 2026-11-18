"""Championship Dashboard and Top-K Analytics Screen.

Displays race results, cumulative championship standings, interactive sort-method
switching (Merge Sort, Quick Sort, Heap Sort) showing identical rankings,
and Top-K heap analytics with benchmark timing against full sort.
"""

import time
import pygame
from typing import Dict, Any, Callable, List, Optional
from core.models import ChampionshipEntry, RaceResult
from algos.comparator import championship_sort_key
from algos.sorting import merge_sort, quick_sort, heap_sort
from algos.topk import top_k_heap, full_sort_topk


class DashboardScreen:
    """Championship Dashboard & Top-K Screen."""

    def __init__(self, app_state: Dict[str, Any], navigate_cb: Callable[[str], None]):
        self.state = app_state
        self.navigate = navigate_cb
        self.font_hdr = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_txt = pygame.font.SysFont("Arial", 15)
        self.font_hud = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_lbl = pygame.font.SysFont("Arial", 13)

        self.sort_methods = ["Merge Sort", "Quick Sort", "Heap Sort"]
        self.selected_sort_method = "Merge Sort"

        self.k_val: int = 3
        self.topk_time_ms: float = 0.0
        self.full_sort_time_ms: float = 0.0

        self.btn_back = pygame.Rect(30, 20, 100, 36)
        self.btn_k_minus = pygame.Rect(720, 290, 36, 30)
        self.btn_k_plus = pygame.Rect(800, 290, 36, 30)

        self.benchmark_topk()

    def get_entries(self) -> List[ChampionshipEntry]:
        results: List[RaceResult] = self.state.get("last_race_results", [])
        if not results:
            # Default placeholder championship participants
            return [
                ChampionshipEntry(1, "Player (Human)", total_points=75, wins=3, sum_positions=3, best_fastest_lap=105.9),
                ChampionshipEntry(2, "Bot 1 (Apex Cruiser)", total_points=54, wins=0, sum_positions=6, best_fastest_lap=108.4),
                ChampionshipEntry(3, "Bot 2 (Velocity Nitro)", total_points=45, wins=0, sum_positions=9, best_fastest_lap=107.1),
                ChampionshipEntry(4, "Bot 3 (Eco Optimizer)", total_points=36, wins=0, sum_positions=12, best_fastest_lap=112.5),
            ]

        # Convert results to championship entries
        entries = []
        for r in results:
            entries.append(ChampionshipEntry(
                racer_id=r.racer_id,
                racer_name=r.racer_name,
                total_points=r.points,
                wins=1 if r.finish_position == 1 and not r.dnf else 0,
                sum_positions=r.finish_position,
                best_fastest_lap=r.fastest_lap,
                race_results=[r],
            ))
        return entries

    def get_sorted_entries(self) -> List[ChampionshipEntry]:
        entries = self.get_entries()
        if self.selected_sort_method == "Quick Sort":
            return quick_sort(entries, key=championship_sort_key)
        elif self.selected_sort_method == "Heap Sort":
            return heap_sort(entries, key=championship_sort_key)
        else:
            return merge_sort(entries, key=championship_sort_key)

    def benchmark_topk(self) -> None:
        entries = self.get_entries() * 50  # scale up for measurable timing
        k = max(1, min(self.k_val, len(entries)))

        t0 = time.perf_counter()
        for _ in range(50):
            top_k_heap(entries, k=k, key=championship_sort_key)
        self.topk_time_ms = (time.perf_counter() - t0) * 1000.0 / 50.0

        t1 = time.perf_counter()
        for _ in range(50):
            full_sort_topk(entries, k=k, key=championship_sort_key)
        self.full_sort_time_ms = (time.perf_counter() - t1) * 1000.0 / 50.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if self.btn_back.collidepoint(mx, my):
                self.navigate("menu")
                return

            if self.btn_k_minus.collidepoint(mx, my):
                if self.k_val > 1:
                    self.k_val -= 1
                    self.benchmark_topk()
            elif self.btn_k_plus.collidepoint(mx, my):
                if self.k_val < 4:
                    self.k_val += 1
                    self.benchmark_topk()

            # Sort method selector
            sx = 30
            for method in self.sort_methods:
                rect = pygame.Rect(sx, 70, 140, 32)
                if rect.collidepoint(mx, my):
                    self.selected_sort_method = method
                    return
                sx += 150

    def update(self) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((16, 20, 30))

        # Header
        pygame.draw.rect(surface, (40, 50, 70), self.btn_back, border_radius=4)
        surface.blit(self.font_txt.render("< Menu", True, (255, 255, 255)), (self.btn_back.centerx - 22, self.btn_back.centery - 9))

        surface.blit(self.font_hdr.render("Championship Standings & Analytics", True, (255, 215, 0)), (150, 24))

        # Sort Method Buttons
        sx = 30
        for method in self.sort_methods:
            rect = pygame.Rect(sx, 70, 140, 32)
            active = (self.selected_sort_method == method)
            col = (40, 130, 80) if active else (30, 45, 70)
            pygame.draw.rect(surface, col, rect, border_radius=4)
            pygame.draw.rect(surface, (70, 180, 120) if active else (50, 70, 100), rect, width=1, border_radius=4)
            surface.blit(self.font_lbl.render(method, True, (255, 255, 255)), (rect.centerx - 38, rect.centery - 8))
            sx += 150

        # Standings Table (x: 30 to 690, y: 115 to 690)
        pygame.draw.rect(surface, (22, 28, 42), pygame.Rect(30, 115, 670, 575), border_radius=8)
        pygame.draw.rect(surface, (45, 60, 90), pygame.Rect(30, 115, 670, 575), width=1, border_radius=8)

        surface.blit(self.font_hdr.render("Current Championship Standings", True, (255, 215, 0)), (45, 130))
        surface.blit(self.font_lbl.render(f"Sorted using: {self.selected_sort_method} (All sorts produce identical total-order)", True, (160, 190, 230)), (45, 160))

        # Table Header
        ty = 195
        headers = ["Pos", "ID", "Competitor Name", "Points", "Wins", "Sum Pos", "Fastest Lap"]
        offsets = [45, 90, 140, 340, 420, 490, 570]
        for h_text, off_x in zip(headers, offsets):
            surface.blit(self.font_hud.render(h_text, True, (255, 255, 255)), (off_x, ty))

        pygame.draw.line(surface, (70, 90, 130), (45, ty + 24), (680, ty + 24), 2)
        ty += 35

        sorted_entries = self.get_sorted_entries()
        for pos, entry in enumerate(sorted_entries, 1):
            row_col = (50, 230, 80) if entry.racer_id == 1 else (210, 220, 240)
            surface.blit(self.font_txt.render(str(pos), True, row_col), (offsets[0], ty))
            surface.blit(self.font_txt.render(str(entry.racer_id), True, row_col), (offsets[1], ty))
            surface.blit(self.font_txt.render(entry.racer_name[:20], True, row_col), (offsets[2], ty))
            surface.blit(self.font_txt.render(str(entry.total_points), True, (255, 215, 0)), (offsets[3], ty))
            surface.blit(self.font_txt.render(str(entry.wins), True, row_col), (offsets[4], ty))
            surface.blit(self.font_txt.render(str(entry.sum_positions), True, row_col), (offsets[5], ty))
            f_str = f"{entry.best_fastest_lap:.2f}s" if entry.best_fastest_lap < float("inf") else "N/A"
            surface.blit(self.font_txt.render(f_str, True, row_col), (offsets[6], ty))
            ty += 32

        # Right Top-K Analytics Panel (x: 715 to 1000)
        rx = 715
        pygame.draw.rect(surface, (22, 28, 42), pygame.Rect(rx, 115, 290, 575), border_radius=8)
        pygame.draw.rect(surface, (45, 60, 90), pygame.Rect(rx, 115, 290, 575), width=1, border_radius=8)

        surface.blit(self.font_hdr.render("Top-K Analytics", True, (255, 215, 0)), (rx + 15, 130))
        surface.blit(self.font_txt.render("Heap Selection: O(n log k)", True, (160, 190, 230)), (rx + 15, 160))

        # Top-K Entries list
        topk_list = top_k_heap(self.get_entries(), k=self.k_val, key=championship_sort_key)
        ky = 195
        for rank, item in enumerate(topk_list, 1):
            surface.blit(self.font_txt.render(f"#{rank} {item.racer_name[:16]} ({item.total_points} pts)", True, (100, 240, 150)), (rx + 15, ky))
            ky += 24

        # K Selector Buttons
        surface.blit(self.font_hud.render(f"Choose k: {self.k_val}", True, (255, 255, 255)), (rx + 15, 295))
        pygame.draw.rect(surface, (40, 60, 90), self.btn_k_minus, border_radius=4)
        surface.blit(self.font_hud.render("-", True, (255, 255, 255)), (self.btn_k_minus.centerx - 5, self.btn_k_minus.centery - 10))

        pygame.draw.rect(surface, (40, 60, 90), self.btn_k_plus, border_radius=4)
        surface.blit(self.font_hud.render("+", True, (255, 255, 255)), (self.btn_k_plus.centerx - 5, self.btn_k_plus.centery - 10))

        # Benchmark Timing Comparison
        surface.blit(self.font_hdr.render("Performance Comparison", True, (255, 215, 0)), (rx + 15, 360))
        surface.blit(self.font_lbl.render("Evaluated on n=200 participants:", True, (170, 180, 200)), (rx + 15, 390))

        topk_str = f"top_k_heap (O(n log k)): {self.topk_time_ms:.4f} ms"
        full_str = f"full_sort (O(n log n)): {self.full_sort_time_ms:.4f} ms"
        surface.blit(self.font_txt.render(topk_str, True, (100, 255, 140)), (rx + 15, 420))
        surface.blit(self.font_txt.render(full_str, True, (255, 180, 80)), (rx + 15, 450))

        if self.full_sort_time_ms > 0:
            speedup = (self.full_sort_time_ms - self.topk_time_ms) / self.full_sort_time_ms * 100.0
            surface.blit(self.font_lbl.render(f"Bounded heap advantage: {max(0.0, speedup):.1f}% faster", True, (200, 240, 255)), (rx + 15, 485))
