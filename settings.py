"""
Global tunables for Space Invaders (pure Python + pygame).

Everything a curious player might want to tweak lives here: window size,
colors, speeds, scoring, wave difficulty scaling. No game logic.
"""

# --- Display ---------------------------------------------------------------
WIDTH = 800
HEIGHT = 720
FPS = 60
TITLE = "SPACE INVADERS  *  pure Python + pygame"

# --- Art -------------------------------------------------------------------
SPRITE_SCALE = 3          # each 1px of bitmap art becomes 3px on screen

# --- Colors (R, G, B) ------------------------------------------------------
BLACK = (12, 12, 20)
WHITE = (235, 235, 235)
GREEN = (70, 225, 100)     # player, shields, accents
UFO_RED = (255, 90, 90)
UFO_LABEL_COLOR = (255, 200, 120)   # floating score text when the UFO dies
BOMB_YELLOW = (245, 205, 100)
GREY = (150, 150, 160)
HI_GREEN = (110, 255, 140)

# --- Playfield geometry ----------------------------------------------------
MIN_X = 20                 # left edge the invaders may not cross
MAX_X = WIDTH - 20         # right edge
HUD_TOP = 66               # vertical space reserved for the score bar
BOTTOM_BAR_Y = HEIGHT - 46 # bottom HUD separator line

PLAYER_Y = 650             # top-left y of the player cannon
SHIELD_Y = 560             # top-left y of the bunkers
INVADER_Y_FLOOR = PLAYER_Y # invaders reaching this y = invasion (game over)

# --- Invader grid ----------------------------------------------------------
GRID_COLS = 11
GRID_ROWS = 5
X_STEP = 50                # horizontal cell size (px)
Y_STEP = 44                # vertical cell size (px)
GRID_START_X = (WIDTH - (GRID_COLS - 1) * X_STEP - 48) // 2
GRID_START_Y = 130         # moves down a little every wave
STEP_X = 8                 # px the grid shifts on every march step
DROP_Y = 24                # px the grid drops when it hits an edge

# March cadence: interval (seconds) between grid steps, based on how many
# invaders are left. Fewer invaders -> faster march, like the original.
MARCH_BASE = 0.03
MARCH_SPREAD = 0.62
MARCH_WAVE_SCALE = 0.95    # each wave marches 5% faster

# --- Invader firing --------------------------------------------------------
BOMB_INTERVAL = 1.0        # avg seconds between bomb drops
BOMB_MIN_INTERVAL = 0.35
MAX_BOMBS_BASE = 3         # grows by one per wave, capped
MAX_BOMBS_CAP = 7
BOMB_SPEED = 240           # px/s, grows slightly per wave
BOMB_AIM_CHANCE = 0.35     # chance a bomb targets the player's column

# --- Player ----------------------------------------------------------------
PLAYER_SPEED = 320         # px/s
BULLET_SPEED = 560         # px/s
START_LIVES = 3
MAX_LIVES = 6
EXTRA_LIFE_AT = 1500       # score that awards a bonus cannon (once per game)
RESPAWN_INVULN = 1.6       # seconds of blinking safety after respawning

# --- UFO -------------------------------------------------------------------
UFO_SPEED = 130            # px/s
UFO_MIN_ALIENS = 8         # no UFO when fewer invaders remain
UFO_SPAWN_RANGE = (16.0, 28.0)   # random seconds between appearances
UFO_SCORES = [50, 100, 150, 300] # classic mystery values

# --- Waves -----------------------------------------------------------------
WAVE_PAUSE = 2.0           # seconds of "WAVE CLEARED" fanfare
WAVE_DROP_PER = 14         # px lower the grid starts per wave
WAVE_DROP_MAX_STEPS = 4
PLAYER_DEAD_PAUSE = 1.4    # seconds of explosion before respawn/game over

# --- Scoring ----------------------------------------------------------------
SCORES = {"squid": 30, "crab": 20, "octopus": 10}

# --- Misc -------------------------------------------------------------------
HI_SCORE_FILE = ".hiscore"
