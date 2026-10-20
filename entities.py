"""
Game entities: player cannon, invader grid, projectiles, shields, UFO, booms.

All positions are plain pygame rects; float precision is kept where movement
per frame would otherwise be truncated away (UFO glide, bullet speed).
"""

import random

import pygame

from settings import (
    BOMB_AIM_CHANCE,
    DROP_Y,
    GRID_COLS,
    GRID_ROWS,
    GRID_START_X,
    HUD_TOP,
    INVADER_Y_FLOOR,
    MAX_X,
    MARCH_BASE,
    MARCH_SPREAD,
    MARCH_WAVE_SCALE,
    MIN_X,
    PLAYER_DEAD_PAUSE,
    PLAYER_SPEED,
    PLAYER_Y,
    RESPAWN_INVULN,
    SCORES,
    SHIELD_Y,
    START_LIVES,
    STEP_X,
    UFO_SCORES,
    UFO_SPEED,
    WAVE_DROP_MAX_STEPS,
    WAVE_DROP_PER,
    WHITE,
    WIDTH,
    X_STEP,
    Y_STEP,
)


class Player:
    """The laser cannon at the bottom of the screen."""

    def __init__(self, sprites):
        self.image = sprites.player
        self.reset()

    def reset(self):
        self.rect = self.image.get_rect()
        self.rect.midtop = (WIDTH // 2, PLAYER_Y)
        self.lives = START_LIVES
        self.alive = True
        self.invuln = 0.0      # seconds of blinking safety remaining
        self.cooldown = 0.0    # seconds until the cannon may fire again
        self.dead_timer = 0.0  # explosion pause before respawn / game over
        self.boom_frame = 0.0

    def update(self, dt, keys):
        if not self.alive:
            self.dead_timer -= dt
            self.boom_frame += dt * 9
            return
        self.invuln = max(0.0, self.invuln - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        dx = 0
        if keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_RIGHT]:
            dx += 1
        self.rect.x = max(
            MIN_X,
            min(MAX_X - self.rect.w, self.rect.x + int(dx * PLAYER_SPEED * dt)),
        )

    def can_shoot(self):
        return self.alive and self.cooldown <= 0.0

    def die(self):
        self.alive = False
        self.lives -= 1
        self.dead_timer = PLAYER_DEAD_PAUSE
        self.boom_frame = 0.0

    def respawn(self):
        self.alive = True
        self.invuln = RESPAWN_INVULN
        self.cooldown = 0.3
        self.rect.midtop = (WIDTH // 2, PLAYER_Y)


class Alien:
    """One invader. Position is owned by the grid; kind decides art/points."""

    def __init__(self, kind, row, col):
        self.kind = kind
        self.row = row
        self.col = col
        self.points = SCORES[kind]
        self.alive = True
        self.rect = pygame.Rect(0, 0, 0, 0)


class InvaderGrid:
    """The classic 5x11 formation with marching, edge drops and bombing."""

    def __init__(self, wave, sprites, on_step=None):
        self.wave = wave
        self.sprites = sprites
        self.on_step = on_step
        self.frame = 0
        self.timer = 0.0
        self.step_count = 0
        self.direction = 1
        self.pending_drop = False

        drop = min(wave - 1, WAVE_DROP_MAX_STEPS) * WAVE_DROP_PER
        self.x = float(GRID_START_X)
        self.y = float(130 + drop)

        self.aliens = []
        for row in range(GRID_ROWS):
            kind = "squid" if row == 0 else ("crab" if row < 3 else "octopus")
            for col in range(GRID_COLS):
                alien = Alien(kind, row, col)
                size = sprites.alien[kind][0].get_size()
                alien.rect.size = size
                self.aliens.append(alien)
        self._layout()

        self.interval = self._interval()

    # -- geometry -------------------------------------------------------------
    def _layout(self):
        for a in self.aliens:
            if not a.alive:
                continue
            w = a.rect.w
            a.rect.topleft = (
                int(self.x + a.col * X_STEP + (X_STEP - w) / 2),
                int(self.y + a.row * Y_STEP),
            )

    # -- state helpers ----------------------------------------------------------
    @property
    def alive_count(self):
        return sum(1 for a in self.aliens if a.alive)

    def _interval(self):
        """Seconds between march steps; shrinks as invaders die."""
        ratio = self.alive_count / float(GRID_ROWS * GRID_COLS)
        scaled = (MARCH_BASE + MARCH_SPREAD * ratio) * (
            MARCH_WAVE_SCALE ** (self.wave - 1)
        )
        return max(0.035, scaled)

    def note_kill(self):
        self.interval = self._interval()

    def reached_bottom(self):
        return any(
            a.rect.bottom >= INVADER_Y_FLOOR for a in self.aliens if a.alive
        )

    def collide(self, rect):
        for a in self.aliens:
            if a.alive and a.rect.colliderect(rect):
                return a
        return None

    def pick_bomber(self, target_x=None):
        """Choose an invader to drop a bomb; sometimes aim at the player."""
        alive = [a for a in self.aliens if a.alive]
        if not alive:
            return None
        if target_x is not None and random.random() < BOMB_AIM_CHANCE:
            column = [
                a for a in alive if abs(a.rect.centerx - target_x) <= X_STEP
            ]
            if column:
                return max(column, key=lambda a: a.row)
        return random.choice(alive)

    # -- simulation -------------------------------------------------------------
    def update(self, dt):
        self.timer += dt
        # Guard the loop so a huge dt can't march the grid dozens of times.
        for _ in range(6):
            if self.timer < self.interval:
                break
            self.timer -= self.interval
            self._step()

    def _step(self):
        alive = [a for a in self.aliens if a.alive]
        if not alive:
            return
        if self.pending_drop:
            self.y += DROP_Y
            self.pending_drop = False
        else:
            left = min(a.rect.left for a in alive)
            right = max(a.rect.right for a in alive)
            if self.direction > 0 and right + STEP_X >= MAX_X:
                self.pending_drop = True
                self.direction = -1
            elif self.direction < 0 and left - STEP_X <= MIN_X:
                self.pending_drop = True
                self.direction = 1
            else:
                self.x += STEP_X * self.direction
        self._layout()
        self.frame ^= 1
        self.step_count += 1
        if self.on_step:
            self.on_step(self)


class Bullet:
    """The player's laser: one on screen at a time, like the original.

    Movement is owned by the engine so it can be sub-stepped for accurate
    collision against the thin bunker walls.
    """

    def __init__(self, x, y):
        self.image = pygame.Surface((3, 14))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect(midbottom=(x, y))

    def offscreen(self):
        return self.rect.bottom <= HUD_TOP


class Bomb:
    """Invader bomb: a zigzag bolt that chews through bunkers.

    Like the bullet, movement is engine-owned (sub-stepped per frame).
    """

    def __init__(self, x, y, sprites):
        self.frames = sprites.bomb
        self.rect = self.frames[0].get_rect(midtop=(x, y))
        self._anim = 0.0

    def advance(self, px):
        self._anim += px / 14.0
        self.rect.y += px

    @property
    def image(self):
        return self.frames[int(self._anim) % 2]


class UFO:
    """The mystery ship that crosses the top of the screen."""

    def __init__(self, sprites):
        self.points = random.choice(UFO_SCORES)
        self.image = sprites.ufo
        self.dir = random.choice((-1, 1))
        self.rect = self.image.get_rect()
        self.rect.y = 84
        self.x = float(-self.rect.w) if self.dir > 0 else float(WIDTH)

    def update(self, dt):
        self.x += self.dir * UFO_SPEED * dt
        self.rect.x = int(self.x)
        if self.rect.right < 0 or self.rect.left > WIDTH:
            return False
        return True


class Shield:
    """A destructible bunker. Damage is carved straight into the pixels."""

    def __init__(self, sprites, center_x):
        self.image = sprites.shield.copy()
        self.rect = self.image.get_rect()
        self.rect.centerx = center_x
        self.rect.top = SHIELD_Y
        self.w, self.h = self.rect.w, self.rect.h

    def _opaque_in(self, x0, y0, x1, y1):
        for yy in range(max(0, y0), min(self.h, y1), 2):
            for xx in range(max(0, x0), min(self.w, x1), 2):
                if self.image.get_at((xx, yy))[3] > 0:
                    return True
        return False

    def collide(self, rect, carve_w, carve_h, moving_down):
        """Test a projectile against opaque pixels; carve a hole on impact."""
        if not self.rect.colliderect(rect):
            return False
        ox, oy = rect.x - self.rect.x, rect.y - self.rect.y
        if not self._opaque_in(ox, oy, ox + rect.w, oy + rect.h):
            return False
        center_x = ox + rect.w // 2
        center_y = oy + rect.h if moving_down else oy
        hole = pygame.Rect(0, 0, carve_w, carve_h)
        hole.center = (center_x, center_y)
        self.image.fill((0, 0, 0, 0), hole)
        return True

    def crush(self, rect):
        """Erase the overlapped region (invaders marching through)."""
        if not self.rect.colliderect(rect):
            return
        ox, oy = rect.x - self.rect.x, rect.y - self.rect.y
        box = pygame.Rect(ox, oy, rect.w, rect.h).clip(
            pygame.Rect(0, 0, self.w, self.h)
        )
        if box.w > 0 and box.h > 0:
            self.image.fill((0, 0, 0, 0), box)


class Boom:
    """A timed one-shot effect; can show any surface, even score text."""

    def __init__(self, image, center, duration=0.2):
        self.image = image
        self.rect = image.get_rect(center=center)
        self.life = duration

    def update(self, dt):
        self.life -= dt
        return self.life > 0
