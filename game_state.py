"""
game_state.py
-------------
GameState is the single source of truth for a save file's contents.
Your future pygame loop should hold ONE GameState instance and read/write
through it — screens shouldn't keep their own copies of duck lists, coin
counts, etc. That's the #1 source of "why did my coins reset" bugs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from models import Duck, Building, Mission, ResearchNode, BuildingType, MissionStatus


@dataclass
class GameState:
    # Meta
    save_version: int = 1
    academy_name: str = "Duck Aerospace Academy"
    play_time_seconds: float = 0.0

    # Economy
    space_coins: int = 500

    # Collections — keyed by id for O(1) lookup instead of scanning lists
    ducks: Dict[str, Duck] = field(default_factory=dict)
    buildings: Dict[str, Building] = field(default_factory=dict)
    missions: Dict[str, Mission] = field(default_factory=dict)
    research: Dict[str, ResearchNode] = field(default_factory=dict)

    unlocked_planets: List[str] = field(default_factory=lambda: ["Earth"])

    # -- Convenience methods ------------------------------------------------

    def add_duck(self, duck: Duck) -> None:
        self.ducks[duck.duck_id] = duck

    def remove_duck(self, duck_id: str) -> None:
        self.ducks.pop(duck_id, None)

    def get_building(self, building_type: BuildingType) -> Optional[Building]:
        return self.buildings.get(building_type.value)

    def spend_coins(self, amount: int) -> bool:
        """Returns False (and spends nothing) if the player can't afford it.
        Always route spending through this instead of `state.space_coins -= x`
        directly, so you can never go negative by accident."""
        if amount > self.space_coins:
            return False
        self.space_coins -= amount
        return True

    def earn_coins(self, amount: int) -> None:
        self.space_coins += amount

    # -- Serialization --------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "save_version": self.save_version,
            "academy_name": self.academy_name,
            "play_time_seconds": self.play_time_seconds,
            "space_coins": self.space_coins,
            "ducks": {k: v.to_dict() for k, v in self.ducks.items()},
            "buildings": {k: v.to_dict() for k, v in self.buildings.items()},
            "missions": {k: v.to_dict() for k, v in self.missions.items()},
            "research": {k: v.to_dict() for k, v in self.research.items()},
            "unlocked_planets": self.unlocked_planets,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        return cls(
            save_version=data.get("save_version", 1),
            academy_name=data.get("academy_name", "Duck Aerospace Academy"),
            play_time_seconds=data.get("play_time_seconds", 0.0),
            space_coins=data.get("space_coins", 500),
            ducks={k: Duck.from_dict(v) for k, v in data.get("ducks", {}).items()},
            buildings={k: Building.from_dict(v) for k, v in data.get("buildings", {}).items()},
            missions={k: Mission.from_dict(v) for k, v in data.get("missions", {}).items()},
            research={k: ResearchNode.from_dict(v) for k, v in data.get("research", {}).items()},
            unlocked_planets=data.get("unlocked_planets", ["Earth"]),
        )

    @classmethod
    def new_game(cls) -> "GameState":
        """Factory for a fresh save: starting buildings at level 1,
        first mission unlocked, everything else locked."""
        state = cls()

        for bt in BuildingType:
            state.buildings[bt.value] = Building(building_type=bt, level=1)

        state.missions["weather_balloon_test"] = Mission(
            mission_id="weather_balloon_test",
            name="Weather Balloon Test",
            status=MissionStatus.AVAILABLE,
            required_stats={"piloting": 1},
            reward_coins=100,
        )

        return state