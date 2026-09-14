"""배포 리소스·던전·맵 편집기의 실제 파일/렌더링 검증.

원본 맵은 읽기만 하고 복사본은 tmp_path에 저장한다. JSON의 의미 비교와
원본 SHA-256 비교를 함께 사용해 보존 여부를 구분한다. 편집기 종료 입력만
주입하며 실제 화면 Surface 생성과 flip은 그대로 실행한다."""

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
    """모든 맵을 복사·복원해 동일한 JSON 의미와 원본 파일 해시를 확인한다.

    직렬화 시 필요한 플레이어 엔티티만 실제 factory로 주입한다."""
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
    """난이도별 고정 seed로 던전을 생성하고 벽/장식/NPC 및 월드 내부 시작 위치를 검사한다."""
    from pythongame.leveled_dungeons import _generate_dungeon
    random.seed(difficulty)
    dungeon = _generate_dungeon(difficulty)
    assert dungeon.walls and dungeon.decorations and dungeon.npcs
    assert dungeon.world_area.collidepoint(dungeon.player_position)


@pytest.mark.parametrize("with_grid", [True, False], ids=["smart-grid", "no-grid"])
def test_editor_save_preserves_grid_and_original_map(game_data, tmp_path, caplog, with_grid):
    """그리드가 있는 경우와 없는 경우를 분리해 저장 진입점의 JSON/log 계약을 검사한다.

    무한 GUI 루프를 피하기 위해 편집기의 저장에 필요한 상태만 구성하고 파일 쓰기는 실제 실행한다."""
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
    """실제 flip을 실행한 후 QUIT 이벤트를 주입해 렌더링과 종료 정리를 확인한다."""
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
    """프로젝트 상대 리소스는 실제 존재해야 하고 외부 절대 경로는 그대로 유지되어야 한다."""
    assert resource_path("resources/maps/map1.json").is_file()
    assert resource_path(tmp_path / "custom.json") == tmp_path / "custom.json"
