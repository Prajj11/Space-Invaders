"""
AI Autopilot Agents for Space Invaders.

Implements four foundational search algorithms for game playing:
1. Hill Climbing  — Local heuristic search (greedy evaluation of immediate moves)
2. A* Search      — Informed heuristic search (optimal path planning minimizing f = g + h)
3. BFS            — Breadth-First Search (shallowest-path layer-by-layer exploration)
4. DFS            — Depth-First Search (deep-horizon survival path check with backtracking)

Each agent inspects the game state (player, falling bombs, bunkers, invaders, UFO)
and returns:
  - move_dir: -1 (LEFT), 0 (STAY), +1 (RIGHT)
  - shoot: bool (whether to fire)
  - telemetry: dict of performance stats (nodes expanded, search depth, compute time)
"""

import collections
import heapq
import time
from typing import Dict, List, Optional, Tuple

from settings import (
    BOMB_SPEED,
    MAX_X,
    MIN_X,
    PLAYER_SPEED,
    PLAYER_Y,
    SHIELD_Y,
    WIDTH,
)

# Discrete simulation parameters for planning
MOVE_STEP_PX = 24       # Horizontal movement per discrete search step
SEARCH_HORIZON = 6      # Lookahead steps (approx 0.45 - 0.5s horizon)
DANGER_MARGIN = 26      # Horizontal proximity to a falling bomb considered dangerous
TARGET_ALIGN_TOL = 12   # Pixel tolerance to trigger firing at target


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
    bomb_speed = BOMB_SPEED * (1.0 + 0.08 * (game.wave - 1))

    # Extract falling bombs: (bomb_center_x, time_to_reach_player_y, is_shielded)
    bombs = []
    for b in game.bombs:
        dist_y = PLAYER_Y - b.rect.bottom
        if dist_y > 0:
            time_to_hit = dist_y / max(1.0, bomb_speed)
            # Check if this bomb will hit an intact bunker shield first
            shielded = False
            for shield in game.shields:
                if shield.rect.left <= b.rect.centerx <= shield.rect.right:
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

    # Sort targets descending by priority
    targets.sort(key=lambda t: t["priority"], reverse=True)

    # Intact shield spans for player cover
    shield_spans = []
    for s in game.shields:
        shield_spans.append((s.rect.left, s.rect.right))

    return {
        "player_x": player_x,
        "player_w": player_w,
        "can_shoot": game.player.can_shoot() and len(game.bullets) == 0,
        "bombs": bombs,
        "targets": targets,
        "shield_spans": shield_spans,
        "shields": game.shields,
    }


def is_in_danger(x: float, step: int, bombs: List[Dict], dt_step: float = 0.08) -> float:
    """
    Computes danger penalty at position x at future step k.
    Returns 0.0 if safe, or a positive threat penalty.
    """
    future_time = step * dt_step
    threat = 0.0
    for b in bombs:
        # Time remaining until this bomb reaches the player's cannon row
        t_hit = b["time_to_hit"]
        # If the bomb hits around this time step
        if abs(t_hit - future_time) < 0.18:
            dist = abs(x - b["x"])
            if dist < DANGER_MARGIN:
                if b["shielded"]:
                    threat += 40.0 / (1.0 + dist)
                else:
                    # Lethal threat from unshielded bomb
                    threat += 1000.0 / (1.0 + dist)
        # Spatial danger: bomb is already close vertically
        elif t_hit < future_time and abs(t_hit - future_time) < 0.35:
            dist = abs(x - b["x"])
            if dist < DANGER_MARGIN and not b["shielded"]:
                threat += 500.0 / (1.0 + dist)
    return threat


def is_shield_blocking(x: float, shields) -> bool:
    """Checks whether firing from position x will directly hit an intact bunker."""
    for s in shields:
        if s.rect.left <= x <= s.rect.right:
            ox = int(x - s.rect.x)
            if 0 <= ox < s.w and s._opaque_in(ox - 3, 0, ox + 3, s.h):
                return True
    return False


def clamp_x(x: float) -> float:
    """Ensures player position stays within playfield walls."""
    return max(MIN_X + 16, min(MAX_X - 16, x))


# -----------------------------------------------------------------------------
# Base Agent Class
# -----------------------------------------------------------------------------
class BaseAgent:
    name: str = "Base Agent"
    short_name: str = "BASE"

    def decide(self, game) -> Tuple[int, bool, Dict]:
        """
        Returns (move_dir, should_shoot, telemetry_dict).
        move_dir: -1 (left), 0 (stay), 1 (right)
        should_shoot: True or False
        """
        raise NotImplementedError


# -----------------------------------------------------------------------------
# 1. Hill Climbing Agent (Local Heuristic Search)
# -----------------------------------------------------------------------------
class HillClimbingAgent(BaseAgent):
    """
    Hill Climbing: Greedy local search.
    Evaluates immediate neighbors {LEFT, STAY, RIGHT} using a heuristic evaluation
    function and climbs toward the local state with the highest score.
    """
    name: str = "Hill Climbing (Local Search)"
    short_name: str = "HILL CLIMB"

    def evaluate_state(self, x: float, world: Dict) -> float:
        score = 0.0

        # 1. Safety from bombs (major penalty for danger)
        threat = is_in_danger(x, 1, world["bombs"])
        score -= threat * 2.5

        # 2. Target alignment bonus
        if world["targets"]:
            primary = world["targets"][0]
            dist_to_target = abs(x - primary["x"])
            # Alignment reward
            if dist_to_target <= TARGET_ALIGN_TOL:
                score += 250.0
            else:
                score -= dist_to_target * 0.85

        # 3. Shield cover bonus during heavy bomb rain
        if world["bombs"]:
            for left, right in world["shield_spans"]:
                if left <= x <= right:
                    score += 15.0

        # 4. Wall avoidance penalty (avoid getting cornered)
        if x <= MIN_X + 30 or x >= MAX_X - 30:
            score -= 40.0

        return score

    def decide(self, game) -> Tuple[int, bool, Dict]:
        t0 = time.perf_counter()
        world = get_world_model(game)
        cur_x = world["player_x"]

        # Neighbors: STAY, LEFT, RIGHT
        actions = [
            (0, clamp_x(cur_x)),
            (-1, clamp_x(cur_x - MOVE_STEP_PX)),
            (1, clamp_x(cur_x + MOVE_STEP_PX)),
        ]

        best_score = -float("inf")
        best_dir = 0
        nodes_evaluated = 0

        for move_dir, nx in actions:
            nodes_evaluated += 1
            score = self.evaluate_state(nx, world)
            if score > best_score:
                best_score = score
                best_dir = move_dir

        # Decide whether to shoot
        should_shoot = False
        if world["can_shoot"] and world["targets"]:
            primary = world["targets"][0]
            if abs(cur_x - primary["x"]) <= TARGET_ALIGN_TOL + 4:
                # Shoot if unobstructed or if target is below shield
                if not is_shield_blocking(cur_x, world["shields"]) or primary["y"] > SHIELD_Y:
                    should_shoot = True

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        telemetry = {
            "algorithm": self.name,
            "nodes": nodes_evaluated,
            "depth": 1,
            "time_ms": elapsed_ms,
            "eval_score": round(best_score, 1),
            "action": "LEFT" if best_dir == -1 else ("RIGHT" if best_dir == 1 else "STAY"),
        }
        return best_dir, should_shoot, telemetry


# -----------------------------------------------------------------------------
# 2. A* Search Agent (Optimal Informed Heuristic Search)
# -----------------------------------------------------------------------------
class AStarAgent(BaseAgent):
    """
    A* Search: Finds the optimal trajectory over a time horizon by minimizing:
      f(n) = g(n) + h(n)
    where:
      g(n) = path cost (movement effort + accumulated danger along path)
      h(n) = heuristic estimate (danger risk + distance to optimal target alignment)
    """
    name: str = "A* Search (Informed Search)"
    short_name: str = "A* SEARCH"

    def heuristic(self, x: float, step: int, world: Dict) -> float:
        h = 0.0
        # Danger heuristic
        threat = is_in_danger(x, step, world["bombs"])
        h += threat * 3.0

        # Distance to best target alignment
        if world["targets"]:
            primary = world["targets"][0]
            dist = abs(x - primary["x"])
            h += (dist / float(WIDTH)) * 120.0
            if dist > TARGET_ALIGN_TOL:
                h += 30.0

        # Penalty for wall proximity
        if x <= MIN_X + 25 or x >= MAX_X - 25:
            h += 35.0

        return h

    def decide(self, game) -> Tuple[int, bool, Dict]:
        t0 = time.perf_counter()
        world = get_world_model(game)
        start_x = world["player_x"]

        # Priority queue entries: (f, g, counter, current_x, step, path)
        open_set = []
        counter = 0

        h0 = self.heuristic(start_x, 0, world)
        heapq.heappush(open_set, (h0, 0.0, counter, start_x, 0, []))

        best_path = []
        best_leaf_f = float("inf")
        nodes_expanded = 0
        visited = set()

        while open_set and nodes_expanded < 75:
            f, g, _, cx, step, path = heapq.heappop(open_set)
            nodes_expanded += 1

            state_key = (round(cx / 10.0), step)
            if state_key in visited:
                continue
            visited.add(state_key)

            # Horizon reached
            if step >= SEARCH_HORIZON:
                if f < best_leaf_f:
                    best_leaf_f = f
                    best_path = path
                break

            # Expand successors: STAY, LEFT, RIGHT
            for move_dir in (0, -1, 1):
                nx = clamp_x(cx + move_dir * MOVE_STEP_PX)
                threat = is_in_danger(nx, step + 1, world["bombs"])

                # Prune instantly lethal transitions
                if threat >= 900.0:
                    continue

                # Transition cost: step penalty + danger cost + direction switch cost
                step_cost = 4.0 + threat * 2.0
                if path and path[-1] != move_dir:
                    step_cost += 2.0  # Encourage smooth motion

                new_g = g + step_cost
                new_h = self.heuristic(nx, step + 1, world)
                new_f = new_g + new_h

                counter += 1
                heapq.heappush(open_set, (new_f, new_g, counter, nx, step + 1, path + [move_dir]))

        # Extract first action of planned path
        chosen_dir = best_path[0] if best_path else 0

        # Shooting logic
        should_shoot = False
        if world["can_shoot"] and world["targets"]:
            primary = world["targets"][0]
            if abs(start_x - primary["x"]) <= TARGET_ALIGN_TOL + 4:
                if not is_shield_blocking(start_x, world["shields"]) or primary["y"] > SHIELD_Y:
                    should_shoot = True

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        telemetry = {
            "algorithm": self.name,
            "nodes": nodes_expanded,
            "depth": len(best_path) if best_path else SEARCH_HORIZON,
            "time_ms": elapsed_ms,
            "eval_score": round(best_leaf_f, 1) if best_leaf_f != float("inf") else 0.0,
            "action": "LEFT" if chosen_dir == -1 else ("RIGHT" if chosen_dir == 1 else "STAY"),
        }
        return chosen_dir, should_shoot, telemetry


# -----------------------------------------------------------------------------
# 3. Breadth-First Search Agent (BFS - Shortest-Path Exploration)
# -----------------------------------------------------------------------------
class BFSAgent(BaseAgent):
    """
    Breadth-First Search (BFS): Explores moves layer-by-layer up to horizon D.
    Guarantees finding the shallowest, shortest sequence of moves to a safe
    shooting corridor while avoiding bomb paths.
    """
    name: str = "Breadth-First Search (BFS)"
    short_name: str = "BFS"

    def decide(self, game) -> Tuple[int, bool, Dict]:
        t0 = time.perf_counter()
        world = get_world_model(game)
        start_x = world["player_x"]

        # Queue items: (current_x, step, path)
        queue = collections.deque([(start_x, 0, [])])
        visited = set()

        nodes_expanded = 0
        best_path = []
        safest_leaf_path = []
        min_danger = float("inf")

        while queue and nodes_expanded < 120:
            cx, step, path = queue.popleft()
            nodes_expanded += 1

            state_key = (round(cx / 12.0), step)
            if state_key in visited:
                continue
            visited.add(state_key)

            threat = is_in_danger(cx, step, world["bombs"])

            # Goal check: Safe state aligned with high-priority target
            if world["targets"]:
                primary = world["targets"][0]
                if abs(cx - primary["x"]) <= TARGET_ALIGN_TOL and threat == 0.0 and step > 0:
                    best_path = path
                    break

            # Track safest leaf if explicit goal not met early
            if step >= SEARCH_HORIZON:
                total_threat = threat
                if world["targets"]:
                    total_threat += abs(cx - world["targets"][0]["x"]) * 0.5
                if total_threat < min_danger:
                    min_danger = total_threat
                    safest_leaf_path = path
                continue

            # Branch out: STAY, LEFT, RIGHT
            for move_dir in (0, -1, 1):
                nx = clamp_x(cx + move_dir * MOVE_STEP_PX)
                next_threat = is_in_danger(nx, step + 1, world["bombs"])
                if next_threat < 900.0:  # Prune lethal branches
                    queue.append((nx, step + 1, path + [move_dir]))

        chosen_path = best_path or safest_leaf_path
        chosen_dir = chosen_path[0] if chosen_path else 0

        # Shooting logic
        should_shoot = False
        if world["can_shoot"] and world["targets"]:
            primary = world["targets"][0]
            if abs(start_x - primary["x"]) <= TARGET_ALIGN_TOL + 4:
                if not is_shield_blocking(start_x, world["shields"]) or primary["y"] > SHIELD_Y:
                    should_shoot = True

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        telemetry = {
            "algorithm": self.name,
            "nodes": nodes_expanded,
            "depth": len(chosen_path) if chosen_path else SEARCH_HORIZON,
            "time_ms": elapsed_ms,
            "eval_score": round(min_danger, 1) if min_danger != float("inf") else 0.0,
            "action": "LEFT" if chosen_dir == -1 else ("RIGHT" if chosen_dir == 1 else "STAY"),
        }
        return chosen_dir, should_shoot, telemetry


# -----------------------------------------------------------------------------
# 4. Depth-First Search Agent (DFS - Deep Survival Path Exploration)
# -----------------------------------------------------------------------------
class DFSAgent(BaseAgent):
    """
    Depth-First Search (DFS): Explores deep movement paths up to horizon D
    before backtracking. Rapidly checks if a survival path exists under heavy bombing.
    """
    name: str = "Depth-First Search (DFS)"
    short_name: str = "DFS"

    def decide(self, game) -> Tuple[int, bool, Dict]:
        t0 = time.perf_counter()
        world = get_world_model(game)
        start_x = world["player_x"]

        # Stack items: (current_x, step, path)
        stack = [(start_x, 0, [])]
        visited = set()

        nodes_expanded = 0
        backtracks = 0
        surviving_path = []

        # Order moves biased toward target to avoid pathological DFS wandering
        bias_dir = 0
        if world["targets"]:
            tx = world["targets"][0]["x"]
            if tx > start_x + 10:
                bias_dir = 1
            elif tx < start_x - 10:
                bias_dir = -1

        # Move ordering for stack (pushed in reverse of desired pop order)
        move_order = [bias_dir, 0, -bias_dir if bias_dir != 0 else -1]
        # Remove duplicates while preserving order
        ordered_moves = []
        for m in move_order:
            if m not in ordered_moves:
                ordered_moves.append(m)

        while stack and nodes_expanded < 100:
            cx, step, path = stack.pop()
            nodes_expanded += 1

            state_key = (round(cx / 14.0), step)
            if state_key in visited:
                continue
            visited.add(state_key)

            threat = is_in_danger(cx, step, world["bombs"])
            if threat >= 900.0:
                backtracks += 1
                continue

            # Target alignment goal or maximum search depth reached safely
            if step >= SEARCH_HORIZON:
                surviving_path = path
                break

            # Push successors onto LIFO stack
            for move_dir in reversed(ordered_moves):
                nx = clamp_x(cx + move_dir * MOVE_STEP_PX)
                next_threat = is_in_danger(nx, step + 1, world["bombs"])
                if next_threat < 900.0:
                    stack.append((nx, step + 1, path + [move_dir]))

        chosen_dir = surviving_path[0] if surviving_path else 0

        # Shooting logic
        should_shoot = False
        if world["can_shoot"] and world["targets"]:
            primary = world["targets"][0]
            if abs(start_x - primary["x"]) <= TARGET_ALIGN_TOL + 4:
                if not is_shield_blocking(start_x, world["shields"]) or primary["y"] > SHIELD_Y:
                    should_shoot = True

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        telemetry = {
            "algorithm": self.name,
            "nodes": nodes_expanded,
            "depth": len(surviving_path) if surviving_path else SEARCH_HORIZON,
            "time_ms": elapsed_ms,
            "backtracks": backtracks,
            "action": "LEFT" if chosen_dir == -1 else ("RIGHT" if chosen_dir == 1 else "STAY"),
        }
        return chosen_dir, should_shoot, telemetry


# -----------------------------------------------------------------------------
# Agent Registry & Factory
# -----------------------------------------------------------------------------
AGENTS = {
    0: ("Manual (Human)", None),
    1: ("Hill Climbing", HillClimbingAgent()),
    2: ("A* Search", AStarAgent()),
    3: ("BFS", BFSAgent()),
    4: ("DFS", DFSAgent()),
}
