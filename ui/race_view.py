"""Live Racing Simulation View Screen.

Renders track roads, dynamic events, cars progressing along graph edges,
player HUD (fuel bar, nitro charges, race clock, checkpoint status),
and live event ticker with road closure dynamic rerouting.
"""

import os
import pygame
from typing import Dict, Any, Callable, List, Optional, Tuple
from core.graph import Graph
from core.models import Racer, RaceResult, Event
import core.config as cfg
from engine.race import Race
from engine.opponents import create_standard_opponents
from data.circuits.loader import load_circuit_from_json


class RaceViewScreen:
    """Racing Screen."""

    def __init__(self, app_state: Dict[str, Any], navigate_cb: Callable[[str], None]):
        self.state = app_state
        self.navigate = navigate_cb
        self.font_hdr = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_txt = pygame.font.SysFont("Arial", 15)
        self.font_hud = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_lbl = pygame.font.SysFont("Arial", 12)

        self.race: Optional[Race] = None
        self.is_paused: bool = False
        self.sim_speed: int = 1  # 1x, 2x, 5x

        self.btn_back = pygame.Rect(30, 20, 100, 36)
        self.btn_pause = pygame.Rect(140, 20, 100, 36)
        self.btn_nitro = pygame.Rect(720, 20, 120, 36)
        self.btn_dash = pygame.Rect(860, 20, 140, 36)

        self.reset_race()

    def reset_race(self) -> None:
        cid = self.state.get("circuit_id", 1)
        preset = self.state.get("preset", "Balanced")
        laps = self.state.get("laps", 2)

        base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "circuits")
        circuit_path = os.path.join(base_dir, f"circuit{cid}.json")
        graph = load_circuit_from_json(circuit_path)

        human = Racer(id=1, name="Player (Human)", preset=preset, strategy="human")
        opponents = create_standard_opponents()
        racers = [human] + opponents

        self.race = Race(graph=graph, racers=racers, laps=laps, seed=42)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_n:
                self.activate_human_nitro()
            elif event.key == pygame.K_SPACE:
                self.is_paused = not self.is_paused

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.btn_back.collidepoint(mx, my):
                self.navigate("menu")
            elif self.btn_pause.collidepoint(mx, my):
                self.is_paused = not self.is_paused
            elif self.btn_nitro.collidepoint(mx, my):
                self.activate_human_nitro()
            elif self.btn_dash.collidepoint(mx, my):
                if self.race and self.race.is_finished():
                    self.navigate("dashboard")

    def activate_human_nitro(self) -> None:
        if self.race and self.race.racers:
            human = self.race.racers[0]
            if human.nitro_charges > 0 and human.nitro_active_timer <= 0:
                human.nitro_charges -= 1
                human.nitro_active_timer = cfg.NITRO_DURATION

    def update(self) -> None:
        if self.race and not self.is_paused and not self.race.is_finished():
            # Advance simulation
            for _ in range(self.sim_speed):
                self.race.step()
                if self.race.is_finished():
                    # Save results to state for dashboard
                    self.state["last_race_results"] = self.race.run()
                    break

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((14, 18, 28))

        # Top Bar
        pygame.draw.rect(surface, (40, 50, 70), self.btn_back, border_radius=4)
        surface.blit(self.font_txt.render("< Menu", True, (255, 255, 255)), (self.btn_back.centerx - 22, self.btn_back.centery - 9))

        pygame.draw.rect(surface, (50, 80, 120), self.btn_pause, border_radius=4)
        t_pause = "Resume" if self.is_paused else "Pause"
        surface.blit(self.font_txt.render(t_pause, True, (255, 255, 255)), (self.btn_pause.centerx - 22, self.btn_pause.centery - 9))

        # Nitro button
        human = self.race.racers[0] if self.race and self.race.racers else None
        can_nitro = human and human.nitro_charges > 0 and human.nitro_active_timer <= 0
        n_col = (140, 40, 200) if can_nitro else (60, 40, 80)
        pygame.draw.rect(surface, n_col, self.btn_nitro, border_radius=4)
        surface.blit(self.font_hud.render(f"Nitro [N] ({human.nitro_charges if human else 0})", True, (255, 255, 255)), (self.btn_nitro.centerx - 45, self.btn_nitro.centery - 9))

        if self.race and self.race.is_finished():
            pygame.draw.rect(surface, (30, 160, 80), self.btn_dash, border_radius=4)
            surface.blit(self.font_hud.render("View Standings >", True, (255, 255, 255)), (self.btn_dash.centerx - 55, self.btn_dash.centery - 9))

        # Race Track Canvas (left: 30 to 710, 70 to 690)
        pygame.draw.rect(surface, (20, 25, 38), pygame.Rect(30, 70, 680, 620), border_radius=8)
        pygame.draw.rect(surface, (40, 55, 80), pygame.Rect(30, 70, 680, 620), width=1, border_radius=8)

        if self.race:
            graph = self.race.graph

            def to_scr(px: float, py: float) -> Tuple[int, int]:
                return int(px * 0.72 + 50), int(py * 0.82 + 90)

            # Draw Roads
            for edge in graph.edges.values():
                u_v = graph.vertices.get(edge.from_node)
                v_v = graph.vertices.get(edge.to_node)
                if not u_v or not v_v:
                    continue
                p1 = to_scr(u_v.x, u_v.y)
                p2 = to_scr(v_v.x, v_v.y)

                if edge.status == "Blocked":
                    col = (220, 50, 50)
                    width = 4
                elif edge.status == "Restricted":
                    col = (240, 140, 20)
                    width = 3
                elif edge.isShortcut:
                    col = (50, 200, 240)
                    width = 3
                else:
                    col = (85, 100, 125)
                    width = 3
                pygame.draw.line(surface, col, p1, p2, width)

            # Draw Vertices
            for vid, v in graph.vertices.items():
                pos = to_scr(v.x, v.y)
                if v.type == "start":
                    v_col = (0, 220, 100)
                elif v.type == "checkpoint":
                    v_col = (0, 180, 240)
                elif v.type == "station":
                    v_col = (255, 200, 30) if v.active else (100, 100, 100)
                elif v.type == "nitro":
                    v_col = (180, 50, 240) if v.active else (100, 100, 100)
                elif v.type == "dead_end":
                    v_col = (160, 40, 40)
                else:
                    v_col = (130, 145, 165)

                pygame.draw.circle(surface, v_col, pos, 8)
                label = str(v.checkpointOrder) if v.checkpointOrder else (v.type[:2].upper() if v.type != "regular" else "")
                if label:
                    t_lbl = self.font_lbl.render(label, True, (255, 255, 255))
                    surface.blit(t_lbl, (pos[0] - t_lbl.get_width() // 2, pos[1] - t_lbl.get_height() // 2))

            # Draw Cars
            car_colors = [
                (50, 230, 50),   # P1 (Human): Bright Green
                (240, 60, 60),   # B1 (Apex): Red
                (60, 140, 255),  # B2 (Velocity): Blue
                (255, 180, 30),  # B3 (Eco): Orange
            ]
            car_names = ["P1", "B1", "B2", "B3"]

            for idx, r in enumerate(self.race.racers):
                if r.finished and not r.dnf:
                    # Car finished at finish line
                    c_pos = to_scr(graph.vertices[self.race.finish_vid].x, graph.vertices[self.race.finish_vid].y)
                elif r.planned_route and len(r.planned_route) >= 2:
                    u_v = graph.vertices.get(r.planned_route[0])
                    v_v = graph.vertices.get(r.planned_route[1])
                    if u_v and v_v:
                        p1 = to_scr(u_v.x, u_v.y)
                        p2 = to_scr(v_v.x, v_v.y)
                        prg = r.edge_progress
                        cx = int(p1[0] + prg * (p2[0] - p1[0]))
                        cy = int(p1[1] + prg * (p2[1] - p1[1]))
                        c_pos = (cx, cy)
                    else:
                        c_pos = to_scr(graph.vertices[r.current_vertex].x, graph.vertices[r.current_vertex].y)
                else:
                    c_pos = to_scr(graph.vertices[r.current_vertex].x, graph.vertices[r.current_vertex].y)

                # Offset slightly so overlapping cars remain visible
                off_x = (idx % 2) * 8 - 4
                off_y = (idx // 2) * 8 - 4
                c_pos = (c_pos[0] + off_x, c_pos[1] + off_y)

                pygame.draw.circle(surface, car_colors[idx], c_pos, 7)
                pygame.draw.circle(surface, (255, 255, 255), c_pos, 7, width=1)
                t_c = self.font_lbl.render(car_names[idx], True, (0, 0, 0))
                surface.blit(t_c, (c_pos[0] - t_c.get_width() // 2, c_pos[1] - t_c.get_height() // 2))

        # Right HUD Panel (x in [725, 1000])
        hx = 725
        pygame.draw.rect(surface, (20, 25, 38), pygame.Rect(hx, 70, 275, 620), border_radius=8)
        pygame.draw.rect(surface, (40, 55, 80), pygame.Rect(hx, 70, 275, 620), width=1, border_radius=8)

        # Race Timer & Laps
        if self.race:
            t_clock = self.font_hdr.render(f"Clock: {self.race.current_time:.1f} s", True, (255, 215, 0))
            surface.blit(t_clock, (hx + 15, 85))

            if human:
                lap_str = f"Lap: {human.completed_laps + 1} / {self.race.target_laps}"
                if human.finished:
                    lap_str = "Status: FINISHED"
                elif human.dnf:
                    lap_str = "Status: DNF"
                surface.blit(self.font_hud.render(lap_str, True, (100, 240, 150)), (hx + 15, 115))

                # Next target checkpoint
                surface.blit(self.font_txt.render(f"Next Target: CP {human.next_checkpoint_idx}", True, (180, 200, 230)), (hx + 15, 140))

                # Fuel Gauge Bar
                surface.blit(self.font_txt.render("Fuel Level:", True, (220, 220, 220)), (hx + 15, 170))
                pygame.draw.rect(surface, (40, 45, 55), pygame.Rect(hx + 15, 190, 240, 18), border_radius=4)
                fuel_pct = max(0.0, min(1.0, human.fuel / cfg.MAX_FUEL))
                f_bar_col = (50, 220, 80) if fuel_pct > 0.25 else (230, 50, 50)
                pygame.draw.rect(surface, f_bar_col, pygame.Rect(hx + 15, 190, int(240 * fuel_pct), 18), border_radius=4)
                surface.blit(self.font_lbl.render(f"{human.fuel:.1f} / 100", True, (255, 255, 255)), (hx + 110, 192))

                # Nitro Boost Bar
                surface.blit(self.font_txt.render("Nitro Boost:", True, (220, 220, 220)), (hx + 15, 220))
                for s in range(cfg.MAX_NITRO_CHARGES):
                    n_rect = pygame.Rect(hx + 15 + s * 80, 240, 72, 16)
                    active_n = (s < human.nitro_charges)
                    pygame.draw.rect(surface, (160, 50, 220) if active_n else (50, 40, 65), n_rect, border_radius=3)
                    pygame.draw.rect(surface, (200, 120, 255) if active_n else (80, 70, 95), n_rect, width=1, border_radius=3)

        # Standings Leaderboard in Race
        surface.blit(self.font_hdr.render("Live Standings", True, (255, 215, 0)), (hx + 15, 275))
        if self.race:
            racers_sorted = sorted(self.race.racers, key=lambda r: (-r.completed_laps, -r.completed_checkpoints, r.total_time))
            ly = 305
            for rank, r in enumerate(racers_sorted, 1):
                col = (50, 230, 50) if r.id == 1 else (200, 210, 230)
                txt = f"{rank}. {r.name[:18]:<18} L{r.completed_laps} CP{r.completed_checkpoints}"
                surface.blit(self.font_txt.render(txt, True, col), (hx + 15, ly))
                ly += 22

        # Live Event Feed Ticker
        surface.blit(self.font_hdr.render("Event Log", True, (255, 215, 0)), (hx + 15, 415))
        pygame.draw.rect(surface, (12, 15, 24), pygame.Rect(hx + 15, 445, 245, 230), border_radius=4)
        if self.race:
            events_to_show = self.race.event_log[-9:]
            ey = 450
            for line in events_to_show:
                surface.blit(self.font_lbl.render(line[:36], True, (240, 200, 100)), (hx + 20, ey))
                ey += 24
