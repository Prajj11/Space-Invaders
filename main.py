"""
Space Invaders -- main game engine.

Pure Python + pygame for everything: rendering (frontend) and all game
simulation (backend). All art is code-drawn bitmaps and all audio is
synthesized at runtime; the game ships with zero asset files.

Run:  python main.py
"""

import random

import pygame

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
from ai_agent import AGENTS, get_world_model

STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_WAVE_PAUSE = "wave_pause"
STATE_GAME_OVER = "game_over"


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

        self.player = Player(self.sprites)
        self.death_boom = None
        self._new_game(score_reset=True)
        self.state = STATE_MENU
        self.menu_flash = 0.0

        # AI Agent Autopilot integration (0: Manual, 1: Hill Climb, 2: A*, 3: BFS, 4: DFS)
        self.ai_mode = 0
        self.ai_telemetry = {}
        self.show_ai_debug = True

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
        self.player.reset()
        self._start_wave(1)
        self.shots_fired = 0

    def _start_wave(self, wave):
        self.wave = wave
        self.grid = InvaderGrid(wave, self.sprites, on_step=self._on_grid_step)
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
        if event.type == pygame.KEYDOWN:
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
                elif event.key == pygame.K_p:
                    self.state = STATE_PAUSED
            elif self.state == STATE_PAUSED and event.key == pygame.K_p:
                self.state = STATE_PLAYING
            elif (self.state == STATE_GAME_OVER
                    and event.key == pygame.K_RETURN):
                self._new_game(score_reset=True)
                self.state = STATE_PLAYING

            # AI Mode selection shortcuts: 0=Manual, 1=Hill Climb, 2=A*, 3=BFS, 4=DFS, TAB=cycle, V=debug
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
        elif event.type == pygame.QUIT:
            self._save_hiscore()
            raise SystemExit

    def _player_shoot(self):
        if not self.player.can_shoot() or self.bullets:
            return
        self.bullets.append(
            Bullet(self.player.rect.centerx, self.player.rect.top)
        )
        self.player.cooldown = 0.34
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
        self._add_score(alien.points)
        self.booms.append(Boom(self.sprites.alien_boom, alien.rect.center,
                               0.22))
        self.sounds.play("alien_die")

    # ---------------------------------------------------------------- update
    def update(self, dt):
        self.menu_flash += dt

        if self.state in (STATE_MENU, STATE_PAUSED, STATE_GAME_OVER):
            return

        if self.state == STATE_WAVE_PAUSE:
            self.wave_pause_timer -= dt
            if self.wave_pause_timer <= 0:
                self._start_wave(self.wave + 1)
                self.state = STATE_PLAYING
            return

        # ---- STATE_PLAYING ----
        was_alive = self.player.alive

        # AI Autopilot or Human control
        agent_info = AGENTS.get(self.ai_mode)
        agent = agent_info[1] if agent_info else None

        if agent is not None and self.player.alive:
            move_dir, should_shoot, telemetry = agent.decide(self)
            self.ai_telemetry = telemetry
            ai_keys = {
                pygame.K_LEFT: move_dir == -1,
                pygame.K_RIGHT: move_dir == 1,
            }
            self.player.update(dt, ai_keys)
            if should_shoot:
                self._player_shoot()
        else:
            self.ai_telemetry = {}
            self.player.update(dt, pygame.key.get_pressed())

        self.grid.update(dt)
        if self.grid.reached_bottom():
            self._end_game()
            return

        self._update_bullets(dt)
        self._update_bombs(dt)  # may kill the player via bomb hit

        if was_alive and not self.player.alive:
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

        if self.grid.alive_count == 0 and self.player.alive:
            self._begin_wave_pause()

    def _end_game(self):
        self.sounds.ufo_stop()
        self.ufo = None
        self.state = STATE_GAME_OVER
        self._save_hiscore()

    def _begin_wave_pause(self):
        self.sounds.ufo_stop()
        self.ufo = None
        self.sounds.play("wave_clear")
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
        # UFO first (highest target, mystery points).
        if self.ufo and self.ufo.rect.colliderect(bullet.rect):
            points = self.ufo.points
            label = self.font_tiny.render(str(points), True, UFO_LABEL_COLOR)
            self.booms.append(Boom(label, self.ufo.rect.center, 0.9))
            self.booms.append(
                Boom(self.sprites.alien_boom, self.ufo.rect.center, 0.3))
            self._add_score(points)
            self.sounds.ufo_stop()
            self.sounds.play("ufo_die")
            self.ufo = None
            return True

        alien = self.grid.collide(bullet.rect)
        if alien:
            self._kill_alien(alien)
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
            remaining = speed * dt
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
        return BOMB_SPEED * (1.0 + 0.08 * (self.wave - 1))

    def _spawn_bombs(self, dt):
        self.bomb_timer -= dt
        if self.bomb_timer > 0:
            return
        self.bomb_timer = max(
            BOMB_MIN_INTERVAL,
            random.uniform(BOMB_INTERVAL, BOMB_INTERVAL * 2) / self.wave,
        )
        max_bombs = min(MAX_BOMBS_BASE + self.wave - 1, MAX_BOMBS_CAP)
        if len(self.bombs) >= max_bombs or not self.player.alive:
            return
        bomber = self.grid.pick_bomber(self.player.rect.centerx)
        if bomber:
            self.bombs.append(
                Bomb(bomber.rect.centerx, bomber.rect.bottom, self.sprites))

    def _update_ufo(self, dt):
        if self.ufo:
            if not self.ufo.update(dt):
                self.ufo = None
                self.sounds.ufo_stop()
            return
        if self.grid.alive_count < UFO_MIN_ALIENS:
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
                                          "press ENTER to play again")
            elif self.state == STATE_PAUSED:
                self._draw_center_overlay("PAUSED", "press P to resume")

        pygame.display.flip()

    def _draw_stars(self):
        # Deterministic starfield so it doesn't flicker between frames.
        rnd = random.Random(42)
        for _ in range(70):
            x = rnd.randint(0, WIDTH - 1)
            y = rnd.randint(HUD_TOP + 10, HEIGHT - 60)
            grey = rnd.randint(28, 60)
            self.screen.fill((grey, grey, grey + 8), (x, y, 2, 2))

    def _draw_world(self):
        for alien in self.grid.aliens:
            if not alien.alive:
                continue
            frames = self.sprites.alien[alien.kind]
            self.screen.blit(frames[self.grid.frame], alien.rect)

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

        if self.show_ai_debug and self.ai_mode != 0 and self.player.alive:
            self._draw_ai_debug()

        self._draw_hud()
        if self.state == STATE_WAVE_PAUSE:
            self._draw_center_overlay(
                "WAVE %d CLEARED" % self.wave,
                "get ready for wave %d..." % (self.wave + 1),
            )

    def _draw_hud(self):
        pygame.draw.line(self.screen, GREY, (0, HUD_TOP - 8),
                         (WIDTH, HUD_TOP - 8), 2)
        pygame.draw.line(self.screen, GREY, (0, BOTTOM_BAR_Y),
                         (WIDTH, BOTTOM_BAR_Y), 2)

        score_s = self.font_mid.render("SCORE %05d" % self.score, True, WHITE)
        hi_s = self.font_mid.render("HI %05d" % self.hi_score, True, HI_GREEN)
        wave_s = self.font_mid.render("WAVE %d" % self.wave, True, GREY)
        self.screen.blit(score_s, (20, 18))
        self.screen.blit(hi_s, (WIDTH // 2 - hi_s.get_width() // 2, 18))
        self.screen.blit(wave_s, (WIDTH - wave_s.get_width() - 20, 18))

        icon = self.sprites.life_icon
        for i in range(self.player.lives):
            self.screen.blit(icon, (24 + i * (icon.get_width() + 10),
                                    BOTTOM_BAR_Y + 12))

        # Bottom HUD: AI Autopilot Telemetry and Controls
        ai_name, agent = AGENTS.get(self.ai_mode, ("Manual", None))
        ai_color = self._get_ai_color()
        if self.ai_mode == 0:
            ai_msg = "MODE: MANUAL (0-4 / TAB: AI Autopilot | V: Debug)"
            ai_surf = self.font_tiny.render(ai_msg, True, GREY)
        else:
            tel = self.ai_telemetry
            nodes = tel.get("nodes", 0)
            t_ms = tel.get("time_ms", 0.0)
            act = tel.get("action", "STAY")
            ai_msg = "%s  |  Nodes: %d  |  %.1fms  |  %s  (TAB / V)" % (
                ai_name.upper(), nodes, t_ms, act
            )
            ai_surf = self.font_tiny.render(ai_msg, True, ai_color)

        self.screen.blit(ai_surf, (WIDTH // 2 - ai_surf.get_width() // 2, BOTTOM_BAR_Y + 14))

        mute_s = self.font_tiny.render(
            "M: sound %s   P: pause" % ("off" if self.muted else "on"),
            True, GREY)
        self.screen.blit(mute_s, (WIDTH - mute_s.get_width() - 20,
                                  BOTTOM_BAR_Y + 14))

        # Top AI Banner when AI Autopilot is active
        if self.ai_mode != 0:
            banner = "[AI: %s]" % ai_name.upper()
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
        world = get_world_model(self)
        ai_color = self._get_ai_color()

        # 1. Target reticle and tracking guideline
        if world["targets"]:
            primary = world["targets"][0]
            tx, ty = int(primary["x"]), int(primary["y"])
            # Small targeting circle
            pygame.draw.circle(self.screen, ai_color, (tx, ty), 10, 1)
            # Subtle vertical guide ray from player cannon to target row
            top_y = min(ty, int(self.player.rect.top))
            bot_y = max(ty, int(self.player.rect.top))
            ray = pygame.Surface((2, max(1, bot_y - top_y)), pygame.SRCALPHA)
            ray.fill((*ai_color[:3], 45))
            self.screen.blit(ray, (int(self.player.rect.centerx - 1), top_y))

        # 2. Predicted bomb drop threat indicators along cannon track
        for b in world["bombs"]:
            if not b["shielded"] and b["time_to_hit"] < 1.6:
                bx = int(b["x"])
                danger_surf = pygame.Surface((36, 4), pygame.SRCALPHA)
                danger_surf.fill((255, 60, 60, 160))
                self.screen.blit(danger_surf, (bx - 18, int(self.player.rect.bottom + 2)))

    def _draw_menu(self):
        title = self.font_big.render("SPACE  INVADERS", True, HI_GREEN)
        sub = self.font_small.render("pure python + pygame", True, GREY)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 200))
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 270))

        y = 340
        frame = int(self.menu_flash * 2) % 2
        for kind, points in (("squid", 30), ("crab", 20), ("octopus", 10)):
            img = self.sprites.alien[kind][frame]
            self.screen.blit(img, (WIDTH // 2 - 130, y))
            text = self.font_small.render("= %d points" % points, True, WHITE)
            self.screen.blit(text, (WIDTH // 2 - 80, y + 8))
            y += 56
        self.screen.blit(self.sprites.ufo, (WIDTH // 2 - 130, y))
        text = self.font_small.render("= ???", True, WHITE)
        self.screen.blit(text, (WIDTH // 2 - 80, y + 8))

        if int(self.menu_flash * 1.6) % 2 == 0:
            prompt = self.font_mid.render("PRESS  ENTER  TO  START",
                                          True, WHITE)
            self.screen.blit(prompt,
                             (WIDTH // 2 - prompt.get_width() // 2, 580))
        controls = self.font_tiny.render(
            "ARROWS to move   SPACE to fire   P pause   M mute", True, GREY)
        self.screen.blit(controls,
                         (WIDTH // 2 - controls.get_width() // 2, 634))
        ai_banner = self.font_tiny.render(
            "AI AUTOPILOT: 0: Manual | 1: Hill Climb | 2: A* | 3: BFS | 4: DFS  (TAB / V)",
            True, (120, 215, 255),
        )
        self.screen.blit(ai_banner,
                         (WIDTH // 2 - ai_banner.get_width() // 2, 664))

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

        if self.state == STATE_GAME_OVER:
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
