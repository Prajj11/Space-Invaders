"""
Headless smoke test: drives a full game session with no window or audio.

Run:  python test_smoke.py
"""

import os

# Must be set before pygame initializes anything.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import main as game_mod  # noqa: E402
from entities import Bomb  # noqa: E402
from settings import MIN_X, MAX_X  # noqa: E402

FAILURES = []


def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        FAILURES.append(name)


def main():
    game = game_mod.Game()
    dt = 1.0 / 60.0

    # --- menu -> playing -------------------------------------------------
    check("starts in menu", game.state == game_mod.STATE_MENU)
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_RETURN))
    check("enter starts game", game.state == game_mod.STATE_PLAYING)
    # Keep random bombs/UFOs out of the test window for determinism.
    game.bomb_timer = 9999.0
    game.ufo_timer = 9999.0
    check("grid has 55 invaders", game.grid.alive_count == 55)
    check("4 shields built", len(game.shields) == 4)
    check("player has 3 lives", game.player.lives == 3)

    # --- a few seconds of play -------------------------------------------
    keys = {k: False for k in (pygame.K_LEFT, pygame.K_RIGHT)}
    pressed = pygame.key.get_pressed()
    for _ in range(240):
        game.update(dt)
    check("game still running", game.state == game_mod.STATE_PLAYING)

    # --- shooting kills an invader ---------------------------------------
    x0 = game.grid.alive_count
    score0 = game.score
    game._player_shoot()
    check("one bullet on screen", len(game.bullets) == 1)
    for _ in range(600):
        game.update(dt)
        if game.grid.alive_count < x0 or not game.bullets:
            break
    # Aim: teleport a bullet onto an alien to force a deterministic kill.
    if game.grid.alive_count == x0:
        target = next(a for a in game.grid.aliens if a.alive)
        game.bullets.clear()
        bullet = game_mod.Bullet(target.rect.centerx,
                                 target.rect.bottom + 2)
        game.bullets.append(bullet)
        game.update(dt)
    check("invader was killed", game.grid.alive_count == x0 - 1)
    check("score increased", game.score > score0)

    # --- march accelerates as invaders die --------------------------------
    slow = game.grid.interval
    for a in game.grid.aliens[::2]:
        a.alive = False
    game.grid.note_kill()
    fast = game.grid.interval
    check("march speeds up when invaders die", fast < slow)

    # --- player death by bomb ---------------------------------------------
    lives0 = game.player.lives
    bomb = Bomb(game.player.rect.centerx, game.player.rect.top - 4,
                game.sprites)
    game.bombs.append(bomb)
    game.update(dt)
    game.update(dt)
    check("bomb hit kills player", not game.player.alive)
    check("life lost", game.player.lives == lives0 - 1)
    for _ in range(200):
        game.update(dt)
        if game.player.alive or game.state != game_mod.STATE_PLAYING:
            break
    check("player respawns", game.player.alive)

    # --- wave clear -> wave pause -> next wave ----------------------------
    for a in game.grid.aliens:
        a.alive = False
    game.update(dt)
    check("wave pause entered", game.state == game_mod.STATE_WAVE_PAUSE)
    game.wave_pause_timer = 0.01
    game.update(dt)
    check("next wave starts", game.state == game_mod.STATE_PLAYING
          and game.wave == 2)
    check("grid repopulated", game.grid.alive_count == 55)

    # --- UFO scoring ------------------------------------------------------
    game.ufo = game_mod.UFO(game.sprites)
    pts = game.ufo.points
    game.bullets.clear()
    bullet = game_mod.Bullet(game.ufo.rect.centerx, game.ufo.rect.bottom + 2)
    game.bullets.append(bullet)
    score1 = game.score
    game.update(dt)
    check("ufo destroyed for points", game.ufo is None
          and game.score == score1 + pts)

    # --- pause toggles ----------------------------------------------------
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    check("pause works", game.state == game_mod.STATE_PAUSED)
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    check("unpause works", game.state == game_mod.STATE_PLAYING)

    # --- shields actually erode -------------------------------------------
    shield = game.shields[0]
    before = sum(1 for x in range(shield.w) for y in range(shield.h)
                 if shield.image.get_at((x, y))[3] > 0)
    game.bullets.clear()
    # Spawn inside the bunker so the upward-moving shot carves its roof.
    bullet = game_mod.Bullet(shield.rect.centerx, shield.rect.top + 24)
    game.bullets.append(bullet)
    for _ in range(120):
        game.update(dt)
        if not game.bullets:
            break
    after = sum(1 for x in range(shield.w) for y in range(shield.h)
                if shield.image.get_at((x, y))[3] > 0)
    check("bunker erodes when hit", after < before)

    # --- rendering every state -------------------------------------------
    for state in (game_mod.STATE_PLAYING, game_mod.STATE_WAVE_PAUSE,
                  game_mod.STATE_PAUSED, game_mod.STATE_GAME_OVER,
                  game_mod.STATE_MENU):
        game.state = state
        game.draw()
    check("draws in every state", True)

    # --- AI Autopilot agent checks ----------------------------------------
    for mode_idx, mode_name in [(1, "Hill Climbing"), (2, "A* Search"),
                                 (3, "BFS"), (4, "DFS")]:
        game.ai_mode = mode_idx
        game.state = game_mod.STATE_PLAYING
        # Simulate several ticks under AI control
        for _ in range(30):
            game.update(dt)
        check(f"{mode_name} agent runs and produces telemetry",
              bool(game.ai_telemetry and "nodes" in game.ai_telemetry))
        check(f"{mode_name} player stays within boundaries",
              MIN_X <= game.player.rect.x <= MAX_X)

    # TAB cycling check
    game.ai_mode = 0
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    check("TAB switches to Hill Climbing", game.ai_mode == 1)
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    check("TAB switches to A* Search", game.ai_mode == 2)
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_0))
    check("0 switches back to Manual", game.ai_mode == 0)

    # --- hi-score persistence ---------------------------------------------
    game.hi_score = 99999
    game._save_hiscore()
    check("hi-score saved", game._load_hiscore() == 99999)
    os.remove(game_mod.HI_SCORE_FILE)  # keep the workspace clean

    pygame.quit()
    print()
    if FAILURES:
        print("%d FAILURE(S): %s" % (len(FAILURES), ", ".join(FAILURES)))
        raise SystemExit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
