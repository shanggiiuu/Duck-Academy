"""
constants.py
------------
Tunable numbers shared across the physics and game layer. Kept in one
place so "does this feel right" tuning never means hunting through
physics.py for a magic number.
"""

# -- World / physics --------------------------------------------------------

G0 = 9.8                       # m/s^2, gravity at sea level

KARMAN_LINE_M = 100_000.0      # real-world internationally recognized edge of space
MACH1_MPS = 343.0              # speed of sound at sea level, m/s

SAFE_LANDING_VSPEED_MPS = 6.0  # descend faster than this on touchdown -> crash
SAFE_LANDING_AOA_DEG = 20.0    # touch down with more angle of attack than this -> crash

THROTTLE_RATE_PER_S = 0.6      # fraction of throttle range per second, while held

# Fictional atmosphere scale height (real air thins by ~63% every 8.5km;
# we reuse that curve so "air gets thin fast" still feels physically honest).
ATMOSPHERE_SCALE_HEIGHT_M = 8_000.0
ATMOSPHERE_TOP_M = 50_000.0    # above this, air density is treated as zero

# Real low-Earth-orbit speed is ~7,800 m/s — reachable in real life with a
# multi-stage rocket over minutes, but not in a few minutes of arcade play.
# We scale the target down and the duck says so explicitly (honesty > silent
# simplification), so the *concept* (go high AND go sideways fast) survives
# even though the number doesn't match reality.
ORBITAL_ALTITUDE_TARGET_M = 120_000.0
ORBITAL_SPEED_TARGET_MPS = 1_500.0

# -- Screen / camera ---------------------------------------------------------

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
