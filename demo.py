"""
demo.py
-------
Proves the data architecture works, end to end, with zero pygame code.
Run this with: python demo.py

This is the kind of thing worth keeping around (or turning into real
unit tests with pytest) so that when you build the pygame layer on top,
you already know save/load isn't the source of any bugs you hit.
"""

from models import Duck, DuckStats
from game_state import GameState
from save_manager import SaveManager


def main():
    print("=== Duck Aerospace Academy — Save System Demo ===\n")

    # 1. Start a fresh game
    state = GameState.new_game()
    print(f"New academy '{state.academy_name}' created with {state.space_coins} coins.")
    print(f"Buildings: {list(state.buildings.keys())}")
    print(f"Starting mission: {state.missions['weather_balloon_test'].name}\n")

    # 2. Recruit some ducks
    quackers = Duck(
        name="Quackers",
        traits=["loves_engineering", "afraid_of_heights"],
        stats=DuckStats(engineering=8, intelligence=6, piloting=2),
    )
    captain_fluff = Duck(
        name="Captain Fluff",
        traits=["excellent_pilot", "gets_hungry_often"],
        stats=DuckStats(piloting=9, intelligence=4),
    )
    state.add_duck(quackers)
    state.add_duck(captain_fluff)
    print(f"Recruited: {quackers.name} (id={quackers.duck_id}), "
          f"{captain_fluff.name} (id={captain_fluff.duck_id})\n")

    # 3. Spend coins upgrading a building
    from models import BuildingType
    training_center = state.get_building(BuildingType.TRAINING_CENTER)
    cost = training_center.upgrade_cost()
    if state.spend_coins(cost):
        training_center.level += 1
        print(f"Upgraded Training Center to level {training_center.level} "
              f"for {cost} coins. Remaining: {state.space_coins}\n")

    # 4. Complete the starting mission, earn coins
    mission = state.missions["weather_balloon_test"]
    mission.assigned_duck_id = captain_fluff.duck_id
    from models import MissionStatus
    mission.status = MissionStatus.COMPLETED
    state.earn_coins(mission.reward_coins)
    print(f"Mission '{mission.name}' completed by {captain_fluff.name}. "
          f"Earned {mission.reward_coins} coins. Total: {state.space_coins}\n")

    # 5. Save to slot 1
    manager = SaveManager(save_dir="saves")
    manager.save_game(state, slot=1)
    print("Saved to slot 1.\n")

    # 6. Simulate restarting the app: load fresh from disk
    loaded_state = manager.load_game(slot=1)
    assert loaded_state is not None, "Save failed to load!"

    print("=== Reloaded from disk ===")
    print(f"Academy: {loaded_state.academy_name}")
    print(f"Coins: {loaded_state.space_coins}")
    print(f"Ducks: {[d.name for d in loaded_state.ducks.values()]}")
    print(f"Training Center level: {loaded_state.buildings['training_center'].level}")
    print(f"Mission status: {loaded_state.missions['weather_balloon_test'].status.value}")

    # 7. Sanity check: reloaded data should exactly match what we saved
    assert loaded_state.space_coins == state.space_coins
    assert loaded_state.buildings["training_center"].level == training_center.level
    assert set(d.name for d in loaded_state.ducks.values()) == {"Quackers", "Captain Fluff"}
    print("\n✅ All checks passed — save/load round-trip is solid.")


if __name__ == "__main__":
    main()