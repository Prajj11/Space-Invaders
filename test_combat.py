"""Regression checks for combat upgrades. Run: python -m unittest test_combat.py."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import unittest
from unittest.mock import patch
import pygame
from main import Game, STATE_PLAYING, STATE_PAUSED
from effects import Supply
from entities import Bomb


class CombatTests(unittest.TestCase):
    def setUp(self):
        saver = patch.object(Game, "_save_hiscore")
        saver.start()
        self.addCleanup(saver.stop)
        self.game = Game()
        self.game.state = STATE_PLAYING
        self.game.bomb_timer = self.game.ufo_timer = 9999

    def tearDown(self):
        pygame.quit()

    def test_collect_rapid_and_expire(self):
        g = self.game
        g.supplies.append(Supply(g.player.rect.center, 'rapid'))
        g._update_supplies(0)
        self.assertEqual(g.rapid_timer, 8)
        for _ in range(5):
            g.player.cooldown = 0
            g._player_shoot()
        self.assertEqual(len(g.bullets), 4)
        g.rapid_timer = .01
        g.update(.02)
        self.assertEqual(g.rapid_timer, 0)

    def test_shield_absorbs_once(self):
        g = self.game
        g.supplies.append(Supply(g.player.rect.center, 'shield'))
        g._update_supplies(0)
        bomb = Bomb(*g.player.rect.center, g.sprites)
        self.assertTrue(g._bomb_collides(bomb))
        self.assertTrue(g.player.alive)
        self.assertFalse(g.shield_charge)
        g.player.invuln = 0
        g._bomb_collides(bomb)
        self.assertFalse(g.player.alive)

    def test_pulse_and_wave_reset(self):
        g = self.game
        g.bombs.append(Bomb(100, 300, g.sprites))
        g._activate_pulse()
        self.assertFalse(g.bombs)
        self.assertFalse(g.pulse_ready)
        g.bombs.append(Bomb(100, 300, g.sprites))
        g._activate_pulse()
        self.assertEqual(len(g.bombs), 1)
        g._start_wave(2)
        self.assertTrue(g.pulse_ready)
        self.assertFalse(g.supplies)

    def test_combo_scoring_and_timeout(self):
        g = self.game
        with patch('main.random.random', return_value=1):
            for alien in g.grid.aliens[:4]:
                g._kill_alien(alien)
        self.assertEqual(g.score, 150)
        g.combo_timer = .01
        g.update(.02)
        self.assertEqual(g.combo, 0)

    def test_pause_freezes_upgrades_and_effects(self):
        g = self.game
        g.rapid_timer = 8
        g.state = STATE_PAUSED
        before = g.effects.time
        g.update(1)
        g._activate_pulse()
        self.assertEqual(g.rapid_timer, 8)
        self.assertEqual(g.effects.time, before)
        self.assertTrue(g.pulse_ready)


if __name__ == '__main__':
    unittest.main()
