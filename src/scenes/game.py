# src/scenes/game.py

import sys
import os
import pygame

from settings1 import CAR_ASSETS
from utils.profile_manager import save_profile

from track.track_data import LEVELS
from track.track import Track, lerp
from systems.props_system import PropsSystem


def load_crop_alpha(path: str) -> pygame.Surface:
    img = pygame.image.load(path).convert_alpha()
    rect = img.get_bounding_rect()
    if rect.width > 0 and rect.height > 0:
        img = img.subsurface(rect).copy()
    return img


class GameScene:
    def __init__(self, game, level, car_id):
        self.game = game
        self.level = level
        self.car_id = car_id

        self.screen_w, self.screen_h = self.game.screen.get_size()

        # -------- PATHS --------
        src_path = os.path.dirname(os.path.dirname(__file__))   # src/
        project_root = os.path.dirname(src_path)
        assets_path = os.path.join(project_root, "assets")
        self.level_path = os.path.join(assets_path, "Levels", f"level_{level}")

        # -------- COLORS --------
        self.sky_color = (20, 90, 140)
        self.road_color = (70, 70, 70)
        self.road_edge_color = (110, 110, 110)
        self.center_line_color = (255, 220, 0)
        self.hud_color = (255, 255, 255)

        self.hud_font = pygame.font.Font(None, 36)

        # -------- TRACK --------
        cfg = LEVELS.get(level)
        if not cfg:
            raise ValueError(f"No track data for level {level} in track_data.py")

        self.track = Track(
            level_id=level,
            length=cfg["length"],
            checkpoint_every=cfg["checkpoint_every"],
            segments=cfg["segments"],
            blend_zone=0.22,
            lookahead=350.0,
            curve_scale_px=280.0,
        )

        # -------- HORIZON --------
        horizon_path = os.path.join(self.level_path, "horizon.png")
        if not os.path.exists(horizon_path):
            raise FileNotFoundError(f"Missing horizon.png in {self.level_path}")

        self.horizon_h = int(self.screen_h * 0.28)
        self.horizon = load_crop_alpha(horizon_path)
        self.horizon = pygame.transform.smoothscale(self.horizon, (self.screen_w, self.horizon_h))

        self.road_top_y = self.horizon_h
        self.road_bottom_y = self.screen_h

        # -------- GROUND SCROLL --------
        bg_path = os.path.join(self.level_path, "background.png")
        if not os.path.exists(bg_path):
            raise FileNotFoundError(f"Missing background.png in {self.level_path}")

        ground_raw = pygame.image.load(bg_path).convert_alpha()
        self.ground_area_y = self.road_top_y
        self.ground_area_h = self.screen_h - self.ground_area_y
        self.ground = pygame.transform.smoothscale(ground_raw, (self.screen_w, self.ground_area_h))
        self.ground_scroll = 0.0
        self.ground_parallax = 0.35

        # -------- PLAYER --------
        car_data = CAR_ASSETS.get(car_id)
        if not car_data:
            raise ValueError(f"Invalid car_id: {car_id}")

        car_path = os.path.join(assets_path, "Car images", car_data["folder"], car_data["back"])
        if not os.path.exists(car_path):
            raise FileNotFoundError(f"Car image not found: {car_path}")

        self.car_image = pygame.image.load(car_path).convert_alpha()
        self.player_speed_x = 10
        self.player_pos = [
            self.screen_w // 2 - self.car_image.get_width() // 2,
            self.screen_h - self.car_image.get_height() - 40
        ]

        # -------- ROAD RENDER PARAMS --------
        self.road_segments = 220
        self.road_width_near = 0.75
        self.road_width_far = 0.08
        self.gamma = 2.0

        self.dash_cycle = 8.0
        self.dash_len = 3.2

        # -------- RUN STATE --------
        self.distance = 0.0
        self.base_speed = 320.0
        self.speed = self.base_speed

        self.checkpoints = self.track.checkpoints
        self.last_checkpoint_index = -1
        self.finished = False

        self.run_started_ticks = pygame.time.get_ticks()
        self.finish_time_seconds = None

        # -------- PROPS SYSTEM --------
        self.props = PropsSystem(
            self.level_path,
            enabled=True,
            seed=1337 + level,
            view_depth=650.0,
            world_length=self.track.length,
            count=22
        )

    # -------- CHECKPOINT / RESPAWN --------

    def update_checkpoint(self):
        while self.last_checkpoint_index + 1 < len(self.checkpoints) and self.distance >= self.checkpoints[self.last_checkpoint_index + 1]:
            self.last_checkpoint_index += 1

    def respawn_to_checkpoint(self):
        if self.last_checkpoint_index >= 0:
            self.distance = self.checkpoints[self.last_checkpoint_index]
        else:
            self.distance = 0.0

        cx = self.track.road_center_x(self.screen_w, self.distance, 1.0)
        self.player_pos[0] = cx - self.car_image.get_width() // 2
        self.speed = self.base_speed * 0.6

    # -------- INPUT --------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            from scenes.menu import MenuScene
            self.game.current_scene = MenuScene(self.game)
            return

        if keys[pygame.K_r]:
            self.respawn_to_checkpoint()

        if not self.finished:
            if keys[pygame.K_LEFT]:
                self.player_pos[0] -= self.player_speed_x
            if keys[pygame.K_RIGHT]:
                self.player_pos[0] += self.player_speed_x

    # -------- UPDATE --------

    def update(self):
        dt = self.game.clock.get_time() / 1000.0
        if dt <= 0 or self.finished:
            return

        # off-road penalty (near depth)
        player_center_x = self.player_pos[0] + self.car_image.get_width() // 2

        p_near = 1.0
        cx = self.track.road_center_x(self.screen_w, self.distance, p_near)
        road_w = int(lerp(self.road_width_far, self.road_width_near, p_near) * self.screen_w)

        left = cx - road_w // 2
        right = cx + road_w // 2

        on_road = left <= player_center_x <= right

        if on_road:
            self.speed = lerp(self.speed, self.base_speed, 0.08)
        else:
            self.speed = lerp(self.speed, self.base_speed * 0.55, 0.15)

        self.distance += self.speed * dt
        if self.distance >= self.track.length:
            self.distance = self.track.length
            self.finished = True
            self.finish_time_seconds = (pygame.time.get_ticks() - self.run_started_ticks) / 1000.0
            self.try_save_best_time()
            return

        self.player_pos[0] = max(0, min(self.player_pos[0], self.screen_w - self.car_image.get_width()))

        self.ground_scroll -= self.speed * dt * self.ground_parallax
        self.ground_scroll %= self.ground_area_h

        self.update_checkpoint()

    # -------- SAVE BEST TIME --------

    def try_save_best_time(self):
        prof = getattr(self.game, "current_profile", None)
        if not prof or "username" not in prof:
            return

        level_key = f"level_{self.level}"
        best = prof.get("best_times", {})
        prev = best.get(level_key)

        if prev is None or self.finish_time_seconds < float(prev):
            best[level_key] = round(self.finish_time_seconds, 3)
            prof["best_times"] = best
            save_profile(prof)

    # -------- DRAW HELPERS --------

    def draw_ground(self):
        clip_rect = pygame.Rect(0, self.ground_area_y, self.screen_w, self.ground_area_h)
        old_clip = self.game.screen.get_clip()
        self.game.screen.set_clip(clip_rect)

        y = self.ground_area_y - int(self.ground_scroll)
        self.game.screen.blit(self.ground, (0, y))
        self.game.screen.blit(self.ground, (0, y + self.ground_area_h))

        self.game.screen.set_clip(old_clip)

    def draw_road(self):
        top = self.road_top_y
        bottom = self.road_bottom_y
        height = bottom - top

        for i in range(self.road_segments):
            z0 = i / self.road_segments
            z1 = (i + 1) / self.road_segments

            p0 = (z0 ** self.gamma)
            p1 = (z1 ** self.gamma)

            y0 = int(top + p0 * height)
            y1 = int(top + p1 * height)

            w0 = int(lerp(self.road_width_far, self.road_width_near, p0) * self.screen_w)
            w1 = int(lerp(self.road_width_far, self.road_width_near, p1) * self.screen_w)

            cx0 = self.track.road_center_x(self.screen_w, self.distance, p0)
            cx1 = self.track.road_center_x(self.screen_w, self.distance, p1)

            l0, r0 = cx0 - w0 // 2, cx0 + w0 // 2
            l1, r1 = cx1 - w1 // 2, cx1 + w1 // 2

            pygame.draw.polygon(
                self.game.screen,
                self.road_color,
                [(l0, y0), (r0, y0), (r1, y1), (l1, y1)]
            )

            edge_thickness = max(1, int(3 * p1))
            pygame.draw.line(self.game.screen, self.road_edge_color, (l0, y0), (l1, y1), edge_thickness)
            pygame.draw.line(self.game.screen, self.road_edge_color, (r0, y0), (r1, y1), edge_thickness)

            world0 = (self.distance * 0.06) + (p0 * 60.0)
            world1 = (self.distance * 0.06) + (p1 * 60.0)

            def in_dash(w):
                return (w % self.dash_cycle) < self.dash_len

            if in_dash(world0) or in_dash(world1):
                line_w = max(1, int(8 * p1))
                pygame.draw.line(self.game.screen, self.center_line_color, (cx0, y0), (cx1, y1), line_w)

    def draw_hud(self):
        t = (pygame.time.get_ticks() - self.run_started_ticks) / 1000.0
        if self.finished and self.finish_time_seconds is not None:
            t = self.finish_time_seconds

        txt_time = self.hud_font.render(f"TIME: {t:0.3f}s", True, self.hud_color)
        txt_dist = self.hud_font.render(f"DIST: {self.distance:0.0f}/{self.track.length:0.0f}", True, self.hud_color)
        cp = self.checkpoints[self.last_checkpoint_index] if self.last_checkpoint_index >= 0 else 0
        txt_cp = self.hud_font.render(f"CHECKPOINT: {cp:0.0f}", True, self.hud_color)

        self.game.screen.blit(txt_time, (20, 12))
        self.game.screen.blit(txt_dist, (20, 44))
        self.game.screen.blit(txt_cp, (20, 76))

        if self.finished:
            done = self.hud_font.render("FINISH! (ESC to menu)", True, (255, 240, 120))
            self.game.screen.blit(done, (20, 110))

    # -------- DRAW --------

    def draw(self):
        self.game.screen.fill(self.sky_color)
        self.game.screen.blit(self.horizon, (0, 0))

        self.draw_ground()
        self.draw_road()

        # props on top
        self.props.draw(
            self.game.screen,
            track_center_fn=lambda p: self.track.road_center_x(self.screen_w, self.distance, p),
            road_width_fn=None,
            top_y=self.road_top_y,
            bottom_y=self.road_bottom_y,
            gamma=self.gamma,
            distance=self.distance,
            screen_w=self.screen_w,
            screen_h=self.screen_h,
            road_width_far=self.road_width_far,
            road_width_near=self.road_width_near,
        )

        self.game.screen.blit(self.car_image, self.player_pos)
        self.draw_hud()
