"""Campaign, enemy, boss, lab and progression integration checks."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import unittest
from unittest.mock import patch
import pygame
from main import (Game, STATE_PLAYING, STATE_PAUSED, STATE_WAVE_PAUSE,
                  STATE_COMPARISON, STATE_VICTORY)
from campaign import LEVELS
from entities import Bullet
from ai_agent import AGENTS, get_world_model


class CampaignTests(unittest.TestCase):
    def setUp(self):
        saver = patch.object(Game, "_save_hiscore")
        saver.start()
        self.addCleanup(saver.stop)
        self.game = Game()
        self.game.state = STATE_PLAYING
        self.game.bomb_timer = self.game.ufo_timer = 9999

    def tearDown(self):
        pygame.quit()

    def key(self, key):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_armor_requires_two_hits_and_scores_once(self):
        g = self.game
        g._start_wave(3)
        alien = next(a for a in g.grid.aliens if a.role == "armor")
        bullet = Bullet(alien.rect.centerx, alien.rect.bottom)
        g._bullet_hits(bullet)
        self.assertTrue(alien.alive)
        self.assertEqual(g.score, 0)
        g._bullet_hits(bullet)
        self.assertFalse(alien.alive)
        self.assertEqual(g.score, alien.points)

    def test_scout_motion_and_bomber_warning_cancel(self):
        g = self.game
        g._start_wave(2)
        scout = next(a for a in g.grid.aliens if a.role == "scout")
        x = scout.rect.x
        g.grid.update(.1)
        self.assertNotEqual(scout.rect.x, x)
        g._start_wave(3)
        bomber = next(a for a in g.grid.aliens if a.role == "bomber")
        g.bomb_timer = 0
        with patch.object(g.grid, "pick_bomber", return_value=bomber):
            g._spawn_bombs(.01)
        self.assertEqual(len(g.warnings), 1)
        self.assertFalse(g.bombs)
        bomber.alive = False
        g._update_encounter(1)
        self.assertFalse(g.warnings)
        self.assertFalse(g.bombs)

    def test_survival_objective_does_not_clear_empty_grid(self):
        g = self.game
        g._start_wave(4)
        g.update(.01)
        self.assertEqual(g.state, STATE_PLAYING)
        g.level_elapsed = g.level.duration
        g.update(.01)
        self.assertEqual(g.state, STATE_WAVE_PAUSE)

    def test_boss_damage_phases_attack_warning_and_clear(self):
        g = self.game
        g._start_wave(5)
        g.update(.01)
        self.assertEqual(g.state, STATE_PLAYING)
        boss = g.boss
        hp = boss.hp
        g._bullet_hits(Bullet(boss.core.centerx, boss.rect.bottom))
        self.assertEqual(boss.hp, hp - 2)
        boss.hp = 1
        self.assertEqual(boss.phase, 3)
        boss.attack_timer = 0
        g._update_encounter(.01)
        self.assertEqual(len(g.warnings), 5)
        self.assertFalse(g.bombs)
        self.assertEqual(get_world_model(g)["targets"][0]["kind"], "boss")
        g._bullet_hits(Bullet(boss.core.centerx, boss.rect.bottom))
        self.assertIsNone(g.boss)
        g.update(.01)
        self.assertEqual(g.state, STATE_WAVE_PAUSE)

    def test_upgrade_selection_progression_and_victory(self):
        g = self.game
        for number in range(1, len(LEVELS) + 1):
            self.assertEqual(g.wave, number)
            if number == 10:
                with patch.object(g, "_save_hiscore"):
                    g._begin_wave_pause()
                self.assertEqual(g.state, STATE_VICTORY)
            else:
                g._begin_wave_pause()
                self.key(pygame.K_RIGHT)
                self.key(pygame.K_RETURN)
                self.assertEqual(g.state, STATE_PLAYING)
                self.assertTrue(g.shield_charge)
                self.assertEqual(g.shield_hits, min(number, 3))
        self.key(pygame.K_RETURN)
        self.assertEqual(g.wave, 1)
        self.assertEqual(g.shield_rank, 0)
        self.assertEqual(g.score, 0)

    def test_lab_freezes_simulation_and_replays_trace(self):
        g = self.game
        self.key(pygame.K_c)
        self.assertEqual(g.state, STATE_COMPARISON)
        self.assertEqual(len(g.comparison.results), 4)
        x = g.player.rect.x
        elapsed = g.level_elapsed
        timer = g.bomb_timer
        self.key(pygame.K_SPACE)
        g.update(1)
        self.assertEqual((g.player.rect.x, g.level_elapsed, g.bomb_timer), (x, elapsed, timer))
        self.assertFalse(g.bullets)
        self.key(pygame.K_n)
        self.assertEqual(g.comparison.step, 1)
        self.key(pygame.K_a)
        self.assertEqual(g.comparison.step, len(g.comparison.results[1]["trace"]))
        g.draw()
        self.key(pygame.K_c)
        self.assertEqual(g.state, STATE_PLAYING)
        g.state = STATE_PAUSED
        self.key(pygame.K_c)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.state, STATE_PAUSED)

    def test_target_selection_dash_and_cooldown(self):
        g = self.game
        alien = g.grid.aliens[-1]
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=alien.rect.center))
        self.assertIs(g.selected_target, alien)
        self.assertEqual(get_world_model(g)["targets"][0]["kind"], "selected")
        alien.alive = False
        self.assertNotEqual(get_world_model(g)["targets"][0]["kind"], "selected")
        x = g.player.rect.x
        g._dash()
        self.assertEqual(g.player.rect.x, x + 130)
        g._dash()
        self.assertEqual(g.player.rect.x, x + 130)
        self.assertGreater(g.player.invuln, 0)

    def test_all_levels_render_and_guidance_under_hazards(self):
        g = self.game
        for number in range(1, 11):
            g._start_wave(number)
            g._warn(400, 180, .5, 1.2)
            for _ in range(60):
                g.update(1 / 60)
            for mode in range(1, 5):
                g.ai_mode = mode
                _, _, g.ai_telemetry = AGENTS[mode][1].decide(g)
                self.assertIn("trace", g.ai_telemetry)
                g.draw()

    def test_difficulty_changes_speed_and_boss_health(self):
        g = self.game
        g.difficulty = "Easy"
        g._start_wave(5)
        easy_hp, easy_speed = g.boss.hp, g._bomb_speed()
        g.difficulty = "Hard"
        g._start_wave(5)
        self.assertGreater(g.boss.hp, easy_hp)
        self.assertGreater(g._bomb_speed(), easy_speed)

    def test_upgraded_pulse_and_shields_keep_their_capacity(self):
        from entities import Bomb
        g = self.game
        g.pulse_rank = 2
        g.shield_rank = 2
        g._start_wave(2)
        g._activate_pulse()
        self.assertEqual(g.pulse_charges, 2)
        self.assertTrue(g.pulse_ready)
        g.player.invuln = 0
        bomb = Bomb(*g.player.rect.center, g.sprites)
        g._bomb_collides(bomb)
        self.assertTrue(g.shield_charge)
        self.assertEqual(g.shield_hits, 1)
        g.player.invuln = 0
        g._bomb_collides(bomb)
        self.assertFalse(g.shield_charge)
        self.assertTrue(g.player.alive)

    def test_warning_becomes_visible_meteor_after_delay(self):
        g = self.game
        g._start_wave(4)
        g.bomb_timer = 9999
        g._warn(400, 150, .5, 1.15)
        g._update_encounter(.25)
        self.assertFalse(g.bombs)
        g._update_encounter(.25)
        self.assertFalse(g.warnings)
        self.assertEqual(len(g.bombs), 1)
        self.assertIsNotNone(g.bombs[0].meteor_image)


if __name__ == "__main__":
    unittest.main()
