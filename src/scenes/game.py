# src/scenes/game.py

import sys
import os
import pygame

from settings1 import CAR_ASSETS
from utils.profile_manager import save_profile

from track.track_data import LEVELS
from track.track import Track, lerp
from systems.props_system import PropsSystem
from systems.obstacles_system import ObstaclesSystem


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
        src_path = os.path.dirname(os.path.dirname(__file__))  # src/
        project_root = os.path.dirname(src_path)
        self.assets_path = os.path.join(project_root, "assets")
        self.level_path = os.path.join(self.assets_path, "Levels", f"level_{level}")

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

        # -------- GROUND --------
        bg_path = os.path.join(self.level_path, "background.png")
        if not os.path.exists(bg_path):
            raise FileNotFoundError(f"Missing background.png in {self.level_path}")

        ground_raw = pygame.image.load(bg_path).convert_alpha()
        self.ground_area_y = self.road_top_y
        self.ground_area_h = self.screen_h - self.ground_area_y
        self.ground = pygame.transform.smoothscale(ground_raw, (self.screen_w, self.ground_area_h))
        self.ground_scroll = 0.0
        self.ground_parallax = 0.35

        # -------- PLAYER (BACK/LEFT/RIGHT) --------
        car_data = CAR_ASSETS.get(car_id)
        if not car_data:
            raise ValueError(f"Invalid car_id: {car_id}")

        car_folder = car_data["folder"]
        back_path = os.path.join(self.assets_path, "Car images", car_folder, car_data["back"])
        left_path = os.path.join(self.assets_path, "Car images", car_folder, car_data["left"])
        right_path = os.path.join(self.assets_path, "Car images", car_folder, car_data["right"])

        for pth in (back_path, left_path, right_path):
            if not os.path.exists(pth):
                raise FileNotFoundError(f"Car image not found: {pth}")

        self.car_back = pygame.image.load(back_path).convert_alpha()
        self.car_left = pygame.image.load(left_path).convert_alpha()
        self.car_right = pygame.image.load(right_path).convert_alpha()

        # Ако искаш друг размер - пипай scale
        scale = 2.0
        def scale_img(img: pygame.Surface) -> pygame.Surface:
            w, h = img.get_size()
            return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))

        self.car_back = scale_img(self.car_back)
        self.car_left = scale_img(self.car_left)
        self.car_right = scale_img(self.car_right)

        self.car_image = self.car_back
        self.player_anchor_y = self.screen_h - 40
        self.player_center_x = self.screen_w // 2

        # --- Steering physics (velocity/drift feel) ---
        self.steer_input = 0
        self.player_vel_x = 0.0
        self.steer_accel = 2600.0
        self.steer_max_vel = 900.0
        self.friction = 0.88
        self.brake_when_turning = 0.985

        # -------- ROAD RENDER --------
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

        self.hit_timer = 0.0

        # -------- PROPS --------
        self.props = PropsSystem(
            self.level_path,
            enabled=True,
            seed=1337 + level,
            view_depth=650.0,
            world_length=self.track.length,
            count=22
        )

        # -------- OBSTACLES --------
        self.obstacles = ObstaclesSystem(
            self.level_path,
            enabled=True,
            seed=9001 + level,
            track_length=self.track.length,
            view_depth=800.0,
            count=14,
            min_gap=450.0,
            lane_width=0.62,
            collision_window=90.0,
        )

        # -------- FINISH UI --------
        self._init_finish_ui()

    # ---------------- FINISH UI ----------------

    def _init_finish_ui(self):
        # try assets/Basic/finish.png first
        basic_finish = os.path.join(self.assets_path, "Basic","finish","finish_end_text_results.png")
        level_finish = os.path.join(self.level_path, "finish.png")

        finish_path = basic_finish if os.path.exists(basic_finish) else level_finish
        self.finish_panel = None

        if os.path.exists(finish_path):
            self.finish_panel = pygame.image.load(finish_path).convert_alpha()

            # scale to screen nicely (keep aspect)
            max_w = int(self.screen_w * 0.60)
            max_h = int(self.screen_h * 0.65)
            w, h = self.finish_panel.get_size()
            s = min(max_w / w, max_h / h)
            self.finish_panel = pygame.transform.smoothscale(self.finish_panel, (int(w * s), int(h * s)))

        # panel rect (even if image missing, we will draw a fallback rectangle)
        panel_w = self.finish_panel.get_width() if self.finish_panel else int(self.screen_w * 0.55)
        panel_h = self.finish_panel.get_height() if self.finish_panel else int(self.screen_h * 0.55)
        self.finish_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.finish_rect.center = (self.screen_w // 2, self.screen_h // 2)

        # fonts
        self.finish_title_font = pygame.font.Font(None, 64)
        self.finish_text_font = pygame.font.Font(None, 42)
        self.finish_btn_font = pygame.font.Font(None, 44)

        # buttons inside panel
        btn_w = int(self.finish_rect.width * 0.60)
        btn_h = 56
        gap = 16

        btn_x = self.finish_rect.centerx - btn_w // 2
        btn_y1 = self.finish_rect.bottom - (btn_h * 2 + gap + 40)
        btn_y2 = btn_y1 + btn_h + gap

        self.btn_retry = pygame.Rect(btn_x, btn_y1, btn_w, btn_h)
        self.btn_exit = pygame.Rect(btn_x, btn_y2, btn_w, btn_h)

    def draw_text_box(
            self,
            surf: pygame.Surface,
            text_surf: pygame.Surface,
            center: tuple[int, int],
            *,
            padding_x: int = 18,
            padding_y: int = 10,
            bg=(230, 230, 230),
            border=(0, 0, 0),
            border_w: int = 3,
            radius: int = 12,
    ):
        rect = text_surf.get_rect(center=center)
        box = pygame.Rect(
            rect.left - padding_x,
            rect.top - padding_y,
            rect.width + padding_x * 2,
            rect.height + padding_y * 2,
        )
        pygame.draw.rect(surf, bg, box, border_radius=radius)
        pygame.draw.rect(surf, border, box, border_w, border_radius=radius)
        surf.blit(text_surf, rect)
        return box

    def _draw_finish_overlay(self):
        # darken background
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(160)
        self.game.screen.blit(overlay, (0, 0))

        # panel
        if self.finish_panel:
            self.game.screen.blit(self.finish_panel, self.finish_rect.topleft)
        else:
            pygame.draw.rect(self.game.screen, (30, 30, 30), self.finish_rect, border_radius=18)
            pygame.draw.rect(self.game.screen, (220, 220, 220), self.finish_rect, 3, border_radius=18)

        # username + time
        prof = getattr(self.game, "current_profile", None)
        username = "Player"
        if prof and isinstance(prof, dict) and prof.get("username"):
            username = str(prof["username"])

        time_s = float(self.finish_time_seconds or 0.0)

        title = self.finish_title_font.render("FINISH!", True, (0, 0, 0))
        name_txt = self.finish_text_font.render(f"Racer: {username}", True, (0, 0, 0))
        time_txt = self.finish_text_font.render(f"Time: {time_s:.3f}s", True, (0, 0, 0))

        tx = self.finish_rect.centerx

        # --- dynamic layout: always above buttons ---
        pad_x, pad_y = 18, 10
        gap = 14

        def box_h(s: pygame.Surface) -> int:
            return s.get_height() + pad_y * 2

        total_h = box_h(title) + box_h(name_txt) + box_h(time_txt) + gap * 2

        # Keep stack inside panel: clamp between top padding and button area
        stack_bottom = self.btn_retry.top - 18
        min_top = self.finish_rect.top + 45
        start_y = stack_bottom - total_h
        if start_y < min_top:
            start_y = min_top

        y1 = int(start_y + box_h(title) * 0.5)
        y2 = int(y1 + box_h(title) * 0.5 + gap + box_h(name_txt) * 0.5)
        y3 = int(y2 + box_h(name_txt) * 0.5 + gap + box_h(time_txt) * 0.5)

        self.draw_text_box(
            self.game.screen, title, (tx, y1),
            bg=(240, 240, 240), padding_x=pad_x, padding_y=pad_y
        )
        self.draw_text_box(
            self.game.screen, name_txt, (tx, y2),
            bg=(240, 240, 240), padding_x=pad_x, padding_y=pad_y
        )
        self.draw_text_box(
            self.game.screen, time_txt, (tx, y3),
            bg=(240, 240, 240), padding_x=pad_x, padding_y=pad_y
        )

        # buttons (hover)
        mx, my = pygame.mouse.get_pos()

        def draw_button(rect: pygame.Rect, text: str):
            hover = rect.collidepoint(mx, my)
            fill = (240, 240, 240) if hover else (210, 210, 210)
            border = (0, 0, 0)
            pygame.draw.rect(self.game.screen, fill, rect, border_radius=12)
            pygame.draw.rect(self.game.screen, border, rect, 3, border_radius=12)
            t = self.finish_btn_font.render(text, True, (0, 0, 0))
            self.game.screen.blit(t, t.get_rect(center=rect.center))

        draw_button(self.btn_retry, "TRY AGAIN")
        draw_button(self.btn_exit, "EXIT")

    # ---------------- CHECKPOINT / RESPAWN ----------------

    def update_checkpoint(self):
        while (self.last_checkpoint_index + 1 < len(self.checkpoints)
               and self.distance >= self.checkpoints[self.last_checkpoint_index + 1]):
            self.last_checkpoint_index += 1

    def respawn_to_checkpoint(self):
        if self.last_checkpoint_index >= 0:
            self.distance = self.checkpoints[self.last_checkpoint_index]
        else:
            self.distance = 0.0

        self.player_center_x = self.track.road_center_x(self.screen_w, self.distance, 1.0)
        self.speed = self.base_speed * 0.6
        self.player_vel_x = 0.0
        self.hit_timer = 0.55

    # ---------------- INPUT ----------------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Finish screen controls
            if self.finished:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self._restart_level()
                        return
                    if event.key == pygame.K_ESCAPE:
                        self._exit_to_menu()
                        return

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.btn_retry.collidepoint(event.pos):
                        self._restart_level()
                        return
                    if self.btn_exit.collidepoint(event.pos):
                        self._exit_to_menu()
                        return

                # When finished, ignore other inputs
                continue

        keys = pygame.key.get_pressed()

        if keys[pygame.K_ESCAPE]:
            self._exit_to_menu()
            return

        if keys[pygame.K_r]:
            self.respawn_to_checkpoint()

        self.steer_input = 0
        if not self.finished:
            if keys[pygame.K_LEFT]:
                self.steer_input = -1
            elif keys[pygame.K_RIGHT]:
                self.steer_input = 1

    def _restart_level(self):
        # restart same level/car
        self.game.current_scene = GameScene(self.game, self.level, self.car_id)

    def _exit_to_menu(self):
        from scenes.menu import MenuScene
        self.game.current_scene = MenuScene(self.game)

    # ---------------- UPDATE ----------------

    def update(self):
        dt = self.game.clock.get_time() / 1000.0
        if dt <= 0 or self.finished:
            return

        if self.steer_input != 0:
            self.player_vel_x += self.steer_input * self.steer_accel * dt
            self.player_vel_x *= self.brake_when_turning
        else:
            self.player_vel_x *= (self.friction ** (dt * 60.0))

        if self.player_vel_x > self.steer_max_vel:
            self.player_vel_x = self.steer_max_vel
        elif self.player_vel_x < -self.steer_max_vel:
            self.player_vel_x = -self.steer_max_vel

        self.player_center_x += self.player_vel_x * dt

        max_w = max(self.car_back.get_width(), self.car_left.get_width(), self.car_right.get_width())
        half = max_w // 2
        self.player_center_x = max(half, min(self.player_center_x, self.screen_w - half))

        # off-road penalty
        p_near = 1.0
        cx_near = self.track.road_center_x(self.screen_w, self.distance, p_near)
        road_w_near = int(lerp(self.road_width_far, self.road_width_near, p_near) * self.screen_w)

        left = cx_near - road_w_near // 2
        right = cx_near + road_w_near // 2
        on_road = left <= self.player_center_x <= right

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

        self.ground_scroll -= self.speed * dt * self.ground_parallax
        self.ground_scroll %= self.ground_area_h

        self.update_checkpoint()

        if self.hit_timer > 0:
            self.hit_timer = max(0.0, self.hit_timer - dt)

        # sprite choose
        if self.steer_input < 0 or self.player_vel_x < -120:
            self.car_image = self.car_left
        elif self.steer_input > 0 or self.player_vel_x > 120:
            self.car_image = self.car_right
        else:
            self.car_image = self.car_back

        car_rect = self.car_image.get_rect(midbottom=(int(self.player_center_x), self.player_anchor_y))

        hit = self.obstacles.check_hit(
            car_rect=car_rect,
            track_center_fn=lambda p: self.track.road_center_x(self.screen_w, self.distance, p),
            top_y=self.road_top_y,
            bottom_y=self.road_bottom_y,
            gamma=self.gamma,
            distance=self.distance,
            screen_w=self.screen_w,
            road_width_far=self.road_width_far,
            road_width_near=self.road_width_near,
        )
        if hit:
            self.respawn_to_checkpoint()

    # ---------------- SAVE BEST TIME ----------------

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

    # ---------------- DRAW HELPERS ----------------

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

            world0 = (-self.distance * 0.06) + (p0 * 60.0)
            world1 = (-self.distance * 0.06) + (p1 * 60.0)

            def in_dash(w):
                return (w % self.dash_cycle) < self.dash_len

            if in_dash(world0) or in_dash(world1):
                line_w = max(1, int(8 * p1))
                pygame.draw.line(self.game.screen, self.center_line_color, (cx0, y0), (cx1, y1), line_w)

    def draw_hud(self):
        if self.finished and self.finish_time_seconds is not None:
            t = self.finish_time_seconds
        else:
            t = (pygame.time.get_ticks() - self.run_started_ticks) / 1000.0

        txt_time = self.hud_font.render(f"TIME: {t:0.3f}s", True, self.hud_color)
        txt_dist = self.hud_font.render(f"DIST: {self.distance:0.0f}/{self.track.length:0.0f}", True, self.hud_color)
        cp = self.checkpoints[self.last_checkpoint_index] if self.last_checkpoint_index >= 0 else 0
        txt_cp = self.hud_font.render(f"CHECKPOINT: {cp:0.0f}", True, self.hud_color)

        self.game.screen.blit(txt_time, (20, 12))
        self.game.screen.blit(txt_dist, (20, 44))
        self.game.screen.blit(txt_cp, (20, 76))

    # ---------------- DRAW ----------------

    def draw(self):
        self.game.screen.fill(self.sky_color)
        self.game.screen.blit(self.horizon, (0, 0))

        self.draw_ground()
        self.draw_road()

        # obstacles on road
        self.obstacles.draw(
            self.game.screen,
            track_center_fn=lambda p: self.track.road_center_x(self.screen_w, self.distance, p),
            top_y=self.road_top_y,
            bottom_y=self.road_bottom_y,
            gamma=self.gamma,
            distance=self.distance,
            screen_w=self.screen_w,
            screen_h=self.screen_h,
            road_width_far=self.road_width_far,
            road_width_near=self.road_width_near,
        )

        # roadside props
        self.props.draw(
            self.game.screen,
            track_center_fn=lambda p: self.track.road_center_x(self.screen_w, self.distance, p),
            top_y=self.road_top_y,
            bottom_y=self.road_bottom_y,
            gamma=self.gamma,
            distance=self.distance,
            screen_w=self.screen_w,
            screen_h=self.screen_h,
            road_width_far=self.road_width_far,
            road_width_near=self.road_width_near,
        )

        car_rect = self.car_image.get_rect(midbottom=(int(self.player_center_x), self.player_anchor_y))
        self.game.screen.blit(self.car_image, car_rect)

        self.draw_hud()

        # FINISH overlay on top
        if self.finished:
            self._draw_finish_overlay()
