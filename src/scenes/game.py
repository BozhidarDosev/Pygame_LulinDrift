import sys
import os
import pygame
import math

from settings1 import CAR_ASSETS
from utils.profile_manager import save_profile
from systems.ghost_system import GhostSystem
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
        self.project_root = project_root

        self.assets_path = os.path.join(project_root, "assets")
        self.level_path = os.path.join(self.assets_path, "Levels", f"level_{level}")
        self.finish_path = os.path.join(self.assets_path, "Basic", "finish")

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

        # -------- FINISH LINE (ON ROAD) --------
        finish_line_path = os.path.join(self.finish_path, "finish_line.png")
        self.finish_line_img = None
        if os.path.exists(finish_line_path):
            self.finish_line_img = pygame.image.load(finish_line_path).convert_alpha()

        # колко преди финала да започне да се вижда
        self.finish_line_view_depth = 1200.0  # tweak: 800..1600

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

        # -------- SETTINGS (PAUSE + VOLUME) --------
        self.settings_open = False
        self.master_volume = 0.85
        self.dragging_volume = False

        # -------- AUDIO --------
        self._init_audio()

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

        # -------- PAUSE TIME ACCUMULATION --------
        self.pause_accum_ms = 0
        self.pause_started_ms = None

        # -------- BEST TIME (loaded from profile) --------
        self.best_time_seconds = None
        self.is_new_best = False
        self._load_best_time()

        self.hit_timer = 0.0

        # -------- PROPS --------
        props_names = None
        props_weights = None
        props_count = 22
        props_view_depth = 650.0

        if level == 2:
            props_names = ["tree1", "rock2"]
            props_weights = {"tree1": 6.0, "rock2": 1.0}
            props_count = 70
            props_view_depth = 1100.0

        elif level == 3:
            props_names = ["penguin1", "penguin2", "penguin3"]
            props_weights = {"penguin1": 1.0, "penguin2": 1.0, "penguin3": 1.0}
            props_count = 85
            props_view_depth = 1100.0

        self.props = PropsSystem(
            self.level_path,
            enabled=True,
            seed=1337 + level,
            view_depth=props_view_depth,
            world_length=self.track.length,
            count=props_count,
            names=props_names,
            weights=props_weights,
        )

        # -------- OBSTACLES --------
        obstacle_names = None
        ob_count = 14
        ob_gap = 450.0

        if level == 2:
            obstacle_names = ["log1", "log2"]
        elif level == 3:
            obstacle_names = ["puddle"]
            ob_count = 24  # <-- повече puddles
            ob_gap = 320.0  # <-- по-малка дистанция между тях

        self.obstacles = ObstaclesSystem(
            self.level_path,
            enabled=True,
            seed=9001 + level,
            track_length=self.track.length,
            view_depth=800.0,
            count=ob_count,
            min_gap=ob_gap,
            lane_width=0.62,
            collision_window=90.0,
            names=obstacle_names,
        )

        # -------- GHOST --------
        ghost_dir = os.path.join(self.project_root, "data", "ghosts")

        prof = getattr(self.game, "current_profile", None)
        username = "Player"
        if prof and isinstance(prof, dict) and prof.get("username"):
            username = str(prof["username"])

        self.ghost = GhostSystem(
            base_dir=ghost_dir,
            username=username,
            level=self.level,
            car_back=self.car_back,
            car_left=self.car_left,
            car_right=self.car_right,
            enabled=True,
            sample_dt=1.0 / 30.0,
            view_depth=1200.0,
            alpha=120,
        )
        self.ghost.start_run()

        # -------- FINISH UI --------
        self._init_finish_ui()

        self.settings_title_font = pygame.font.Font(None, 64)
        self.settings_text_font = pygame.font.Font(None, 36)

        # panel + slider rects
        panel_w = int(self.screen_w * 0.62)
        panel_h = int(self.screen_h * 0.42)
        self.settings_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.settings_rect.center = (self.screen_w // 2, self.screen_h // 2)

        slider_w = int(panel_w * 0.70)
        slider_h = 10
        slider_x = self.settings_rect.centerx - slider_w // 2
        slider_y = self.settings_rect.centery + 30
        self.volume_bar = pygame.Rect(slider_x, slider_y, slider_w, slider_h)

        self.knob_radius = 14

        # apply volume immediately
        self._apply_master_volume()

        btn_w = int(panel_w * 0.55)
        btn_h = 52
        btn_x = self.settings_rect.centerx - btn_w // 2
        btn_y = self.settings_rect.bottom - 85
        self.btn_main_menu = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    def _clamp(self, x: float, a: float = 0.0, b: float = 1.0) -> float:
        return max(a, min(b, x))

    def _run_time_seconds(self) -> float:
        now = pygame.time.get_ticks()

        paused_ms = self.pause_accum_ms

        if self.settings_open and self.pause_started_ms is not None:
            paused_ms += (now - self.pause_started_ms)

        return (now - self.run_started_ticks - paused_ms) / 1000.0

    def _apply_master_volume(self):
        if not getattr(self, "audio_enabled", False):
            return

        # FX channel uses master directly
        if hasattr(self, "ch_fx"):
            self.ch_fx.set_volume(self.master_volume)

        # accel is dynamic -> multiply by master
        if hasattr(self, "ch_accel"):
            base = getattr(self, "accel_volume", 0.0)
            self.ch_accel.set_volume(base * self.master_volume)

    def _toggle_settings(self):
        self.settings_open = not self.settings_open
        self.dragging_volume = False

        now = pygame.time.get_ticks()

        # --- pause timer bookkeeping ---
        if self.settings_open:
            self.pause_started_ms = now
        else:
            if self.pause_started_ms is not None:
                self.pause_accum_ms += (now - self.pause_started_ms)
                self.pause_started_ms = None

        # --- pause/unpause audio ---
        if getattr(self, "audio_enabled", False):
            if self.settings_open:
                self.ch_accel.pause()
                self.ch_fx.pause()
            else:
                self.ch_accel.unpause()
                self.ch_fx.unpause()
                self._apply_master_volume()

    def _set_volume_from_mouse(self, mx: int):
        t = (mx - self.volume_bar.left) / max(1, self.volume_bar.width)
        self.master_volume = self._clamp(t, 0.0, 1.0)
        self._apply_master_volume()

    def _draw_settings_overlay(self):
        # dark overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(170)
        self.game.screen.blit(overlay, (0, 0))

        # panel
        pygame.draw.rect(self.game.screen, (235, 235, 235), self.settings_rect, border_radius=18)
        pygame.draw.rect(self.game.screen, (0, 0, 0), self.settings_rect, 3, border_radius=18)

        title = self.settings_title_font.render("SETTINGS", True, (0, 0, 0))
        self.game.screen.blit(title, title.get_rect(center=(self.settings_rect.centerx, self.settings_rect.top + 55)))

        label = self.settings_text_font.render("Volume", True, (0, 0, 0))
        self.game.screen.blit(label, (self.volume_bar.left, self.volume_bar.top - 35))

        # bar background
        pygame.draw.rect(self.game.screen, (80, 80, 80), self.volume_bar, border_radius=8)

        # fill
        fill_w = int(self.volume_bar.width * self.master_volume)
        fill_rect = pygame.Rect(self.volume_bar.left, self.volume_bar.top, fill_w, self.volume_bar.height)
        pygame.draw.rect(self.game.screen, (20, 140, 220), fill_rect, border_radius=8)

        # knob
        knob_x = self.volume_bar.left + fill_w
        knob_y = self.volume_bar.centery
        pygame.draw.circle(self.game.screen, (255, 255, 255), (knob_x, knob_y), self.knob_radius)
        pygame.draw.circle(self.game.screen, (0, 0, 0), (knob_x, knob_y), self.knob_radius, 2)

        hint = self.settings_text_font.render("ESC to resume", True, (0, 0, 0))
        self.game.screen.blit(hint, hint.get_rect(center=(self.settings_rect.centerx, self.settings_rect.bottom - 45)))


        #main menu button
        mx, my = pygame.mouse.get_pos()
        hover = self.btn_main_menu.collidepoint(mx, my)
        fill = (245, 245, 245) if hover else (220, 220, 220)

        pygame.draw.rect(self.game.screen, fill, self.btn_main_menu, border_radius=12)
        pygame.draw.rect(self.game.screen, (0, 0, 0), self.btn_main_menu, 3, border_radius=12)

        txt = self.settings_text_font.render("MAIN MENU", True, (0, 0, 0))
        self.game.screen.blit(txt, txt.get_rect(center=self.btn_main_menu.center))

    # ---------------- AUDIO ----------------

    def _init_audio(self):
        # init mixer ако не е init-нат (ако вече го правиш в main, няма да пречи)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as e:
            print("Audio disabled:", e)
            self.audio_enabled = False
            return

        self.audio_enabled = True

        sounds_dir = os.path.join(self.project_root, "assets", "Sounds")
        accel_path = os.path.join(sounds_dir, "car_acceleration_sound_fx.wav")
        skid_path = os.path.join(sounds_dir, "car_skidding_sound_fx.wav")
        victory_path = os.path.join(sounds_dir, "gaming-victory.mp3")

        try:
            self.snd_accel = pygame.mixer.Sound(accel_path)
            self.snd_skid = pygame.mixer.Sound(skid_path)
            self.snd_victory = pygame.mixer.Sound(victory_path)
        except Exception as e:
            print("Failed to load sounds:", e)
            self.audio_enabled = False
            return

        # отделни канали (за да не се прекъсват)
        self.ch_accel = pygame.mixer.Channel(0)
        self.ch_fx = pygame.mixer.Channel(1)

        self.accel_volume = 1.0
        self._restart_accel_sound()

    def _restart_accel_sound(self):
        if not getattr(self, "audio_enabled", False):
            return
        # рестарт от начало (loop)
        self.ch_accel.stop()
        self.accel_volume = 0.0  # ще се вдигне плавно в update
        self.ch_accel.play(self.snd_accel, loops=-1)
        self.ch_accel.set_volume(self.accel_volume * self.master_volume)

    def _play_skid(self):
        if not getattr(self, "audio_enabled", False):
            return
        self.ch_fx.set_volume(self.master_volume)
        self.ch_fx.play(self.snd_skid)

    def _play_victory(self):
        if not getattr(self, "audio_enabled", False):
            return
        self.ch_fx.set_volume(self.master_volume)
        self.ch_fx.play(self.snd_victory)

    # ---------------- Stop audio from playing ----------------

    def _stop_all_audio(self):
        if not getattr(self, "audio_enabled", False):
            return
        if hasattr(self, "ch_accel"):
            self.ch_accel.stop()
        if hasattr(self, "ch_fx"):
            self.ch_fx.stop()

    # ---------------- FINISH LINE ----------------

    def draw_finish_line(self):
        if not self.finish_line_img:
            return

        dist_ahead = self.track.length - self.distance
        if dist_ahead <= 0 or dist_ahead > self.finish_line_view_depth:
            return

        top = self.road_top_y
        bottom = self.road_bottom_y
        height = bottom - top

        t = dist_ahead / self.finish_line_view_depth
        z_screen = 1.0 - t
        depth = z_screen ** self.gamma  # 0..1

        y = int(top + depth * height)

        road_w = int(lerp(self.road_width_far, self.road_width_near, depth) * self.screen_w)
        cx = self.track.road_center_x(self.screen_w, self.distance, depth)

        target_w = max(2, int(road_w * 0.98))
        iw, ih = self.finish_line_img.get_size()
        s = target_w / max(1, iw)
        target_h = max(2, int(ih * s))

        spr = pygame.transform.smoothscale(self.finish_line_img, (target_w, target_h))
        rect = spr.get_rect(midbottom=(cx, y))
        self.game.screen.blit(spr, rect)

    # ---------------- FINISH UI ----------------

    def _init_finish_ui(self):
        basic_finish = os.path.join(self.assets_path, "Basic", "finish", "finish_end_text_results.png")
        level_finish = os.path.join(self.level_path, "finish.png")

        finish_path = basic_finish if os.path.exists(basic_finish) else level_finish
        self.finish_panel = None

        if os.path.exists(finish_path):
            self.finish_panel = pygame.image.load(finish_path).convert_alpha()
            max_w = int(self.screen_w * 0.60)
            max_h = int(self.screen_h * 0.65)
            w, h = self.finish_panel.get_size()
            s = min(max_w / w, max_h / h)
            self.finish_panel = pygame.transform.smoothscale(self.finish_panel, (int(w * s), int(h * s)))

        panel_w = self.finish_panel.get_width() if self.finish_panel else int(self.screen_w * 0.55)
        panel_h = self.finish_panel.get_height() if self.finish_panel else int(self.screen_h * 0.55)
        self.finish_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.finish_rect.center = (self.screen_w // 2, self.screen_h // 2)

        self.finish_title_font = pygame.font.Font(None, 64)
        self.finish_text_font = pygame.font.Font(None, 42)
        self.finish_btn_font = pygame.font.Font(None, 44)

        # buttons side-by-side
        btn_h = 52
        pad = 28
        gap = 18

        total_w = self.finish_rect.width - pad * 2
        btn_w = int((total_w - gap) / 2)

        y = self.finish_rect.bottom - pad - btn_h
        x1 = self.finish_rect.left + pad
        x2 = x1 + btn_w + gap

        self.btn_retry = pygame.Rect(x1, y, btn_w, btn_h)
        self.btn_exit = pygame.Rect(x2, y, btn_w, btn_h)

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
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(160)
        self.game.screen.blit(overlay, (0, 0))

        if self.finish_panel:
            self.game.screen.blit(self.finish_panel, self.finish_rect.topleft)
        else:
            pygame.draw.rect(self.game.screen, (30, 30, 30), self.finish_rect, border_radius=18)
            pygame.draw.rect(self.game.screen, (220, 220, 220), self.finish_rect, 3, border_radius=18)

        prof = getattr(self.game, "current_profile", None)
        username = "Player"
        if prof and isinstance(prof, dict) and prof.get("username"):
            username = str(prof["username"])

        time_s = float(self.finish_time_seconds or 0.0)

        title = self.finish_title_font.render("FINISH!", True, (0, 0, 0))
        name_txt = self.finish_text_font.render(f"Racer: {username}", True, (0, 0, 0))
        time_txt = self.finish_text_font.render(f"Time: {time_s:.3f}s", True, (0, 0, 0))

        tx = self.finish_rect.centerx

        pad_x, pad_y = 18, 10
        gap = 14

        def box_h(s: pygame.Surface) -> int:
            return s.get_height() + pad_y * 2

        total_h = box_h(title) + box_h(name_txt) + box_h(time_txt) + gap * 2

        stack_bottom = self.btn_retry.top - 18
        min_top = self.finish_rect.top + 45
        start_y = stack_bottom - total_h
        if start_y < min_top:
            start_y = min_top

        y1 = int(start_y + box_h(title) * 0.5)
        y2 = int(y1 + box_h(title) * 0.5 + gap + box_h(name_txt) * 0.5)
        y3 = int(y2 + box_h(name_txt) * 0.5 + gap + box_h(time_txt) * 0.5)

        self.draw_text_box(self.game.screen, title, (tx, y1), bg=(240, 240, 240), padding_x=pad_x, padding_y=pad_y)
        self.draw_text_box(self.game.screen, name_txt, (tx, y2), bg=(240, 240, 240), padding_x=pad_x, padding_y=pad_y)
        self.draw_text_box(self.game.screen, time_txt, (tx, y3), bg=(240, 240, 240), padding_x=pad_x, padding_y=pad_y)

        mx, my = pygame.mouse.get_pos()

        def draw_button(rect: pygame.Rect, text: str):
            hover = rect.collidepoint(mx, my)
            fill = (240, 240, 240) if hover else (210, 210, 210)
            pygame.draw.rect(self.game.screen, fill, rect, border_radius=12)
            pygame.draw.rect(self.game.screen, (0, 0, 0), rect, 3, border_radius=12)
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

        self._restart_accel_sound()
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
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._toggle_settings()
                return

            if self.settings_open:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # MAIN MENU button
                    if self.btn_main_menu.collidepoint(event.pos):
                        self._abort_to_menu()
                        return
                    # click on bar sets volume + start drag
                    if self.volume_bar.collidepoint(event.pos):
                        self.dragging_volume = True
                        self._set_volume_from_mouse(event.pos[0])

                elif event.type == pygame.MOUSEMOTION and self.dragging_volume:
                    self._set_volume_from_mouse(event.pos[0])

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging_volume = False

                continue

        if self.settings_open:
            return
        keys = pygame.key.get_pressed()

        if keys[pygame.K_r]:
            self.respawn_to_checkpoint()

        self.steer_input = 0
        if keys[pygame.K_LEFT]:
            self.steer_input = -1
        elif keys[pygame.K_RIGHT]:
            self.steer_input = 1

    def _restart_level(self):
        self.game.current_scene = GameScene(self.game, self.level, self.car_id)

    def _abort_to_menu(self):
        # спри всичко аудио
        self._stop_all_audio()

        # safety: никакви “finish” флагове/време
        self.finished = False
        self.finish_time_seconds = None
        self.is_new_best = False

        # ако някъде пазиш "continue scene" в game, чистим го безопасно
        for attr in (
                "resume_scene", "saved_scene", "last_scene", "continue_scene",
                "paused_scene", "game_scene", "last_game_scene"
        ):
            if hasattr(self.game, attr):
                setattr(self.game, attr, None)

        # към главното меню
        from scenes.menu import MenuScene
        self.game.current_scene = MenuScene(self.game)

    def _exit_to_menu(self):
        from scenes.menu import MenuScene
        self.game.current_scene = MenuScene(self.game)

    # ---------------- UPDATE ----------------

    def update(self):
        dt = self.game.clock.get_time() / 1000.0
        if dt <= 0 or self.finished or self.settings_open:
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

        # off-road penalty (near)
        p_near = 1.0
        cx_near = self.track.road_center_x(self.screen_w, self.distance, p_near)
        road_w_near = int(lerp(self.road_width_far, self.road_width_near, p_near) * self.screen_w)

        left = cx_near - road_w_near // 2
        right = cx_near + road_w_near // 2
        on_road = left <= self.player_center_x <= right

        # --- ghost recording ---
        run_t = self._run_time_seconds()

        road_half_near = max(1.0, road_w_near * 0.5)
        lane = (float(self.player_center_x) - float(cx_near)) / road_half_near
        if lane < -1.0:
            lane = -1.0
        elif lane > 1.0:
            lane = 1.0

        if self.steer_input < 0 or self.player_vel_x < -120:
            gdir = -1
        elif self.steer_input > 0 or self.player_vel_x > 120:
            gdir = 1
        else:
            gdir = 0

        self.ghost.record(dt=dt, t=run_t, distance=self.distance, lane=lane, dir=gdir)

        if on_road:
            self.speed = lerp(self.speed, self.base_speed, 0.08)
        else:
            self.speed = lerp(self.speed, self.base_speed * 0.55, 0.15)

        # -------- AUDIO: accel volume based on speed + on/off road --------
        if getattr(self, "audio_enabled", False):
            # 0..1 според текущата скорост
            sp = 0.0 if self.base_speed <= 0 else max(0.0, min(1.0, self.speed / self.base_speed))

            # ако е off-road -> по-тихо
            road_mul = 1.0 if on_road else 0.35

            target_vol = sp * road_mul

            # плавно приближаване
            k = 6.0
            a = min(1.0, k * dt)
            self.accel_volume += (target_vol - self.accel_volume) * a

            self.ch_accel.set_volume(self.accel_volume * self.master_volume)

        self.distance += self.speed * dt

        if self.distance >= self.track.length:
            self.distance = self.track.length
            self.finished = True
            self.finish_time_seconds = self._run_time_seconds()

            self._stop_all_audio()
            self._play_victory()

            new_best = self.try_save_best_time()
            if new_best:
                self.ghost.save_recording_as_best(self.finish_time_seconds)

            return

        self.ground_scroll -= self.speed * dt * self.ground_parallax
        self.ground_scroll %= self.ground_area_h

        self.update_checkpoint()

        if self.hit_timer > 0:
            self.hit_timer = max(0.0, self.hit_timer - dt)

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
            # self.respawn_to_checkpoint()
            self._play_skid()
            self.respawn_to_checkpoint()

    # ---------------- SAVE BEST TIME (IMPORTANT FIX) ----------------

    def try_save_best_time(self) -> bool:
        """
        Updates profile best time.
        Returns True if NEW BEST was set, else False.
        Also updates:
          - self.is_new_best
          - self.best_time_seconds
        """
        prof = getattr(self.game, "current_profile", None)
        if not prof or "username" not in prof:
            self.is_new_best = False
            return False

        level_key = f"level_{self.level}"
        best_dict = prof.get("best_times", {})
        prev = best_dict.get(level_key)

        prev_f = float(prev) if prev is not None else None
        finish = float(self.finish_time_seconds or 0.0)

        if prev_f is None or finish < prev_f:
            self.is_new_best = True
            self.best_time_seconds = finish
            best_dict[level_key] = round(finish, 3)
            prof["best_times"] = best_dict
            save_profile(prof)
            return True

        self.is_new_best = False
        self.best_time_seconds = prev_f
        return False

    def _load_best_time(self):
        prof = getattr(self.game, "current_profile", None)
        if not prof or "username" not in prof:
            self.best_time_seconds = None
            return

        level_key = f"level_{self.level}"
        prev = prof.get("best_times", {}).get(level_key)
        self.best_time_seconds = float(prev) if prev is not None else None

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
            t = float(self.finish_time_seconds)
        else:
            t = self._run_time_seconds()


        txt_time = self.hud_font.render(f"TIME: {t:0.3f}s", True, self.hud_color)
        self.game.screen.blit(txt_time, (20, 12))

        if self.finished and self.is_new_best:
            best_line = f"NEW BEST TIME: {t:0.3f}s"
        else:
            if self.best_time_seconds is None:
                best_line = "BEST: --"
            else:
                best_line = f"BEST: {self.best_time_seconds:0.3f}s"

        txt_best = self.hud_font.render(best_line, True, self.hud_color)
        self.game.screen.blit(txt_best, (20, 44))

        txt_dist = self.hud_font.render(
            f"DIST: {self.distance:0.0f}/{self.track.length:0.0f}",
            True,
            self.hud_color
        )
        cp = self.checkpoints[self.last_checkpoint_index] if self.last_checkpoint_index >= 0 else 0
        txt_cp = self.hud_font.render(f"CHECKPOINT: {cp:0.0f}", True, self.hud_color)

        self.game.screen.blit(txt_dist, (20, 76))
        self.game.screen.blit(txt_cp, (20, 108))

    # ---------------- DRAW ----------------

    def draw(self):
        self.game.screen.fill(self.sky_color)
        self.game.screen.blit(self.horizon, (0, 0))

        self.draw_ground()
        self.draw_road()
        self.draw_finish_line()

        # ghost draw (before obstacles)
        run_t = self._run_time_seconds()

        self.ghost.draw(
            self.game.screen,
            t=run_t,
            player_distance=self.distance,
            track_center_fn=lambda p: self.track.road_center_x(self.screen_w, self.distance, p),
            top_y=self.road_top_y,
            bottom_y=self.road_bottom_y,
            gamma=self.gamma,
            screen_w=self.screen_w,
            screen_h=self.screen_h,
            road_width_far=self.road_width_far,
            road_width_near=self.road_width_near,
        )

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

        car_rect = self.car_image.get_rect(midbottom=(int(self.player_center_x), self.player_anchor_y))
        self.game.screen.blit(self.car_image, car_rect)

        self.draw_hud()

        if self.finished:
            self._draw_finish_overlay()

        if self.settings_open:
            self._draw_settings_overlay()

