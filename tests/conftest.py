import logging
import os
import random

# SDL reads these at initialization; set them before any game imports.
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pytest


@pytest.fixture(autouse=True)
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    random_state = random.getstate()
    random.seed(42)
    yield
    random.setstate(random_state)


@pytest.fixture
def saved_data():
    return {
        "hero": "MAGE", "level": 1, "exp": 0, "money": 0,
        "consumables": {str(slot): [] for slot in range(1, 6)},
        "items": [], "enabled_portals": {},
        "talents": [], "total_time_played": 0,
        "active_quests": [], "completed_quests": [],
    }


@pytest.fixture
def save_handler(tmp_path):
    from pythongame.player_file import SaveFileHandler
    return SaveFileHandler(tmp_path / "characters")


@pytest.fixture
def application_logging():
    from pythongame.logging_config import shutdown_logging
    logger = logging.getLogger("pythongame")
    previous_level = logger.level
    yield
    shutdown_logging()
    logger.setLevel(previous_level)


def pytest_collection_modifyitems(items):
    for item in items:
        if "unit" in item.path.parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)
