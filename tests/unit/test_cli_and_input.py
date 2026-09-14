"""CLI 경계값과 키 입력 상태 전이 검사.

CLI 인수 검증에는 GUI가 필요하지 않다. 입력 검증에는 실제 pygame Event를
사용하되 OS 키보드 입력을 기다리지 않아 빠르고 결정적으로 실행한다.
0/-1/잘못된 타입, 키 반복, 해제 이벤트 누락을 각각 다른 실패 조건으로 다룬다."""

import importlib

import pygame
import pytest

import run
from pythongame.core.common import Direction
from pythongame.core.user_input import ActionMoveInDirection, ActionStopMoving, PlayingUserInputHandler


@pytest.mark.parametrize("args,level,money", [
    ([], None, None), (["--level", "1", "--money", "0"], 1, 0),
    (["--level", "5", "--money", "100"], 5, 100),
])
def test_cli_integer_boundaries(args, level, money):
    """미지정 기본값과 최소 허용 정수, 일반 값을 비교해 타입 변환 결과를 검사한다."""
    parsed = run.parse_args(args)
    assert parsed.level == level and parsed.money == money


@pytest.mark.parametrize("args", [
    ["--level", "0"], ["--level", "-1"], ["--level", "1.5"],
    ["--money", "-1"], ["--money", "invalid"], ["--hero", "UNKNOWN"],
    ["--log-level", "INVALID"],
])
def test_invalid_cli_inputs_fail_before_startup(args, capsys):
    """범위/타입/선택지 오류가 argparse 종료 코드 2와 error 메시지로 나타나야 한다."""
    with pytest.raises(SystemExit) as caught:
        run.parse_args(args)
    assert caught.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--disable_fullscreen", "--disable-fullscreen"])
def test_both_windowed_flags(flag):
    """기존 밑줄 옵션과 새 하이픈 옵션이 같은 창 모드 플래그를 설정하는지 검사한다."""
    assert run.parse_args([flag]).disable_fullscreen


@pytest.mark.parametrize("module", ["run", "map_editor"])
def test_log_options(module):
    """게임과 편집기 모두 동일한 파일 경로·로그 레벨 옵션을 지원해야 한다."""
    parser = importlib.import_module(module).parse_args
    args = parser(["--log-file", "logs/session.log", "--log-level", "DEBUG"])
    assert args.log_file == "logs/session.log" and args.log_level == "DEBUG"


def key(event_type, value):
    """OS 입력 없이 실제 pygame 키 이벤트를 만드는 TC용 작은 헬퍼."""
    return pygame.event.Event(event_type, key=value)


def test_latest_direction_wins_then_reverts_on_release():
    """좌→우 입력에서는 우가 우선하고 우 해제 시 좌로 복귀한 뒤 모두 해제 시 정지해야 한다."""
    handler = PlayingUserInputHandler()
    actions = handler.get_actions([key(pygame.KEYDOWN, pygame.K_LEFT), key(pygame.KEYDOWN, pygame.K_RIGHT)])
    assert isinstance(actions[-1], ActionMoveInDirection) and actions[-1].direction == Direction.RIGHT
    actions = handler.get_actions([key(pygame.KEYUP, pygame.K_RIGHT)])
    assert actions[-1].direction == Direction.LEFT
    actions = handler.get_actions([key(pygame.KEYUP, pygame.K_LEFT)])
    assert isinstance(actions[-1], ActionStopMoving)


def test_duplicate_keydown_and_unmatched_keyup_are_safe():
    """키 반복과 이미 해제된 키의 KEYUP이 예외나 잔여 이동 상태를 만들지 않아야 한다."""
    handler = PlayingUserInputHandler()
    handler.get_actions([key(pygame.KEYDOWN, pygame.K_LEFT), key(pygame.KEYDOWN, pygame.K_LEFT)])
    actions = handler.get_actions([key(pygame.KEYUP, pygame.K_LEFT), key(pygame.KEYUP, pygame.K_RIGHT)])
    assert isinstance(actions[-1], ActionStopMoving)


def test_focus_loss_clears_movement_abilities_and_shift(monkeypatch):
    """이동·스킬·Shift를 누른 채 창 포커스를 잃으면 모든 held-key 상태를 초기화해야 한다."""
    from pythongame.core.abilities import KEYS_BY_ABILITY_TYPE, UserAbilityKey
    from pythongame.core.common import AbilityType
    ability = AbilityType.FIREBALL
    monkeypatch.setitem(KEYS_BY_ABILITY_TYPE, ability, UserAbilityKey("Q", pygame.K_q))
    handler = PlayingUserInputHandler()
    handler.get_actions([key(pygame.KEYDOWN, pygame.K_RIGHT), key(pygame.KEYDOWN, pygame.K_q),
                         key(pygame.KEYDOWN, pygame.K_LSHIFT)])
    assert handler.is_shift_held_down()
    actions = handler.get_actions([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
    assert len(actions) == 1 and isinstance(actions[0], ActionStopMoving)
    assert not handler.is_shift_held_down()


def test_cli_dispatch_and_log_cleanup_on_failure(tmp_path, monkeypatch, application_logging):
    """실행기로 전달하는 인수와 예외 종료 시 로그 핸들 해제를 검사한다.

    UI 대신 main.start만 실패하도록 대체한다. 로그 파일 이동이 성공해야 Windows에서도
    핸들이 열린 채 남지 않았다고 판단할 수 있다.
    """
    from unittest.mock import Mock
    from pythongame import main
    start = Mock(side_effect=RuntimeError("startup-error"))
    monkeypatch.setattr(main, "start", start)
    path = tmp_path / "cli.log"
    with pytest.raises(RuntimeError, match="startup-error"):
        run.cli(["--hero", "MAGE", "--level", "5", "--money", "100", "--disable-fullscreen",
                 "--log-file", str(path)])
    start.assert_called_once_with(None, "MAGE", 5, 100, None, False)
    path.rename(tmp_path / "closed.log")
