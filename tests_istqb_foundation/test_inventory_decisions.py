"""DT01/BVA05/ST01: 슬롯 배치 우선순위, 용량 경계, 이동 시 내용 보존."""

from collections import Counter
from copy import deepcopy

import pytest

from pythongame.core.common import ConsumableType
from pythongame.core.consumable_inventory import ConsumableInventory

pytestmark = pytest.mark.unit
H = ConsumableType.HEALTH
M = ConsumableType.MANA


@pytest.mark.parametrize("slots,expected", [
    pytest.param({1: [], 2: [H]}, {1: [], 2: [H, H]}, id="R1-matching-before-empty"),
    pytest.param({1: [M], 2: []}, {1: [M], 2: [H]}, id="R2-empty-before-mixed"),
    pytest.param({1: [M], 2: [M, M]}, {1: [M, H], 2: [M, M]}, id="R3-mixed-fallback"),
    pytest.param({1: [H, H], 2: [M, M]}, None, id="R4-full-rejection"),
])
def test_dt01_consumable_placement_priority(slots, expected):
    inventory = ConsumableInventory(deepcopy(slots))
    notifications = []
    inventory.was_updated.register_observer(lambda state: notifications.append(deepcopy(state)))
    if expected is None:
        with pytest.raises(Exception, match="No space for consumable!"):
            inventory.add_consumable(H)
        assert inventory.consumables_in_slots == slots
        assert notifications == []
    else:
        inventory.add_consumable(H)
        assert inventory.consumables_in_slots == expected
        assert notifications == [expected]


@pytest.mark.parametrize("count,space", [(0, True), (1, True), (2, False)])
def test_bva05_slot_capacity(count, space):
    """유효 슬롯 길이 0..2에서 공간 유무 경계 1/2 및 유효 이웃 0을 실행한다."""
    inventory = ConsumableInventory({1: [H] * count})
    assert inventory.has_space_for_more() is space
    if space:
        inventory.add_consumable(H)
        assert len(inventory.consumables_in_slots[1]) == count + 1
    else:
        with pytest.raises(Exception, match="No space for consumable!"):
            inventory.add_consumable(H)
        assert inventory.consumables_in_slots == {1: [H, H]}


@pytest.mark.parametrize("slots,target,expected", [
    pytest.param({1: [H, M], 2: []}, 2, {1: [M], 2: [H]}, id="move-to-empty"),
    pytest.param({1: [H], 2: [M, M]}, 2, {1: [M], 2: [H, M]}, id="swap-with-full"),
    pytest.param({1: [H, M], 2: []}, 1, {1: [H, M], 2: []}, id="same-slot"),
])
def test_st01_drag_preserves_consumables(slots, target, expected):
    inventory = ConsumableInventory(deepcopy(slots))
    before = Counter(value for values in slots.values() for value in values)
    inventory.drag_consumable_between_inventory_slots(1, target)
    assert inventory.consumables_in_slots == expected
    assert Counter(value for values in inventory.consumables_in_slots.values() for value in values) == before
    assert all(len(values) <= 2 for values in inventory.consumables_in_slots.values())


def test_st02_consume_until_empty_is_idempotent():
    inventory = ConsumableInventory({1: [H, M]})
    assert inventory.get_consumable_at_slot(1) is H
    assert inventory.remove_consumable_from_slot(1) is H
    assert inventory.get_consumable_at_slot(1) is M
    assert inventory.remove_consumable_from_slot(1) is M
    assert inventory.get_consumable_at_slot(1) is None
    assert inventory.remove_consumable_from_slot(1) is None
    assert inventory.consumables_in_slots == {1: []}
