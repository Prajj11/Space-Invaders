"""Python-only campaign definitions and boss simulation."""
from dataclasses import dataclass
import math
import pygame
from settings import WIDTH


@dataclass(frozen=True)
class Level:
    name: str
    briefing: str
    enemy_types: tuple = ()
    objective: str = "clear"
    duration: float = 0
    color: tuple = (100, 220, 255)


LEVELS = (
    Level("First Contact", "Destroy the formation. Collect R and S supplies."),
    Level("Scout Patrol", "Cyan scouts weave quickly across their formation.", ("scout",)),
    Level("Iron Guard", "Gold armor takes two hits. Red bombers warn before firing.", ("armor", "bomber")),
    Level("Meteor Run", "Survive 35 seconds. Red lanes warn of incoming meteors.", objective="survive", duration=35),
    Level("Sentinel", "Defeat the boss. Its glowing core takes double damage.", objective="boss"),
    Level("Counterattack", "Scouts and armored guards defend the next sector.", ("scout", "armor")),
    Level("Bombardment", "Destroy the bombers before their warning lanes fire.", ("bomber", "armor")),
    Level("Last Fleet", "All enemy types. Break the formation before it lands.", ("scout", "armor", "bomber")),
    Level("Storm Passage", "Survive 45 seconds of faster meteor strikes.", objective="survive", duration=45),
    Level("Overlord", "Final boss: three attack phases. Watch the warning lanes.", objective="boss", color=(255, 120, 170)),
)

DIFFICULTIES = {"Easy": .75, "Normal": 1.0, "Hard": 1.25}


class Boss:
    def __init__(self, level, difficulty):
        self.max_hp = round((32 if level == 5 else 48) * difficulty)
        self.hp = self.max_hp
        self.rect = pygame.Rect(WIDTH // 2 - 90, 165, 180, 64)
        self.time = 0.0
        self.attack_timer = 1.6

    @property
    def phase(self):
        return min(3, 1 + int(3 * (1 - self.hp / self.max_hp)))

    @property
    def core(self):
        return pygame.Rect(self.rect.centerx - 18, self.rect.bottom - 25, 36, 25)

    def update(self, dt):
        self.time += dt
        self.rect.centerx = round(WIDTH / 2 + math.sin(self.time * (.55 + self.phase * .12)) * 240)
        self.attack_timer -= dt

    def hit(self, bullet_rect):
        self.hp = max(0, self.hp - (2 if self.core.colliderect(bullet_rect) else 1))

    def draw(self, screen, font):
        color = (255, 100 + self.phase * 25, 120)
        pygame.draw.polygon(screen, (70, 45, 85), [self.rect.midtop, self.rect.topright,
                            self.rect.bottomright, self.rect.midbottom,
                            self.rect.bottomleft, self.rect.topleft])
        pygame.draw.rect(screen, color, self.rect, 3, border_radius=16)
        pygame.draw.rect(screen, (255, 230, 110), self.core, border_radius=7)
        for offset in (-60, 60):
            pygame.draw.circle(screen, color, (self.rect.centerx + offset, self.rect.centery), 12)
        bar = pygame.Rect(200, 134, 400, 8)
        pygame.draw.rect(screen, (60, 35, 50), bar)
        pygame.draw.rect(screen, color, (bar.x, bar.y, round(bar.w * self.hp / self.max_hp), bar.h))
        label = font.render("BOSS %d / %d   PHASE %d   GOLD CORE: 2x DAMAGE" %
                            (self.hp, self.max_hp, self.phase), True, color)
        screen.blit(label, label.get_rect(center=(WIDTH // 2, 154)))
