"""Track Explorer and Route Planner Screen.

Visualizes track topologies, handles vertex selection, executes BFS, DFS, Dijkstra,
and A*, displays alternative routes, preset comparisons, and resource recommendations.
"""

import os
import pygame
from typing import Dict, Any, Callable, List, Optional, Tuple
from core.graph import Graph
from core.models import Vertex, Edge
from core.cost import CircuitReferenceValues, edge_cost
from core.counters import OpCounters
from data.circuits.loader import load_circuit_from_json
from algos.bfs_dfs import bfs, dfs_traverse, alternative_routes
from algos.dijkstra import dijkstra
from algos.astar import astar
from algos.knapsack import knapsack_dp
from algos.greedy import greedy_knapsack
from algos.refuel_dp import refuel_dp


class ExplorerScreen:
    """Track Explorer Screen."""

    def __init__(self, app_state: Dict[str, Any], navigate_cb: Callable[[str], None]):
        self.state = app_state
        self.navigate = navigate_cb
        self.font_hdr = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_txt = pygame.font.SysFont("Arial", 15)
        self.font_lbl = pygame.font.SysFont("Arial", 13)

        self.graph: Optional[Graph] = None
        self.current_circuit_loaded: int = -1

        self.selected_src: Optional[int] = 0
        self.selected_dst: Optional[int] = 4
        self.highlighted_path: Optional[List[int]] = None
        self.alt_paths: List[List[int]] = []
        self.active_algo: str = "dijkstra"
        self.status_message: str = "Select two vertices and click an algorithm."

        self.route_metrics: Dict[str, float] = {}
        self.preset_costs: Dict[str, float] = {}
        self.recommendations: Dict[str, Any] = {}

        self.btn_back = pygame.Rect(30, 20, 100, 36)
        self.btn_bfs = pygame.Rect(720, 70, 70, 32)
        self.btn_dfs = pygame.Rect(800, 70, 70, 32)
        self.btn_dijk = pygame.Rect(880, 70, 80, 32)
        self.btn_astar = pygame.Rect(970, 70, 70, 32)

        self.load_active_circuit()

    def load_active_circuit(self) -> None:
        cid = self.state.get("circuit_id", 1)
        if cid != self.current_circuit_loaded:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "circuits")
            p = os.path.join(base_dir, f"circuit{cid}.json")
            if os.path.exists(p):
                self.graph = load_circuit_from_json(p)
                self.current_circuit_loaded = cid
                self.run_current_algo()

    def run_current_algo(self) -> None:
        if self.graph is None or self.selected_src is None or self.selected_dst is None:
            return

        preset = self.state.get("preset", "Balanced")
        ref = CircuitReferenceValues.from_graph(self.graph)
        src = self.selected_src
        dst = self.selected_dst

        path = None
        cost, dist, time = 0.0, 0.0, 0.0

        if self.active_algo == "bfs":
            visited, parent, path = bfs(self.graph, src=src, dst=dst)
            if path:
                self.status_message = f"BFS: Found min-hop path ({len(path)-1} edges)."
            else:
                self.status_message = "BFS: Target is UNREACHABLE."

        elif self.active_algo == "dfs":
            order = dfs_traverse(self.graph, src=src)
            _, _, path = bfs(self.graph, src=src, dst=dst)
            self.status_message = f"DFS: Traversal order explored {len(order)} vertices."

        elif self.active_algo == "dijkstra":
            path, cost, dist, time = dijkstra(self.graph, src=src, dst=dst, preset=preset, ref=ref)
            if path:
                self.status_message = f"Dijkstra: Optimal cost={cost:.3f}, dist={dist:.1f}m, time={time:.1f}s."
            else:
                self.status_message = "Dijkstra: Target is UNREACHABLE."

        elif self.active_algo == "astar":
            path, cost, dist, time = astar(self.graph, src=src, dst=dst, preset=preset, ref=ref)
            if path:
                self.status_message = f"A*: Optimal cost={cost:.3f}, dist={dist:.1f}m, time={time:.1f}s."
            else:
                self.status_message = "A*: Target is UNREACHABLE."

        self.highlighted_path = path

        if path:
            # Metrics
            edges_in_path = []
            for i in range(len(path) - 1):
                e = self.graph.find_edge(path[i], path[i + 1])
                if e:
                    edges_in_path.append(e)

            dist_val = sum(e.distance for e in edges_in_path)
            time_val = sum(e.baseTime for e in edges_in_path)
            self.route_metrics = {
                "distance": dist_val,
                "time": time_val,
                "edges": len(edges_in_path),
            }

            # Preset comparison
            self.preset_costs = {}
            for p_name in ["Balanced", "Speed", "Economy", "Safety"]:
                total_p_cost = sum(edge_cost(e, preset=p_name, ref=ref) for e in edges_in_path)
                self.preset_costs[p_name] = total_p_cost

            # Alternative routes
            self.alt_paths = alternative_routes(self.graph, start=src, finish=dst, main_route=path, max_routes=3)

            # Resource Recommendations
            bonus_items = [
                {"id": "Nitro", "cost": 3, "value": 15.0},
                {"id": "Shield", "cost": 2, "value": 8.0},
                {"id": "Aero", "cost": 4, "value": 18.0},
                {"id": "FuelPack", "cost": 5, "value": 24.0},
            ]
            dp_v, dp_ids, _ = knapsack_dp(bonus_items, budget=7)
            gr_v, gr_ids = greedy_knapsack(bonus_items, budget=7)
            self.recommendations["knapsack_dp"] = (dp_v, dp_ids)
            self.recommendations["knapsack_greedy"] = (gr_v, gr_ids)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if self.btn_back.collidepoint(mx, my):
                self.navigate("menu")
                return

            # Algo buttons
            if self.btn_bfs.collidepoint(mx, my):
                self.active_algo = "bfs"
                self.run_current_algo()
            elif self.btn_dfs.collidepoint(mx, my):
                self.active_algo = "dfs"
                self.run_current_algo()
            elif self.btn_dijk.collidepoint(mx, my):
                self.active_algo = "dijkstra"
                self.run_current_algo()
            elif self.btn_astar.collidepoint(mx, my):
                self.active_algo = "astar"
                self.run_current_algo()

            # Vertex selection click on canvas
            if self.graph:
                for vid, v in self.graph.vertices.items():
                    # Canvas mapping: x in [0, 850], y in [0, 650] -> screen [40, 680], [80, 680]
                    vx = int(v.x * 0.75 + 40)
                    vy = int(v.y * 0.85 + 80)
                    if (mx - vx) ** 2 + (my - vy) ** 2 <= 144:  # radius 12
                        if self.selected_src is None or (self.selected_src is not None and self.selected_dst is not None):
                            self.selected_src = vid
                            self.selected_dst = None
                        elif self.selected_dst is None and vid != self.selected_src:
                            self.selected_dst = vid
                            self.run_current_algo()
                        break

    def update(self) -> None:
        self.load_active_circuit()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((16, 20, 30))

        # Header bar
        pygame.draw.rect(surface, (40, 50, 70), self.btn_back, border_radius=4)
        t_back = self.font_txt.render("< Back", True, (255, 255, 255))
        surface.blit(t_back, (self.btn_back.centerx - t_back.get_width() // 2, self.btn_back.centery - t_back.get_height() // 2))

        cid = self.state.get("circuit_id", 1)
        t_title = self.font_hdr.render(f"Track Explorer - Circuit {cid}", True, (255, 215, 0))
        surface.blit(t_title, (160, 24))

        # Algorithm buttons
        for btn, name, label in [
            (self.btn_bfs, "bfs", "BFS"),
            (self.btn_dfs, "dfs", "DFS"),
            (self.btn_dijk, "dijkstra", "Dijkstra"),
            (self.btn_astar, "astar", "A*"),
        ]:
            active = (self.active_algo == name)
            col = (40, 140, 80) if active else (35, 55, 90)
            pygame.draw.rect(surface, col, btn, border_radius=4)
            pygame.draw.rect(surface, (80, 200, 120) if active else (70, 90, 130), btn, width=1, border_radius=4)
            t = self.font_txt.render(label, True, (255, 255, 255))
            surface.blit(t, (btn.centerx - t.get_width() // 2, btn.centery - t.get_height() // 2))

        # Draw circuit graph on canvas (left area: x in [30, 690], y in [70, 690])
        pygame.draw.rect(surface, (22, 28, 42), pygame.Rect(30, 70, 670, 620), border_radius=8)
        pygame.draw.rect(surface, (45, 60, 90), pygame.Rect(30, 70, 670, 620), width=1, border_radius=8)

        if self.graph:
            # Map coordinates
            def to_scr(px: float, py: float) -> Tuple[int, int]:
                return int(px * 0.72 + 50), int(py * 0.82 + 90)

            # Draw edges
            highlighted_edges = set()
            if self.highlighted_path and len(self.highlighted_path) >= 2:
                for i in range(len(self.highlighted_path) - 1):
                    highlighted_edges.add((self.highlighted_path[i], self.highlighted_path[i + 1]))
                    highlighted_edges.add((self.highlighted_path[i + 1], self.highlighted_path[i]))

            for edge in self.graph.edges.values():
                u_v = self.graph.vertices.get(edge.from_node)
                v_v = self.graph.vertices.get(edge.to_node)
                if not u_v or not v_v:
                    continue

                p1 = to_scr(u_v.x, u_v.y)
                p2 = to_scr(v_v.x, v_v.y)

                is_hl = (edge.from_node, edge.to_node) in highlighted_edges
                if is_hl:
                    col = (255, 220, 40)
                    width = 4
                elif edge.status == "Blocked":
                    col = (220, 50, 50)
                    width = 2
                elif edge.status == "Restricted":
                    col = (230, 140, 30)
                    width = 2
                elif edge.isShortcut:
                    col = (50, 180, 240)
                    width = 2
                else:
                    col = (90, 110, 140)
                    width = 2

                pygame.draw.line(surface, col, p1, p2, width)

            # Draw vertices
            for vid, v in self.graph.vertices.items():
                pos = to_scr(v.x, v.y)
                # Vertex color
                if vid == self.selected_src:
                    v_col = (50, 230, 50)  # green for source
                elif vid == self.selected_dst:
                    v_col = (240, 50, 50)  # red for destination
                elif self.highlighted_path and vid in self.highlighted_path:
                    v_col = (255, 215, 0)  # gold
                elif v.type == "start":
                    v_col = (0, 200, 100)
                elif v.type == "checkpoint":
                    v_col = (0, 180, 240)
                elif v.type == "station":
                    v_col = (240, 200, 40)
                elif v.type == "nitro":
                    v_col = (180, 60, 240)
                elif v.type == "dead_end":
                    v_col = (140, 30, 30)
                else:
                    v_col = (160, 180, 200)

                pygame.draw.circle(surface, v_col, pos, 10)
                pygame.draw.circle(surface, (255, 255, 255), pos, 10, width=1)

                # Label text
                label = str(v.checkpointOrder) if v.checkpointOrder else (v.type[:2].upper() if v.type != "regular" else str(vid))
                t_lbl = self.font_lbl.render(label, True, (255, 255, 255))
                surface.blit(t_lbl, (pos[0] - t_lbl.get_width() // 2, pos[1] - t_lbl.get_height() // 2))

        # Right sidebar: Metrics, Presets, and Recommendations (x in [720, 1000])
        rx = 715
        pygame.draw.rect(surface, (22, 28, 42), pygame.Rect(rx, 115, 290, 575), border_radius=8)
        pygame.draw.rect(surface, (45, 60, 90), pygame.Rect(rx, 115, 290, 575), width=1, border_radius=8)

        # Status message
        t_st = self.font_txt.render(self.status_message, True, (240, 220, 140))
        surface.blit(t_st, (rx + 10, 125))

        # Selection info
        src_lbl = f"Source: {self.selected_src if self.selected_src is not None else 'None'}"
        dst_lbl = f"Target: {self.selected_dst if self.selected_dst is not None else 'None'}"
        surface.blit(self.font_txt.render(src_lbl, True, (100, 255, 100)), (rx + 10, 155))
        surface.blit(self.font_txt.render(dst_lbl, True, (255, 120, 120)), (rx + 150, 155))

        # Route Metrics Table
        surface.blit(self.font_hdr.render("Route Metrics", True, (255, 215, 0)), (rx + 10, 185))
        dist_s = f"Distance: {self.route_metrics.get('distance', 0.0):.1f} m"
        time_s = f"Est Time: {self.route_metrics.get('time', 0.0):.1f} s"
        edge_s = f"Edge Hops: {self.route_metrics.get('edges', 0)}"
        surface.blit(self.font_txt.render(dist_s, True, (220, 220, 220)), (rx + 10, 215))
        surface.blit(self.font_txt.render(time_s, True, (220, 220, 220)), (rx + 10, 235))
        surface.blit(self.font_txt.render(edge_s, True, (220, 220, 220)), (rx + 10, 255))

        # Preset Comparison Table
        surface.blit(self.font_hdr.render("Preset Scalar Cost", True, (255, 215, 0)), (rx + 10, 290))
        py_off = 320
        for p_name, p_cost in self.preset_costs.items():
            line = f"{p_name:<10}: {p_cost:.3f}"
            is_active_preset = (p_name == self.state.get("preset"))
            c = (80, 240, 120) if is_active_preset else (200, 200, 200)
            surface.blit(self.font_txt.render(line, True, c), (rx + 10, py_off))
            py_off += 22

        # Alternative Routes
        surface.blit(self.font_hdr.render(f"Alt Routes ({len(self.alt_paths)})", True, (255, 215, 0)), (rx + 10, py_off + 10))
        py_off += 35
        for idx, alt in enumerate(self.alt_paths[:2], 1):
            line = f"Alt {idx}: {'->'.join(str(n) for n in alt[:6])}..."
            surface.blit(self.font_lbl.render(line, True, (170, 190, 220)), (rx + 10, py_off))
            py_off += 20

        # Resource Recommendations (Knapsack DP vs Greedy)
        surface.blit(self.font_hdr.render("Resource Optimization", True, (255, 215, 0)), (rx + 10, py_off + 10))
        py_off += 35
        if "knapsack_dp" in self.recommendations:
            dp_v, dp_ids = self.recommendations["knapsack_dp"]
            gr_v, gr_ids = self.recommendations["knapsack_greedy"]
            surface.blit(self.font_txt.render(f"DP Knapsack: val={dp_v:.0f} {dp_ids}", True, (100, 255, 150)), (rx + 10, py_off))
            surface.blit(self.font_txt.render(f"Greedy Knapsack: val={gr_v:.0f} {gr_ids}", True, (240, 180, 100)), (rx + 10, py_off + 22))
