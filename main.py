"""
Space Invaders -- main game engine.

Pure Python + pygame for everything: rendering (frontend) and all game
simulation (backend). All art is code-drawn bitmaps and all audio is
synthesized at runtime; the game ships with zero asset files.

Run:  python main.py
"""

import random

import pygame

from effects import CombatEffects, Supply
from campaign import LEVELS, DIFFICULTIES, Boss
from comparison import Comparison
from entities import (
    Boom,
    Bomb,
    Bullet,
    InvaderGrid,
    Player,
    Shield,
    UFO,
)
from settings import (
    BLACK,
    BOTTOM_BAR_Y,
    BOMB_INTERVAL,
    BOMB_MIN_INTERVAL,
    BOMB_SPEED,
    BULLET_SPEED,
    EXTRA_LIFE_AT,
    FPS,
    GREY,
    HEIGHT,
    HI_GREEN,
    HI_SCORE_FILE,
    HUD_TOP,
    MAX_BOMBS_BASE,
    MAX_BOMBS_CAP,
    MAX_LIVES,
    MIN_X,
    MAX_X,
    TITLE,
    UFO_LABEL_COLOR,
    UFO_MIN_ALIENS,
    UFO_SPAWN_RANGE,
    WAVE_PAUSE,
    WHITE,
    WIDTH,
)
from sounds import SoundBank
from sprites import Sprites
from ai_agent import AGENTS

STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_WAVE_PAUSE = "wave_pause"
STATE_GAME_OVER = "game_over"
STATE_VICTORY = "victory"
STATE_COMPARISON = "comparison"


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.sprites = Sprites()
        self.sounds = SoundBank()

        self.font_big = pygame.font.Font(None, 64)
        self.font_mid = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 30)
        self.font_tiny = pygame.font.Font(None, 26)

        self.hi_score = self._load_hiscore()
        self.muted = False

        self.difficulty = "Normal"
        self.comparison = None
        self.effects = CombatEffects()
        self.player = Player(self.sprites)
        self.death_boom = None
        self._new_game(score_reset=True)
        self.state = STATE_MENU
        self.menu_flash = 0.0

        # User-selected visual guidance; controls always remain manual.
        self.ai_mode = 0
        self.ai_telemetry = {}
        self.show_ai_debug = True
        self.guidance_timer = 0.0

    # ------------------------------------------------------------------ setup
    def _load_hiscore(self):
        try:
            with open(HI_SCORE_FILE, "r", encoding="utf-8") as fh:
                return int(fh.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def _save_hiscore(self):
        try:
            with open(HI_SCORE_FILE, "w", encoding="utf-8") as fh:
                fh.write(str(self.hi_score))
        except OSError:
            pass

    def _new_game(self, score_reset=True):
        if score_reset:
            self.score = 0
            self.extra_life_awarded = False
        self.weapon_rank = 0
        self.shield_rank = 0
        self.pulse_rank = 0
        self.player.reset()
        self._start_wave(1)
        self.shots_fired = 0

    def _start_wave(self, wave):
        self.ai_telemetry = {}
        self.guidance_timer = 0.0
        self.wave = wave
        self.level = LEVELS[wave - 1]
        self.level_elapsed = 0.0
        self.intro_timer = 4.0
        self.selected_target = None
        self.dash_cooldown = 0.0
        self.last_direction = 1
        self.warnings = []
        self.upgrade_choice = 0
        self.comparison = None
        self.boss = Boss(wave, DIFFICULTIES[self.difficulty]) if self.level.objective == "boss" else None
        self.supplies = []
        self.rapid_timer = 0.0
        self.shield_charge = self.shield_rank > 0
        self.shield_hits = self.shield_rank
        self.combo = 0
        self.combo_timer = 0.0
        self.pulse_charges = 1 + self.pulse_rank
        self.pulse_ready = True
        self.pulse_flash = 0.0
        self.effects.particles.clear()
        self.grid = InvaderGrid(wave, self.sprites, on_step=self._on_grid_step)
        self.grid.speed_scale = DIFFICULTIES[self.difficulty]
        if self.level.objective != "clear":
            for alien in self.grid.aliens:
                alien.alive = False
        elif self.level.enemy_types:
            for i, alien in enumerate(self.grid.aliens):
                if i % 3 == 0:
                    alien.role = self.level.enemy_types[(i // 3) % len(self.level.enemy_types)]
                    alien.hp = 2 if alien.role == "armor" else 1
                    alien.points += {"armor": 20, "scout": 10, "bomber": 20}[alien.role]
        self.bullets = []
        self.bombs = []
        self.booms = []
        self.death_boom = None
        self.shields = [Shield(self.sprites, x)
                        for x in self._shield_x_positions()]
        self.ufo = None
        self.ufo_timer = random.uniform(*UFO_SPAWN_RANGE)
        self.bomb_timer = random.uniform(BOMB_INTERVAL, BOMB_INTERVAL * 2)

    @staticmethod
    def _shield_x_positions():
        base = WIDTH // 2
        offset = WIDTH // 4
        return (base - offset, base - offset // 3,
                base + offset // 3, base + offset)

    # ------------------------------------------------------------- callbacks
    def _on_grid_step(self, grid):
        self.sounds.play_march(grid.step_count)
        # Invaders grind through any bunker they march into.
        for alien in grid.aliens:
            if alien.alive and alien.rect.top > 480:
                for shield in self.shields:
                    shield.crush(alien.rect)

    # ---------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.state == STATE_PLAYING:
            if event.button == 1:
                self.selected_target = next((a for a in self.grid.aliens
                                             if a.alive and a.rect.collidepoint(event.pos)), None)
                if self.boss and self.boss.rect.collidepoint(event.pos):
                    self.selected_target = self.boss
                self.guidance_timer = 0
            elif event.button == 3:
                self.selected_target = None
            return
        if event.type == pygame.KEYDOWN and self.state == STATE_COMPARISON:
            if event.key in (pygame.K_c, pygame.K_ESCAPE):
                self.state = self.comparison_return_state
                self.comparison = None
            else:
                self.comparison.handle(event.key)
            return
        if event.type == pygame.KEYDOWN and self.state == STATE_WAVE_PAUSE:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.upgrade_choice = (self.upgrade_choice + (1 if event.key == pygame.K_RIGHT else -1)) % 3
            elif event.key == pygame.K_RETURN:
                self._apply_upgrade()
                self._start_wave(self.wave + 1)
                self.state = STATE_PLAYING
            return
        if event.type == pygame.KEYDOWN:
            previous_mode = self.ai_mode
            if event.key == pygame.K_ESCAPE and self.state in (STATE_GAME_OVER, STATE_VICTORY):
                self.state = STATE_MENU
                return
            if event.key == pygame.K_c and self.state in (STATE_PLAYING, STATE_PAUSED):
                self.comparison_return_state = self.state
                self.comparison = Comparison(self)
                self.state = STATE_COMPARISON
                return
            if event.key == pygame.K_d and self.state == STATE_MENU:
                names = list(DIFFICULTIES)
                self.difficulty = names[(names.index(self.difficulty) + 1) % len(names)]
                return
            if event.key == pygame.K_m:
                self.muted = not self.muted
                self.sounds.set_muted(self.muted)
            elif self.state == STATE_MENU and event.key == pygame.K_RETURN:
                self.sounds.play("wave_clear")
                self._new_game(score_reset=True)
                self.state = STATE_PLAYING
            elif self.state == STATE_PLAYING:
                if event.key == pygame.K_SPACE:
                    self._player_shoot()
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self._dash()
                elif event.key == pygame.K_e:
                    self._activate_pulse()
                elif event.key == pygame.K_p:
                    self.state = STATE_PAUSED
            elif self.state == STATE_PAUSED and event.key == pygame.K_p:
                self.state = STATE_PLAYING
            elif (self.state in (STATE_GAME_OVER, STATE_VICTORY)
                    and event.key == pygame.K_RETURN):
                self._new_game(score_reset=True)
                self.state = STATE_PLAYING

            # Guidance selection works in every state; V hides/shows the overlay.
            if event.key in (pygame.K_0, pygame.K_KP0):
                self.ai_mode = 0
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.ai_mode = 1
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.ai_mode = 2
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.ai_mode = 3
            elif event.key in (pygame.K_4, pygame.K_KP4):
                self.ai_mode = 4
            elif event.key == pygame.K_TAB:
                self.ai_mode = (self.ai_mode + 1) % len(AGENTS)
            elif event.key == pygame.K_v:
                self.show_ai_debug = not self.show_ai_debug
            if self.ai_mode != previous_mode or event.key == pygame.K_v:
                self.ai_telemetry = {}
                self.guidance_timer = 0.0
        elif event.type == pygame.QUIT:
            self._save_hiscore()
            raise SystemExit

    def _player_shoot(self):
        limit = 4 if self.rapid_timer > 0 else 1 + self.weapon_rank
        if not self.player.can_shoot() or len(self.bullets) >= limit:
            return
        self.bullets.append(
            Bullet(self.player.rect.centerx, self.player.rect.top)
        )
        self.player.cooldown = 0.13 if self.rapid_timer > 0 else max(.16, .34 - self.weapon_rank * .06)
        self.effects.burst(self.player.rect.midtop, (100, 230, 255), 4)
        self.shots_fired += 1
        self.sounds.play("shoot")

    # --------------------------------------------------------------- scoring
    def _add_score(self, points):
        self.score += points
        if (not self.extra_life_awarded
                and self.score >= EXTRA_LIFE_AT
                and self.player.lives < MAX_LIVES):
            self.extra_life_awarded = True
            self.player.lives += 1
            self.sounds.play("extra_life")
        if self.score > self.hi_score:
            self.hi_score = self.score

    def _kill_alien(self, alien):
        alien.alive = False
        self.grid.note_kill()
        self.combo += 1
        self.combo_timer = 2.5
        multiplier = min(4, 1 + (self.combo - 1) // 3)
        self._add_score(alien.points * multiplier)
        self.effects.burst(alien.rect.center, (110, 255, 160))
        label = self.font_tiny.render("+%d" % (alien.points * multiplier), True, HI_GREEN)
        self.booms.append(Boom(label, alien.rect.center, .6))
        if random.random() < .12:
            self.supplies.append(Supply(alien.rect.center, random.choice(("rapid", "shield"))))
        self.booms.append(Boom(self.sprites.alien_boom, alien.rect.center,
                               0.22))
        self.sounds.play("alien_die")

    # ---------------------------------------------------------------- update
    def update(self, dt):
        if self.state == STATE_COMPARISON:
            return
        self.menu_flash += dt
        if self.state not in (STATE_PAUSED, STATE_GAME_OVER, STATE_VICTORY):
            self.effects.update(dt)

        if self.state in (STATE_MENU, STATE_PAUSED, STATE_GAME_OVER, STATE_VICTORY):
            return

        if self.state == STATE_WAVE_PAUSE:
            return

        # ---- STATE_PLAYING ----
        was_alive = self.player.alive
        self.level_elapsed += dt
        self.intro_timer = max(0, self.intro_timer - dt)
        self.dash_cooldown = max(0, self.dash_cooldown - dt)
        self.rapid_timer = max(0.0, self.rapid_timer - dt)
        self.combo_timer = max(0.0, self.combo_timer - dt)
        self.pulse_flash = max(0.0, self.pulse_flash - dt)
        if self.combo_timer == 0:
            self.combo = 0

        # Guidance never supplies movement keys or fires the cannon.
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.last_direction = -1
        elif keys[pygame.K_RIGHT]:
            self.last_direction = 1
        self.player.update(dt, keys)
        if keys[pygame.K_SPACE]:
            self._player_shoot()

        self._update_supplies(dt)

        self._update_encounter(dt)
        self.grid.update(dt)
        if self.grid.reached_bottom():
            self._end_game()
            return

        self._update_bullets(dt)
        self._update_bombs(dt)  # may kill the player via bomb hit

        if was_alive and not self.player.alive:
            self.combo = 0
            self.combo_timer = 0.0
            self.rapid_timer = 0.0
            self.shield_charge = False
            self.effects.burst(self.player.rect.center, (255, 130, 70), 50)
            self.death_boom = Boom(
                self.sprites.player_boom[0], self.player.rect.center,
                1e9,  # persists until respawn logic clears it
            )
            self.death_boom.is_player_death = True
            self.sounds.play("player_die")
        if self.death_boom is not None:
            self.death_boom.image = self.sprites.player_boom[
                int(self.player.boom_frame) % 2
            ]

        self._update_ufo(dt)
        self._spawn_bombs(dt)
        self.booms = [b for b in self.booms if b.update(dt)]

        if not self.player.alive and self.player.dead_timer <= 0:
            if self.player.lives > 0:
                self.player.respawn()
                self.death_boom = None
            else:
                self._end_game()
                return

        complete = (self.level.objective == "clear" and self.grid.alive_count == 0
                    or self.level.objective == "boss" and self.boss is None
                    or self.level.objective == "survive" and self.level_elapsed >= self.level.duration)
        if complete and self.player.alive:
            self._begin_wave_pause()
        self._update_guidance(dt)

    def _update_guidance(self, dt):
        agent = AGENTS.get(self.ai_mode, (None, None))[1]
        if (agent is None or not self.show_ai_debug or not self.player.alive
                or self.state != STATE_PLAYING):
            self.ai_telemetry = {}
            return
        self.guidance_timer -= dt
        if self.guidance_timer <= 0:
            _, _, self.ai_telemetry = agent.decide(self)
            self.guidance_timer = .12

    def _dash(self):
        if self.state != STATE_PLAYING or not self.player.alive or self.dash_cooldown > 0:
            return
        keys = pygame.key.get_pressed()
        direction = -1 if keys[pygame.K_LEFT] else (1 if keys[pygame.K_RIGHT] else self.last_direction)
        self.effects.burst(self.player.rect.center, (100, 220, 255), 20)
        self.player.rect.x = max(MIN_X, min(MAX_X - self.player.rect.w,
                                          self.player.rect.x + direction * 130))
        self.player.invuln = max(self.player.invuln, .22)
        self.dash_cooldown = 3.0

    def _warn(self, x, y, delay, speed_scale=1.0, source=None):
        if len(self.bombs) + len(self.warnings) >= 18:
            return
        self.warnings.append({"x": max(24, min(WIDTH - 24, x)), "y": y,
                              "timer": delay, "speed_scale": speed_scale, "source": source})

    def _update_encounter(self, dt):
        for warning in list(self.warnings):
            if warning["source"] is not None and not warning["source"].alive:
                self.warnings.remove(warning)
                continue
            warning["timer"] -= dt
            if warning["timer"] <= 0:
                self.bombs.append(Bomb(warning["x"], warning["y"], self.sprites,
                                       warning["speed_scale"], meteor=self.level.objective == "survive"))
                self.warnings.remove(warning)
        if self.boss:
            self.boss.update(dt)
            if self.boss.attack_timer <= 0 and self.player.alive:
                self.boss.attack_timer = (2.3 - self.boss.phase * .35) / DIFFICULTIES[self.difficulty]
                offsets = {1: (-50, 50), 2: (-100, 0, 100), 3: (-160, -80, 0, 80, 160)}[self.boss.phase]
                for offset in offsets:
                    self._warn(self.player.rect.centerx + offset, self.boss.rect.bottom, .85)
        elif self.level.objective == "survive":
            self.bomb_timer -= dt
            if self.bomb_timer <= 0 and self.player.alive:
                self.bomb_timer = (1.05 if self.wave == 4 else .65) / DIFFICULTIES[self.difficulty]
                self._warn(random.randint(30, WIDTH - 30), 150, .9, 1.15)
                if self.wave == 9:
                    self._warn(self.player.rect.centerx, 150, .9, 1.15)

    def _apply_upgrade(self):
        # Repeated choices cap at three ranks; a capped choice repairs a life.
        name = ("weapon_rank", "shield_rank", "pulse_rank")[self.upgrade_choice]
        rank = getattr(self, name)
        if rank < 3:
            setattr(self, name, rank + 1)
        else:
            self.player.lives = min(MAX_LIVES, self.player.lives + 1)

    def _draw_upgrade_screen(self):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((5, 10, 24, 235))
        self.screen.blit(veil, (0, 0))
        def centered(message, y, font=None, color=WHITE):
            label = (font or self.font_small).render(message, True, color)
            self.screen.blit(label, label.get_rect(center=(WIDTH // 2, y)))
        centered("LEVEL %d CLEARED" % self.wave, 190, self.font_big)
        centered("Next: %d - %s" % (self.wave + 1, LEVELS[min(self.wave, 9)].name), 250)
        centered("Choose one campaign upgrade", 300, color=HI_GREEN)
        options = (
            "WEAPON %d/3: extra shot + faster fire" % self.weapon_rank,
            "SHIELD %d/3: start each level with more protection" % self.shield_rank,
            "PULSE %d/3: one extra charge each level" % self.pulse_rank,
        )
        for i, option in enumerate(options):
            centered(("> " if i == self.upgrade_choice else "  ") + option, 360 + i * 52,
                     color=(255, 220, 100) if i == self.upgrade_choice else GREY)
        centered("LEFT / RIGHT choose | ENTER upgrade and continue", 555)
        centered("Ranks persist this run. A max-rank choice repairs one life.", 595, self.font_tiny)

    def _activate_pulse(self):
        if self.state != STATE_PLAYING or not self.player.alive or not self.pulse_ready:
            return
        self.pulse_charges -= 1
        self.pulse_ready = self.pulse_charges > 0
        self.pulse_flash = .6
        for bomb in self.bombs:
            self.effects.burst(bomb.rect.center, (100, 220, 255), 10)
        self.bombs.clear()
        self.player.invuln = max(self.player.invuln, 1.0)
        self.sounds.play("wave_clear")

    def _update_supplies(self, dt):
        for supply in list(self.supplies):
            if not supply.update(dt):
                self.supplies.remove(supply)
            elif self.player.alive and supply.rect.colliderect(self.player.rect):
                if supply.kind == "rapid":
                    self.rapid_timer = 8.0
                else:
                    self.shield_charge = True
                    self.shield_hits = max(1, self.shield_rank)
                self.effects.burst(supply.rect.center, Supply.COLORS[supply.kind])
                self.sounds.play("extra_life")
                self.supplies.remove(supply)

    def _end_game(self):
        self.sounds.ufo_stop()
        self.ufo = None
        self.state = STATE_GAME_OVER
        self._save_hiscore()

    def _begin_wave_pause(self):
        self.sounds.ufo_stop()
        self.ufo = None
        self.sounds.play("wave_clear")
        self.bombs.clear()
        self.warnings.clear()
        self.ai_telemetry = {}
        self._add_score(200 * self.wave)
        if self.wave == len(LEVELS):
            self.state = STATE_VICTORY
            self._save_hiscore()
        else:
            self.state = STATE_WAVE_PAUSE
        self.wave_pause_timer = WAVE_PAUSE

    # ------------------------------------------------------- projectile sims
    def _update_bullets(self, dt):
        """Sub-step bullet movement so nothing tunnels through thin walls."""
        for bullet in list(self.bullets):
            remaining = BULLET_SPEED * dt
            while remaining > 0 and bullet in self.bullets:
                px = min(6.0, remaining)
                remaining -= px
                bullet.rect.y -= int(px + 0.5)
                if bullet.offscreen():
                    self.bullets.remove(bullet)
                    break
                if self._bullet_hits(bullet):
                    self.bullets.remove(bullet)
                    break

    def _bullet_hits(self, bullet):
        if self.boss and self.boss.rect.colliderect(bullet.rect):
            self.boss.hit(bullet.rect)
            self.effects.burst(bullet.rect.center, (255, 190, 90), 8)
            self.sounds.play("pop")
            if self.boss.hp <= 0:
                self.effects.burst(self.boss.rect.center, (255, 100, 160), 80)
                self._add_score(1500)
                self.boss = None
                self.selected_target = None
            return True
        # UFO first (highest target, mystery points).
        if self.ufo and self.ufo.rect.colliderect(bullet.rect):
            points = self.ufo.points
            label = self.font_tiny.render(str(points), True, UFO_LABEL_COLOR)
            self.booms.append(Boom(label, self.ufo.rect.center, 0.9))
            self.booms.append(
                Boom(self.sprites.alien_boom, self.ufo.rect.center, 0.3))
            self._add_score(points)
            self.effects.burst(self.ufo.rect.center, (255, 110, 90), 35)
            self.supplies.append(Supply(self.ufo.rect.center, "rapid"))
            self.sounds.ufo_stop()
            self.sounds.play("ufo_die")
            self.ufo = None
            return True

        alien = self.grid.collide(bullet.rect)
        if alien:
            alien.hp -= 1
            if alien.hp <= 0:
                self._kill_alien(alien)
            else:
                self.effects.burst(alien.rect.center, (255, 210, 80), 12)
                self.sounds.play("shield_hit")
            return True

        # Bombs can be shot down mid-air.
        for bomb in self.bombs:
            if bomb.rect.colliderect(bullet.rect):
                self.booms.append(
                    Boom(self.sprites.alien_boom, bomb.rect.center, 0.15))
                self.bombs.remove(bomb)
                self.sounds.play("pop")
                return True

        # Bunker tops.
        for shield in self.shields:
            if shield.collide(bullet.rect, 10, 8, moving_down=False):
                self.sounds.play("shield_hit")
                return True
        return False

    def _update_bombs(self, dt):
        speed = self._bomb_speed()
        for bomb in list(self.bombs):
            remaining = speed * bomb.speed_scale * dt
            while remaining > 0 and bomb in self.bombs:
                px = min(6.0, remaining)
                remaining -= px
                bomb.advance(px)
                if bomb.rect.top > BOTTOM_BAR_Y:
                    self.bombs.remove(bomb)
                    break
                if self._bomb_collides(bomb):
                    self.bombs.remove(bomb)
                    break

    def _bomb_collides(self, bomb):
        for shield in self.shields:
            if shield.collide(bomb.rect, 8, 6, moving_down=True):
                self.sounds.play("shield_hit")
                return True
        if (self.player.alive
                and self.player.invuln <= 0
                and bomb.rect.colliderect(self.player.rect)):
            if self.shield_charge:
                self.shield_hits = max(0, self.shield_hits - 1)
                self.shield_charge = self.shield_hits > 0
                self.player.invuln = .5
                self.effects.burst(self.player.rect.center, (80, 210, 255), 30)
                self.sounds.play("pop")
            else:
                self.player.die()
            return True
        for bullet in list(self.bullets):
            if bullet.rect.colliderect(bomb.rect):
                self.bullets.remove(bullet)
                self.booms.append(
                    Boom(self.sprites.alien_boom, bomb.rect.center, 0.12))
                self.sounds.play("pop")
                return True
        return False

    def _bomb_speed(self):
        return BOMB_SPEED * (1.0 + 0.06 * (self.wave - 1)) * DIFFICULTIES[self.difficulty]

    def _spawn_bombs(self, dt):
        if self.level.objective != "clear":
            return
        self.bomb_timer -= dt
        if self.bomb_timer > 0:
            return
        self.bomb_timer = max(
            BOMB_MIN_INTERVAL,
            random.uniform(BOMB_INTERVAL, BOMB_INTERVAL * 2) / (1 + .22 * (self.wave - 1)) / DIFFICULTIES[self.difficulty],
        )
        max_bombs = min(MAX_BOMBS_BASE + self.wave - 1, MAX_BOMBS_CAP)
        if len(self.bombs) >= max_bombs or not self.player.alive:
            return
        bomber = self.grid.pick_bomber(self.player.rect.centerx)
        if bomber and bomber.role == "bomber":
            self._warn(bomber.rect.centerx, bomber.rect.bottom, .7, 1.35, bomber)
        elif bomber:
            self.bombs.append(
                Bomb(bomber.rect.centerx, bomber.rect.bottom, self.sprites))

    def _update_ufo(self, dt):
        if self.ufo:
            if not self.ufo.update(dt):
                self.ufo = None
                self.sounds.ufo_stop()
            return
        if self.level.objective != "clear" or self.grid.alive_count < UFO_MIN_ALIENS:
            return
        self.ufo_timer -= dt
        if self.ufo_timer <= 0:
            self.ufo_timer = random.uniform(*UFO_SPAWN_RANGE)
            self.ufo = UFO(self.sprites)
            self.sounds.ufo_start()

    # ------------------------------------------------------------------ draw
    def draw(self):
        self.screen.fill(BLACK)
        self._draw_stars()

        if self.state == STATE_MENU:
            self._draw_menu()
        else:
            self._draw_world()
            if self.state == STATE_GAME_OVER:
                self._draw_center_overlay("GAME OVER",
                                          "ENTER restart | ESC menu")
            elif self.state == STATE_VICTORY:
                self._draw_center_overlay("CAMPAIGN COMPLETE", "All 10 cleared! ENTER restart | ESC menu")
            elif self.state == STATE_COMPARISON:
                self.comparison.draw(self)
            elif self.state == STATE_PAUSED:
                self._draw_center_overlay("PAUSED", "press P to resume")

        pygame.display.flip()

    def _draw_stars(self):
        self.effects.draw_stars(self.screen)

    def _draw_world(self):
        for alien in self.grid.aliens:
            if not alien.alive:
                continue
            frames = self.sprites.alien[alien.kind]
            self.screen.blit(frames[self.grid.frame], alien.rect)
            role_color = {"armor": (255, 210, 80), "scout": (80, 220, 255), "bomber": (255, 100, 100)}.get(alien.role)
            if role_color:
                pygame.draw.rect(self.screen, role_color, alien.rect.inflate(4, 4), 1)
                if alien.role == "armor":
                    for i in range(alien.hp):
                        pygame.draw.circle(self.screen, role_color, (alien.rect.left + 7 + i * 9, alien.rect.top - 5), 3)
        if self.boss:
            self.boss.draw(self.screen, self.font_tiny)
        for warning in self.warnings:
            x = int(warning["x"])
            pygame.draw.line(self.screen, (160, 65, 70), (x, int(warning["y"])), (x, 648), 1)
            pygame.draw.polygon(self.screen, (255, 110, 90), [(x - 7, 630), (x + 7, 630), (x, 641)])
        if self.selected_target and getattr(self.selected_target, "alive", True):
            pygame.draw.rect(self.screen, (255, 255, 130), self.selected_target.rect.inflate(10, 10), 2)

        for shield in self.shields:
            self.screen.blit(shield.image, shield.rect)

        if self.ufo:
            self.screen.blit(self.ufo.image, self.ufo.rect)

        if self.player.alive:
            if self.player.invuln <= 0 or int(self.player.invuln * 8) % 2 == 0:
                self.screen.blit(self.player.image, self.player.rect)
        elif (self.state == STATE_PLAYING
                and self.death_boom is not None):
            self.screen.blit(self.death_boom.image, self.death_boom.rect)

        for bullet in self.bullets:
            self.screen.blit(bullet.image, bullet.rect)
        for bomb in self.bombs:
            self.screen.blit(bomb.image, bomb.rect)
        for boom in self.booms:
            if getattr(boom, "is_player_death", False):
                continue
            self.screen.blit(boom.image, boom.rect)

        for supply in self.supplies:
            supply.draw(self.screen, self.font_tiny)
        self.effects.draw(self.screen)
        if self.player.alive and self.shield_charge:
            pygame.draw.ellipse(self.screen, (80, 210, 255),
                                self.player.rect.inflate(14, 12), 2)
        if self.pulse_flash > 0:
            radius = int((1 - self.pulse_flash / .6) * WIDTH)
            pygame.draw.circle(self.screen, (100, 220, 255),
                               self.player.rect.center, max(1, radius), 3)

        if self.show_ai_debug and self.ai_mode != 0 and self.player.alive:
            self._draw_ai_debug()

        self._draw_hud()
        if self.state == STATE_WAVE_PAUSE:
            self._draw_upgrade_screen()
        elif self.intro_timer > 0 and self.state == STATE_PLAYING:
            label = self.font_tiny.render(self.level.briefing, True, (220, 230, 245))
            rect = label.get_rect(center=(WIDTH // 2, 466)).inflate(16, 12)
            pygame.draw.rect(self.screen, BLACK, rect, border_radius=6)
            self.screen.blit(label, label.get_rect(center=rect.center))

    def _draw_hud(self):
        pygame.draw.line(self.screen, GREY, (0, HUD_TOP - 8),
                         (WIDTH, HUD_TOP - 8), 2)
        pygame.draw.line(self.screen, GREY, (0, BOTTOM_BAR_Y),
                         (WIDTH, BOTTOM_BAR_Y), 2)

        score_s = self.font_mid.render("SCORE %05d" % self.score, True, WHITE)
        hi_s = self.font_mid.render("HI %05d" % self.hi_score, True, HI_GREEN)
        wave_s = self.font_mid.render("LEVEL %d/10" % self.wave, True, GREY)
        self.screen.blit(score_s, (20, 18))
        self.screen.blit(hi_s, (WIDTH // 2 - hi_s.get_width() // 2, 18))
        self.screen.blit(wave_s, (WIDTH - wave_s.get_width() - 20, 18))

        icon = self.sprites.life_icon
        for i in range(self.player.lives):
            self.screen.blit(icon, (24 + i * (icon.get_width() + 10),
                                    BOTTOM_BAR_Y + 4))

        status = "E: PULSE %d   R: %s   SHIELD: %s   COMBO x%d" % (
            self.pulse_charges,
            ("%.1fs" % self.rapid_timer) if self.rapid_timer > 0 else "--",
            "ON" if self.shield_charge else "--",
            min(4, 1 + max(0, self.combo - 1) // 3))
        self.screen.blit(self.font_tiny.render(status, True, (120, 215, 255)), (20, 104))

        dash = "DASH %s" % ("READY" if self.dash_cooldown <= 0 else "%.1fs" % self.dash_cooldown)
        dash_s = self.font_tiny.render(dash, True, GREY)
        self.screen.blit(dash_s, (WIDTH - dash_s.get_width() - 20, 104))
        objective = ("Survive %.0fs" % max(0, self.level.duration - self.level_elapsed)
                     if self.level.objective == "survive" else self.level.name)
        obj_s = self.font_tiny.render(objective, True, self.level.color)
        self.screen.blit(obj_s, (250, BOTTOM_BAR_Y + 4))

        # Bottom HUD: optional guidance telemetry
        ai_name, agent = AGENTS.get(self.ai_mode, ("Manual", None))
        ai_color = self._get_ai_color()
        if self.ai_mode == 0:
            ai_msg = "YOU CONTROL | 1-4 / TAB: guidance"
            ai_surf = self.font_tiny.render(ai_msg, True, GREY)
        else:
            tel = self.ai_telemetry
            nodes = tel.get("nodes", 0)
            t_ms = tel.get("time_ms", 0.0)
            act = tel.get("action", "STAY")
            ai_msg = "%s | %d nodes | %.1fms | %s" % (
                ai_name.upper(), nodes, t_ms, act
            )
            ai_surf = self.font_tiny.render(ai_msg, True, ai_color)

        if ai_surf.get_width() > 420:
            ai_surf = pygame.transform.smoothscale(ai_surf, (420, ai_surf.get_height()))
        self.screen.blit(ai_surf, (20, BOTTOM_BAR_Y + 26))

        mute_s = self.font_tiny.render(
            "M: %s   P: pause   C: lab" % ("off" if self.muted else "on"),
            True, GREY)
        self.screen.blit(mute_s, (WIDTH - mute_s.get_width() - 20,
                                  BOTTOM_BAR_Y + 14))

        # Guidance status, including unavailable/partial search outcomes
        if self.ai_mode != 0:
            status = self.ai_telemetry.get("status", "Calculating...")
            if not self.show_ai_debug:
                status = "Hidden (V to show)"
            banner = "%s: %s" % (ai_name.upper(), status)
            banner_surf = self.font_tiny.render(banner, True, ai_color)
            self.screen.blit(banner_surf, (20, HUD_TOP + 4))

    def _get_ai_color(self):
        colors = {
            0: WHITE,
            1: (255, 215, 60),   # Hill Climbing: Gold
            2: (80, 220, 255),   # A* Search: Cyan
            3: (255, 145, 60),   # BFS: Orange
            4: (255, 105, 180),  # DFS: Pink / Magenta
        }
        return colors.get(self.ai_mode, WHITE)

    def _draw_ai_debug(self):
        """Plot suggested horizontal positions; all actions remain the user's."""
        tel = self.ai_telemetry
        if not tel:
            return
        color = self._get_ai_color()
        positions = tel["positions"]
        track_y = self.player.rect.top - 14
        if len(positions) > 1:
            pygame.draw.lines(self.screen, color, False,
                              [(int(x), track_y) for x in positions], 2)
        for x in positions:
            pygame.draw.circle(self.screen, color, (int(x), track_y), 3)
        end_x = int(positions[-1])
        if not tel["status"].startswith("No "):
            pygame.draw.rect(self.screen, color,
                             (end_x - self.player.rect.w // 2, track_y - 6,
                              self.player.rect.w, 12), 2, border_radius=4)
        if self.ai_mode == 2 and tel["target"]:
            target = tel["target"]
            tx, ty = int(target["x"]), int(target["y"])
            pygame.draw.circle(self.screen, color, (tx, ty), 12, 1)
            for y in range(ty + 14, track_y, 12):
                pygame.draw.line(self.screen, color, (tx, y), (tx, y + 4))
        moves = tel["path"]
        sequence = " ".join({-1: "L", 0: "-", 1: "R"}[m] for m in moves[:12])
        if len(moves) > 12:
            sequence += " ..."
        hint = "SUGGESTION: %s | %s | V hide | 0 off" % (
            tel["action"], sequence or "hold")
        label = self.font_tiny.render(hint, True, color)
        backing = label.get_rect(topleft=(20, 607)).inflate(8, 4)
        pygame.draw.rect(self.screen, BLACK, backing)
        self.screen.blit(label, (20, 607))
        for bomb in tel["bombs"]:
            if not bomb["shielded"] and bomb["time_to_hit"] < 1.6:
                pygame.draw.line(self.screen, (255, 75, 75),
                                 (int(bomb["x"]) - 16, track_y + 8),
                                 (int(bomb["x"]) + 16, track_y + 8), 3)

    def _draw_menu(self):
        title = self.font_big.render("SPACE  INVADERS", True, HI_GREEN)
        sub = self.font_small.render("COLLECT UPGRADES. CHAIN KILLS. SURVIVE.", True, GREY)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 200))
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 270))

        selected = "Selected: %s | You move and fire" % AGENTS[self.ai_mode][0]
        selected_surf = self.font_tiny.render(selected, True, self._get_ai_color())
        self.screen.blit(selected_surf, (WIDTH // 2 - selected_surf.get_width() // 2, 306))

        difficulty = self.font_tiny.render("10 LEVEL CAMPAIGN | D: difficulty " + self.difficulty, True, (255, 210, 100))
        self.screen.blit(difficulty, difficulty.get_rect(center=(WIDTH // 2, 340)))
        y = 370
        frame = int(self.menu_flash * 2) % 2
        for kind, points in (("squid", 30), ("crab", 20), ("octopus", 10)):
            img = self.sprites.alien[kind][frame]
            self.screen.blit(img, (WIDTH // 2 - 130, y))
            text = self.font_small.render("= %d points" % points, True, WHITE)
            self.screen.blit(text, (WIDTH // 2 - 80, y + 8))
            y += 46
        self.screen.blit(self.sprites.ufo, (WIDTH // 2 - 130, y))
        text = self.font_small.render("= ???", True, WHITE)
        self.screen.blit(text, (WIDTH // 2 - 80, y + 8))

        if int(self.menu_flash * 1.6) % 2 == 0:
            prompt = self.font_mid.render("PRESS  ENTER  TO  START",
                                          True, WHITE)
            self.screen.blit(prompt,
                             (WIDTH // 2 - prompt.get_width() // 2, 580))
        controls = self.font_tiny.render(
            "ARROWS move | SPACE fire | SHIFT dash | E pulse | C lab", True, GREY)
        self.screen.blit(controls,
                         (WIDTH // 2 - controls.get_width() // 2, 634))
        ai_banner = self.font_tiny.render(
            "GUIDES: 1 Hill | 2 A* | 3 BFS | 4 DFS | TAB cycle | V hide | 0 off",
            True, (120, 215, 255),
        )
        self.screen.blit(ai_banner,
                         (WIDTH // 2 - ai_banner.get_width() // 2, 664))
        help_s = self.font_tiny.render("Click enemy: target | Right click: clear | P pause | M mute", True, GREY)
        self.screen.blit(help_s, help_s.get_rect(center=(WIDTH // 2, 702)))

    def _draw_center_overlay(self, heading, subline):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 140))
        self.screen.blit(veil, (0, 0))

        big = self.font_big.render(heading, True, WHITE)
        self.screen.blit(big, (WIDTH // 2 - big.get_width() // 2,
                               HEIGHT // 2 - 70))
        small = self.font_small.render(subline, True, GREY)
        self.screen.blit(small, (WIDTH // 2 - small.get_width() // 2,
                                 HEIGHT // 2 + 10))

        if self.state in (STATE_GAME_OVER, STATE_VICTORY):
            s = self.font_mid.render("final score  %d" % self.score,
                                     True, HI_GREEN)
            self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2,
                                 HEIGHT // 2 + 60))

    # ------------------------------------------------------------------ loop
    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()


def main():
    Game().run()


if __name__ == "__main__":
    main()
