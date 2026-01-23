
from __future__ import annotations
import os
import random
import pygame
from typing import Dict, List, Tuple, Optional

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class PropsSystem:
    """
    Рисува roadside props (bush/rock) по детерминистичен seed.
    """
    def __init__(
        self,
        level_path: str,
        *,
        enabled: bool = True,
        seed: int = 1337,
        view_depth: float = 650.0,
        world_length: float = 3000.0,
        count: int = 22,
        names: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.enabled = enabled
        self.view_depth = float(view_depth)
        self.world_length = float(world_length)

        self.prop_images: Dict[str, pygame.Surface] = {}
        self._cache: Dict[Tuple[str, int], pygame.Surface] = {}
        self.props: List[dict] = []

        if not enabled:
            return

        props_dir = os.path.join(level_path, "props")
        if not os.path.isdir(props_dir):
            self.enabled = False
            return

        default_names = ["bush", "rock1", "rock2"]
        load_names = names if names else default_names

        for name in load_names:
            pth = os.path.join(props_dir, f"{name}.png")
            if os.path.exists(pth):
                self.prop_images[name] = pygame.image.load(pth).convert_alpha()

        if not self.prop_images:
            self.enabled = False
            return

        rng = random.Random(seed)
        kinds = list(self.prop_images.keys())

        w_map = weights or {}
        w_list = [float(w_map.get(k, 1.0)) for k in kinds]

        for _ in range(count):
            z = rng.uniform(150.0, max(200.0, self.world_length - 50.0))
            kind = rng.choices(kinds, weights=w_list, k=1)[0]
            side = rng.choice([-1, 1])
            spread = rng.random()
            self.props.append({"kind": kind, "side": side, "spread": spread, "z": z})

        # far -> near за правилен draw order
        self.props.sort(key=lambda p: p["z"], reverse=True)

    def _scaled(self, kind: str, scale: float) -> pygame.Surface:
        key = (kind, int(scale * 100))
        if key in self._cache:
            return self._cache[key]

        img = self.prop_images[kind]
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

        for p in self.props:
            dist_ahead = p["z"] - distance
            if dist_ahead < 0 or dist_ahead > self.view_depth:
                continue

            t = dist_ahead / self.view_depth
            z_screen = 1.0 - t
            depth = z_screen ** gamma

            y = int(top_y + depth * height)

            road_w = int(lerp(road_width_far, road_width_near, depth) * screen_w)
            road_half = road_w / 2
            cx = track_center_fn(depth)

            # -------- spread по целия бекграунд --------
            margin = 12
            max_extra = (screen_w * 0.5) - road_half - margin  # до ръба на екрана
            if max_extra <= 5:
                continue

            min_extra = 10  # колко минимум “извън пътя”
            extra = lerp(min_extra, max_extra, p.get("spread", 0.0))

            #далечината:
            extra *= (0.35 + 0.65 * depth)

            x = int(cx + p["side"] * (road_half + extra))

            scale = lerp(0.10, 1.05, depth)
            spr = self._scaled(p["kind"], scale)
            rect = spr.get_rect(midbottom=(x, y))
            screen.blit(spr, rect)

        screen.set_clip(old_clip)