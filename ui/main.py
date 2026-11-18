"""Main GUI Entry Point for Smart Racing Championship.

Run via:
  python -m ui.main
"""

import sys
import pygame
from typing import Dict, Any
from ui.menu import MenuScreen
from ui.explorer import ExplorerScreen
from ui.race_view import RaceViewScreen
from ui.lab import LabScreen
from ui.dashboard import DashboardScreen


def main() -> None:
    """Launch the Smart Racing Championship Pygame Application."""
    pygame.init()
    pygame.font.init()

    screen_width, screen_height = 1040, 720
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Smart Racing Championship - Design & Analysis of Algorithms")
    clock = pygame.time.Clock()

    app_state: Dict[str, Any] = {
        "circuit_id": 1,
        "preset": "Balanced",
        "laps": 2,
        "last_race_results": [],
    }

    screens: Dict[str, Any] = {}
    current_screen_name = "menu"

    def navigate(screen_name: str) -> None:
        nonlocal current_screen_name
        if screen_name in ("championship", "quick_race", "race"):
            # Reset race view when launching a new race
            if "race" in screens:
                screens["race"].reset_race()
            current_screen_name = "race"
        else:
            current_screen_name = screen_name

    screens["menu"] = MenuScreen(app_state, navigate)
    screens["explorer"] = ExplorerScreen(app_state, navigate)
    screens["race"] = RaceViewScreen(app_state, navigate)
    screens["lab"] = LabScreen(app_state, navigate)
    screens["dashboard"] = DashboardScreen(app_state, navigate)

    running = True
    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and current_screen_name == "menu":
                running = False
            else:
                active_screen = screens.get(current_screen_name)
                if active_screen:
                    active_screen.handle_event(event)

        active_screen = screens.get(current_screen_name)
        if active_screen:
            active_screen.update()
            active_screen.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
