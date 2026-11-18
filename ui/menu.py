"""Main Menu GUI Screen.

Provides navigation to Championship, Quick Race, Track Explorer, Algorithm Lab,
Instructions, and configuration settings (Preset, Laps, Circuit).
"""

import pygame
from typing import Dict, Any, Callable


class MenuScreen:
    """Main Menu Screen."""

    def __init__(self, app_state: Dict[str, Any], navigate_cb: Callable[[str], None]):
        self.state = app_state
        self.navigate = navigate_cb
        self.font_title = pygame.font.SysFont("Arial", 38, bold=True)
        self.font_btn = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_info = pygame.font.SysFont("Arial", 16)

        # Buttons definition: (label, action_id, rect)
        self.buttons = [
            ("Start Championship (3 Circuits)", "championship", pygame.Rect(360, 200, 360, 48)),
            ("Quick Race (Current Circuit)", "quick_race", pygame.Rect(360, 260, 360, 48)),
            ("Track Explorer & Route Planner", "explorer", pygame.Rect(360, 320, 360, 48)),
            ("Algorithm Lab (Step-by-Step)", "lab", pygame.Rect(360, 380, 360, 48)),
            ("Championship Dashboard & Top-K", "dashboard", pygame.Rect(360, 440, 360, 48)),
        ]

        # Presets selector
        self.presets = ["Balanced", "Speed", "Economy", "Safety"]
        self.circuits = [1, 2, 3]
        self.laps_options = [1, 2, 3]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Main buttons
            for label, act, rect in self.buttons:
                if rect.collidepoint(mx, my):
                    self.navigate(act)
                    return

            # Preset toggle buttons
            for idx, p in enumerate(self.presets):
                p_rect = pygame.Rect(360 + idx * 92, 530, 88, 34)
                if p_rect.collidepoint(mx, my):
                    self.state["preset"] = p

            # Laps toggle buttons
            for idx, l in enumerate(self.laps_options):
                l_rect = pygame.Rect(450 + idx * 80, 580, 70, 34)
                if l_rect.collidepoint(mx, my):
                    self.state["laps"] = l

            # Circuit selector buttons
            for idx, c in enumerate(self.circuits):
                c_rect = pygame.Rect(450 + idx * 80, 630, 70, 34)
                if c_rect.collidepoint(mx, my):
                    self.state["circuit_id"] = c

    def update(self) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 24, 34))

        # Title
        title_surf = self.font_title.render("SMART RACING CHAMPIONSHIP", True, (255, 215, 0))
        surface.blit(title_surf, (surface.get_width() // 2 - title_surf.get_width() // 2, 60))

        sub_surf = self.font_info.render("Design & Analysis of Algorithms - 12 Mandatory Algorithm Families", True, (170, 185, 205))
        surface.blit(sub_surf, (surface.get_width() // 2 - sub_surf.get_width() // 2, 115))

        # Navigation buttons
        mouse_pos = pygame.mouse.get_pos()
        for label, act, rect in self.buttons:
            hover = rect.collidepoint(mouse_pos)
            bg_color = (45, 90, 160) if hover else (32, 60, 110)
            pygame.draw.rect(surface, bg_color, rect, border_radius=6)
            pygame.draw.rect(surface, (70, 130, 220), rect, width=2, border_radius=6)

            text_surf = self.font_btn.render(label, True, (255, 255, 255))
            surface.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))

        # Settings Panel
        lbl_p = self.font_info.render("Route Cost Preset:", True, (220, 220, 220))
        surface.blit(lbl_p, (200, 536))
        for idx, p in enumerate(self.presets):
            p_rect = pygame.Rect(360 + idx * 92, 530, 88, 34)
            selected = (self.state.get("preset") == p)
            color = (30, 140, 70) if selected else (40, 50, 70)
            pygame.draw.rect(surface, color, p_rect, border_radius=4)
            pygame.draw.rect(surface, (80, 200, 120) if selected else (80, 90, 110), p_rect, width=1, border_radius=4)
            t = self.font_info.render(p, True, (255, 255, 255))
            surface.blit(t, (p_rect.centerx - t.get_width() // 2, p_rect.centery - t.get_height() // 2))

        lbl_l = self.font_info.render("Championship Laps:", True, (220, 220, 220))
        surface.blit(lbl_l, (200, 586))
        for idx, l in enumerate(self.laps_options):
            l_rect = pygame.Rect(450 + idx * 80, 580, 70, 34)
            selected = (self.state.get("laps") == l)
            color = (30, 140, 70) if selected else (40, 50, 70)
            pygame.draw.rect(surface, color, l_rect, border_radius=4)
            pygame.draw.rect(surface, (80, 200, 120) if selected else (80, 90, 110), l_rect, width=1, border_radius=4)
            t = self.font_info.render(f"{l} Laps", True, (255, 255, 255))
            surface.blit(t, (l_rect.centerx - t.get_width() // 2, l_rect.centery - t.get_height() // 2))

        lbl_c = self.font_info.render("Active Circuit:", True, (220, 220, 220))
        surface.blit(lbl_c, (200, 636))
        for idx, c in enumerate(self.circuits):
            c_rect = pygame.Rect(450 + idx * 80, 630, 70, 34)
            selected = (self.state.get("circuit_id") == c)
            color = (180, 100, 20) if selected else (40, 50, 70)
            pygame.draw.rect(surface, color, c_rect, border_radius=4)
            pygame.draw.rect(surface, (240, 160, 40) if selected else (80, 90, 110), c_rect, width=1, border_radius=4)
            t = self.font_info.render(f"Track {c}", True, (255, 255, 255))
            surface.blit(t, (c_rect.centerx - t.get_width() // 2, c_rect.centery - t.get_height() // 2))
