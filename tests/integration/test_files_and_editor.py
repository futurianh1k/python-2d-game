import hashlib
import json
import logging
from pathlib import Path
import random
from types import SimpleNamespace

import pygame
import pytest

from pythongame.resources import resource_path

MAP_FILES = sorted(path.name for path in resource_path("resources/maps").glob("*.json"))


@pytest.mark.parametrize("filename", MAP_FILES)
def test_all_bundled_maps_round_trip_without_touching_source(game_data, tmp_path, filename):
    from pythongame.core.common import HeroId
    from pythongame.core.entity_creation import create_hero_world_entity
    from pythongame.map_file import MapJson, load_map_from_json_file, save_map_to_json_file
    source = resource_path("resources/maps") / filename
    before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    data = load_map_from_json_file(source)
    data.game_world.player_entity = create_hero_world_entity(HeroId.MAGE, data.player_position)
    output = tmp_path / filename
    save_map_to_json_file(data, output)
    restored = load_map_from_json_file(output)
    restored.game_world.player_entity = create_hero_world_entity(HeroId.MAGE, restored.player_position)
    assert MapJson.serialize(restored) == MapJson.serialize(data)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before_hash
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize("difficulty", range(1, 5))
def test_dungeons_have_entities_and_valid_spawn(game_data, difficulty):
    from pythongame.leveled_dungeons import _generate_dungeon
    random.seed(difficulty)
    dungeon = _generate_dungeon(difficulty)
    assert dungeon.walls and dungeon.decorations and dungeon.npcs
    assert dungeon.world_area.collidepoint(dungeon.player_position)


@pytest.mark.parametrize("with_grid", [True, False], ids=["smart-grid", "no-grid"])
def test_editor_save_preserves_grid_and_original_map(game_data, tmp_path, caplog, with_grid):
    from pythongame.core.common import HeroId
    from pythongame.core.entity_creation import create_hero_world_entity
    from pythongame.map_editor.map_editor import MapEditor
    from pythongame.map_file import load_map_from_json_file
    editor = MapEditor.__new__(MapEditor)
    data = load_map_from_json_file(resource_path("resources/maps/map1.json"))
    data.game_world.player_entity = create_hero_world_entity(HeroId.MAGE, data.player_position)
    editor.game_state = SimpleNamespace(game_world=data.game_world)
    editor.config = data.map_editor_config
    editor.grid = SimpleNamespace(serialize=lambda: "grid-fixture") if with_grid else None
    editor.map_file_path = str(tmp_path / "edited.json")
    with caplog.at_level(logging.INFO):
        editor.save()
    written = json.loads(Path(editor.map_file_path).read_text(encoding="utf-8"))
    assert written["grid"] == ("grid-fixture" if with_grid else None)
    assert "Saved map:" in caplog.text
    assert written["player"]["position"] == list(data.player_position)


def test_editor_renders_one_frame_and_quits(monkeypatch, caplog):
    from pythongame.map_editor.map_editor import main
    flip = pygame.display.flip
    frames = []

    def render_and_quit():
        flip()
        frames.append(pygame.display.get_surface().get_size())
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    monkeypatch.setattr(pygame.display, "flip", render_and_quit)
    with caplog.at_level(logging.INFO), pytest.raises(SystemExit):
        main("map1.json")
    assert frames == [(1200, 750)]
    assert not pygame.get_init()
    assert "Map editor stopped" in caplog.text


def test_absolute_and_project_relative_resources(tmp_path):
    assert resource_path("resources/maps/map1.json").is_file()
    assert resource_path(tmp_path / "custom.json") == tmp_path / "custom.json"
