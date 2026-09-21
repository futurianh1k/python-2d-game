"""ST03–07/BVA07–09: 시간·경험치·특성·퀘스트의 관찰 가능한 상태 모델."""

import pytest

from pythongame.core.common import AbilityType, HeroUpgradeId, Millis
from pythongame.core.game_state import PlayerLeveledUp, PlayerLearnedNewAbility, PlayerUnlockedNewTalent, StunStatus
from pythongame.core.quests import Quest, QuestId
from pythongame.core.talents import TalentsState, TalentTierStatus

pytestmark = pytest.mark.unit
ABILITY = AbilityType.FIREBALL


@pytest.mark.parametrize("elapsed,cooling", [(998, True), (999, True), (1000, False), (1001, False)])
def test_bva07_cooldown_expiration(player, elapsed, cooling):
    player.add_to_ability_cooldown(ABILITY, Millis(1000))
    player.recharge_ability_cooldowns(Millis(elapsed))
    assert player.is_ability_on_cooldown(ABILITY) is cooling


def test_st03_cooldown_ready_wait_ready_reset(player):
    events = []
    player.cooldowns_were_updated.register_observer(lambda values: events.append(dict(values)))
    assert not player.is_ability_on_cooldown(ABILITY)
    player.recharge_ability_cooldowns(Millis(10))
    assert events == []
    player.add_to_ability_cooldown(ABILITY, Millis(1000))
    player.recharge_ability_cooldowns(Millis(999))
    assert player.is_ability_on_cooldown(ABILITY)
    player.recharge_ability_cooldowns(Millis(1))
    assert not player.is_ability_on_cooldown(ABILITY)
    player.add_to_ability_cooldown(ABILITY, Millis(1000))
    player.set_ability_cooldown_to_zero(ABILITY)
    assert not player.is_ability_on_cooldown(ABILITY)
    assert [values[ABILITY] for values in events] == [1000, 1, 0, 1000, 0]


def test_eg02_reequipping_item_cannot_bypass_cooldown(player):
    item_ability = AbilityType.ITEM_CANDLE
    player.set_active_item_ability(item_ability)
    player.add_to_ability_cooldown(item_ability, Millis(1000))
    player.set_active_item_ability(None)
    assert item_ability not in player.abilities
    player.recharge_ability_cooldowns(Millis(100))
    player.set_active_item_ability(item_ability)
    assert player.abilities.count(item_ability) == 1
    assert player.is_ability_on_cooldown(item_ability)
    player.recharge_ability_cooldowns(Millis(900))
    assert not player.is_ability_on_cooldown(item_ability)


@pytest.mark.parametrize("amount,level,remainder", [(48, 1, 48), (49, 1, 49), (50, 2, 0), (51, 2, 1), (132, 3, 0)])
def test_bva08_experience_thresholds(player, amount, level, remainder):
    """최초 50 경험치와 다음 82 경험치의 합은 132; 큰 보상도 누락 없이 성장한다."""
    player.health_resource.set_zero()
    player.mana_resource.set_zero()
    events = player.gain_exp(amount)
    assert (player.level, player.exp) == (level, remainder)
    if level == 1:
        assert events == []
        assert player.health_resource.value == player.mana_resource.value == 0
        assert not player.has_unpicked_talents()
    else:
        assert [type(event) for event in events] == [PlayerLeveledUp, PlayerLearnedNewAbility, PlayerUnlockedNewTalent]
        assert events[1].ability_type is AbilityType.TELEPORT
        assert player.abilities.count(AbilityType.TELEPORT) == 1
        assert player.has_unpicked_talents()
        assert player.health_resource.value == 100 + 10 * (level - 1)
        assert player.mana_resource.value == 100 + 5 * (level - 1)


@pytest.mark.parametrize("exp,remaining", [(0, 0), (24, 0), (25, 0), (26, 1), (27, 2), (49, 24)])
def test_bva09_death_penalty_does_not_make_experience_negative(player, exp, remaining):
    player.gain_exp(exp)
    player.lose_exp_from_death()
    assert (player.level, player.exp) == (1, remaining)


def test_st04_overlapping_stuns_require_both_removals():
    status = StunStatus()
    assert not status.is_stunned()
    status.add_one()
    assert status.is_stunned()
    status.add_one()
    status.remove_one()
    assert status.is_stunned()
    status.remove_one()
    assert not status.is_stunned()


def test_st05_stun_removal_without_active_stun_is_rejected():
    """하나의 무효 전이만 시도한다. 예외 이후 객체 재사용 안전성은 별도 리뷰 항목이다."""
    with pytest.raises(Exception, match="Number of active stuns went below 0"):
        StunStatus().remove_one()


def test_st06_talent_unlock_pick_reset(player):
    snapshots = []
    player.talents_were_updated.register_observer(
        lambda state: snapshots.append([(tier.status, tier.picked_index) for tier in state.tiers]))
    assert player.get_serilized_talent_tier_choices() == [None, None]
    assert not player.has_unpicked_talents()
    player.gain_exp(50)
    assert snapshots[-1] == [(TalentTierStatus.PENDING, None), (TalentTierStatus.LOCKED, None)]
    assert player.choose_talent(0, 1) == ("Mana", HeroUpgradeId.MAX_MANA)
    assert snapshots[-1] == [(TalentTierStatus.PICKED, 1), (TalentTierStatus.LOCKED, None)]
    assert player.has_upgrade(HeroUpgradeId.MAX_MANA)
    assert not player.has_unpicked_talents()
    assert player.reset_talents() == [HeroUpgradeId.MAX_MANA]
    assert snapshots[-1] == [(TalentTierStatus.PENDING, None), (TalentTierStatus.LOCKED, None)]
    assert not player.has_upgrade(HeroUpgradeId.MAX_MANA)
    assert player.get_serilized_talent_tier_choices() == [None, None]
    assert player.reset_talents() == []


def test_st06b_unrelated_level_does_not_unlock_talent(talent_config):
    state = TalentsState(talent_config)
    assert [tier.required_level for tier in state.tiers] == [2, 4]
    state.unlock_tier(3)
    assert all(tier.status is TalentTierStatus.LOCKED for tier in state.tiers)


def test_st07_quest_start_duplicate_complete(player):
    quest = Quest(QuestId.RETRIEVE_FROG, "Frog", "Find the frog")
    notifications = []
    player.quests_were_updated.register_observer(
        lambda values: notifications.append(tuple([quest.quest_id for quest in quests] for quests in values)))
    assert player.active_quests == player.completed_quests == []
    player.start_quest(quest)
    player.start_quest(Quest(QuestId.RETRIEVE_FROG, "Duplicate", "Same identity"))
    assert player.active_quests == [quest]
    assert player.completed_quests == []
    assert notifications == [([QuestId.RETRIEVE_FROG], [])]
    player.complete_quest(quest)
    assert player.active_quests == []
    assert player.completed_quests == [quest]
    assert notifications[-1] == ([], [QuestId.RETRIEVE_FROG])
