"""CTFL 테스트의 독립 실행, 임시 파일 격리 및 JUnit 실행 환경 기록.

형제 폴더 tests/conftest.py의 fixture에 의존하지 않는다. 게임 데이터 전역 등록,
이미지 로딩, 실제 저장 폴더 쓰기 없이 실제 도메인 객체를 구성한다.
"""

from importlib.metadata import version
import os
from pathlib import Path
import platform
import random
import subprocess

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests_istqb_foundation" in item.path.parts:
            item.add_marker(pytest.mark.istqb_foundation)


@pytest.fixture(scope="session", autouse=True)
def foundation_run_metadata(record_testsuite_property):
    root = Path(__file__).resolve().parents[1]
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
            text=True, check=True, timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = "unavailable (source archive)"
    metadata = {
        "source_revision": revision,
        "build_number": os.environ.get("GITHUB_RUN_NUMBER", "local"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pygame-ce": version("pygame-ce"),
        "pytest": version("pytest"),
        "configuration": "SDL dummy; serial; fixed inputs; temporary cwd",
        "suite": "tests_istqb_foundation",
        "runner": os.environ.get("RUNNER_OS", "local"),
    }
    for key, value in metadata.items():
        record_testsuite_property(f"istqb_foundation.{key}", value)


@pytest.fixture(autouse=True)
def foundation_isolation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    previous_random_state = random.getstate()
    random.seed(42)
    yield
    random.setstate(previous_random_state)


@pytest.fixture
def save_payload():
    return {
        "hero": "MAGE", "level": 1, "exp": 0, "money": 0,
        "consumables": {str(slot): [] for slot in range(1, 6)},
        "items": [], "enabled_portals": {}, "talents": [],
        "total_time_played": 0, "active_quests": [], "completed_quests": [],
    }


@pytest.fixture
def talent_config():
    from pythongame.core.common import HeroUpgradeId, UiIconSprite
    from pythongame.core.talents import TalentsConfig, TalentTierConfig, TalentTierOptionConfig

    def tier():
        return TalentTierConfig(
            TalentTierOptionConfig("Armor", "Armor option", HeroUpgradeId.ARMOR,
                                   UiIconSprite.TALENT_MOVE_SPEED),
            TalentTierOptionConfig("Mana", "Mana option", HeroUpgradeId.MAX_MANA,
                                   UiIconSprite.TALENT_MOVE_SPEED),
        )

    # 순서를 뒤집어 넣어도 레벨 순으로 티어가 노출돼야 한다.
    return TalentsConfig({4: tier(), 2: tier()})


@pytest.fixture
def player(talent_config):
    from pythongame.core.common import AbilityType, HeroId
    from pythongame.core.consumable_inventory import ConsumableInventory
    from pythongame.core.game_data import PlayerLevelBonus
    from pythongame.core.game_state import PlayerState
    from pythongame.core.health_and_mana import HealthOrManaResource
    from pythongame.core.item_inventory import ItemInventory

    return PlayerState(
        health_resource=HealthOrManaResource(100, 0),
        mana_resource=HealthOrManaResource(100, 0),
        consumable_inventory=ConsumableInventory({1: [], 2: []}),
        abilities=[AbilityType.FIREBALL], item_inventory=ItemInventory([]),
        new_level_abilities={2: AbilityType.TELEPORT}, hero_id=HeroId.MAGE,
        armor=2, base_dodge_chance=0, level_bonus=PlayerLevelBonus(10, 5, 1),
        talents_config=talent_config, base_block_chance=0,
        base_magic_resist_chance=0, enabled_portals={},
    )
