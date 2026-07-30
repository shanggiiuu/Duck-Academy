"""
duck_instructor_jet.py
------------------------
Professor Quackers, Lesson 2: the Fighter Jet. Builds on the plane's
four-forces/AoA lesson (see duck_instructor.py) and adds jet-specific
concepts: turbine thrust, the afterburner, thrust-to-weight > 1, and
breaking the sound barrier.

Kept as its own class instead of subclassing DuckInstructor because the
lesson content and trigger conditions are different enough that sharing
would mean a pile of "if vehicle_kind == ..." branches. A little
duplication of the small _say/_wrap plumbing is worth it for two lesson
scripts that stay easy to read independently.
"""

from dataclasses import dataclass
from typing import List, Optional

from .vehicles import VehicleState, Controls
from .constants import SAFE_LANDING_VSPEED_MPS, SAFE_LANDING_AOA_DEG

INTRO_TEXT = (
    "Welcome to the Fighter Jet! Same four forces as the plane — thrust, "
    "drag, lift, weight — but a very different engine. A jet turbine "
    "sucks in air, burns fuel with it, and blasts the hot exhaust out the "
    "back far harder than any propeller. Press SPACE to light it up."
)

MESSAGE_HOLD_S = 7.0


@dataclass
class DuckInstructorJet:
    started: bool = False
    message: str = INTRO_TEXT
    urgent: bool = False
    _timer: float = 0.0

    _shown_throttle_tip: bool = False
    _shown_afterburner_tip: bool = False
    _shown_vertical_tip: bool = False
    _shown_supersonic_tip: bool = False
    _shown_stall_tip: bool = False
    _shown_fuel_tip: bool = False
    _shown_landed: bool = False
    _shown_crashed: bool = False
    _went_supersonic: bool = False

    def _say(self, text: str, urgent: bool = False) -> None:
        self.message = text
        self.urgent = urgent
        self._timer = MESSAGE_HOLD_S

    def begin(self) -> None:
        self.started = True
        self._say(
            "Hold [W] for throttle, same as before. New trick: hold "
            "[Left Shift] at full throttle to light the AFTERBURNER."
        )

    def reset_for_retry(self) -> None:
        self._shown_afterburner_tip = False
        self._shown_vertical_tip = False
        self._shown_supersonic_tip = False
        self._shown_landed = False
        self._shown_crashed = False
        self._went_supersonic = False
        self._say("New flight! Let's push this one further.")

    def update(
        self,
        state: VehicleState,
        controls: Controls,
        events: List[str],
        dt: float,
        prev_vy: Optional[float] = None,
        prev_aoa: Optional[float] = None,
    ) -> None:
        if self._timer > 0:
            self._timer -= dt

        if not self.started:
            return

        if not self._shown_throttle_tip and state.throttle > 0.05:
            self._shown_throttle_tip = True
            self._say(
                "Engine's spooling up — that's THRUST from burning fuel in "
                "a stream of compressed air, way more powerful than a "
                "propeller. Push it to full throttle before trying the "
                "afterburner."
            )
            return

        if "afterburner_on" in events and not self._shown_afterburner_tip:
            self._shown_afterburner_tip = True
            self._say(
                "AFTERBURNER! It sprays raw fuel into the hot exhaust for a "
                "huge extra kick of thrust. This jet's thrust now actually "
                "beats its own weight — but it drinks fuel about 8x faster, "
                "so use it in bursts."
            )
            return

        if (
            not self._shown_vertical_tip
            and state.afterburner_on
            and not state.on_ground
            and abs(state.pitch_deg - 90.0) < 20.0
            and state.vy > 40.0
        ):
            self._shown_vertical_tip = True
            self._say(
                "Look at that — nose almost straight up, full afterburner, "
                "and you're still accelerating skyward. That's a "
                "thrust-to-weight ratio greater than 1: the engine alone "
                "beats gravity. Wings are optional up here."
            )
            return

        if "supersonic" in events:
            self._went_supersonic = True
            if not self._shown_supersonic_tip:
                self._shown_supersonic_tip = True
                self._say(
                    "MACH 1 — you just broke the sound barrier! In real "
                    "life, air piles up into a shockwave right around here "
                    "and drag spikes hard (this game keeps drag simple so "
                    "you can reach Mach 1 without a fight — real supersonic "
                    "jets are shaped the way they are specifically to fight "
                    "that spike)."
                )
                return

        if "stall_entered" in events:
            if not self._shown_stall_tip:
                self._shown_stall_tip = True
                self._say(
                    "STALL! Fighters tolerate a steeper angle of attack "
                    "than the trainer plane before losing lift, but you "
                    "pushed past even that. Nose down to recover!",
                    urgent=True,
                )
            else:
                self._say("Stalling again — nose down, rebuild speed!", urgent=True)
            return

        if "stall_recovered" in events:
            self._say("Recovered — wings biting into the air again.")
            return

        if "fuel_out" in events and not self._shown_fuel_tip:
            self._shown_fuel_tip = True
            self._say(
                "Out of fuel — the afterburner drinks it fast, and now "
                "there's none left for THRUST at all. You're gliding on "
                "DRAG and WEIGHT vs whatever LIFT your speed still makes.",
                urgent=True,
            )
            return

        if "landed" in events and not self._shown_landed:
            self._shown_landed = True
            if self._went_supersonic:
                self._say(
                    "Great landing — and you broke the sound barrier this "
                    "flight! Thrust-to-weight, afterburners, and going "
                    "supersonic: that's real fighter-jet engineering. "
                    "Press [R] to fly again."
                )
            else:
                self._say(
                    "Nice landing! Try pushing to full throttle plus "
                    "afterburner next time and see if you can break Mach 1. "
                    "Press [R] to fly again."
                )
            return

        if "crashed" in events and not self._shown_crashed:
            self._shown_crashed = True
            too_fast = prev_vy is not None and -prev_vy > SAFE_LANDING_VSPEED_MPS
            too_steep = prev_aoa is not None and abs(prev_aoa) > SAFE_LANDING_AOA_DEG
            if too_fast and not too_steep:
                self._say(
                    f"Crashed — sink rate over {SAFE_LANDING_VSPEED_MPS:.0f} "
                    "m/s at touchdown. This jet is fast and heavy; cut "
                    "throttle earlier and level off sooner. Press [R] to "
                    "try again.",
                    urgent=True,
                )
            elif too_steep:
                self._say(
                    "Crashed — nose was tipped too far up at touchdown. "
                    "Keep it closer to level when you land. Press [R] to "
                    "try again.",
                    urgent=True,
                )
            else:
                self._say(
                    "Crashed! Press [R] to try again — gentle throttle and "
                    "a shallow nose angle make for a soft landing.",
                    urgent=True,
                )
            return
