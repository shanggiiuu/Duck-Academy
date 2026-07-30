"""
vehicles.py
-----------
Simplified but *honest* flight physics for three craft: a prop plane, a
fighter jet, and a spaceship. "Honest" means the forces are the real ones
(thrust, lift, drag, weight) combined in the real way, with numbers tuned
for arcade-game pacing rather than textbook accuracy. Where we cheat for
gameplay (e.g. orbital speed), constants.py says so and the duck says so.

Everything here is DATA + a pure step function, no pygame. That mirrors
the project's existing convention (see models.py) of keeping simulation
logic testable without a display.

The core trick that makes this teach real aerodynamics with very little
code: angle of attack (AoA) is *derived*, not set by the player. The
player only controls where the NOSE points (pitch) and how hard the
engine pushes (throttle). Where the plane actually TRAVELS (its flight
path) is a consequence of physics. AoA = nose angle - flight path angle.
Fly too slow while holding the nose up, and AoA grows past the critical
angle on its own -- that's a real stall, discovered the same way real
pilots discover it.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .constants import (
    G0,
    KARMAN_LINE_M,
    MACH1_MPS,
    SAFE_LANDING_VSPEED_MPS,
    SAFE_LANDING_AOA_DEG,
    THROTTLE_RATE_PER_S,
    ATMOSPHERE_SCALE_HEIGHT_M,
    ATMOSPHERE_TOP_M,
    ORBITAL_ALTITUDE_TARGET_M,
    ORBITAL_SPEED_TARGET_MPS,
)


class VehicleKind(str, Enum):
    PLANE = "plane"
    FIGHTER_JET = "fighter_jet"
    SPACESHIP = "spaceship"


def _normalize_angle_deg(angle: float) -> float:
    """Wrap to (-180, 180] so angle math never blows up across the 0/360 seam."""
    return ((angle + 180.0) % 360.0) - 180.0


# ---------------------------------------------------------------------------
# Config — the "what kind of vehicle is this" data, one instance per kind.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VehicleConfig:
    kind: VehicleKind
    display_name: str

    mass_kg: float
    max_thrust_n: float
    has_wings: bool

    lift_coefficient: float = 0.0
    drag_coefficient: float = 0.1
    critical_aoa_deg: float = 16.0

    fuel_capacity_kg: float = 100.0
    fuel_burn_rate_kg_s: float = 1.0          # at throttle=1.0, no afterburner

    afterburner_thrust_n: float = 0.0          # 0 = vehicle has no afterburner
    afterburner_burn_rate_kg_s: float = 0.0

    max_pitch_rate_deg_s: float = 40.0
    start_pitch_deg: float = 0.0               # nose orientation sitting at start

    # Two-stage rocket support (spaceship only). None on the other vehicles.
    stage2_mass_kg: Optional[float] = None
    stage2_thrust_n: Optional[float] = None
    stage2_fuel_kg: Optional[float] = None
    stage2_burn_rate_kg_s: Optional[float] = None


PLANE_CONFIG = VehicleConfig(
    kind=VehicleKind.PLANE,
    display_name="Prop Plane",
    mass_kg=1_100.0,
    max_thrust_n=2_000.0,          # thrust-to-weight ~0.19, like a real light aircraft
    has_wings=True,
    lift_coefficient=15.0,
    drag_coefficient=0.18,
    critical_aoa_deg=16.0,
    fuel_capacity_kg=150.0,
    fuel_burn_rate_kg_s=0.6,
    max_pitch_rate_deg_s=35.0,
    start_pitch_deg=0.0,
)

FIGHTER_JET_CONFIG = VehicleConfig(
    kind=VehicleKind.FIGHTER_JET,
    display_name="Fighter Jet",
    mass_kg=9_000.0,
    max_thrust_n=65_000.0,         # dry thrust, T/W ~0.74
    has_wings=True,
    lift_coefficient=13.0,
    drag_coefficient=0.05,
    critical_aoa_deg=20.0,         # fighters tolerate a steeper AoA before stalling
    fuel_capacity_kg=3_000.0,
    fuel_burn_rate_kg_s=3.0,
    afterburner_thrust_n=45_000.0,  # WITH afterburner, T/W > 1: can accelerate straight up
    afterburner_burn_rate_kg_s=25.0,  # afterburner drinks fuel ~8x faster than dry
    max_pitch_rate_deg_s=70.0,
    start_pitch_deg=0.0,
)

SPACESHIP_CONFIG = VehicleConfig(
    kind=VehicleKind.SPACESHIP,
    display_name="Spaceship",
    mass_kg=45_000.0,              # stage 1, fueled
    max_thrust_n=750_000.0,        # T/W ~1.7 off the pad, like a real orbital rocket
    has_wings=False,
    drag_coefficient=0.02,
    fuel_capacity_kg=25_000.0,
    fuel_burn_rate_kg_s=420.0,     # ~60s stage-1 burn
    max_pitch_rate_deg_s=25.0,     # rockets turn gradually (the "gravity turn")
    start_pitch_deg=90.0,          # straight up, off the pad
    stage2_mass_kg=14_000.0,
    stage2_thrust_n=180_000.0,
    stage2_fuel_kg=7_000.0,
    stage2_burn_rate_kg_s=70.0,
)

ALL_CONFIGS = {
    VehicleKind.PLANE: PLANE_CONFIG,
    VehicleKind.FIGHTER_JET: FIGHTER_JET_CONFIG,
    VehicleKind.SPACESHIP: SPACESHIP_CONFIG,
}


# ---------------------------------------------------------------------------
# State — everything that changes frame to frame.
# ---------------------------------------------------------------------------

@dataclass
class VehicleState:
    x: float = 0.0
    y: float = 0.0                 # altitude in meters, 0 = ground
    vx: float = 0.0
    vy: float = 0.0
    pitch_deg: float = 0.0

    throttle: float = 0.0          # 0..1
    afterburner_on: bool = False
    fuel_kg: float = 0.0

    stage: int = 1                 # rocket only; 1 or 2
    current_mass_kg: float = 0.0
    current_thrust_n: float = 0.0

    on_ground: bool = True
    stalled: bool = False
    crashed: bool = False
    landed: bool = False

    max_altitude_m: float = 0.0
    max_speed_mps: float = 0.0
    time_s: float = 0.0

    # one-shot flags so events fire exactly once per flight
    _has_taken_off: bool = False
    _reached_supersonic: bool = False
    _reached_space: bool = False
    _achieved_orbit: bool = False
    _fuel_out: bool = False
    _prev_dynamic_pressure: float = 0.0
    _dynamic_pressure_rising: bool = True
    _max_q_fired: bool = False


@dataclass
class Controls:
    pitch_input: float = 0.0       # -1..1, nose down/up
    throttle_input: float = 0.0    # -1..1, held to ramp throttle down/up
    afterburner: bool = False


def make_initial_state(config: VehicleConfig) -> VehicleState:
    state = VehicleState(
        pitch_deg=config.start_pitch_deg,
        fuel_kg=config.fuel_capacity_kg,
        current_mass_kg=config.mass_kg,
        current_thrust_n=config.max_thrust_n,
        on_ground=True,
    )
    return state


def air_density_factor(altitude_m: float) -> float:
    """1.0 at sea level, decaying like real air, 0 above the fictional
    atmosphere ceiling. Drives both lift and drag to zero once you're
    high enough that there's no air left to push against."""
    if altitude_m <= 0:
        return 1.0
    if altitude_m >= ATMOSPHERE_TOP_M:
        return 0.0
    return math.exp(-altitude_m / ATMOSPHERE_SCALE_HEIGHT_M)


def gravity_at_altitude(altitude_m: float, config: VehicleConfig) -> float:
    """Planes/jets never fly high enough for gravity to meaningfully
    change, so we keep it constant for them. The spaceship flies high
    enough that a *gentle* real inverse-square falloff is worth showing --
    the point being that orbit is NOT "escaping gravity" (gravity barely
    drops), it's moving sideways fast enough to keep missing the ground.
    """
    if config.kind != VehicleKind.SPACESHIP:
        return G0
    effective_earth_radius_m = 630_000.0  # scaled down so the curve is visible in-game
    ratio = effective_earth_radius_m / (effective_earth_radius_m + altitude_m)
    return G0 * ratio * ratio


def step_physics(state: VehicleState, config: VehicleConfig, controls: Controls, dt: float) -> List[str]:
    """Advance the simulation by dt seconds. Mutates state in place.
    Returns a list of event strings for anything noteworthy that just
    happened, so the duck instructor / UI layer can react."""
    events: List[str] = []
    if state.crashed or state.landed:
        return events

    state.time_s += dt

    # -- 1. Player input -----------------------------------------------
    state.pitch_deg = _normalize_angle_deg(
        state.pitch_deg + controls.pitch_input * config.max_pitch_rate_deg_s * dt
    )
    state.throttle = max(0.0, min(1.0, state.throttle + controls.throttle_input * THROTTLE_RATE_PER_S * dt))

    can_afterburn = config.afterburner_thrust_n > 0 and state.throttle >= 0.99 and state.fuel_kg > 0
    was_afterburning = state.afterburner_on
    state.afterburner_on = bool(controls.afterburner and can_afterburn)
    if state.afterburner_on and not was_afterburning:
        events.append("afterburner_on")
    elif was_afterburning and not state.afterburner_on:
        events.append("afterburner_off")

    # -- 2. Fuel burn / staging -----------------------------------------
    burn = config.fuel_burn_rate_kg_s * state.throttle
    if state.afterburner_on:
        burn += config.afterburner_burn_rate_kg_s
    state.fuel_kg = max(0.0, state.fuel_kg - burn * dt)

    if state.fuel_kg <= 0 and not state._fuel_out:
        state._fuel_out = True
        events.append("fuel_out")

    if (
        config.stage2_mass_kg is not None
        and state.stage == 1
        and state.fuel_kg <= 0
        and not state.on_ground
    ):
        state.stage = 2
        state.current_mass_kg = config.stage2_mass_kg
        state.current_thrust_n = config.stage2_thrust_n or 0.0
        state.fuel_kg = config.stage2_fuel_kg or 0.0
        events.append("stage_separation")

    # -- 3. Forces --------------------------------------------------------
    rho = air_density_factor(state.y)
    airspeed = math.hypot(state.vx, state.vy)

    # Thrust: along the nose, scaled by throttle, zero if out of fuel.
    thrust_n = state.current_thrust_n * state.throttle if state.fuel_kg > 0 else 0.0
    if state.afterburner_on:
        thrust_n += config.afterburner_thrust_n
    pitch_rad = math.radians(state.pitch_deg)
    thrust_x = thrust_n * math.cos(pitch_rad)
    thrust_y = thrust_n * math.sin(pitch_rad)

    # Lift + drag need a direction of travel; at rest, fall back to nose direction.
    if airspeed > 0.5:
        flight_path_deg = math.degrees(math.atan2(state.vy, state.vx))
    else:
        flight_path_deg = state.pitch_deg

    lift_x = lift_y = 0.0
    if config.has_wings:
        aoa = _normalize_angle_deg(state.pitch_deg - flight_path_deg)
        critical = config.critical_aoa_deg
        if abs(aoa) <= critical:
            lift_coef = aoa / critical
            is_stalled = False
        else:
            excess = abs(aoa) - critical
            lift_coef = math.copysign(max(0.15, 1.0 - excess * 0.06), aoa)
            is_stalled = airspeed > 5.0  # sitting still with nose up isn't a "stall"

        if is_stalled and not state.stalled:
            events.append("stall_entered")
        elif state.stalled and not is_stalled:
            events.append("stall_recovered")
        state.stalled = is_stalled

        lift_mag = config.lift_coefficient * rho * airspeed * airspeed * lift_coef
        fp_rad = math.radians(flight_path_deg)
        # perpendicular to velocity, rotated +90 degrees (CCW)
        lift_x = -math.sin(fp_rad) * lift_mag
        lift_y = math.cos(fp_rad) * lift_mag

    drag_x = drag_y = 0.0
    if airspeed > 0.1:
        drag_mag = config.drag_coefficient * rho * airspeed * airspeed
        drag_x = -drag_mag * (state.vx / airspeed)
        drag_y = -drag_mag * (state.vy / airspeed)

    # Max-Q: the moment dynamic pressure (rho * v^2) peaks during ascent --
    # real rockets briefly throttle down here because it's the point of
    # greatest structural stress.
    dynamic_pressure = 0.5 * rho * airspeed * airspeed
    if not config.has_wings:  # only really meaningful (and only tracked) for the rocket
        if state._dynamic_pressure_rising and dynamic_pressure < state._prev_dynamic_pressure:
            if not state._max_q_fired and state.y > 500:
                state._max_q_fired = True
                events.append("max_q")
            state._dynamic_pressure_rising = False
        elif dynamic_pressure > state._prev_dynamic_pressure:
            state._dynamic_pressure_rising = True
        state._prev_dynamic_pressure = dynamic_pressure

    g = gravity_at_altitude(state.y, config)
    weight_y = -g * state.current_mass_kg

    # -- 4. Integrate -----------------------------------------------------
    fx = thrust_x + lift_x + drag_x
    fy = thrust_y + lift_y + drag_y + weight_y
    ax = fx / state.current_mass_kg
    ay = fy / state.current_mass_kg

    state.vx += ax * dt
    state.vy += ay * dt
    state.x += state.vx * dt
    state.y += state.vy * dt

    # -- 5. Ground handling -------------------------------------------------
    was_on_ground = state.on_ground
    if state.y <= 0.0:
        impact_vspeed = -state.vy if state.vy < 0 else 0.0
        aoa_at_impact = abs(_normalize_angle_deg(state.pitch_deg - flight_path_deg)) if config.has_wings else 0.0
        state.y = 0.0
        if state.vy < 0:
            state.vy = 0.0
        state.on_ground = True

        if not was_on_ground:
            if impact_vspeed > SAFE_LANDING_VSPEED_MPS or aoa_at_impact > SAFE_LANDING_AOA_DEG:
                state.crashed = True
                events.append("crashed")
            else:
                state.landed = True
                events.append("landed")
    else:
        state.on_ground = False
        if was_on_ground and not state._has_taken_off:
            state._has_taken_off = True
            events.append("takeoff")

    # -- 6. Records / milestones --------------------------------------------
    state.max_altitude_m = max(state.max_altitude_m, state.y)
    state.max_speed_mps = max(state.max_speed_mps, airspeed)

    if airspeed >= MACH1_MPS and not state._reached_supersonic:
        state._reached_supersonic = True
        events.append("supersonic")

    if state.y >= KARMAN_LINE_M and not state._reached_space:
        state._reached_space = True
        events.append("reached_space")

    if (
        config.kind == VehicleKind.SPACESHIP
        and not state._achieved_orbit
        and state.y >= ORBITAL_ALTITUDE_TARGET_M
        and abs(state.vx) >= ORBITAL_SPEED_TARGET_MPS
    ):
        state._achieved_orbit = True
        events.append("orbit_achieved")

    return events
