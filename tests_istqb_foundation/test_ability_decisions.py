"""DT02/BVA06/WB02: 스킬 사용의 조건 조합과 자원·쿨다운·이벤트 결과.

PlayerControls, PlayerState, 자원/기절/쿨다운은 실제 객체다. 효과 실행과
음향·메시지 출력 경계만 대체하므로 실제 영웅별 효과 검증은 기존 통합 TC가 맡는다.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pythongame.core.abilities import AbilityData
from pythongame.core.ability_effects import AbilityFailedToExecute, AbilityWasUsedSuccessfully
from pythongame.core.common import AbilityType, Millis, SoundId, UiIconSprite
from pythongame.core.game_state import PlayerUsedAbilityEvent
from pythongame.scenes.scenes_game import player_controls

pytestmark = pytest.mark.integration
ABILITY = AbilityType.FIREBALL


@pytest.fixture
def controls(player, monkeypatch):
    data = AbilityData("Test Fireball", UiIconSprite.ABILITY_FIREBALL, 10,
                       Millis(1000), "Controlled cost/cooldown", None)
    monkeypatch.setitem(player_controls.ABILITIES, ABILITY, data)
    effect = Mock(return_value=AbilityWasUsedSuccessfully())
    sound = Mock()
    monkeypatch.setattr(player_controls, "apply_ability_effect", effect)
    monkeypatch.setattr(player_controls, "play_sound", sound)
    event_spy = Mock(wraps=player.notify_about_event)
    monkeypatch.setattr(player, "notify_about_event", event_spy)
    return SimpleNamespace(player=player, world=SimpleNamespace(player_state=player),
                           message=Mock(), effect=effect, sound=sound, events=event_spy)


@pytest.mark.parametrize("learned,stunned,cooldown,mana,result,expected_mana,expected_cd,message,called,emitted", [
    pytest.param(False, False, 0, 10, "ok", 10, 0, None, False, False, id="R1-unlearned"),
    pytest.param(True, True, 0, 10, "ok", 10, 0, None, False, False, id="R2-stunned"),
    pytest.param(True, False, 1, 10, "ok", 10, 1, None, False, False, id="R3-cooling"),
    pytest.param(True, False, 0, 9, "ok", 9, 500, "Not enough mana!", False, False, id="R4-insufficient-mana"),
    pytest.param(True, False, 0, 10, "fail", 10, 500, "Can't do that! (No target)", True, False, id="R5-effect-failed"),
    pytest.param(True, False, 0, 10, "fail-no-reason", 10, 500, "Can't do that!", True, False, id="R5b-no-reason"),
    pytest.param(True, False, 0, 10, "refund", 10, 500, None, True, True, id="R6-refund"),
    pytest.param(True, False, 0, 10, "ok", 0, 1000, None, True, True, id="R7-success"),
])
def test_dt02_ability_use_rules(controls, learned, stunned, cooldown, mana, result,
                              expected_mana, expected_cd, message, called, emitted):
    c = controls
    c.player.mana_resource.set_zero()
    c.player.mana_resource.gain(mana)
    if not learned:
        c.player.abilities.clear()
    if stunned:
        c.player.stun_status.add_one()
    c.player.add_to_ability_cooldown(ABILITY, Millis(cooldown))
    c.effect.return_value = {
        "ok": AbilityWasUsedSuccessfully(),
        "refund": AbilityWasUsedSuccessfully(True),
        "fail": AbilityFailedToExecute("No target"),
        "fail-no-reason": AbilityFailedToExecute(),
    }[result]
    cooldown_events = []
    c.player.cooldowns_were_updated.register_observer(lambda values: cooldown_events.append(dict(values)))

    if not learned:
        with pytest.raises(Exception, match="Cannot use ability"):
            player_controls.PlayerControls.try_use_ability(ABILITY, c.world, c.message)
    else:
        player_controls.PlayerControls.try_use_ability(ABILITY, c.world, c.message)

    assert c.player.mana_resource.value == expected_mana
    assert c.player.is_ability_on_cooldown(ABILITY) is (expected_cd > 0)
    assert cooldown_events == ([{ABILITY: expected_cd}] if message or emitted else [])
    if called:
        c.effect.assert_called_once_with(c.world, ABILITY)
    else:
        c.effect.assert_not_called()
    if message:
        c.message.set_message.assert_called_once_with(message)
        c.sound.assert_called_once_with(SoundId.INVALID_ACTION)
    else:
        c.message.set_message.assert_not_called()
        c.sound.assert_not_called()
    if emitted:
        c.events.assert_called_once()
        event, world = c.events.call_args.args
        assert isinstance(event, PlayerUsedAbilityEvent)
        assert event.ability is ABILITY and world is c.world
    else:
        c.events.assert_not_called()


@pytest.mark.parametrize("mana,remaining,success", [(8, 8, False), (9, 9, False), (10, 0, True), (11, 1, True)])
def test_bva06_mana_cost_boundary(controls, mana, remaining, success):
    c = controls
    c.player.mana_resource.set_zero()
    c.player.mana_resource.gain(mana)
    player_controls.PlayerControls.try_use_ability(ABILITY, c.world, c.message)
    assert c.player.mana_resource.value == remaining
    assert c.effect.call_count == int(success)
    assert c.events.call_count == int(success)


def test_wb02_unknown_effect_result_is_not_success(controls):
    controls.effect.return_value = object()
    with pytest.raises(Exception, match="Unhandled ability effect result"):
        player_controls.PlayerControls.try_use_ability(ABILITY, controls.world, controls.message)
    assert controls.player.mana_resource.value == 100
    assert not controls.player.is_ability_on_cooldown(ABILITY)
    controls.events.assert_not_called()


def test_wb03_success_sound_branch(controls, monkeypatch):
    monkeypatch.setattr(player_controls.ABILITIES[ABILITY], "sound_id", SoundId.INVALID_ACTION)
    player_controls.PlayerControls.try_use_ability(ABILITY, controls.world, controls.message)
    controls.sound.assert_called_once_with(SoundId.INVALID_ACTION)
    assert controls.player.mana_resource.value == 90
    controls.events.assert_called_once()
