"""EP01/BVA01: 저장 경계의 유효·비유효 분할, 타입 혼동, 최소값 이웃.

명세 근거: player_file.py의 정수 필드 검증 계약. 무효 입력은 한 필드만
바꿔 결함 마스킹을 피한다. 실제 UI의 최대 레벨을 임의로 가정하지 않는다.
"""

from copy import deepcopy

import pytest

from pythongame.player_file import PlayerStateJson, SaveFileError

pytestmark = pytest.mark.unit

FIELDS = [("level", 1), ("exp", 0), ("money", 0), ("total_time_played", 0)]


@pytest.mark.parametrize("field,minimum", FIELDS)
@pytest.mark.parametrize("value", [True, False, 1.5, "1", None, []],
                         ids=["bool-true", "bool-false", "fraction", "text", "null", "list"])
def test_ep01_save_integer_type_partitions(save_payload, field, minimum, value):
    """정수처럼 보이는 값도 자동 변환 없이 거부하고 입력을 보존해야 한다."""
    save_payload[field] = value
    before = deepcopy(save_payload)
    with pytest.raises(SaveFileError, match=f"Invalid {field}:"):
        PlayerStateJson.deserialize(save_payload)
    assert save_payload == before


@pytest.mark.parametrize("field,minimum", FIELDS)
@pytest.mark.parametrize("offset", [-2, -1, 0, 1], ids=["below-neighbor", "last-invalid", "first-valid", "above-neighbor"])
def test_bva01_save_integer_minimum(save_payload, field, minimum, offset):
    """인접 두 분할 경계(min-1, min)의 양옆까지 3-value 항목을 모두 실행한다."""
    value = minimum + offset
    save_payload[field] = value
    if offset < 0:
        with pytest.raises(SaveFileError, match=f"Invalid {field}:"):
            PlayerStateJson.deserialize(save_payload)
    else:
        restored = PlayerStateJson.deserialize(save_payload)
        assert PlayerStateJson.serialize(restored)[field] == value
