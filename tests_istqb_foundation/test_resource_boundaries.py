"""BVA02–04/WB01: 체력·마나의 정수 경계와 소수 누적, 관찰자 분기."""

import pytest

from pythongame.core.common import Millis
from pythongame.core.health_and_mana import HealthOrManaResource

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("amount,expected,gained", [(8, 98, 8), (9, 99, 9), (10, 100, 10), (11, 100, 10)])
def test_bva02_gain_saturates_at_maximum(amount, expected, gained):
    resource = HealthOrManaResource(100, 0)
    resource.lose(10)
    notifications = []
    resource.value_was_updated.register_observer(notifications.append)
    assert resource.gain(amount) == gained
    assert resource.value == expected
    assert resource.is_at_max() is (expected == 100)
    assert notifications == [(expected, 100)]


@pytest.mark.parametrize("damage,value,dead", [(8, 2, False), (9, 1, False), (10, 0, True), (11, -1, True)])
def test_bva03_zero_health_predicate(damage, value, dead):
    """음수 체력도 사망 판정 범위다. 구현에 없는 0 클램프를 요구하지 않는다."""
    resource = HealthOrManaResource(10, 0)
    assert resource.lose(damage) == damage
    assert resource.value == value
    assert resource.is_at_or_below_zero() is dead


@pytest.mark.parametrize("elapsed,expected", [(498, 0), (499, 0), (500, 1), (501, 1)])
def test_bva04_regeneration_millisecond_boundary(elapsed, expected):
    resource = HealthOrManaResource(100, 1)
    resource.regen_bonus = 1
    resource.set_zero()
    resource.regenerate(Millis(elapsed))
    assert resource.value == expected


def test_eg01_fractional_regeneration_accumulates():
    """프레임마다 소수를 버리면 자원이 영원히 회복되지 않는 오류를 검출한다."""
    resource = HealthOrManaResource(100, 2)
    resource.set_zero()
    for expected in (0, 0, 0, 1):
        resource.regenerate(Millis(125))
        assert resource.value == expected


@pytest.mark.parametrize("remaining,expected,events", [(70, 70, []), (90, 80, [(80, 80)])])
def test_wb01_reducing_maximum_clamps_only_when_needed(remaining, expected, events):
    resource = HealthOrManaResource(100, 0)
    resource.lose(100 - remaining)
    notifications = []
    resource.value_was_updated.register_observer(notifications.append)
    resource.decrease_max(20)
    assert (resource.value, resource.max_value) == (expected, 80)
    assert notifications == events
    assert resource.gain_to_max() == 80 - expected
    assert resource.value == 80
