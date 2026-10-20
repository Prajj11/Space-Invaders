# 👾 Space Invaders — AI Edition

> A faithful clone of the 1978 arcade classic, supercharged with an **AI Autopilot Engine** — built entirely in pure Python + pygame.

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/pygame--ce-%3E%3D2.5-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
![AI Algorithms](https://img.shields.io/badge/AI-Hill%20Climbing%20%7C%20A*%20%7C%20BFS%20%7C%20DFS-blueviolet?style=flat-square)

---

## ✨ Overview

This project implements the classic **Space Invaders** arcade game from scratch using only **Python** and **pygame-ce**. What makes it unique is the integrated **AI Autopilot Engine** (`ai_agent.py`) that lets four classic AI search algorithms play the game in real time — no pre-trained models, no ML frameworks, just pure algorithmic intelligence.

**Key highlights:**
- 🎨 Every sprite is **pixel art encoded as bitmaps in code** — zero image files
- 🔊 Every sound effect is **synthesized at runtime** from raw PCM waveforms — zero audio files
- 🤖 Four AI algorithms play live with **real-time telemetry HUD**
- 🧱 Pixel-perfect destructible bunkers
- 🛸 Full arcade loop with score, hi-score persistence, lives, waves, and UFO

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/Space-Invaders.git
cd Space-Invaders

# Install dependencies
pip install -r requirements.txt
```

### Run the game

```bash
python main.py
```

---

## 🎮 Controls

| Key | Action |
|-----|--------|
| `←` / `→` | Move the laser cannon (Manual mode) |
| `SPACE` | Fire (one shot on screen, arcade style) |
| `0` | Switch to **Manual** human control |
| `1` | Switch to **Hill Climbing** AI Autopilot |
| `2` | Switch to **A\* Search** AI Autopilot |
| `3` | Switch to **BFS** AI Autopilot |
| `4` | Switch to **DFS** AI Autopilot |
| `TAB` | Cycle to next AI mode |
| `V` | Toggle AI Debug Visualizer (rays & danger zones) |
| `P` | Pause / resume |
| `M` | Mute / unmute |
| `ENTER` | Start game / play again |

---

## 🤖 AI Autopilot Engine

The game features an integrated **AI Autopilot Engine** (`ai_agent.py`) implementing four classic AI search algorithms that play the game in real time. Each algorithm inspects the live game state (player position, falling bombs, bunkers, invaders, UFO) and returns a move direction, shoot decision, and telemetry stats.

### 1. 🏔️ Hill Climbing — Local Heuristic Search

- Evaluates all immediate neighboring actions (`LEFT`, `STAY`, `RIGHT`) using a **multi-factor objective function**.
- Scoring factors: bomb danger penalty, target alignment reward, shield cover bonus, wall avoidance.
- **Greedy and fast** — O(b) per frame, always moves to the locally optimal position.
- Best for: quick reactions with minimal compute overhead.

### 2. ⭐ A\* Search — Informed Best-First Search

- Explores action trajectories across a **multi-step time horizon** minimizing f(n) = g(n) + h(n).
- g(n): Accumulated path cost — movement cost, direction jitter penalties, and threat costs.
- h(n): Heuristic — estimated residual danger + horizontal distance to highest-priority target.
- **Balances survivability with offensive alignment** — the most "intelligent" planner.
- Best for: optimal play with a balance of survival and offense.

### 3. 🔄 Breadth-First Search (BFS)

- Explores moves **layer-by-layer** using a FIFO queue.
- Guaranteed to find the **shallowest (shortest) action path** to a safe, target-aligned firing pocket.
- Prunes branches that pass through lethal bomb zones.
- Best for: guaranteed shortest path to a safe shooting position.

### 4. 🌀 Depth-First Search (DFS)

- Plunges deep into action branches up to a fixed horizon using a LIFO stack.
- Rapidly validates **long-term survival paths** through falling bomb fields with backtracking on lethal branches.
- Best for: fast exploration of long-horizon survival paths.

### 📊 Telemetry HUD

While any AI is active, the on-screen HUD displays:
- Active algorithm name
- Number of nodes expanded
- Decision latency in milliseconds
- Chosen action (`LEFT` / `STAY` / `RIGHT` + `SHOOT`)

Press **V** to toggle the visual debug overlay showing danger rays and threat zones.

---

## 🏗️ Project Structure

```
Space-Invaders/
├── main.py          # Game engine: state machine, collisions, HUD, rendering
├── ai_agent.py      # AI Autopilot: Hill Climbing, A* Search, BFS, DFS
├── entities.py      # Player, InvaderGrid, Projectiles, Shields, UFO
├── sprites.py       # All pixel art as in-code bitmaps → pygame.Surfaces
├── sounds.py        # Procedural audio: PCM waveforms synthesized at startup
├── settings.py      # All tunable constants (sizes, speeds, scoring, colors)
├── test_smoke.py    # Headless smoke tests: full game loop + all AI agents
├── requirements.txt
└── README.md
```

| File | Role |
|------|------|
| `main.py` | Core game engine — state machine, collision detection, HUD rendering, wave scaling |
| `ai_agent.py` | AI Autopilot Engine — world model extraction, four search algorithms, telemetry |
| `entities.py` | Game entities — `Player`, `InvaderGrid`, `Bullet`, `Bomb`, `Shield`, `UFO`, `Boom` |
| `sprites.py` | Procedural pixel art — all sprites encoded as bitmaps, rasterized to `pygame.Surface` at startup |
| `sounds.py` | Procedural audio — march bass, shoot SFX, explosion, UFO siren, synthesized from PCM waveforms |
| `settings.py` | Central config — every tunable game constant (resolution, speeds, scoring, colors, file paths) |
| `test_smoke.py` | Headless integration tests — real game loop with dummy drivers, simulates gameplay + verifies all AI agents |

---

## 🎯 Game Features

- **5×11 Invader Formation** — squid / crab / octopus sprites marching side-to-side, dropping at edges, **speeding up as numbers thin**, with the four-note bass march synced to each step.
- **Destructible Bunkers** — bombs and bullets carve **pixel-level holes**; bunker sprites are destroyed by literally erasing their pixels.
- **Invader Bombing** — bombs aimed at the player's column with increasing frequency per wave.
- **Mystery UFO** — crosses the top of the screen for 50–300 points with a siren sound effect.
- **Full Arcade Loop** — score display, hi-score persistence (`.hiscore`), lives with cannon icons, bonus cannon at 1500 points, wave scaling, wave-clear fanfare, start / pause / game-over screens, and lose condition.
- **Player Respawn** — blinking invulnerability frames after death, cannon explosion animation.

---

## 🧪 Testing

```bash
python test_smoke.py
```

Runs the real game loop with dummy video/audio SDL drivers (no window required), simulates:
- A full gameplay session with kills, wave progression, and player death
- All four AI agents (Hill Climbing, A\*, BFS, DFS) making decisions
- Core game rule verification (scoring, lives, wave transitions)

---

## 📋 Requirements

```
pygame-ce>=2.5
```

```bash
pip install -r requirements.txt
```

---

## 🎓 Academic Context

This project was developed as part of the **Artificial Intelligence (Sem 5)** coursework at **PCCE**, demonstrating the application of classical AI search algorithms in a real-time interactive environment:

- **Uninformed Search**: BFS & DFS for game-tree exploration
- **Informed Search**: A\* with domain-specific heuristics
- **Local Search**: Hill Climbing for greedy optimization
- **Real-time Constraints**: Each algorithm must return a decision within a single game frame (~16ms at 60 FPS)

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">Made with ❤️ and 👾 | PCCE — AI Sem 5</p>
