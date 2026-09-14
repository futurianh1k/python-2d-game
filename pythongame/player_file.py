import logging
from pathlib import Path
from typing import Dict, List, Optional

from pythongame.core.common import Millis, HeroId, ConsumableType, PortalId, Sprite
from pythongame.core.game_state import PlayerState
from pythongame.core.quests import QuestId
from pythongame.json_files import read_json, write_json_atomic

logger = logging.getLogger(__name__)


class SaveFileError(ValueError):
    """A save does not match the supported JSON structure."""


class SavedPlayerState:
    def __init__(self, hero_id: str, level: int, exp: int, consumables_in_slots: Dict[str, List[str]],
                 items: List[List[str]], money: int, enabled_portals: Dict[str, str], talent_tier_choices: List[int],
                 total_time_played_on_character: Millis, active_quests: List[str], completed_quests: List[str]):
        self.hero_id = hero_id
        self.level = level
        self.exp = exp
        self.consumables_in_slots = consumables_in_slots
        self.items: List[List[str]] = items
        self.money = money
        self.enabled_portals = enabled_portals
        self.talent_tier_choices = talent_tier_choices
        self.total_time_played_on_character = total_time_played_on_character
        self.active_quests = active_quests
        self.completed_quests = completed_quests


class PlayerStateJson:
    @staticmethod
    def serialize(player_state: SavedPlayerState):
        return {
            "hero": player_state.hero_id,
            "level": player_state.level,
            "exp": player_state.exp,
            "consumables": player_state.consumables_in_slots,
            "items": player_state.items,
            "money": player_state.money,
            "enabled_portals": player_state.enabled_portals,
            "talents": player_state.talent_tier_choices,
            "total_time_played": player_state.total_time_played_on_character,
            "active_quests": player_state.active_quests,
            "completed_quests": player_state.completed_quests
        }

    @staticmethod
    def deserialize(data) -> SavedPlayerState:
        PlayerStateJson.validate(data)
        return SavedPlayerState(
            data["hero"],
            data["level"],
            data["exp"],
            data["consumables"],
            data["items"],
            data["money"],
            data["enabled_portals"],
            data.get("talents", []),
            data.get("total_time_played", 0),
            data.get("active_quests", []),
            data.get("completed_quests", []),
        )

    @staticmethod
    def validate(data):
        if not isinstance(data, dict):
            raise SaveFileError("Save must be a JSON object")
        required = {"hero", "level", "exp", "consumables", "items", "money", "enabled_portals"}
        if not required <= data.keys():
            raise SaveFileError("Save is missing required fields")
        if not isinstance(data["hero"], str) or data["hero"] not in HeroId.__members__:
            raise SaveFileError("Invalid hero")
        for field, minimum in (("level", 1), ("exp", 0), ("money", 0), ("total_time_played", 0)):
            value = data.get(field, 0)
            if type(value) is not int or value < minimum:
                raise SaveFileError(f"Invalid {field}: expected an integer >= {minimum}")
        consumables = data["consumables"]
        if not isinstance(consumables, dict):
            raise SaveFileError("Invalid consumables")
        for slot, values in consumables.items():
            if slot not in {"1", "2", "3", "4", "5"}:
                raise SaveFileError("Invalid consumable slot")
            PlayerStateJson._validate_enum_list(values, ConsumableType, "consumables")
        items = data["items"]
        if not isinstance(items, list) or any(
            item is not None and (not isinstance(item, list) or len(item) != 2
                                 or not all(isinstance(part, str) for part in item))
            for item in items
        ):
            raise SaveFileError("Invalid items")
        portals = data["enabled_portals"]
        if not isinstance(portals, dict) or any(
            key not in PortalId.__members__ or not isinstance(value, str) or value not in Sprite.__members__
            for key, value in portals.items()
        ):
            raise SaveFileError("Invalid enabled_portals")
        talents = data.get("talents", [])
        if not isinstance(talents, list) or any(
            value is not None and (type(value) is not int or value < 0) for value in talents
        ):
            raise SaveFileError("Invalid talents")
        for field in ("active_quests", "completed_quests"):
            PlayerStateJson._validate_enum_list(data.get(field, []), QuestId, field)

    @staticmethod
    def _validate_enum_list(values, enum_type, field):
        if not isinstance(values, list) or any(
            not isinstance(value, str) or value not in enum_type.__members__ for value in values
        ):
            raise SaveFileError(f"Invalid {field}")


class SaveFileHandler:

    def __init__(self, directory: str | Path = "saved_characters"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, filename: str) -> Path:
        if not filename or "/" in filename or "\\" in filename or Path(filename).is_absolute() \
                or Path(filename).suffix != ".json":
            raise SaveFileError("Save filename must be a .json basename")
        path = self.directory / filename
        if path.is_symlink():
            raise SaveFileError("Save file must not be a symbolic link")
        return path

    def load_player_state_from_json_file(self, filename: str) -> SavedPlayerState:
        path = self._path(filename)
        json_data = read_json(path)
        try:
            return PlayerStateJson.deserialize(json_data)
        except SaveFileError:
            logger.exception("Invalid save structure: %s", path)
            raise

    def _save_player_state_to_json_file(self, player_state: SavedPlayerState, filename: str):
        json_data = PlayerStateJson.serialize(player_state)
        PlayerStateJson.validate(json_data)
        write_json_atomic(self._path(filename), json_data)

    def save_to_file(self, player_state: PlayerState, existing_save_file: Optional[str],
                     total_time_played_on_character: Millis) -> str:
        if existing_save_file:
            filename = existing_save_file
        else:
            filename = self._generate_filename_for_new_character()
        saved_player_state = SavedPlayerState(
            hero_id=player_state.hero_id.name,
            level=player_state.level,
            exp=player_state.exp,
            consumables_in_slots={str(slot_number): [c.name for c in consumables] for (slot_number, consumables)
                                  in player_state.consumable_inventory.consumables_in_slots.items()},
            items=[[slot.get_item_id().stats_string, slot.get_item_id().name] if not slot.is_empty() else None
                   for slot in player_state.item_inventory.slots],
            money=player_state.money,
            enabled_portals={portal_id.name: sprite.name
                             for (portal_id, sprite) in player_state.enabled_portals.items()},
            talent_tier_choices=player_state.get_serilized_talent_tier_choices(),
            total_time_played_on_character=total_time_played_on_character,
            active_quests=[q.quest_id.name for q in player_state.active_quests],
            completed_quests=[q.quest_id.name for q in player_state.completed_quests]
        )
        self._save_player_state_to_json_file(saved_player_state, filename)
        logger.info("Saved character: %s", self.directory / filename)
        return filename

    def list_save_files(self):
        files = [path.name for path in self.directory.glob("*.json")
                 if path.is_file() and not path.is_symlink()]
        return sorted(files, key=lambda name: (0, int(Path(name).stem), name)
                      if Path(name).stem.isascii() and Path(name).stem.isdecimal() else (1, 0, name))

    def _generate_filename_for_new_character(self):
        # Reserve numeric names even when the entry is a directory or a damaged save.
        existing_ids = [int(path.stem) for path in self.directory.glob("*.json")
                        if path.stem.isascii() and path.stem.isdecimal()]
        return f"{max(existing_ids, default=0) + 1}.json"
