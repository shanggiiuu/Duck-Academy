"""
duck_instructor_spaceship.py
------------------------------
Professor Quackers, Lesson 3: the Spaceship. Builds on the plane's
thrust/drag/lift/weight lesson and the jet's engine lesson, and adds
rocket-specific ideas: carrying your own oxidizer, the gravity turn,
Max-Q, staging, the edge of space, and what "orbit" really means.

Kept as its own class for the same reason as DuckInstructorJet — the
lesson content and trigger conditions are different enough that a shared
class would turn into a pile of "if vehicle_kind == ..." branches.
"""

from dataclasses import dataclass
from typing import List, Optional

from .vehicles import VehicleState, Controls
from .constants import SAFE_LANDING_VSPEED_MPS, MACH1_MPS

INTRO_TEXT = (
    "Welcome to the Spaceship! Planes and jets push against AIR to fly — "
    "but up in space there's no air to push against. That's why rockets "
    "carry their own oxygen (called an oxidizer) along with their fuel, so "
    "they can burn and make THRUST even in a total vacuum. Press SPACE to "
    "light the engine."
)

MESSAGE_HOLD_S = 7.0


@dataclass
class DuckInstructorSpaceship:
    started: bool = False
    message: str = INTRO_TEXT
    urgent: bool = False
    _timer: float = 0.0

    _shown_throttle_tip: bool = False
    _shown_liftoff: bool = False
    _shown_turn_tip: bool = False
    _shown_max_q: bool = False
    _shown_stage: bool = False
    _shown_supersonic: bool = False
    _shown_space: bool = False
    _shown_orbit: bool = False
    _shown_fuel_tip: bool = False
    _shown_landed: bool = False
    _shown_crashed: bool = False
    _reached_orbit: bool = False

    def _say(self, text: str, urgent: bool = False) -> None:
        self.message = text
        self.urgent = urgent
        self._timer = MESSAGE_HOLD_S

    def begin(self) -> None:
        self.started = True
        self._say(
            "Hold [W] to throttle up. Once you're off the pad, tap [Down "
            "Arrow] every so often to slowly tip over — that's how real "
            "rockets trade 'going up' for 'going sideways' on the way to "
            "orbit."
        )

    def reset_for_retry(self) -> None:
        self._shown_turn_tip = False
        self._shown_max_q = False
        self._shown_stage = False
        self._shown_supersonic = False
        self._shown_space = False
        self._shown_orbit = False
        self._shown_landed = False
        self._shown_crashed = False
        self._reached_orbit = False
        self._say("New launch! Let's try to reach orbit this time.")

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
                "Engine lit! A rocket engine mixes fuel with its own "
                "oxidizer and burns it in a chamber, then squeezes the hot "
                "gas out a narrow nozzle — that's your THRUST. Push to "
                "full throttle to lift off the pad."
            )
            return

        if "takeoff" in events and not self._shown_liftoff:
            self._shown_liftoff = True
            self._say(
                "Liftoff! Right now THRUST is barely beating WEIGHT, so "
                "you're climbing slowly at first — that's normal, you're "
                "carrying a full tank of fuel and it's heavy."
            )
            return

        if (
            not self._shown_turn_tip
            and not state.on_ground
            and state.y > 3000.0
        ):
            self._shown_turn_tip = True
            self._say(
                "Try tapping [Down Arrow] gently to start leaning over. "
                "This is the GRAVITY TURN: real rockets tip sideways early "
                "so their engine builds up SIDEWAYS speed, not just "
                "height — and sideways speed is exactly what you need to "
                "reach orbit."
            )
            return

        if "max_q" in events and not self._shown_max_q:
            self._shown_max_q = True
            self._say(
                "That was MAX-Q — the point where the air pushing back on "
                "you (DRAG) is at its strongest for this whole flight. "
                "You're moving fast, but there's still enough thick air "
                "below to shove back hard. Real rockets briefly ease off "
                "the throttle right here so they don't shake apart."
            )
            return

        if "stage_separation" in events and not self._shown_stage:
            self._shown_stage = True
            self._say(
                "STAGING! Your first fuel tank just ran dry, so you "
                "dropped it and lit a second, smaller engine. Carrying "
                "less empty, dead weight means the rest of your fuel goes "
                "a lot further — that's why real rockets are built in "
                "stages instead of one giant tank."
            )
            return

        if "supersonic" in events and not self._shown_supersonic:
            self._shown_supersonic = True
            self._say(
                f"You just passed {MACH1_MPS:.0f} m/s — faster than "
                "sound! Going up, that matters less than it does for a "
                "jet, since the air (and its drag) is already thinning "
                "out fast the higher you climb."
            )
            return

        if "reached_space" in events and not self._shown_space:
            self._shown_space = True
            self._say(
                "You just crossed the KARMAN LINE, 100 kilometers up — "
                "the internationally agreed edge of space! There's "
                "basically no air here, so wings and even drag stop "
                "mattering. Only THRUST, your speed, and gravity decide "
                "where you go now."
            )
            return

        if "orbit_achieved" in events and not self._shown_orbit:
            self._shown_orbit = True
            self._reached_orbit = True
            self._say(
                "ORBIT ACHIEVED! Here's the secret: orbit isn't about "
                "escaping gravity — gravity is still pulling on you just "
                "as hard. You're simply moving SIDEWAYS so fast that as "
                "you fall, the ground curves away underneath you just as "
                "quickly. You're falling and missing, forever.",
                urgent=False,
            )
            return

        if "fuel_out" in events and not self._shown_fuel_tip:
            self._shown_fuel_tip = True
            self._say(
                "Out of fuel — no more THRUST. Up here there's barely any "
                "DRAG either, so you'll keep coasting on whatever speed "
                "and direction you already had. Only WEIGHT (gravity) is "
                "still pulling on you now.",
                urgent=True,
            )
            return

        if "landed" in events and not self._shown_landed:
            self._shown_landed = True
            if self._reached_orbit:
                self._say(
                    "Nice touchdown — and you reached orbit this flight! "
                    "Rocket engines, the gravity turn, staging, and orbit: "
                    "that's real spaceflight engineering. Press [R] to "
                    "launch again."
                )
            else:
                self._say(
                    "Nice touchdown! Try tipping over earlier and holding "
                    "more throttle next time to build enough sideways "
                    "speed for orbit. Press [R] to launch again."
                )
            return

        if "crashed" in events and not self._shown_crashed:
            self._shown_crashed = True
            too_fast = prev_vy is not None and -prev_vy > SAFE_LANDING_VSPEED_MPS
            if too_fast:
                self._say(
                    "Crashed — you came down way too fast. Rockets are "
                    "heavy; cut the throttle and level off much earlier "
                    "next time. Press [R] to try again.",
                    urgent=True,
                )
            else:
                self._say(
                    "Crashed! Press [R] to try again — gentle throttle "
                    "and a controlled descent make for a soft landing.",
                    urgent=True,
                )
            return
