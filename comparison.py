"""Frozen algorithm comparison and replay of actual search expansion order."""
import pygame
from ai_agent import AGENTS, get_world_model
from settings import WIDTH, HEIGHT, MIN_X, MAX_X


class Comparison:
    def __init__(self, game):
        # All algorithms receive the same world, without advancing simulation.
        world = get_world_model(game)
        self.results = {mode: agent.analyze(world)[2]
                        for mode, (_, agent) in AGENTS.items() if agent}
        self.mode = game.ai_mode or 1
        self.step = 0

    def handle(self, key):
        if key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            self.mode = key - pygame.K_0
            self.step = 0
        elif key == pygame.K_n:
            self.step = min(len(self.results[self.mode]["trace"]), self.step + 1)
        elif key == pygame.K_r:
            self.step = 0
        elif key == pygame.K_a:
            self.step = len(self.results[self.mode]["trace"])

    def draw(self, game):
        screen = game.screen
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((5, 10, 24, 245))
        screen.blit(veil, (0, 0))
        def text(message, x, y, color=(215, 225, 240), font=None):
            screen.blit((font or game.font_tiny).render(message, True, color), (x, y))
        text("ALGORITHM LAB", 30, 25, font=game.font_mid)
        text("Same frozen situation. You remain in control when you resume.", 30, 65)
        for heading, x in (("Algorithm", 30), ("Suggestion", 260), ("Nodes", 400), ("Time", 500), ("Steps", 650)):
            text(heading, x, 105)
        for mode, tel in self.results.items():
            y = 142 + (mode - 1) * 63
            color = (100, 220, 255) if mode == self.mode else (180, 190, 205)
            text("%d  %s" % (mode, AGENTS[mode][0]), 30, y, color)
            text(tel["action"], 260, y, color)
            text(str(tel["nodes"]), 400, y, color)
            text("%.2f ms" % tel["time_ms"], 500, y, color)
            text(str(tel["depth"]), 650, y, color)
            text(tel["status"], 55, y + 23, (135, 150, 170))
        tel = self.results[self.mode]
        trace = tel["trace"][:self.step]
        area = pygame.Rect(60, 445, 680, 155)
        pygame.draw.rect(screen, (22, 32, 48), area)
        depth = max(1, max((step for _, step in tel["trace"]), default=1))
        def point(x, step):
            return (int(area.left + (x - MIN_X) / (MAX_X - MIN_X) * area.w),
                    int(area.top + step / depth * area.h))
        for x, step in trace:
            pygame.draw.circle(screen, (90, 125, 165), point(x, step), 3)
        if trace:
            pygame.draw.circle(screen, (255, 215, 80), point(*trace[-1]), 6, 2)
        # The chosen path appears once all explored states have been revealed.
        if self.step == len(tel["trace"]) and len(tel["positions"]) > 1:
            pygame.draw.lines(screen, (100, 255, 170), False,
                              [point(x, i) for i, x in enumerate(tel["positions"])], 2)
        text("%s | explored %d / %d" % (AGENTS[self.mode][0], self.step, len(tel["trace"])), 30, 402)
        text("Horizontal: ship position | Vertical: future step (not flight altitude)", 30, 615)
        text("1-4 inspect | N next expansion | A show all | R reset | C / ESC return", 30, 655)
