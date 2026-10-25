"""Headless regression tests for read-only, user-controlled guidance."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import unittest
from unittest.mock import patch
import pygame

from ai_agent import (AGENTS, AStarAgent, BFSAgent, DFSAgent, HillClimbingAgent,
                      MOVE_STEP_PX, safe_transition, get_world_model)
from entities import Bomb
from main import Game, STATE_PLAYING, STATE_PAUSED
from settings import MIN_X, MAX_X


def world(bombs=None, target=472):
    return {"player_x": 400, "player_w": 30, "bombs": bombs or [],
            "targets": [] if target is None else [{"x": target, "y": 300}],
            "shields": []}


class PlannerTests(unittest.TestCase):
    def test_hill_moves_to_safer_neighbor(self):
        w = world([{"x": 400, "time_to_hit": .4, "shielded": False}])
        path, _, status = HillClimbingAgent().plan(w)
        self.assertIn(path, ([-1], [1]))
        self.assertEqual(status, "Safer nearby position")

    def test_astar_reaches_target_alignment(self):
        path, _, status = AStarAgent().plan(world())
        self.assertEqual(path, [1, 1, 1])
        self.assertEqual(status, "Route to target alignment")
        self.assertEqual(AStarAgent().plan(world(target=None))[2], "No target available")

    def test_bfs_finds_shallowest_safe_position(self):
        self.assertEqual(BFSAgent().plan(world())[0], [])
        w = world([{"x": 400, "time_to_hit": .4, "shielded": False}])
        path, _, _ = BFSAgent().plan(w)
        self.assertEqual(len(path), 1)
        self.assertIn(path[0], (-1, 1))

    def test_dfs_returns_actual_valid_sequence(self):
        w = world()
        path, _, _ = DFSAgent().plan(w)
        self.assertEqual(len(path), 6)
        x = w["player_x"]
        for step, move in enumerate(path):
            nx = x + move * MOVE_STEP_PX
            self.assertTrue(safe_transition(x, nx, step, w))
            x = nx

    def test_no_false_safe_result_when_all_moves_blocked(self):
        bombs = [{"x": x, "time_to_hit": .05, "shielded": False}
                 for x in range(350, 451, 10)]
        for planner in (AStarAgent(), BFSAgent(), DFSAgent()):
            path, _, status = planner.plan(world(bombs))
            self.assertFalse(path)
            self.assertTrue(status.startswith("No "))


class ControlTests(unittest.TestCase):
    def setUp(self):
        saver = patch.object(Game, "_save_hiscore")
        saver.start()
        self.addCleanup(saver.stop)
        self.game = Game()
        self.game.state = STATE_PLAYING
        self.game.bomb_timer = self.game.ufo_timer = 9999
        self.keys = {pygame.K_LEFT: False, pygame.K_RIGHT: False, pygame.K_SPACE: False}

    def tearDown(self):
        pygame.quit()

    def test_every_guide_leaves_movement_and_firing_to_user(self):
        g = self.game
        for mode in range(1, 5):
            g.ai_mode = mode
            g.guidance_timer = 0
            x = g.player.rect.x
            with patch("pygame.key.get_pressed", return_value=self.keys):
                g.update(.02)
            self.assertEqual(g.player.rect.x, x)
            self.assertEqual(g.shots_fired, 0)
            self.assertIn("positions", g.ai_telemetry)
            self.keys[pygame.K_RIGHT] = self.keys[pygame.K_SPACE] = True
            g.bullets.clear()
            g.player.cooldown = 0
            shots = g.shots_fired
            with patch("pygame.key.get_pressed", return_value=self.keys):
                g.update(.02)
            self.assertGreater(g.player.rect.x, x)
            self.assertEqual(g.shots_fired, shots + 1)
            self.keys[pygame.K_RIGHT] = self.keys[pygame.K_SPACE] = False
            g.shots_fired = 0

    def test_hidden_off_and_paused_guidance(self):
        g = self.game
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
        g._update_guidance(.02)
        self.assertTrue(g.ai_telemetry)
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v))
        g._update_guidance(.02)
        self.assertFalse(g.ai_telemetry)
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v))
        g._update_guidance(.02)
        snapshot = g.ai_telemetry.copy()
        g.state = STATE_PAUSED
        g.update(1)
        self.assertEqual(g.ai_telemetry, snapshot)
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_0))
        self.assertFalse(g.ai_telemetry)

    def test_guidance_bounds_rendering_and_read_only(self):
        g = self.game
        for x in (MIN_X, MAX_X - g.player.rect.w):
            g.player.rect.x = x
            for mode, (_, agent) in AGENTS.items():
                if agent is None:
                    continue
                g.ai_mode = mode
                rect = g.player.rect.copy()
                _, shoot, g.ai_telemetry = agent.decide(g)
                self.assertEqual(g.player.rect, rect)
                self.assertFalse(shoot)
                for pos in g.ai_telemetry["positions"]:
                    self.assertGreaterEqual(pos, MIN_X + g.player.rect.w // 2)
                    self.assertLessEqual(pos, MAX_X - (g.player.rect.w - g.player.rect.w // 2))
                g.draw()

    def test_bomb_below_bunker_is_not_protected(self):
        g = self.game
        shield = g.shields[0]
        g.bombs = [Bomb(shield.rect.centerx, shield.rect.bottom + 5, g.sprites)]
        self.assertFalse(get_world_model(g)["bombs"][0]["shielded"])


if __name__ == "__main__":
    unittest.main()
