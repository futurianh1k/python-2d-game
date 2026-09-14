"""실제 pygame을 사용하는 통합 테스트 fixture.

장면·렌더러·이미지·폰트·음원은 실제 구현을 사용한다. 입력 이벤트와 가상 시간만
통제해 재현 가능하게 하고, 테스트 종료 시 오디오 캐시와 SDL을 정리한다.
게임 데이터의 전역 레지스트리는 기존 구조를 유지하므로 이 테스트들은 직렬 실행한다."""

import pytest


@pytest.fixture
def game_data():
    """실제 데이터 등록기를 호출한다. 랜덤 아이템은 상위 fixture의 고정 seed를 따른다."""
    from pythongame.register_game_data import register_all_game_data
    register_all_game_data()


@pytest.fixture
def app_factory():
    """사용자가 고른 실행 인수로 실제 Main을 만든다.

    테스트 전후 sound cache/pygame.quit을 정리하며, 한 테스트 안의 장면 재로딩은
    동일 앱을 사용해 오래된 UI 상태가 남는 회귀도 노출한다."""
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
    """한 프레임을 입력 → 시간 → 전환 → 렌더 순서로 실행한다.

    16ms를 직접 주입해 CPU 속도에 독립적인 게임 시간을 만들고, 입력은 첫 프레임에만
    전달한다. 이후에는 input handler의 실제 held-key 상태가 동작해야 한다."""
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
