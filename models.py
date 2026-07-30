"""
models.py
---------
Core data classes for Duck Aerospace Academy.

These classes hold DATA ONLY. No pygame, no rendering, no game loop logic.
Keeping them "dumb" like this means:
  1. You can unit-test them without a display.
  2. You can save/load them trivially (see save_manager.py).
  3. Later, your pygame code just reads/writes these objects instead of
     tangling game state with drawing code.

Each class has:
  - a dataclass definition (the fields)
  - to_dict()   -> plain dict, safe for json.dumps
  - from_dict() -> classmethod that rebuilds the object from that dict
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional
import uuid


# ---------------------------------------------------------------------------
# Enums — using these instead of raw strings prevents typos like
# "Traning Center" silently creating a brand new building type.
# ---------------------------------------------------------------------------

class BuildingType(str, Enum):
    TRAINING_CENTER = "training_center"
    FLIGHT_SIMULATOR = "flight_simulator"
    ROCKET_HANGAR = "rocket_hangar"
    CAFETERIA = "cafeteria"
    DORMITORY = "dormitory"
    RESEARCH_LAB = "research_lab"
    MISSION_CONTROL = "mission_control"


class MissionStatus(str, Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DuckStatus(str, Enum):
    IDLE = "idle"
    TRAINING = "training"
    ON_MISSION = "on_mission"
    INJURED = "injured"


# ---------------------------------------------------------------------------
# Duck
# ---------------------------------------------------------------------------

@dataclass
class DuckStats:
    """Grouped separately from Duck itself so it's easy to pass around,
    compare, or feed into a mini-game's difficulty calculation."""
    intelligence: int = 1
    strength: int = 1
    piloting: int = 1
    engineering: int = 1
    morale: int = 100          # 0-100, distinct scale from skill stats
    experience: int = 0        # uncapped, drives leveling

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DuckStats":
        return cls(**data)


@dataclass
class Duck:
    name: str
    traits: List[str] = field(default_factory=list)   # e.g. ["afraid_of_heights"]
    stats: DuckStats = field(default_factory=DuckStats)
    status: DuckStatus = DuckStatus.IDLE
    duck_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "traits": self.traits,
            "stats": self.stats.to_dict(),
            "status": self.status.value,
            "duck_id": self.duck_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Duck":
        return cls(
            name=data["name"],
            traits=data.get("traits", []),
            stats=DuckStats.from_dict(data["stats"]),
            status=DuckStatus(data["status"]),
            duck_id=data["duck_id"],
        )


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

@dataclass
class Building:
    building_type: BuildingType
    level: int = 1
    max_level: int = 5

    def upgrade_cost(self) -> int:
        """Simple cost curve. Tune freely once you playtest."""
        return 100 * (self.level ** 2)

    def can_upgrade(self) -> bool:
        return self.level < self.max_level

    def to_dict(self) -> dict:
        return {
            "building_type": self.building_type.value,
            "level": self.level,
            "max_level": self.max_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Building":
        return cls(
            building_type=BuildingType(data["building_type"]),
            level=data["level"],
            max_level=data["max_level"],
        )


# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------

@dataclass
class Mission:
    mission_id: str            # stable key, e.g. "weather_balloon_test"
    name: str
    status: MissionStatus = MissionStatus.LOCKED
    required_stats: Dict[str, int] = field(default_factory=dict)
    reward_coins: int = 0
    assigned_duck_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "status": self.status.value,
            "required_stats": self.required_stats,
            "reward_coins": self.reward_coins,
            "assigned_duck_id": self.assigned_duck_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Mission":
        return cls(
            mission_id=data["mission_id"],
            name=data["name"],
            status=MissionStatus(data["status"]),
            required_stats=data.get("required_stats", {}),
            reward_coins=data.get("reward_coins", 0),
            assigned_duck_id=data.get("assigned_duck_id"),
        )


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

@dataclass
class ResearchNode:
    research_id: str           # e.g. "better_rockets"
    name: str
    unlocked: bool = False
    cost: int = 500
    prerequisites: List[str] = field(default_factory=list)  # other research_ids

    def to_dict(self) -> dict:
        return {
            "research_id": self.research_id,
            "name": self.name,
            "unlocked": self.unlocked,
            "cost": self.cost,
            "prerequisites": self.prerequisites,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchNode":
        return cls(
            research_id=data["research_id"],
            name=data["name"],
            unlocked=data["unlocked"],
            cost=data["cost"],
            prerequisites=data.get("prerequisites", []),
        )