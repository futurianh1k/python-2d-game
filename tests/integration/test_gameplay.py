import json
import logging

import pygame
import pytest

from pythongame.core.common import Millis
from pythongame.scenes.scene_starting_program.scene_starting_program import CommandlineFlags, StartingProgramScene
from pythongame.scenes.scenes_game.scene_paused import PausedScene
from pythongame.scenes.scenes_game.scene_playing import PlayingScene


@pytest.fixture(params=["MAGE", "ROGUE", "WARRIOR"])
def playing_app(request, app_factory, advance):
    app = app_factory(hero=request.param, level=5, money=100)
    advance(app, frames=90)
    assert isinstance(app.scene, PlayingScene)
    assert app.scene.game_state.player_state.hero_id.name == request.param
    return app


def test_movement_and_release(playing_app, advance):
    app = playing_app
    entity = app.scene.game_state.game_world.player_entity
    original = entity.get_position()
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)], frames=10)
    assert entity.get_position()[0] > original[0]
    advance(app, [pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT)])
    stopped = entity.get_position()
    advance(app, frames=10)
    assert entity.get_position() == stopped


def test_cast_spends_mana_and_starts_cooldown(playing_app, advance):
    app = playing_app
    state = app.scene.game_state.player_state
    ability = state.abilities[0]
    mana_before = state.mana_resource.value
    assert not state.is_ability_on_cooldown(ability)
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q)])
    advance(app, [pygame.event.Event(pygame.KEYUP, key=pygame.K_q)])
    assert state.is_ability_on_cooldown(ability)
    assert state.mana_resource.value < mana_before


def test_pause_freezes_time_and_resume_clears_held_keys(playing_app, advance):
    app = playing_app
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)])
    playing_scene = app.scene
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)])
    assert isinstance(app.scene, PausedScene)
    position = app.scene.game_state.game_world.player_entity.get_position()
    played = playing_scene.total_time_played_on_character
    advance(app, frames=10)
    assert playing_scene.total_time_played_on_character == played
    assert app.scene.game_state.game_world.player_entity.get_position() == position
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)], frames=10)
    assert app.scene is playing_scene
    assert app.scene.game_state.game_world.player_entity.get_position() == position


def test_save_legacy_reload_and_repeated_save_use_same_file(playing_app, advance, caplog):
    app = playing_app
    scene = app.scene
    with caplog.at_level(logging.INFO):
        scene._save_game()
    filename = scene.character_file
    path = app.save_file_handler.directory / filename
    saved = app.save_file_handler.load_player_state_from_json_file(filename)
    assert saved.level == 5 and saved.money == 100
    assert saved.total_time_played_on_character == scene.total_time_played_on_character
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("talents", "total_time_played", "active_quests", "completed_quests"):
        data.pop(key)
    path.write_text(json.dumps(data), encoding="utf-8")
    app.scene = StartingProgramScene(app.scene_factory,
                                    CommandlineFlags(None, None, None, None, filename), app.save_file_handler)
    advance(app, frames=4)
    assert app.scene.game_state.player_state.hero_id.name == saved.hero_id
    assert app.scene.game_state.player_state.level == 5
    assert app.scene.character_file == filename
    app.scene._save_game()
    app.scene._save_game()
    assert app.save_file_handler.list_save_files() == [filename]
    assert "Saved character" in caplog.text


def test_fullscreen_switching_keeps_rendering(app_factory, advance):
    app = app_factory(hero="MAGE")
    advance(app, frames=4)
    for expected in (True, False):
        app.toggle_fullscreen()
        advance(app)
        assert app.fullscreen is expected
        assert pygame.display.get_surface().get_size() == (800, 600)


def test_menu_skips_corrupt_save_and_preserves_file_mapping(app_factory, advance, saved_data, caplog):
    from pythongame.player_file import PlayerStateJson
    app = app_factory()
    folder = app.save_file_handler.directory
    (folder / "1.json").write_text('{"broken":', encoding="utf-8")
    (folder / "notes.txt").write_text('unrelated', encoding="utf-8")
    app.save_file_handler._save_player_state_to_json_file(PlayerStateJson.deserialize(saved_data), "2.json")
    advance(app)
    menu = app.scene
    assert menu._files == ["2.json"] and len(menu._saved_characters) == 1
    assert "Skipping unreadable save: 1.json" in caplog.text
    assert (folder / "1.json").read_text(encoding="utf-8") == '{"broken":'
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)], frames=2)
    assert isinstance(app.scene, PlayingScene) and app.scene.character_file == "2.json"


def test_new_game_hero_selection(app_factory, advance):
    app = app_factory()
    advance(app, frames=2)
    assert type(app.scene).__name__ == "PickingHeroScene"
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)])
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)], frames=2)
    assert isinstance(app.scene, PlayingScene)
    assert app.scene.game_state.player_state.hero_id.name == "WARRIOR"


def test_audio_unavailable_is_logged_and_game_keeps_running(app_factory, advance, monkeypatch, caplog):
    from pythongame.core.common import SoundId
    from pythongame.core.sound_player import play_sound, stop_looping_sound
    monkeypatch.setenv("SDL_AUDIODRIVER", "unavailable-test-driver")
    app = app_factory(hero="MAGE")
    advance(app, frames=4)
    assert isinstance(app.scene, PlayingScene)
    assert pygame.mixer.get_init() is None
    assert any(record.levelno == logging.WARNING and "Audio device unavailable" in record.message
               for record in caplog.records)
    play_sound(SoundId.DIALOG)
    stop_looping_sound(SoundId.FOOTSTEPS)


def test_start_quit_can_repeat_without_stale_audio(monkeypatch, caplog):
    from pythongame.main import start
    for _ in range(2):
        monkeypatch.setattr(pygame.event, "get", lambda: [pygame.event.Event(pygame.QUIT)])
        with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as caught:
            start(None, None, None, None, None, False)
        assert caught.value.code in (None, 0)
        assert not pygame.get_init()
    assert "Game stopped" in caplog.text
