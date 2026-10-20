"""
Pixel art encoded as bitmaps in code -- the game ships zero image files.

Each sprite is a list of equal-length strings where 'X' is an opaque pixel
and '.' is transparent. build() blows them up by SPRITE_SCALE into real
pygame Surfaces. Sprites are cached on the Sprites object created after the
display is ready.
"""

import pygame

from settings import (
    BOMB_YELLOW,
    GREEN,
    SPRITE_SCALE,
    UFO_RED,
    WHITE,
)

# --- Invaders: two animation frames each -------------------------------------
SQUID = [
    [
        "...XX...",
        "..XXXX..",
        ".XXXXXX.",
        "XX.XX.XX",
        "XXXXXXXX",
        "..X..X..",
        ".X.XX.X.",
        "X.X..X.X",
    ],
    [
        "...XX...",
        "..XXXX..",
        ".XXXXXX.",
        "XX.XX.XX",
        "XXXXXXXX",
        ".X.XX.X.",
        "X......X",
        ".X....X.",
    ],
]

CRAB = [
    [
        "..X.....X..",
        "...X...X...",
        "..XXXXXXX..",
        ".XX.XXX.XX.",
        "XXXXXXXXXXX",
        "X.XXXXXXX.X",
        "X.X.....X.X",
        "...XX.XX...",
    ],
    [
        "..X.....X..",
        "X..X...X..X",
        "X.XXXXXXX.X",
        "XXX.XXX.XXX",
        "XXXXXXXXXXX",
        ".XXXXXXXXX.",
        "..X.....X..",
        ".X.......X.",
    ],
]

OCTOPUS = [
    [
        "....XXXX....",
        ".XXXXXXXXXX.",
        "XXXXXXXXXXXX",
        "XXX..XX..XXX",
        "XXXXXXXXXXXX",
        "...XX..XX...",
        "..XX.XX.XX..",
        "XX........XX",
    ],
    [
        "....XXXX....",
        ".XXXXXXXXXX.",
        "XXXXXXXXXXXX",
        "XXX..XX..XXX",
        "XXXXXXXXXXXX",
        "..XXX..XXX..",
        ".XX..XX..XX.",
        "..XX....XX..",
    ],
]

UFO = [
    ".....XXXXXX.....",
    "...XXXXXXXXXX...",
    "..XXXXXXXXXXXX..",
    ".XX.XX.XX.XX.XX.",
    "XXXXXXXXXXXXXXXX",
    "..XXX..XX..XXX..",
    "...X........X...",
]

PLAYER = [
    "......X......",
    ".....XXX.....",
    ".....XXX.....",
    ".XXXXXXXXXXX.",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
]

SHIELD = [
    "....XXXXXXXXXXXXXX....",
    "...XXXXXXXXXXXXXXXX...",
    "..XXXXXXXXXXXXXXXXXX..",
    ".XXXXXXXXXXXXXXXXXXXX.",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXX..XXXXXXXXXX",
    "XXXXXXXXX....XXXXXXXXX",
    "XXXXXXXX......XXXXXXXX",
    "XXXXXXX........XXXXXXX",
    "XXXXXXX........XXXXXXX",
    "XXXXXXX........XXXXXXX",
]

ALIEN_BOOM = [
    "X....X.X....X",
    ".X...X.X...X.",
    "..X.......X..",
    "....X...X....",
    ".X...XXX...X.",
    "....X...X....",
    "..X.......X..",
    ".X...X.X...X.",
]

PLAYER_BOOM = [
    [
        "..X....X.....",
        "....X.....X..",
        ".X....X....X.",
        "....X..X.....",
        "X...X.....X..",
        "..X....X...X.",
        "....X.....X..",
        ".X...X..X....",
    ],
    [
        ".....X....X..",
        "..X.....X....",
        "....X....X...",
        ".X....X....X.",
        "..X.....X..X.",
        "X....X.....X.",
        "..X....X.....",
        "....X....X..X",
    ],
]

BOMB = [
    [".X.", "X..", ".X.", "..X", ".X.", "X..", ".X."],
    [".X.", "..X", ".X.", "X..", ".X.", "..X", ".X."],
]


def build(rows, color, scale=SPRITE_SCALE):
    """Convert bitmap rows into a scaled pygame Surface."""
    w, h = len(rows[0]), len(rows)
    surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "X":
                pygame.draw.rect(
                    surf, color,
                    (x * scale, y * scale, scale, scale),
                )
    return surf


class Sprites:
    """Builds and caches every Surface the game needs."""

    def __init__(self):
        self.alien = {
            "squid": [build(f, WHITE) for f in SQUID],
            "crab": [build(f, WHITE) for f in CRAB],
            "octopus": [build(f, WHITE) for f in OCTOPUS],
        }
        self.ufo = build(UFO, UFO_RED)
        self.player = build(PLAYER, GREEN)
        self.shield = build(SHIELD, GREEN)
        self.alien_boom = build(ALIEN_BOOM, WHITE)
        self.player_boom = [build(f, GREEN) for f in PLAYER_BOOM]
        self.bomb = [build(f, BOMB_YELLOW) for f in BOMB]
        # Small cannon icon for the lives counter (a two-thirds scale player)
        self.life_icon = pygame.transform.scale(
            self.player,
            (self.player.get_width() * 2 // 3,
             self.player.get_height() * 2 // 3),
        )
