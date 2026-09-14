"""Exercise real pygame rendering with SDL's headless video/audio drivers."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class RuntimeTests(unittest.TestCase):
    def run_code(self, code, *args, audio_driver="dummy"):
        env = os.environ.copy()
        env.update(
            SDL_VIDEODRIVER="dummy",
            SDL_AUDIODRIVER=audio_driver,
            PYGAME_HIDE_SUPPORT_PROMPT="1",
            PYTHONPATH=str(PROJECT_ROOT),
        )
        # Every scenario starts outside the repository, with isolated save files
        # and a fresh interpreter for the game's global registries.
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-W", "error", "-c", textwrap.dedent(code), *args],
                cwd=directory, env=env, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_heroes_render_move_cast_pause_and_reload(self):
        for hero in ("MAGE", "ROGUE", "WARRIOR"):
            with self.subTest(hero=hero):
                self.run_code("""
                    import json
                    import random
                    import sys
                    from pathlib import Path
                    import pygame
                    from pythongame.main import Main
                    from pythongame.core.common import Millis
                    from pythongame.scenes.scene_starting_program.scene_starting_program import (
                        CommandlineFlags, StartingProgramScene,
                    )

                    random.seed(42)
                    app = Main(None, sys.argv[1], 5, 100, None, False)
                    def frame(events=()):
                        transition = app.scene.handle_user_input(events)
                        if transition is None:
                            transition = app.scene.run_one_frame(Millis(16))
                        if transition:
                            app.change_scene(transition)
                        app.scene.render()
                        pygame.display.update()

                    for _ in range(90):
                        frame()
                    assert type(app.scene).__name__ == 'PlayingScene'
                    state = app.scene.game_state
                    position = state.game_world.player_entity.get_position()
                    frame([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)])
                    for _ in range(10):
                        frame()
                    frame([pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT)])
                    assert position != state.game_world.player_entity.get_position()
                    frame([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q)])
                    for _ in range(30):
                        frame()
                    frame([pygame.event.Event(pygame.KEYUP, key=pygame.K_q)])
                    frame([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)])
                    assert type(app.scene).__name__ == 'PausedScene'
                    frame([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)])
                    assert type(app.scene).__name__ == 'PlayingScene'
                    app.toggle_fullscreen()
                    frame()
                    app.toggle_fullscreen()
                    frame()

                    filename = app.save_file_handler.save_to_file(state.player_state, None, Millis(1234))
                    saved = app.save_file_handler.load_player_state_from_json_file(filename)
                    assert saved.hero_id == sys.argv[1]
                    assert saved.level == 5 and saved.money == 100
                    assert saved.total_time_played_on_character == 1234
                    # Older saves do not contain the newer optional fields.
                    path = Path('saved_characters') / filename
                    data = json.loads(path.read_text(encoding='utf-8'))
                    for key in ('talents', 'total_time_played', 'active_quests', 'completed_quests'):
                        data.pop(key)
                    path.write_text(json.dumps(data), encoding='utf-8')
                    legacy = app.save_file_handler.load_player_state_from_json_file(filename)
                    assert legacy.total_time_played_on_character == 0
                    app.scene = StartingProgramScene(
                        app.scene_factory, CommandlineFlags(None, None, None, None, filename),
                        app.save_file_handler,
                    )
                    for _ in range(4):
                        frame()
                    assert app.scene.game_state.player_state.hero_id.name == sys.argv[1]
                    assert app.scene.game_state.player_state.level == 5
                    pygame.quit()
                """, hero)

    def test_menu_and_hero_selection(self):
        self.run_code("""
            import pygame
            from pythongame.main import Main
            from pythongame.core.common import Millis
            app = Main(None, None, None, None, None, False)
            app.change_scene(app.scene.run_one_frame(Millis(16)))
            assert type(app.scene).__name__ == 'MainMenuScene'
            app.scene.render()
            app.change_scene(app.scene.run_one_frame(Millis(16)))
            assert type(app.scene).__name__ == 'PickingHeroScene'
            app.scene.render()
            app.change_scene(app.scene.handle_user_input([
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
            ]))
            app.change_scene(app.scene.run_one_frame(Millis(16)))
            assert type(app.scene).__name__ == 'PlayingScene'
            app.scene.render()
            pygame.quit()
        """)

    def test_map_editor_renders_and_quits(self):
        self.run_code("""
            from unittest.mock import patch
            import pygame
            from pythongame.map_editor.map_editor import main
            update = pygame.display.flip
            frames = []
            def render_and_quit():
                update()
                frames.append(pygame.display.get_surface().get_size())
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            with patch('pygame.display.flip', side_effect=render_and_quit):
                try:
                    main('map1.json')
                except SystemExit as exc:
                    assert exc.code in (None, 0)
            assert frames == [(1200, 750)]
            assert not pygame.get_init()
        """)

    def test_maps_and_dungeons_round_trip(self):
        self.run_code("""
            import random
            from pathlib import Path
            from pythongame.register_game_data import register_all_game_data
            from pythongame.core.common import HeroId
            from pythongame.core.entity_creation import create_hero_world_entity
            from pythongame.map_file import (
                load_map_from_json_file, save_map_to_json_file, MapJson,
            )
            from pythongame.leveled_dungeons import _generate_dungeon
            from pythongame.resources import resource_path
            register_all_game_data()
            for path in resource_path('resources/maps').glob('*.json'):
                data = load_map_from_json_file(path)
                data.game_world.player_entity = create_hero_world_entity(HeroId.MAGE, data.player_position)
                output = Path.cwd() / path.name
                save_map_to_json_file(data, output)
                restored = load_map_from_json_file(output)
                restored.game_world.player_entity = create_hero_world_entity(HeroId.MAGE, restored.player_position)
                assert MapJson.serialize(data) == MapJson.serialize(restored), path.name
            for difficulty in range(1, 5):
                random.seed(difficulty)
                dungeon = _generate_dungeon(difficulty)
                assert dungeon.walls and dungeon.decorations and dungeon.npcs
                assert dungeon.world_area.collidepoint(dungeon.player_position)
        """)

    def test_no_audio_device(self):
        self.run_code("""
            import warnings
            import pygame
            from pythongame.main import Main
            from pythongame.core.common import Millis, SoundId
            from pythongame.core.sound_player import play_sound, stop_looping_sound
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always', RuntimeWarning)
                app = Main(None, 'MAGE', None, None, None, False)
            assert any('Audio device unavailable' in str(w.message) for w in caught)
            for _ in range(4):
                transition = app.scene.run_one_frame(Millis(16))
                if transition:
                    app.change_scene(transition)
                app.scene.render()
            play_sound(SoundId.DIALOG)
            stop_looping_sound(SoundId.FOOTSTEPS)
            pygame.quit()
        """, audio_driver="unavailable-test-driver")

    def test_entry_points_and_shutdown(self):
        for module in ("run", "map_editor"):
            with self.subTest(module=module):
                self.run_code("""
                    import importlib
                    import sys
                    import pygame
                    importlib.import_module(sys.argv[1])
                    assert not pygame.get_init()
                """, module)
        self.run_code("""
            from unittest.mock import patch
            import pygame
            from pythongame.main import start
            with patch('pygame.event.get', return_value=[pygame.event.Event(pygame.QUIT)]):
                try:
                    start(None, None, None, None, None, False)
                except SystemExit as exc:
                    assert exc.code in (None, 0)
            assert not pygame.get_init()
        """)


if __name__ == '__main__':
    unittest.main()
