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
    "Hi, I'm Professor Quackers! Flying is a tug-of-war between four "
    "pushes and pulls: THRUST pushes you forward, DRAG pushes back, LIFT "
    "pushes you up, and WEIGHT (that's just gravity) pulls you down. Get "
    "them balanced right and you fly! Press SPACE to start the engine."
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
            "Engine's running! Hold down the [W] key to add power.",
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
                "That push you feel is THRUST! The propeller throws air "
                "backward, so the air pushes you forward — like paddling a "
                "boat, but with air. Hold [S] to slow the throttle back "
                "down."
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
                "Feel that shake? Air is rushing over your wings now. Tap "
                "[Up Arrow] to tilt your nose up just a little — tilting "
                "the wing like that is called ANGLE OF ATTACK, and it's "
                "how wings grab the air to make LIFT."
            )
            return

        # -- Takeoff --------------------------------------------------------
        if "takeoff" in events and not self._shown_takeoff:
            self._shown_takeoff = True
            self._say(
                "You're flying! LIFT is now winning the tug-of-war against "
                "WEIGHT. See the white line? That's where your NOSE is "
                "pointed. The green circle is your FLIGHT PATH — where "
                "you're actually going. They're not always the same spot!"
            )
            return

        # -- Stall ------------------------------------------------------------
        if "stall_entered" in events:
            if not self._shown_stall_tip:
                self._shown_stall_tip = True
                self._say(
                    "STALL! Your nose tilted up too far above where you're "
                    "actually going. The wings lost their grip on the air, "
                    "so LIFT disappeared. Push the nose DOWN to grab the "
                    "air again!",
                    urgent=True,
                )
            else:
                self._say(
                    "Stalling again — nose down, let your speed build back "
                    "up!",
                    urgent=True,
                )
            return

        if "stall_recovered" in events:
            self._say(
                "Nice recovery! Nose is lower, speed is back up, and air "
                "is flowing smoothly over your wings again — LIFT is back."
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
                "Notice the air feels thinner up here? Less air means less "
                "LIFT for your wings — but also less DRAG slowing you down. "
                "That trade-off is why real planes like to cruise up high."
            )
            return

        # -- Fuel running out --------------------------------------------------
        if "fuel_out" in events and not self._shown_fuel_tip:
            self._shown_fuel_tip = True
            self._say(
                "Out of fuel — no more THRUST pushing you forward. Now "
                "it's just DRAG slowing you down and WEIGHT pulling you "
                "toward the ground, fighting whatever LIFT your speed can "
                "still make. You're gliding now — aim for a soft landing!",
                urgent=True,
            )
            return

        # -- Landed -------------------------------------------------------------
        if "landed" in events and not self._shown_landed:
            self._shown_landed = True
            self._say(
                "Beautiful landing! You just learned the whole lesson: "
                "THRUST vs DRAG controlled your speed, LIFT vs WEIGHT "
                "controlled your height. Balancing those four is what "
                "flying really is. Press [R] to fly again!"
            )
            return

        # -- Crashed --------------------------------------------------------------
        if "crashed" in events and not self._shown_crashed:
            self._shown_crashed = True
            too_fast = prev_vy is not None and -prev_vy > SAFE_LANDING_VSPEED_MPS
            too_steep = prev_aoa is not None and abs(prev_aoa) > SAFE_LANDING_AOA_DEG
            if too_fast and not too_steep:
                self._say(
                    "Crashed — you came down too fast and hit hard. Cut "
                    "the throttle earlier next time, and level off before "
                    "you touch the ground. Press [R] to try again.",
                    urgent=True,
                )
            elif too_steep:
                self._say(
                    "Crashed — your nose was tilted up too far when you "
                    "touched down, so the tail hit first. Keep the nose "
                    "closer to level as you land. Press [R] to try again.",
                    urgent=True,
                )
            else:
                self._say(
                    "Crashed! Press [R] to try again — remember, gentle "
                    "power and a level nose make for a soft landing.",
                    urgent=True,
                )
            return
