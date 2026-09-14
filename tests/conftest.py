"""전체 테스트의 파일·난수·로깅 격리 정책.

각 테스트는 tmp_path에서 실행하므로 실제 saved_characters와 리소스를 덮어쓰지 않는다.
SDL dummy 환경은 pygame import 이전에 설정한다. 앱 로깅 정리는 직접 소유한
핸들러만 대상으로 해 pytest의 caplog/실패 로그 수집기를 보존한다."""

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
    """테스트마다 작업 폴더를 바꾸고 난수 상태를 복원한다.

    seed=42는 재현용이며 원래 RNG 상태는 yield 이후 되돌려 다른 테스트에 영향을 주지 않는다.
    monkeypatch가 cwd를 원래 위치로 복구하므로 실패한 assertion도 실제 저장 폴더를 오염시키지 않는다."""
    monkeypatch.chdir(tmp_path)
    random_state = random.getstate()
    random.seed(42)
    yield
    random.setstate(random_state)


@pytest.fixture
def saved_data():
    """각 테스트에 새 dict/list를 제공하는 최소 정상 저장 데이터.

    fixture scope가 function이므로 한 TC의 오류 값 주입이 다음 TC에 남지 않는다."""
    return {
        "hero": "MAGE", "level": 1, "exp": 0, "money": 0,
        "consumables": {str(slot): [] for slot in range(1, 6)},
        "items": [], "enabled_portals": {},
        "talents": [], "total_time_played": 0,
        "active_quests": [], "completed_quests": [],
    }


@pytest.fixture
def save_handler(tmp_path):
    """실제 SaveFileHandler에 임시 디렉터리를 주입해 생성/목록/저장 정책을 검사한다."""
    from pythongame.player_file import SaveFileHandler
    return SaveFileHandler(tmp_path / "characters")


@pytest.fixture
def application_logging():
    """테스트가 설치한 앱 핸들러와 로그 레벨을 복구한다.

    root logger나 pytest 소유 핸들러에는 손대지 않는다."""
    from pythongame.logging_config import shutdown_logging
    logger = logging.getLogger("pythongame")
    previous_level = logger.level
    yield
    shutdown_logging()
    logger.setLevel(previous_level)


def pytest_collection_modifyitems(items):
    """경로로 unit/integration 마커를 부여해 -m 선택 실행을 유지한다.

    별도 process 마커와 중복될 수 있으며 strict-markers 설정이 오타를 검출한다."""
    for item in items:
        if "unit" in item.path.parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)
