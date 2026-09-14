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
    parsed = run.parse_args(args)
    assert parsed.level == level and parsed.money == money


@pytest.mark.parametrize("args", [
    ["--level", "0"], ["--level", "-1"], ["--level", "1.5"],
    ["--money", "-1"], ["--money", "invalid"], ["--hero", "UNKNOWN"],
    ["--log-level", "INVALID"],
])
def test_invalid_cli_inputs_fail_before_startup(args, capsys):
    with pytest.raises(SystemExit) as caught:
        run.parse_args(args)
    assert caught.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--disable_fullscreen", "--disable-fullscreen"])
def test_both_windowed_flags(flag):
    assert run.parse_args([flag]).disable_fullscreen


@pytest.mark.parametrize("module", ["run", "map_editor"])
def test_log_options(module):
    parser = importlib.import_module(module).parse_args
    args = parser(["--log-file", "logs/session.log", "--log-level", "DEBUG"])
    assert args.log_file == "logs/session.log" and args.log_level == "DEBUG"


def key(event_type, value):
    return pygame.event.Event(event_type, key=value)


def test_latest_direction_wins_then_reverts_on_release():
    handler = PlayingUserInputHandler()
    actions = handler.get_actions([key(pygame.KEYDOWN, pygame.K_LEFT), key(pygame.KEYDOWN, pygame.K_RIGHT)])
    assert isinstance(actions[-1], ActionMoveInDirection) and actions[-1].direction == Direction.RIGHT
    actions = handler.get_actions([key(pygame.KEYUP, pygame.K_RIGHT)])
    assert actions[-1].direction == Direction.LEFT
    actions = handler.get_actions([key(pygame.KEYUP, pygame.K_LEFT)])
    assert isinstance(actions[-1], ActionStopMoving)


def test_duplicate_keydown_and_unmatched_keyup_are_safe():
    handler = PlayingUserInputHandler()
    handler.get_actions([key(pygame.KEYDOWN, pygame.K_LEFT), key(pygame.KEYDOWN, pygame.K_LEFT)])
    actions = handler.get_actions([key(pygame.KEYUP, pygame.K_LEFT), key(pygame.KEYUP, pygame.K_RIGHT)])
    assert isinstance(actions[-1], ActionStopMoving)


def test_focus_loss_clears_movement_abilities_and_shift(monkeypatch):
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
