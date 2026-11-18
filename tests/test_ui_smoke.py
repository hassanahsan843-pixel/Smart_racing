"""Headless UI Smoke Test.

Imports each screen and runs one complete frame with SDL_VIDEODRIVER=dummy
to guarantee all GUI screens render without errors.
"""

import os
import pytest

# Force headless dummy driver for testing without display hardware
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from ui.menu import MenuScreen
from ui.explorer import ExplorerScreen
from ui.race_view import RaceViewScreen
from ui.lab import LabScreen
from ui.dashboard import DashboardScreen


def test_ui_screens_headless_smoke():
    """Verify that all 5 UI screens initialize and render one frame cleanly."""
    pygame.init()
    pygame.font.init()

    surface = pygame.display.set_mode((1040, 720))
    app_state = {
        "circuit_id": 1,
        "preset": "Balanced",
        "laps": 1,
        "last_race_results": [],
    }

    dummy_nav = lambda name: None

    screens = {
        "menu": MenuScreen(app_state, dummy_nav),
        "explorer": ExplorerScreen(app_state, dummy_nav),
        "race": RaceViewScreen(app_state, dummy_nav),
        "lab": LabScreen(app_state, dummy_nav),
        "dashboard": DashboardScreen(app_state, dummy_nav),
    }

    dummy_event = pygame.event.Event(pygame.NOEVENT)

    for name, scr in screens.items():
        # Handle event, update, and draw
        scr.handle_event(dummy_event)
        scr.update()
        scr.draw(surface)
        assert surface.get_width() == 1040
        assert surface.get_height() == 720

    pygame.quit()
