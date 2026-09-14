"""사용자 행동을 기준으로 분리한 pygame 통합 TC.

세 영웅은 pytest parameter로 독립 수집되어 실패한 영웅/행동을 바로 식별한다.
이동 좌표, 마나, 쿨다운, 시간, 파일명처럼 관찰 가능한 결과를 검사한다.
단순히 예외가 없었다는 사실만으로 스킬이나 저장의 성공을 판단하지 않는다."""

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
    """세 영웅을 각각 레벨 5/100골드로 시작하고 생성·스폰 보호 시간을 진행시킨다."""
    app = app_factory(hero=request.param, level=5, money=100)
    advance(app, frames=90)
    assert isinstance(app.scene, PlayingScene)
    assert app.scene.game_state.player_state.hero_id.name == request.param
    return app


def test_movement_and_release(playing_app, advance):
    """KEYDOWN 후 x좌표 증가와 KEYUP 후 위치 고정을 함께 검증한다.

    이벤트 처리의 성공과 실제 월드 이동 결과를 구분한다."""
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
    """Q 스킬이 실제 마나를 소비하고 쿨다운에 들어가는지 검사한다.

    이전 테스트의 단순 렌더링 성공보다 강한 행동 결과 판정이다."""
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
    """이동 중 일시정지하면 시간/좌표가 멈추고 복귀 후 키가 자동 유지되지 않아야 한다."""
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
    """실제 저장 후 선택 필드를 제거해 구형 파일을 복원하고 동일 파일 재저장을 확인한다.

    레벨/골드/시간, 영웅, 캐릭터 파일명, 파일 개수와 성공 로그를 각각 판정한다."""
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
    """SDL 모드 선택 차이를 허용하면서 전체 화면 전환 후 렌더링과 창 크기 복원을 검사한다."""
    app = app_factory(hero="MAGE")
    advance(app, frames=4)
    for expected in (True, False):
        app.toggle_fullscreen()
        advance(app)
        assert app.fullscreen is expected
        assert app.pygame_screen is pygame.display.get_surface()
        # SDL의 전체 화면 크기는 사용 가능한 디스플레이 모드에 따라 달라진다.
        # dummy 드라이버도 1024x768을 선택하므로 논리 화면보다 작지 않은지 검사하고,
        # 창 모드로 복귀한 뒤에는 요청한 800x600 크기가 정확히 복원되어야 한다.
        size = pygame.display.get_surface().get_size()
        if expected:
            assert size[0] >= 800 and size[1] >= 600
        else:
            assert size == (800, 600)


def test_menu_skips_corrupt_save_and_preserves_file_mapping(app_factory, advance, saved_data, caplog):
    """손상 파일 앞에 있는 정상 파일의 메뉴 인덱스/파일명을 확인한다.

    경고를 남기되 손상 파일 자체는 변경하지 않고 정상 캐릭터를 계속 불러와야 한다."""
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
    """저장 파일 없는 시작 화면에서 오른쪽 선택 후 WARRIOR로 진입하는 실제 전이를 검사한다."""
    app = app_factory()
    advance(app, frames=2)
    assert type(app.scene).__name__ == "PickingHeroScene"
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)])
    advance(app, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)], frames=2)
    assert isinstance(app.scene, PlayingScene)
    assert app.scene.game_state.player_state.hero_id.name == "WARRIOR"


def test_audio_unavailable_is_logged_and_game_keeps_running(app_factory, advance, monkeypatch, caplog):
    """없는 오디오 드라이버를 지정해 무음 fallback을 실제 SDL 초기화로 재현한다.

    Python warning 예외가 아닌 WARNING 로그가 남고 플레이 화면 진입이 가능해야 한다."""
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
    """같은 인터프리터에서 두 번 시작/종료해 닫힌 Sound 캐시 재사용 오류를 검사한다."""
    from pythongame.main import start
    for _ in range(2):
        monkeypatch.setattr(pygame.event, "get", lambda: [pygame.event.Event(pygame.QUIT)])
        with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as caught:
            start(None, None, None, None, None, False)
        assert caught.value.code in (None, 0)
        assert not pygame.get_init()
    assert "Game stopped" in caplog.text
