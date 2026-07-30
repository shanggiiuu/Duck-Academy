"""
save_manager.py
----------------
Handles reading/writing GameState to disk as JSON.

Design choices:
- Multiple numbered "slots" (save_1.json, save_2.json, ...) since most
  management/sim games offer several save slots.
- A separate autosave.json that's overwritten frequently, so it never
  clobbers a manual save.
- Writes to a temp file then renames it into place (atomic on POSIX).
  This means if the game crashes or is force-quit mid-save, you don't end
  up with a half-written, corrupted JSON file eating someone's progress.
- load_game returns None (not an exception) when a slot is empty, so
  your menu code can just do `if state is None: show "New Game" button`.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from game_state import GameState


class SaveManager:
    def __init__(self, save_dir: str = "saves"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _slot_path(self, slot: int) -> Path:
        return self.save_dir / f"save_{slot}.json"

    def _autosave_path(self) -> Path:
        return self.save_dir / "autosave.json"

    # -- Core read/write --------------------------------------------------

    def _write_atomic(self, path: Path, data: dict) -> None:
        """Write JSON safely: dump to a temp file in the same directory,
        then os.replace() it over the target. os.replace is atomic on the
        same filesystem, so readers never see a partially-written file."""
        fd, tmp_path = tempfile.mkstemp(dir=self.save_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def save_game(self, state: GameState, slot: int = 1) -> None:
        self._write_atomic(self._slot_path(slot), state.to_dict())

    def load_game(self, slot: int = 1) -> Optional[GameState]:
        path = self._slot_path(slot)
        if not path.exists():
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return GameState.from_dict(data)

    def delete_save(self, slot: int) -> None:
        path = self._slot_path(slot)
        if path.exists():
            path.unlink()

    def slot_exists(self, slot: int) -> bool:
        return self._slot_path(slot).exists()

    def list_slots(self, max_slots: int = 5) -> dict:
        """Returns {slot_number: bool_has_save} for menu rendering."""
        return {i: self.slot_exists(i) for i in range(1, max_slots + 1)}

    # -- Autosave -----------------------------------------------------------

    def autosave(self, state: GameState) -> None:
        self._write_atomic(self._autosave_path(), state.to_dict())

    def load_autosave(self) -> Optional[GameState]:
        path = self._autosave_path()
        if not path.exists():
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return GameState.from_dict(data)