"""Lightweight combat effects and falling supply capsules; no external assets."""
import math
import random

import pygame

from settings import HEIGHT, HUD_TOP, WIDTH


class CombatEffects:
    def __init__(self):
        self.rng = random.Random()
        self.particles = []
        self.stars = [(self.rng.randrange(WIDTH), self.rng.randrange(HEIGHT),
                       self.rng.uniform(8, 30)) for _ in range(85)]
        self.time = 0.0

    def burst(self, center, color, count=18):
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(35, 170)
            self.particles.append([float(center[0]), float(center[1]),
                                   math.cos(angle) * speed, math.sin(angle) * speed,
                                   self.rng.uniform(.2, .65), color])
        self.particles = self.particles[-400:]

    def update(self, dt):
        self.time += dt
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]

    def draw_stars(self, screen):
        for x, y, speed in self.stars:
            yy = HUD_TOP + (y + self.time * speed) % (HEIGHT - HUD_TOP - 46)
            brightness = int(45 + speed * 2)
            pygame.draw.line(screen, (brightness, brightness, brightness + 20),
                             (x, yy), (x, yy + speed / 10))

    def draw(self, screen):
        for x, y, vx, vy, life, color in self.particles:
            pygame.draw.line(screen, color, (x, y),
                             (x - vx * .025, y - vy * .025), 2)


class Supply:
    COLORS = {"rapid": (255, 205, 80), "shield": (80, 210, 255)}

    def __init__(self, center, kind):
        self.kind = kind
        self.rect = pygame.Rect(0, 0, 26, 26)
        self.rect.center = center
        self.y = float(self.rect.y)

    def update(self, dt):
        self.y += 110 * dt
        self.rect.y = round(self.y)
        return self.rect.top < HEIGHT

    def draw(self, screen, font):
        color = self.COLORS[self.kind]
        pygame.draw.rect(screen, (18, 25, 40), self.rect, border_radius=6)
        pygame.draw.rect(screen, color, self.rect, 2, border_radius=6)
        label = font.render("R" if self.kind == "rapid" else "S", True, color)
        screen.blit(label, label.get_rect(center=self.rect.center))
