# Space Invaders — AI Guidance Edition

A ten-level arcade campaign built entirely in **Python and pygame-ce**, with
optional guidance from Hill Climbing, A*, BFS and DFS. You control movement and
shooting; the algorithms suggest moves and explain their searches.

Created for Artificial Intelligence coursework at **PCCE, Semester 5**.

## Quick start

Requires Python and pip. Tested with **Python 3.13**. All sprites, effects and audio
are generated in Python; no external asset downloads are needed.

From the project directory:

```bash
python -m pip install -r requirements.txt
python main.py
```

For an isolated environment on Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Press **ENTER** to start. Use **D** on the title screen to select Easy, Normal or
Hard. Difficulty affects enemy movement, projectile speed, attack frequency and
boss health.

## Controls

| Input | Action |
| --- | --- |
| Left / Right arrows | Move |
| Hold SPACE | Fire |
| SHIFT | Dash in the held or last movement direction; 3-second cooldown |
| E | Clear active bombs and gain brief protection; charges reset each level |
| P | Pause / resume |
| M | Mute / unmute |
| 1 / 2 / 3 / 4 | Select Hill Climbing / A* / BFS / DFS guidance |
| TAB | Cycle guidance modes |
| V / 0 | Hide or show guidance / turn guidance off |
| Left-click an enemy or boss | Prioritize that target for guidance |
| Right-click or left-click empty space | Clear the selected target |
| C | Open the algorithm lab during play or pause |
| ENTER | Start or restart a run |
| ESC on game-over or victory screen | Return to the title screen |

Between levels, use **Left / Right** to choose an upgrade and **ENTER** to continue.
The lab has its own controls, listed below.

## Campaign

| Level | Name | Challenge |
| --- | --- | --- |
| 1 | First Contact | Clear the basic formation |
| 2 | Scout Patrol | Fight cyan scouts that weave across the formation |
| 3 | Iron Guard | Defeat two-hit armored enemies and warning-lane bombers |
| 4 | Meteor Run | Survive 35 seconds of meteor strikes |
| 5 | Sentinel | Defeat the first boss |
| 6 | Counterattack | Face scouts and armored guards together |
| 7 | Bombardment | Break through bombers and armored guards |
| 8 | Last Fleet | Clear a formation with all three special enemy types |
| 9 | Storm Passage | Survive 45 seconds of faster meteor strikes |
| 10 | Overlord | Defeat the final boss to complete the campaign |

Bosses have three attack phases, visible health bars and a glowing gold core that
takes double damage. Red lanes warn of scheduled attacks. Destroying a bomber
before it fires cancels its warning. Meteors and bombs can be shot down.

You lose when you run out of lives or the invaders reach your ship's row.
Destructible bunkers provide cover, but both friendly and enemy shots damage them.
Each cleared level awards bonus points.

### Pickups and upgrades

- **R pickup:** eight seconds of rapid fire, with up to four simultaneous shots.
- **S pickup:** protection against a bomb hit; shield ranks increase its capacity.
- **Combos:** kill again within 2.5 seconds to keep the chain alive. The multiplier
  rises every three kills, up to 4x. Losing a life resets the combo and rapid fire.
- **Emergency pulse:** starts with one charge per level; clears existing bombs,
  while already scheduled warning attacks can still fire afterward.

After levels 1–9, choose one upgrade:

| Upgrade | Benefit per rank |
| --- | --- |
| Weapon | One extra normal shot on screen and a shorter firing cooldown |
| Shield | One additional hit of protection at the start of each level |
| Pulse | One additional pulse charge per level |

Each upgrade caps at rank 3. Choosing a capped upgrade restores one life, up to six.
Upgrade ranks last for the current run. Temporary pickups and combos reset between
levels. **Only the high score is saved** in `.hiscore`; new runs start at level 1.

## Algorithm guidance

| Algorithm | Method | On-screen advice |
| --- | --- | --- |
| Hill Climbing | Compare the current position with its immediate neighbors | A nearby position with lower predicted bomb risk, or hold advice |
| A* | Prioritize states using elapsed steps plus estimated remaining distance | A horizontal route toward target alignment |
| BFS | Explore states layer by layer using a queue | The shallowest reachable position predicted safe to hold briefly |
| DFS | Explore a branch using a stack, then backtrack as needed | A possible six-step movement sequence |

The colored track shows suggested horizontal positions. **L**, **R** and **-** mean
left, right and wait. The dotted A* line indicates target alignment, not vertical
flight. The HUD reports the suggested action, search size and calculation time.

Guides refresh approximately every 0.12 seconds. A* and BFS search up to 28 steps
with a 1,600-node limit; DFS searches six steps. One planned step represents 24
pixels over 0.075 seconds. Searches use current bombs, bunker pixels and scheduled
warning lanes. Future attacks or moving targets can invalidate advice; partial
and unavailable routes are labeled explicitly.

### Algorithm lab

Press **C** to freeze the game and compare all four algorithms on the same
situation. The table shows each suggestion, nodes examined, calculation time and
route length.

| Key | Lab action |
| --- | --- |
| 1–4 | Inspect an algorithm |
| N | Reveal the next search expansion or evaluation |
| A | Reveal the full search and selected route |
| R | Reset the search replay |
| C / ESC | Return to the previous playing or paused state |

The plot uses ship position horizontally and future step vertically. Gray points
are explored states, yellow marks the latest state, and green shows the chosen
route once the replay finishes. This replays a completed search; it does not
advance gameplay. Timing comparisons measure local computation, not playing
ability—the algorithms solve different objectives.

## Project files

| File | Purpose |
| --- | --- |
| `main.py` | Game loop, controls, collisions, progression and HUD |
| `campaign.py` | Level definitions, difficulty settings and bosses |
| `entities.py` | Player, invaders, projectiles, bunkers and UFO |
| `ai_agent.py` | World model, four guidance algorithms and search traces |
| `comparison.py` | Frozen comparison lab and search replay |
| `effects.py` | Starfield, particles and supply pickups |
| `sprites.py` / `sounds.py` | Code-generated pixel art and synthesized audio |
| `settings.py` | Display, movement, scoring and other gameplay constants |
| `requirements.txt` | Runtime dependency: `pygame-ce>=2.5` |
| `test_*.py` | Headless regression and smoke tests |

## Tests

```bash
python -m unittest test_campaign.py test_guidance.py test_combat.py
python test_smoke.py
```

Tests use dummy video and audio drivers, so no game window is required. They cover
campaign progression, bosses, combat upgrades, manual control, guidance, the lab
and rendering. Test saves are isolated from the player's high score.

---

The previous README is preserved in [docs/archive/README.previous.md](docs/archive/README.previous.md).
