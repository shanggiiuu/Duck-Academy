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
    "drag, lift, weight — but a very different engine under the hood. A "
    "jet engine sucks in air at the front, squeezes it super tight, mixes "
    "in fuel and burns it, then blasts the hot gas out the back way "
    "harder than any spinning propeller could. Press SPACE to light it up."
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
            "Hold [W] for throttle, same as the plane. New trick: once "
            "you're at full throttle, hold [Left Shift] to light the "
            "AFTERBURNER."
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
                "Engine's spooling up! Inside, spinning blades pack the "
                "air in tight, fuel burns in it, and the hot gas rockets "
                "out the back — that's your THRUST, way stronger than a "
                "propeller. Push all the way to full throttle before "
                "trying the afterburner."
            )
            return

        if "afterburner_on" in events and not self._shown_afterburner_tip:
            self._shown_afterburner_tip = True
            self._say(
                "AFTERBURNER! It sprays extra fuel straight into the hot "
                "exhaust for a huge kick of THRUST. Now this jet actually "
                "pushes harder than it weighs — but it gulps fuel about 8x "
                "faster, so use it in short bursts, not the whole flight."
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
                "Look at that — nose straight up, afterburner blazing, and "
                "you're still speeding up. Your engine is now pushing "
                "harder than gravity pulls you down, so you don't even "
                "need your wings to climb. That's called thrust beating "
                "weight."
            )
            return

        if "supersonic" in events:
            self._went_supersonic = True
            if not self._shown_supersonic_tip:
                self._shown_supersonic_tip = True
                self._say(
                    "MACH 1 — you just flew faster than sound! Sound is a "
                    "wave moving through air, and you just outran your own "
                    "engine noise. In real life the air piles up in front "
                    "of the jet and gets hard to push through right here "
                    "— that's why real supersonic jets have those sharp, "
                    "pointy shapes."
                )
                return

        if "stall_entered" in events:
            if not self._shown_stall_tip:
                self._shown_stall_tip = True
                self._say(
                    "STALL! Fighter wings can tilt steeper than the "
                    "trainer plane before losing their grip on the air, "
                    "but you tilted past even that limit. Nose down to "
                    "grab the air again!",
                    urgent=True,
                )
            else:
                self._say(
                    "Stalling again — nose down, let your speed build "
                    "back up!",
                    urgent=True,
                )
            return

        if "stall_recovered" in events:
            self._say("Recovered — your wings are biting into the air again.")
            return

        if "fuel_out" in events and not self._shown_fuel_tip:
            self._shown_fuel_tip = True
            self._say(
                "Out of fuel — the afterburner gulped it down fast, and "
                "now there's no THRUST left at all. You're gliding now: "
                "DRAG and WEIGHT against whatever LIFT your speed can "
                "still make.",
                urgent=True,
            )
            return

        if "landed" in events and not self._shown_landed:
            self._shown_landed = True
            if self._went_supersonic:
                self._say(
                    "Great landing — and you flew faster than sound this "
                    "flight! Powerful jet engines, afterburners, and "
                    "breaking Mach 1: that's real fighter-jet engineering. "
                    "Press [R] to fly again!"
                )
            else:
                self._say(
                    "Nice landing! Next time, try full throttle plus the "
                    "afterburner and see if you can break Mach 1. Press "
                    "[R] to fly again."
                )
            return

        if "crashed" in events and not self._shown_crashed:
            self._shown_crashed = True
            too_fast = prev_vy is not None and -prev_vy > SAFE_LANDING_VSPEED_MPS
            too_steep = prev_aoa is not None and abs(prev_aoa) > SAFE_LANDING_AOA_DEG
            if too_fast and not too_steep:
                self._say(
                    "Crashed — you came down way too fast. This jet is "
                    "fast and heavy, so cut the throttle earlier and level "
                    "off sooner next time. Press [R] to try again.",
                    urgent=True,
                )
            elif too_steep:
                self._say(
                    "Crashed — your nose was tilted up too far when you "
                    "touched down. Keep it closer to level as you land. "
                    "Press [R] to try again.",
                    urgent=True,
                )
            else:
                self._say(
                    "Crashed! Press [R] to try again — gentle power and a "
                    "level nose make for a soft landing.",
                    urgent=True,
                )
            return
