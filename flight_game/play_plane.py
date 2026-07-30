"""
play_plane.py
--------------
Lesson 1: the Prop Plane. Run with `python play.py` from the project root
(or `python -m flight_game.play_plane`).

This is intentionally the simplest of the three vehicles — no afterburner,
no staging, gentle pitch rate — so the four-forces + angle-of-attack lesson
lands before the fighter jet and spaceship raise the difficulty.
"""

import math
import sys

import pygame

from .constants import SCREEN_WIDTH, SCREEN_HEIGHT
from .vehicles import PLANE_CONFIG, make_initial_state, step_physics, Controls
from .duck_instructor import DuckInstructor
from . import render


def _current_aoa(state):
    airspeed = math.hypot(state.vx, state.vy)
    flight_path_deg = math.degrees(math.atan2(state.vy, state.vx)) if airspeed > 0.5 else state.pitch_deg
    aoa = state.pitch_deg - flight_path_deg
    return ((aoa + 180.0) % 360.0) - 180.0


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Duck Aerospace Academy — Lesson 1: Prop Plane")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    font_small = pygame.font.SysFont("consolas", 15)

    config = PLANE_CONFIG
    state = make_initial_state(config)
    instructor = DuckInstructor()

    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE and not instructor.started:
                    instructor.begin()
                elif event.key == pygame.K_r and (state.crashed or state.landed):
                    state = make_initial_state(config)
                    instructor.reset_for_retry()

        keys = pygame.key.get_pressed()
        controls = Controls(
            pitch_input=(1.0 if keys[pygame.K_UP] else 0.0) - (1.0 if keys[pygame.K_DOWN] else 0.0),
            throttle_input=(1.0 if keys[pygame.K_w] else 0.0) - (1.0 if keys[pygame.K_s] else 0.0),
            afterburner=False,
        )

        prev_vy = state.vy
        prev_aoa = _current_aoa(state)

        events = []
        if instructor.started and not (state.crashed or state.landed):
            events = step_physics(state, config, controls, dt)

        instructor.update(state, controls, events, dt, prev_vy=prev_vy, prev_aoa=prev_aoa)

        screen.fill((0, 0, 0))
        render.draw_sky_and_ground(screen, state, world_offset_x=state.x)
        render.draw_plane(screen, state, config)
        render.draw_hud(screen, font, state, config, aoa_deg=_current_aoa(state))
        render.draw_controls_hint(screen, font_small)
        render.draw_duck_bubble(screen, font, instructor)
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
