# src/systems/ghost_system.py

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import os
import json
import pygame


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def clamp(v: float, a: float, b: float) -> float:
    return a if v < a else b if v > b else v


class GhostSystem:
    """
    Записва и възпроизвежда ghost run (best time) за даден user + level.

    Съхранява:
      - t: seconds from start
      - d: distance along track
      - lane: normalized lateral position vs road half-width (-1..1)
      - dir: -1/0/1 (sprite choice)

    Рисува ghost car в перспектива (като obstacle), използвайки dist_ahead = ghost_d - player_distance.
    """

    def __init__(
        self,
        *,
        base_dir: str,
        username: str,
        level: int,
        car_back: pygame.Surface,
        car_left: pygame.Surface,
        car_right: pygame.Surface,
        enabled: bool = True,
        sample_dt: float = 1.0 / 30.0,
        view_depth: float = 1200.0,
        alpha: int = 120,
    ):
        self.enabled = enabled
        self.base_dir = base_dir
        self.username = username or "Player"
        self.level = int(level)

        self.sample_dt = float(sample_dt)
        self.view_depth = float(view_depth)
        self.alpha = int(alpha)

        self.car_back = car_back
        self.car_left = car_left
        self.car_right = car_right

        self._scale_cache: Dict[Tuple[str, int], pygame.Surface] = {}
        self._record: List[dict] = []
        self._accum = 0.0

        self._ghost_data: Optional[dict] = None
        self._samples: List[dict] = []
        self._play_i = 0

        if not self.enabled:
            return

        os.makedirs(self._user_dir(), exist_ok=True)
        self._load_if_exists()

    # ---------- paths ----------

    def _user_dir(self) -> str:
        return os.path.join(self.base_dir, self.username)

    def _ghost_path(self) -> str:
        return os.path.join(self._user_dir(), f"level_{self.level}.json")

    # ---------- load/save ----------

    def _load_if_exists(self) -> None:
        path = self._ghost_path()
        if not os.path.exists(path):
            self._ghost_data = None
            self._samples = []
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            samples = data.get("samples", [])
            if not isinstance(samples, list) or len(samples) < 2:
                self._ghost_data = None
                self._samples = []
                return

            self._ghost_data = data
            self._samples = samples
            self._play_i = 0
        except Exception:
            self._ghost_data = None
            self._samples = []

    def save_recording_as_best(self, finish_time: float) -> None:
        if not self.enabled or len(self._record) < 2:
            return

        data = {
            "version": 1,
            "username": self.username,
            "level": self.level,
            "best_time": round(float(finish_time), 3),
            "samples": self._record,
        }

        path = self._ghost_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Immediately load it for instant replay on restart
        self._ghost_data = data
        self._samples = data["samples"]
        self._play_i = 0

    def get_best_time(self) -> Optional[float]:
        if not self._ghost_data:
            return None
        bt = self._ghost_data.get("best_time")
        try:
            return float(bt)
        except Exception:
            return None

    # ---------- recording ----------

    def start_run(self) -> None:
        self._record = []
        self._accum = 0.0
        self._play_i = 0

    def record(
        self,
        *,
        dt: float,
        t: float,
        distance: float,
        lane: float,
        dir: int,
    ) -> None:
        if not self.enabled:
            return

        self._accum += float(dt)
        if self._accum < self.sample_dt:
            return

        # keep stable cadence
        while self._accum >= self.sample_dt:
            self._accum -= self.sample_dt

        lane = clamp(float(lane), -1.0, 1.0)
        dir = -1 if dir < 0 else 1 if dir > 0 else 0

        self._record.append({
            "t": round(float(t), 3),
            "d": round(float(distance), 3),
            "lane": round(lane, 4),
            "dir": dir,
        })

    # ---------- playback ----------

    def _sample_at_time(self, t: float) -> Optional[dict]:
        if not self._samples:
            return None

        if t <= self._samples[0]["t"]:
            return self._samples[0]
        if t >= self._samples[-1]["t"]:
            return self._samples[-1]

        # advance pointer
        while self._play_i + 1 < len(self._samples) and self._samples[self._play_i + 1]["t"] <= t:
            self._play_i += 1

        a = self._samples[self._play_i]
        b = self._samples[self._play_i + 1]

        ta = float(a["t"])
        tb = float(b["t"])
        if tb <= ta:
            return a

        u = (t - ta) / (tb - ta)
        u = clamp(u, 0.0, 1.0)

        d = lerp(float(a["d"]), float(b["d"]), u)
        lane = lerp(float(a["lane"]), float(b["lane"]), u)

        # dir: take closer one
        dir_val = a.get("dir", 0) if u < 0.5 else b.get("dir", 0)
        dir_val = -1 if dir_val < 0 else 1 if dir_val > 0 else 0

        return {"t": t, "d": d, "lane": lane, "dir": dir_val}

    def _scaled_sprite(self, kind: str, base: pygame.Surface, scale: float) -> pygame.Surface:
        key = (kind, int(scale * 100))
        if key in self._scale_cache:
            return self._scale_cache[key]

        w = max(1, int(base.get_width() * scale))
        h = max(1, int(base.get_height() * scale))
        spr = pygame.transform.smoothscale(base, (w, h)).convert_alpha()
        spr.set_alpha(self.alpha)
        self._scale_cache[key] = spr
        return spr

    def draw(
        self,
        screen: pygame.Surface,
        *,
        t: float,
        player_distance: float,
        track_center_fn,
        top_y: int,
        bottom_y: int,
        gamma: float,
        screen_w: int,
        screen_h: int,
        road_width_far: float,
        road_width_near: float,
    ) -> None:
        if not self.enabled or not self._samples:
            return

        s = self._sample_at_time(float(t))
        if not s:
            return

        ghost_d = float(s["d"])
        lane = float(s["lane"])
        dir_val = int(s.get("dir", 0))

        dist_ahead = ghost_d - float(player_distance)

        # If ghost is behind camera, you can skip it (cleaner)
        if dist_ahead <= 0:
            return

        if dist_ahead > self.view_depth:
            return

        height = bottom_y - top_y

        # same perspective mapping as obstacles
        tt = dist_ahead / self.view_depth
        z_screen = 1.0 - tt
        depth = (z_screen ** float(gamma))  # 0..1

        y = int(top_y + depth * height)

        road_w = int(lerp(float(road_width_far), float(road_width_near), depth) * screen_w)
        road_half = road_w * 0.5

        cx = int(track_center_fn(depth))
        x = int(cx + lane * road_half * 0.92)

        # choose sprite
        base = self.car_back
        kind = "back"
        if dir_val < 0:
            base = self.car_left
            kind = "left"
        elif dir_val > 0:
            base = self.car_right
            kind = "right"

        # scale by depth
        scale = lerp(0.18, 1.00, depth)
        spr = self._scaled_sprite(kind, base, scale)

        rect = spr.get_rect(midbottom=(x, y))
        screen.blit(spr, rect)
