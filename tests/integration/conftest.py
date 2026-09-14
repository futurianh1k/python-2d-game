import pytest


@pytest.fixture
def game_data():
    from pythongame.register_game_data import register_all_game_data
    register_all_game_data()


@pytest.fixture
def app_factory():
    import pygame
    from pythongame.core.sound_player import shutdown_sound_player
    from pythongame.main import Main
    shutdown_sound_player()
    pygame.quit()

    def create(hero=None, level=None, money=None, filename=None, map_name=None):
        return Main(map_name, hero, level, money, filename, False)

    yield create
    shutdown_sound_player()
    pygame.quit()


@pytest.fixture
def advance():
    import pygame
    from pythongame.core.common import Millis

    def frame(app, events=(), frames=1):
        for _ in range(frames):
            transition = app.scene.handle_user_input(events)
            if transition is None:
                transition = app.scene.run_one_frame(Millis(16))
            if transition:
                app.change_scene(transition)
            app.scene.render()
            pygame.display.update()
            events = ()
    return frame
