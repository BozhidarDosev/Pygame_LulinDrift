from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import os
import random
import pygame


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class ObstaclesSystem:
    """
    Obstacles placed on the road
    Draw + collision in screen-space
    """
    def __init__(
        self,
        level_path: str,
        *,
        enabled: bool = True,
        seed: int = 9001,
        track_length: float = 9000.0,
        view_depth: float = 800.0,
        count: int = 14,
        min_gap: float = 260.0,
        lane_width: float = 0.62,   # how much of the road width obstacles can use (0..1)
        collision_window: float = 90.0,
    ):
        self.enabled = enabled
        self.track_length = float(track_length)
        self.view_depth = float(view_depth)
        self.collision_window = float(collision_window)
        self.lane_width = float(lane_width)

        self.images: Dict[str, pygame.Surface] = {}
        self._cache: Dict[Tuple[str, int], pygame.Surface] = {}

        self.obstacles: List[dict] = []

        if not enabled:
            return

        obstacles_dir = os.path.join(level_path, "obstacles")
        props_dir = os.path.join(level_path, "props")

        candidates = [
            ("rock1", os.path.join(obstacles_dir, "rock1.png")),
            ("rock2", os.path.join(obstacles_dir, "rock2.png")),
            ("bush",  os.path.join(obstacles_dir, "bush.png")),
            ("rock1", os.path.join(props_dir, "rock1.png")),
            ("rock2", os.path.join(props_dir, "rock2.png")),
        ]

        for name, path in candidates:
            if name not in self.images and os.path.exists(path):
                self.images[name] = pygame.image.load(path).convert_alpha()

        if not self.images:
            # No images -> disable cleanly
            self.enabled = False
            return

        rng = random.Random(seed)
        kinds = list(self.images.keys())

        # Spawn z positions with min spacing, within track
        z_list: List[float] = []
        attempts = 0
        while len(z_list) < count and attempts < count * 50:
            attempts += 1
            safe_start = 900.0  # няма препятствия в първите 900 units
            safe_end_margin = 600.0
            z = rng.uniform(safe_start, max(safe_start + 300.0, self.track_length - safe_end_margin))

            if all(abs(z - other) >= min_gap for other in z_list):
                z_list.append(z)

        z_list.sort()

        for z in z_list:
            kind = rng.choice(kinds)
            # избирай от 5 "ленти", за да има логични пролуки
            lanes = [-0.75, -0.35, 0.0, 0.35, 0.75]
            lane_offset = rng.choice(lanes) * self.lane_width

            self.obstacles.append({
                "kind": kind,
                "z": z,
                "lane_offset": lane_offset,
            })

    def _scaled(self, kind: str, scale: float) -> pygame.Surface:
        key = (kind, int(scale * 100))
        if key in self._cache:
            return self._cache[key]

        img = self.images[kind]
        w = max(1, int(img.get_width() * scale))
        h = max(1, int(img.get_height() * scale))
        surf = pygame.transform.smoothscale(img, (w, h))
        self._cache[key] = surf
        return surf

    def draw(
        self,
        screen: pygame.Surface,
        *,
        track_center_fn,
        top_y: int,
        bottom_y: int,
        gamma: float,
        distance: float,
        screen_w: int,
        screen_h: int,
        road_width_far: float,
        road_width_near: float,
    ):
        if not self.enabled:
            return

        height = bottom_y - top_y

        clip_rect = pygame.Rect(0, top_y, screen_w, screen_h - top_y)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for ob in self.obstacles:
            dist_ahead = ob["z"] - distance
            if dist_ahead < 0 or dist_ahead > self.view_depth:
                continue

            t = dist_ahead / self.view_depth
            z_screen = 1.0 - t
            depth = z_screen ** gamma

            y = int(top_y + depth * height)

            road_w = int(lerp(road_width_far, road_width_near, depth) * screen_w)
            road_half = road_w * 0.5

            cx = track_center_fn(depth)
            x = int(cx + ob["lane_offset"] * road_half)

            scale = lerp(0.12, 1.15, depth)
            spr = self._scaled(ob["kind"], scale)
            rect = spr.get_rect(midbottom=(x, y))
            screen.blit(spr, rect)

        screen.set_clip(old_clip)

    def check_hit(
        self,
        *,
        car_rect: pygame.Rect,
        track_center_fn,
        top_y: int,
        bottom_y: int,
        gamma: float,
        distance: float,
        screen_w: int,
        road_width_far: float,
        road_width_near: float,
    ) -> bool:
        """
        Screen-space collision near the player.
        If hit happens, push obstacle forward so you don't instantly re-hit after respawn.
        """
        if not self.enabled:
            return False

        height = bottom_y - top_y

        # check only obstacles close to camera
        for ob in self.obstacles:
            dist_ahead = ob["z"] - distance
            if dist_ahead < 0 or dist_ahead > self.collision_window:
                continue

            t = dist_ahead / self.view_depth
            z_screen = 1.0 - t
            depth = z_screen ** gamma

            y = int(top_y + depth * height)

            road_w = int(lerp(road_width_far, road_width_near, depth) * screen_w)
            road_half = road_w * 0.5

            cx = track_center_fn(depth)
            x = int(cx + ob["lane_offset"] * road_half)

            scale = lerp(0.12, 1.15, depth)
            spr = self._scaled(ob["kind"], scale)
            ob_rect = spr.get_rect(midbottom=(x, y))

            #car hitboxes
            car_hit = car_rect.inflate(-car_rect.width * 0.35, -car_rect.height * 0.35)
            ob_hit = ob_rect.inflate(-ob_rect.width * 0.40, -ob_rect.height * 0.40)

            if ob_hit.colliderect(car_hit):
                ob["z"] = min(self.track_length - 300.0, ob["z"] + 700.0)
                return True

        return False
