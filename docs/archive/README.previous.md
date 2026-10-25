# 👾 Space Invaders — AI Edition

> A faithful clone of the 1978 arcade classic, supercharged with an **Interactive Algorithm Guidance** — built entirely in pure Python + pygame.

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/pygame--ce-%3E%3D2.5-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
![AI Algorithms](https://img.shields.io/badge/AI-Hill%20Climbing%20%7C%20A*%20%7C%20BFS%20%7C%20DFS-blueviolet?style=flat-square)

---

## ✨ Overview

This project implements the classic **Space Invaders** arcade game from scratch using only **Python** and **pygame-ce**. What makes it unique is the integrated **Interactive Algorithm Guidance** (`ai_agent.py`) that lets four classic search algorithms suggest moves while you play — no pre-trained models, no ML frameworks, just pure algorithmic intelligence.

**Key highlights:**
- 🎨 Every sprite is **pixel art encoded as bitmaps in code** — zero image files
- 🔊 Every sound effect is **synthesized at runtime** from raw PCM waveforms — zero audio files
- 🤖 Four algorithms provide optional guidance with **real-time telemetry HUD**
- 🧱 Pixel-perfect destructible bunkers
- 🛸 Full arcade loop with score, hi-score persistence, lives, ten campaign levels, bosses, and UFO

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
| `SPACE` | Hold to fire (four shots with rapid-fire upgrade) |
| `SHIFT` | Dash in held/last direction, 3-second cooldown |
| `C` | Open/close the frozen algorithm comparison lab |
| `D` | Cycle Easy / Normal / Hard on the title screen |
| Left / right mouse | Select an enemy target / clear the selection |
| `E` | Emergency pulse: clears bombs and grants 1 second of protection, one base charge per level (upgradeable) |
| `0` | Turn guidance off (controls always remain manual) |
| `1` | Switch to **Hill Climbing** guidance |
| `2` | Switch to **A\* Search** guidance |
| `3` | Switch to **BFS** guidance |
| `4` | Switch to **DFS** guidance |
| `TAB` | Cycle guidance mode |
| `V` | Hide/show guidance overlays |
| `P` | Pause / resume |
| `M` | Mute / unmute |
| `ENTER` | Start game / play again |

---

## Algorithm guidance (Python only)

You always move with the arrows and fire with SPACE. Press **1-4** at any time
(including the menu or pause screen) to choose a guide; **TAB** cycles guides,
**0** disables guidance, and **V** hides/shows it. Algorithms never move or fire
for you. Selecting a guide while paused takes effect when play resumes.

| Key | Algorithm | What you see |
| --- | --- | --- |
| 1 | Hill Climbing | A nearby position with lower predicted bomb risk, or advice to hold |
| 2 | A* | A horizontal route toward alignment with the highlighted priority target |
| 3 | BFS | The shallowest reachable position predicted safe to hold for 0.6 seconds |
| 4 | DFS | A possible six-step move sequence, with backtracking around predicted hazards |

The colored track above your ship shows suggested positions; its outlined endpoint
marks the destination. The sequence uses **L** for left, **R** for right, and **-**
for waiting. Each step represents 24 pixels / 0.075 seconds. The ship only moves
horizontally; the A* dotted vertical line indicates target alignment, not flight.
Red marks indicate nearby bomb lanes. The HUD reports suggested action, nodes
examined, calculation time, and partial/unavailable results.

A* uses a priority queue with elapsed steps as g and remaining horizontal distance
as h. BFS uses a FIFO queue; DFS uses a LIFO stack. Hill Climbing compares the
current position with its two neighbors and accepts only an improvement. Searches
check intermediate movement positions against predicted bomb arrivals. A* and BFS
search up to 28 steps with a 1,600-node budget; DFS searches six steps. Guides refresh
about eight times per second and freeze when paused.

These are short-term predictions based on visible bombs and current bunker pixels.
Future enemy fire, moving targets and bunker damage can invalidate advice. A* reports
partial routes and blocked firing lanes explicitly; BFS means nearest in movement
steps within the search model, including waiting. Guidance does not guarantee safety.

---

## 🏗️ Project Structure

```
Space-Invaders/
├── main.py          # Game engine: state machine, collisions, HUD, rendering
├── ai_agent.py      # guidance: Hill Climbing, A* Search, BFS, DFS
├── entities.py      # Player, InvaderGrid, Projectiles, Shields, UFO
├── sprites.py       # All pixel art as in-code bitmaps → pygame.Surfaces
├── sounds.py        # Procedural audio: PCM waveforms synthesized at startup
├── settings.py      # All tunable constants (sizes, speeds, scoring, colors)
├── test_smoke.py    # Headless smoke tests: full game loop + all guidance algorithms
├── requirements.txt
└── README.md
```

| File | Role |
|------|------|
| `main.py` | Core game engine — state machine, collision detection, HUD rendering, wave scaling |
| `ai_agent.py` | Interactive Algorithm Guidance — world model extraction, four read-only search algorithms, telemetry |
| `entities.py` | Game entities — `Player`, `InvaderGrid`, `Bullet`, `Bomb`, `Shield`, `UFO`, `Boom` |
| `sprites.py` | Procedural pixel art — all sprites encoded as bitmaps, rasterized to `pygame.Surface` at startup |
| `sounds.py` | Procedural audio — march bass, shoot SFX, explosion, UFO siren, synthesized from PCM waveforms |
| `settings.py` | Central config — every tunable game constant (resolution, speeds, scoring, colors, file paths) |
| `test_smoke.py` | Headless integration tests — real game loop with dummy drivers, simulates gameplay + verifies all guidance algorithms |

---

## 🎯 Game Features

- **5×11 Invader Formation** — squid / crab / octopus sprites marching side-to-side, dropping at edges, **speeding up as numbers thin**, with the four-note bass march synced to each step.
- **Destructible Bunkers** — bombs and bullets carve **pixel-level holes**; bunker sprites are destroyed by literally erasing their pixels.
- **Invader Bombing** — bombs aimed at the player's column with increasing frequency per wave.
- **Mystery UFO** — crosses the top of the screen for 50–300 points with a siren sound effect.
- **Full Arcade Loop** — score display, hi-score persistence (`.hiscore`), lives with cannon icons, bonus cannon at 1500 points, level progression, level-clear upgrades, start / pause / game-over / victory screens, and lose condition.
- **Player Respawn** — blinking invulnerability frames after death, cannon explosion animation.

---

## 🧪 Testing

```bash
python test_smoke.py
```

Runs the real game loop with dummy video/audio SDL drivers (no window required), simulates:
- A full gameplay session with kills, wave progression, and player death
- All four guidance algorithms (Hill Climbing, A\*, BFS, DFS) making decisions
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
- **Real-time Constraints**: Searches use bounded depth/node budgets and refresh approximately every 0.12 seconds

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">Made with ❤️ and 👾 | PCCE — AI Sem 5</p>

## Combat upgrades

- Falling **R** capsules grant 8 seconds of rapid fire. **S** capsules absorb at least one bomb hit (shield upgrade rank increases capacity). Fly into capsules to collect them; they pass through bunkers.
- Invaders have a 12% supply drop chance; destroying a UFO guarantees an R capsule.
- Kill another invader within 2.5 seconds to keep a combo going. Every three kills increases the score multiplier, up to 4x. Taking damage resets the combo and rapid fire.
- Press **E** to clear all current bombs and gain one second of protection, one base charge per level (upgradeable).
- Moving stars, muzzle sparks, explosion debris, shield outlines and a pulse shockwave add combat feedback. Pause freezes gameplay and effects.
- Pickup timers and combos reset between levels. Chosen campaign upgrade ranks persist until a new run. Guidance remains optional; you control movement, firing, pickup collection and the pulse.

Guidance regression tests: `python -m unittest test_guidance.py test_combat.py`.

## Ten-level campaign

| Level | Name | Objective |
| --- | --- | --- |
| 1 | First Contact | Clear the basic formation |
| 2 | Scout Patrol | Clear a formation containing cyan, weaving scouts |
| 3 | Iron Guard | Defeat gold two-hit armor and red bombers |
| 4 | Meteor Run | Survive 35 seconds of telegraphed meteor strikes |
| 5 | Sentinel | Defeat the first boss |
| 6 | Counterattack | Clear scouts and armored guards |
| 7 | Bombardment | Defeat bombers and armored guards |
| 8 | Last Fleet | Clear all three enemy types |
| 9 | Storm Passage | Survive 45 seconds of faster meteor strikes |
| 10 | Overlord | Defeat the final boss and finish the campaign |

Bosses have visible health bars, three health-dependent attack phases, and a gold
core that takes double damage. Red warning lanes show where the next shots will
fall; bomber warnings are cancelled if the bomber is destroyed before firing.
Meteors can be shot down and hit bunkers like other projectiles. Each level clear
awards a level-scaled score bonus. There is no time limit on formation or boss levels.

After levels 1-9, use **LEFT / RIGHT** to choose an upgrade and **ENTER** to continue:

- **Weapon:** an extra simultaneous shot and shorter normal firing cooldown per rank.
- **Shield:** start each level with protection that absorbs one hit per rank.
- **Pulse:** an extra emergency pulse charge per level per rank.

Each upgrade caps at rank 3. Selecting a capped upgrade restores one life (up to
six). Press **ESC** on game-over or victory screens to return to difficulty selection. Runs start from level 1; campaign progress and ranks are not saved between
runs. The high score remains persistent. Difficulty changes formation speed,
projectile speed, attack cadence, and boss health; select it using **D** before play.

**SHIFT** dashes 130 pixels horizontally with brief protection, then recharges for
three seconds. It uses a held arrow direction, or the last direction moved. You
remain in manual control regardless of the selected algorithm.

## Algorithm lab and selected targets

Click an enemy or boss to prioritize it in guidance. Right-click or click empty
space to clear the selection. Dead targets are ignored automatically.

Press **C** during play or pause to freeze the game and compare all four algorithms
against the same situation. The table shows suggestions, expanded/evaluated nodes,
calculation time and route length. Within the lab:

- **1-4:** inspect an algorithm.
- **N:** reveal the next actual search expansion/evaluation.
- **A:** show the full search and its selected route.
- **R:** restart the search replay.
- **C / ESC:** return to the prior playing/paused state.

The plot's horizontal axis is ship position; its vertical axis is the future step.
Gray points show explored states, yellow marks the latest state, and green shows
the selected route after the replay completes. This is a replay of a completed,
bounded search, not a simulation tick. Times are local measurements, not a ranking
of algorithm quality: these algorithms intentionally solve different objectives.
Guidance includes scheduled warning lanes and per-projectile speed, but cannot
predict attacks which have not yet been scheduled.

New Python modules: `campaign.py` defines levels and bosses; `comparison.py` draws
the algorithm lab. No browser, JavaScript, image downloads or external assets are
required.

Run all regression tests with:

```bash
python -m unittest test_campaign.py test_guidance.py test_combat.py
python test_smoke.py
```
