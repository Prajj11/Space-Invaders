"""Read-only movement guidance using four classical search algorithms.

Plans are horizontal positions over time, not vertical flight paths. Predictions
use current bombs and bunker pixels; future enemy fire is unknown.
"""
import collections
import heapq
import time
from typing import Dict

from settings import (
    BOMB_SPEED,
    MAX_X,
    MIN_X,
    PLAYER_SPEED,
    PLAYER_Y,
    SHIELD_Y,
)

# Discrete simulation parameters for planning
MOVE_STEP_PX = 24       # Horizontal movement per discrete search step
SEARCH_HORIZON = 6      # Lookahead steps (approx 0.45 - 0.5s horizon)
TARGET_ALIGN_TOL = 12   # Horizontal tolerance for suggested target alignment


# -----------------------------------------------------------------------------
# World Perception & State Extraction
# -----------------------------------------------------------------------------
def get_world_model(game) -> Dict:
    """
    Extracts a lightweight snapshot of the game state for search algorithms.
    """
    player_x = game.player.rect.centerx
    player_w = game.player.rect.w

    # Calculate actual falling bomb speed for current wave
    bomb_speed = game._bomb_speed()

    # Extract falling bombs: (bomb_center_x, time_to_reach_player_y, is_shielded)
    bombs = []
    for b in game.bombs:
        dist_y = PLAYER_Y - b.rect.bottom
        if dist_y > 0:
            time_to_hit = dist_y / max(1.0, bomb_speed * b.speed_scale)
            # Check if this bomb will hit an intact bunker shield first
            shielded = False
            for shield in game.shields:
                if (b.rect.bottom <= shield.rect.top
                        and shield.rect.left <= b.rect.centerx <= shield.rect.right):
                    # Check if the shield has opaque pixels in this column
                    ox = b.rect.centerx - shield.rect.x
                    if 0 <= ox < shield.w and shield._opaque_in(ox - 4, 0, ox + 4, shield.h):
                        shielded = True
                        break
            bombs.append({
                "x": b.rect.centerx,
                "y": b.rect.bottom,
                "time_to_hit": time_to_hit,
                "shielded": shielded,
            })

    # Include telegraphed attacks that are already scheduled.
    for warning in getattr(game, "warnings", []):
        source = warning["source"]
        if source is not None and not source.alive:
            continue
        travel = max(0, PLAYER_Y - warning["y"]) / (bomb_speed * warning["speed_scale"])
        bombs.append({"x": warning["x"], "y": warning["y"],
                      "time_to_hit": warning["timer"] + travel, "shielded": False})

    # Extract candidate targets: UFO takes highest priority, followed by lowest aliens
    targets = []
    if game.ufo is not None:
        targets.append({
            "x": game.ufo.rect.centerx,
            "y": game.ufo.rect.bottom,
            "priority": 500.0,
            "kind": "ufo",
        })

    # Group alive aliens by column to identify lowest alien per column
    col_map = collections.defaultdict(list)
    for a in game.grid.aliens:
        if a.alive:
            col_map[a.col].append(a)

    for col, aliens in col_map.items():
        lowest = max(aliens, key=lambda a: a.rect.bottom)
        # Closer to invasion floor = higher urgency
        urgency = 100.0 + (lowest.rect.bottom / float(PLAYER_Y)) * 150.0
        # Center columns slightly favored for cluster disruption
        center_bias = 20.0 - abs(col - 5) * 2.0
        targets.append({
            "x": lowest.rect.centerx,
            "y": lowest.rect.bottom,
            "priority": urgency + center_bias,
            "kind": lowest.kind,
        })

    if getattr(game, "boss", None):
        targets.append({"x": game.boss.core.centerx, "y": game.boss.rect.bottom,
                        "priority": 700.0, "kind": "boss"})
    selected = getattr(game, "selected_target", None)
    if selected is not None and getattr(selected, "alive", True):
        targets.insert(0, {"x": selected.rect.centerx, "y": selected.rect.bottom,
                           "priority": 1000.0, "kind": "selected"})

    # Sort targets descending by priority
    targets.sort(key=lambda t: t["priority"], reverse=True)

    # Intact shield spans for player cover
    shield_spans = []
    for s in game.shields:
        shield_spans.append((s.rect.left, s.rect.right))

    return {
        "player_x": player_x,
        "player_w": player_w,
        "can_shoot": game.player.can_shoot() and len(game.bullets) < (4 if game.rapid_timer > 0 else 1),
        "bombs": bombs,
        "targets": targets,
        "shield_spans": shield_spans,
        "shields": game.shields,
    }


def is_shield_blocking(x: float, shields) -> bool:
    """Checks whether firing from position x will directly hit an intact bunker."""
    for s in shields:
        if s.rect.left <= x <= s.rect.right:
            ox = int(x - s.rect.x)
            if 0 <= ox < s.w and s._opaque_in(ox - 3, 0, ox + 3, s.h):
                return True
    return False


STEP_SECONDS = MOVE_STEP_PX / PLAYER_SPEED
PLAN_DEPTH = 28
NODE_LIMIT = 1600


def bounded(x, world):
    left_half = world["player_w"] // 2
    right_half = world["player_w"] - left_half
    return max(MIN_X + left_half, min(MAX_X - right_half, x))


def risk(x, seconds, world):
    """Conservative collision window, including cannon and bomb widths."""
    return sum(1 for b in world["bombs"] if not b["shielded"]
               and abs(b["time_to_hit"] - seconds) < .18
               and abs(b["x"] - x) < world["player_w"] / 2 + 8)


def safe_transition(x, nx, step, world):
    # Sample along the move, so crossing a bomb lane is checked too.
    return all(not risk(x + (nx - x) * fraction,
                        (step + fraction) * STEP_SECONDS, world)
               for fraction in (.25, .5, .75, 1))


def safe_to_hold(x, step, world):
    return all(not risk(x, step * STEP_SECONDS + i * .075, world)
               for i in range(9))


class BaseAgent:
    """Computes suggestions only. Never changes game state or input."""
    def decide(self, game):
        return self.analyze(get_world_model(game))

    def analyze(self, world):
        started = time.perf_counter()
        world = dict(world)
        world["trace"] = []
        path, nodes, status = self.plan(world)
        positions = [world["player_x"]]
        for action in path:
            positions.append(bounded(positions[-1] + action * MOVE_STEP_PX, world))
        direction = path[0] if path else 0
        return direction, False, {
            "nodes": nodes, "depth": len(path), "path": path,
            "trace": world["trace"],
            "positions": positions, "target": world["targets"][0] if world["targets"] else None,
            "bombs": world["bombs"], "status": status,
            "time_ms": (time.perf_counter() - started) * 1000,
            "action": "NONE" if status.startswith("No ") else {-1: "LEFT", 0: "HOLD", 1: "RIGHT"}[direction],
        }


class HillClimbingAgent(BaseAgent):
    def plan(self, world):
        x = world["player_x"]
        def cost(nx):
            return sum(risk(nx, i * .075, world) for i in range(9)) + sum(
                1 / (1 + abs(nx - b["x"])) for b in world["bombs"]
                if not b["shielded"] and 0 <= b["time_to_hit"] <= .6)
        world.setdefault("trace", []).append((x, 0))
        current = cost(x)
        best, best_cost = 0, current
        for move in (-1, 1):
            nx = bounded(x + move * MOVE_STEP_PX, world)
            world["trace"].append((nx, 1))
            value = cost(nx)
            if safe_transition(x, nx, 0, world) and value < best_cost:
                best, best_cost = move, value
        status = "Safer nearby position" if best else (
            "Hold: no nearby threat" if current == 0 else "No safer neighbor found")
        return [best], 3, status


class AStarAgent(BaseAgent):
    def plan(self, world):
        if not world["targets"]:
            return [], 0, "No target available"
        target = world["targets"][0]
        def heuristic(x):
            return max(0, abs(x - target["x"]) - TARGET_ALIGN_TOL) / MOVE_STEP_PX
        start = world["player_x"]
        queue = [(heuristic(start), 0, start, [])]
        visited = set()
        nodes = 0
        partial, closest = [], heuristic(start)
        while queue and nodes < NODE_LIMIT:
            _, step, x, path = heapq.heappop(queue)
            key = (x, step)
            if key in visited:
                continue
            visited.add(key)
            nodes += 1
            world.setdefault("trace", []).append((x, step))
            h = heuristic(x)
            if h < closest:
                closest, partial = h, path
            if h == 0 and safe_to_hold(x, step, world):
                blocked = target["y"] <= SHIELD_Y and is_shield_blocking(x, world["shields"])
                return path, nodes, "Target aligned; bunker blocks shot" if blocked else "Route to target alignment"
            if step >= PLAN_DEPTH:
                continue
            for move in (0, -1, 1):
                nx = bounded(x + move * MOVE_STEP_PX, world)
                if safe_transition(x, nx, step, world):
                    heapq.heappush(queue, (step + 1 + heuristic(nx), step + 1, nx, path + [move]))
        return partial, nodes, "Partial route only" if partial else "No route found within search limit"


class BFSAgent(BaseAgent):
    def plan(self, world):
        queue = collections.deque([(world["player_x"], 0, [])])
        visited = set()
        nodes = 0
        while queue and nodes < NODE_LIMIT:
            x, step, path = queue.popleft()
            if (x, step) in visited:
                continue
            visited.add((x, step))
            nodes += 1
            world.setdefault("trace", []).append((x, step))
            if safe_to_hold(x, step, world):
                return path, nodes, "Nearest safe position" if path else "Current position is safe"
            if step >= PLAN_DEPTH:
                continue
            for move in (0, -1, 1):
                nx = bounded(x + move * MOVE_STEP_PX, world)
                if safe_transition(x, nx, step, world):
                    queue.append((nx, step + 1, path + [move]))
        return [], nodes, "No safe position found within search limit"


class DFSAgent(BaseAgent):
    def plan(self, world):
        stack = [(world["player_x"], 0, [])]
        visited = set()
        nodes = 0
        while stack and nodes < NODE_LIMIT:
            x, step, path = stack.pop()
            if (x, step) in visited:
                continue
            visited.add((x, step))
            nodes += 1
            world.setdefault("trace", []).append((x, step))
            if step >= SEARCH_HORIZON:
                return path, nodes, "Possible move sequence"
            target_x = world["targets"][0]["x"] if world["targets"] else x
            moves = sorted((0, -1, 1), key=lambda m: abs(x + m * MOVE_STEP_PX - target_x))
            for move in reversed(moves):
                nx = bounded(x + move * MOVE_STEP_PX, world)
                if safe_transition(x, nx, step, world):
                    stack.append((nx, step + 1, path + [move]))
        return [], nodes, "No sequence found within search limit"


AGENTS = {
    0: ("Guidance off", None),
    1: ("Hill Climbing", HillClimbingAgent()),
    2: ("A* Search", AStarAgent()),
    3: ("BFS", BFSAgent()),
    4: ("DFS", DFSAgent()),
}
