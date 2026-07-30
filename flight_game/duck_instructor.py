"""
duck_instructor.py
-------------------
Professor Quackers: reacts to what's actually happening in the flight
(events + state thresholds from vehicles.py) and explains the real
aerospace concept behind it, in plain language. This is the "teaching"
layer — it never touches physics, only reads state and step_physics events.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .vehicles import VehicleState, Controls
from .constants import SAFE_LANDING_VSPEED_MPS, SAFE_LANDING_AOA_DEG

INTRO_TEXT = (
    "Hi, I'm Professor Quackers! Every flight is a tug-of-war between four "
    "forces: THRUST pushes you forward, DRAG resists that push, LIFT holds "
    "you up, and WEIGHT (gravity) pulls you down. Get the balance right and "
    "you fly. Press SPACE to start the engine."
)

MESSAGE_HOLD_S = 7.0


@dataclass
class DuckInstructor:
    started: bool = False
    message: str = INTRO_TEXT
    urgent: bool = False
    _timer: float = 0.0

    _shown_throttle_tip: bool = False
    _shown_lift_tip: bool = False
    _shown_takeoff: bool = False
    _shown_altitude_tip: bool = False
    _shown_stall_tip: bool = False
    _shown_fuel_tip: bool = False
    _shown_landed: bool = False
    _shown_crashed: bool = False

    def _say(self, text: str, urgent: bool = False) -> None:
        self.message = text
        self.urgent = urgent
        self._timer = MESSAGE_HOLD_S

    def begin(self) -> None:
        self.started = True
        self._say(
            "Engine's running! Hold [W] to push the throttle up.",
        )

    def reset_for_retry(self) -> None:
        """Called on restart after a landing/crash. Keeps lessons already
        taught (no point re-explaining thrust), just resets flight-specific
        flags so stall/landing tips can fire again."""
        self._shown_lift_tip = False
        self._shown_takeoff = False
        self._shown_altitude_tip = False
        self._shown_landed = False
        self._shown_crashed = False
        self._say("New flight! Let's try that again.")

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

        airspeed = (state.vx ** 2 + state.vy ** 2) ** 0.5

        # -- Throttle: first time the player actually pushes it up ----------
        if not self._shown_throttle_tip and state.throttle > 0.05:
            self._shown_throttle_tip = True
            self._say(
                "That's THRUST! The propeller flings air backward, and the "
                "air shoves you forward — Newton's third law. [S] eases the "
                "throttle back down."
            )
            return

        # -- Lift building on the ground, before rotation --------------------
        if (
            not self._shown_lift_tip
            and state.on_ground
            and airspeed > 25.0
        ):
            self._shown_lift_tip = True
            self._say(
                "Feel that shudder? Air is rushing over your wings. Ease "
                "[Up Arrow] to tilt the nose up a little — that's called "
                "ANGLE OF ATTACK, and it's what makes wings grab the air "
                "and generate LIFT."
            )
            return

        # -- Takeoff --------------------------------------------------------
        if "takeoff" in events and not self._shown_takeoff:
            self._shown_takeoff = True
            self._say(
                "You're airborne! LIFT is now winning against WEIGHT. See "
                "the little diamond marker out front? That's your FLIGHT "
                "PATH — where you're really going. The line is your NOSE — "
                "where you're pointed. The gap between them is your angle "
                "of attack."
            )
            return

        # -- Stall ------------------------------------------------------------
        if "stall_entered" in events:
            if not self._shown_stall_tip:
                self._shown_stall_tip = True
                self._say(
                    "STALL! Your nose is pointed way above your flight path "
                    "— too much angle of attack. The wings can't grip the "
                    "air anymore and lift collapses. Push the nose DOWN to "
                    "recover!",
                    urgent=True,
                )
            else:
                self._say(
                    "Stalling again — nose down, let speed build back up!",
                    urgent=True,
                )
            return

        if "stall_recovered" in events:
            self._say(
                "Nice recovery! Lower nose, more speed, air flowing "
                "smoothly over the wings again — lift is back."
            )
            return

        # -- Altitude milestone ------------------------------------------------
        if (
            not self._shown_altitude_tip
            and not state.on_ground
            and state.y > 800.0
        ):
            self._shown_altitude_tip = True
            self._say(
                "Notice the sky feels thinner up here? Less air means less "
                "LIFT for your wings, but also less DRAG holding you back — "
                "that trade-off is why planes cruise up high."
            )
            return

        # -- Fuel running out --------------------------------------------------
        if "fuel_out" in events and not self._shown_fuel_tip:
            self._shown_fuel_tip = True
            self._say(
                "Out of fuel — no more THRUST. Now it's just DRAG slowing "
                "you and WEIGHT pulling you down against whatever LIFT your "
                "speed can still make. You're gliding — aim for a soft "
                "landing.",
                urgent=True,
            )
            return

        # -- Landed -------------------------------------------------------------
        if "landed" in events and not self._shown_landed:
            self._shown_landed = True
            self._say(
                "Beautiful landing! You just flew the whole lesson: THRUST "
                "vs DRAG controlled your speed, LIFT vs WEIGHT controlled "
                "your altitude. That balance IS flight. Press [R] to fly "
                "again."
            )
            return

        # -- Crashed --------------------------------------------------------------
        if "crashed" in events and not self._shown_crashed:
            self._shown_crashed = True
            too_fast = prev_vy is not None and -prev_vy > SAFE_LANDING_VSPEED_MPS
            too_steep = prev_aoa is not None and abs(prev_aoa) > SAFE_LANDING_AOA_DEG
            if too_fast and not too_steep:
                self._say(
                    f"Crashed — you touched down sinking faster than "
                    f"{SAFE_LANDING_VSPEED_MPS:.0f} m/s. Cut the throttle "
                    "earlier and ease off the dive sooner next time. "
                    "Press [R] to try again.",
                    urgent=True,
                )
            elif too_steep:
                self._say(
                    "Crashed — your nose was tipped up too far at "
                    "touchdown (too much angle of attack) and the tail hit "
                    "first. Keep the nose closer to level when you land. "
                    "Press [R] to try again.",
                    urgent=True,
                )
            else:
                self._say(
                    "Crashed! Press [R] to try again — remember, gentle "
                    "throttle and a shallow nose angle make for a soft "
                    "landing.",
                    urgent=True,
                )
            return
