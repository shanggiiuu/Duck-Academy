"""
render.py
---------
Everything pygame-specific: drawing the sky, ground, plane, HUD, and the
duck instructor's speech bubble. No physics or teaching logic lives here —
it just reads a VehicleState/DuckInstructor and draws them.
"""

import math
import pygame

from .constants import SCREEN_WIDTH, SCREEN_HEIGHT, MACH1_MPS
from .vehicles import VehicleState, VehicleConfig

SKY_TOP = (30, 60, 120)
SKY_BOTTOM = (140, 200, 245)
GROUND_COLOR = (74, 133, 66)
GROUND_LINE_COLOR = (58, 110, 52)
HUD_TEXT = (255, 255, 255)
HUD_WARN = (255, 90, 90)
PANEL_BG = (0, 0, 0, 140)

GROUND_Y = 560
PLANE_SCREEN_X = 280
PIXELS_PER_METER = 0.22
MIN_PLANE_SCREEN_Y = 90

BUBBLE_HEIGHT = 130


def _lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_sky_and_ground(screen, state: VehicleState, world_offset_x: float):
    # Sky darkens/thins visually with altitude, echoing air_density_factor.
    altitude_t = min(state.y / 2500.0, 1.0)
    top = _lerp_color(SKY_TOP, (8, 8, 30), altitude_t)
    bottom = _lerp_color(SKY_BOTTOM, (60, 70, 110), altitude_t)

    plane_screen_y = max(MIN_PLANE_SCREEN_Y, GROUND_Y - state.y * PIXELS_PER_METER)
    ground_screen_y = GROUND_Y - (GROUND_Y - plane_screen_y) if state.y > 0 else GROUND_Y
    horizon_y = int(GROUND_Y - state.y * PIXELS_PER_METER)
    horizon_y = min(horizon_y, GROUND_Y)

    for y in range(0, max(horizon_y, 1)):
        t = y / max(horizon_y, 1)
        pygame.draw.line(screen, _lerp_color(top, bottom, t), (0, y), (SCREEN_WIDTH, y))

    if horizon_y < SCREEN_HEIGHT:
        pygame.draw.rect(screen, GROUND_COLOR, (0, horizon_y, SCREEN_WIDTH, SCREEN_HEIGHT - horizon_y))
        stripe_spacing = 80
        offset = int(world_offset_x) % stripe_spacing
        x = -offset
        while x < SCREEN_WIDTH:
            pygame.draw.line(screen, GROUND_LINE_COLOR, (x, horizon_y), (x, SCREEN_HEIGHT), 3)
            x += stripe_spacing


def _rotate_to_screen(local_x, local_y, angle_deg, center_x, center_y):
    """Rotate a point by angle_deg using math convention (y-up, CCW positive),
    then flip into screen space (y-down)."""
    rad = math.radians(angle_deg)
    rx = local_x * math.cos(rad) - local_y * math.sin(rad)
    ry = local_x * math.sin(rad) + local_y * math.cos(rad)
    return center_x + rx, center_y - ry


def draw_plane(screen, state: VehicleState, config: VehicleConfig):
    center_x = PLANE_SCREEN_X
    center_y = max(MIN_PLANE_SCREEN_Y, GROUND_Y - state.y * PIXELS_PER_METER)

    L = 22
    W = 10
    points = [
        _rotate_to_screen(L, 0, state.pitch_deg, center_x, center_y),
        _rotate_to_screen(-L * 0.6, W, state.pitch_deg, center_x, center_y),
        _rotate_to_screen(-L * 0.3, 0, state.pitch_deg, center_x, center_y),
        _rotate_to_screen(-L * 0.6, -W, state.pitch_deg, center_x, center_y),
    ]
    color = (255, 200, 40) if not state.stalled else (255, 90, 90)
    pygame.draw.polygon(screen, color, points)

    if state.afterburner_on:
        flame_len = 34 + 10 * math.sin(state.time_s * 30.0)
        flame_pts = [
            _rotate_to_screen(-L * 0.6, W * 0.6, state.pitch_deg, center_x, center_y),
            _rotate_to_screen(-L * 0.6 - flame_len, 0, state.pitch_deg, center_x, center_y),
            _rotate_to_screen(-L * 0.6, -W * 0.6, state.pitch_deg, center_x, center_y),
        ]
        pygame.draw.polygon(screen, (255, 140, 30), flame_pts)

    # Nose line (where you're POINTED)
    nose_end = _rotate_to_screen(70, 0, state.pitch_deg, center_x, center_y)
    pygame.draw.line(screen, (255, 255, 255), (center_x, center_y), nose_end, 2)

    # Flight path marker (where you're ACTUALLY going)
    airspeed = math.hypot(state.vx, state.vy)
    if airspeed > 0.5:
        fp_deg = math.degrees(math.atan2(state.vy, state.vx))
    else:
        fp_deg = state.pitch_deg
    fp_x, fp_y = _rotate_to_screen(70, 0, fp_deg, center_x, center_y)
    pygame.draw.circle(screen, (60, 255, 120), (int(fp_x), int(fp_y)), 6, 2)
    pygame.draw.line(screen, (60, 255, 120), (fp_x - 10, fp_y), (fp_x + 10, fp_y), 2)
    pygame.draw.line(screen, (60, 255, 120), (fp_x, fp_y - 10), (fp_x, fp_y + 10), 2)


def draw_hud(screen, font, state: VehicleState, config: VehicleConfig, aoa_deg: float):
    airspeed = math.hypot(state.vx, state.vy)
    lines = [
        f"Altitude: {state.y:6.0f} m",
        f"Speed:    {airspeed:6.1f} m/s",
        f"Mach:     {airspeed / MACH1_MPS:6.2f}",
        f"Pitch:    {state.pitch_deg:+6.1f} deg",
    ]
    aoa_color = HUD_WARN if state.stalled else HUD_TEXT
    lines.append(f"AoA:      {aoa_deg:+6.1f} deg")

    panel = pygame.Surface((230, 170), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 130))
    screen.blit(panel, (10, 10))

    y = 16
    for i, line in enumerate(lines):
        color = aoa_color if line.startswith("AoA") else HUD_TEXT
        screen.blit(font.render(line, True, color), (18, y))
        y += 22

    # Throttle bar
    bar_x, bar_y, bar_w, bar_h = 18, y + 4, 200, 14
    pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
    pygame.draw.rect(screen, (80, 220, 255), (bar_x, bar_y, int(bar_w * state.throttle), bar_h))
    screen.blit(font.render("Throttle", True, HUD_TEXT), (bar_x, bar_y - 18))

    # Fuel bar
    fuel_frac = state.fuel_kg / config.fuel_capacity_kg if config.fuel_capacity_kg else 0
    bar_y2 = bar_y + 26
    pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y2, bar_w, bar_h))
    fuel_color = HUD_WARN if fuel_frac < 0.15 else (255, 200, 60)
    pygame.draw.rect(screen, fuel_color, (bar_x, bar_y2, int(bar_w * fuel_frac), bar_h))
    screen.blit(font.render("Fuel", True, HUD_TEXT), (bar_x, bar_y2 - 18))

    if state.stalled:
        warn = font.render("STALL", True, HUD_WARN)
        screen.blit(warn, (SCREEN_WIDTH // 2 - warn.get_width() // 2, 20))
    elif state.afterburner_on:
        warn = font.render("AFTERBURNER", True, (255, 150, 30))
        screen.blit(warn, (SCREEN_WIDTH // 2 - warn.get_width() // 2, 20))


def draw_controls_hint(screen, font, text="Up/Down: Nose   W/S: Throttle   R: Restart   Esc: Quit"):
    surf = font.render(text, True, (230, 230, 230))
    screen.blit(surf, (SCREEN_WIDTH - surf.get_width() - 14, 12))


def draw_duck_bubble(screen, font, instructor):
    """instructor is duck-typed: any object with .message (str) and
    .urgent (bool) works, so both DuckInstructor and DuckInstructorJet
    can share this renderer."""
    box_y = SCREEN_HEIGHT - BUBBLE_HEIGHT
    panel = pygame.Surface((SCREEN_WIDTH, BUBBLE_HEIGHT), pygame.SRCALPHA)
    panel.fill((10, 10, 20, 210))
    screen.blit(panel, (0, box_y))

    # Simple duck face
    duck_cx, duck_cy = 70, box_y + BUBBLE_HEIGHT // 2
    pygame.draw.circle(screen, (255, 221, 82), (duck_cx, duck_cy), 42)
    pygame.draw.circle(screen, (30, 30, 30), (duck_cx + 14, duck_cy - 12), 5)
    pygame.draw.polygon(
        screen,
        (255, 150, 40),
        [(duck_cx + 30, duck_cy), (duck_cx + 60, duck_cy - 8), (duck_cx + 60, duck_cy + 8)],
    )

    text_color = HUD_WARN if instructor.urgent else (255, 255, 255)
    lines = _wrap_text(instructor.message, font, SCREEN_WIDTH - 170)
    ty = box_y + 14
    for line in lines[:5]:
        screen.blit(font.render(line, True, text_color), (140, ty))
        ty += 22
