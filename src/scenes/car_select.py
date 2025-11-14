import pygame
import os
import sys
from settings1 import *

class CarSelectionScene:
    def __init__(self, game):
        self.game = game
        self.current_car_id = 1

        base_path = os.path.dirname(os.path.dirname(__file__))  # scenes -> src
        self.assets_path = os.path.join(base_path, "../assets")

        # font
        font_path = os.path.join(self.assets_path, "Basic/Dalmation-FREE.otf")
        if os.path.exists(font_path):
            self.font = pygame.font.Font(font_path, 70)
            self.small_font = pygame.font.Font(font_path, 45)
        else:
            self.font = pygame.font.SysFont("Arial", 70, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 45, bold=True)

        # arrows
        self.arrow_left = pygame.image.load(
            os.path.join(self.assets_path, "Basic/arrow_left.png")
        ).convert_alpha()
        self.arrow_right = pygame.image.load(
            os.path.join(self.assets_path, "Basic/arrow_right.png")
        ).convert_alpha()

        w, h = self.game.screen.get_size()
        self.left_rect = self.arrow_left.get_rect(center=(w // 2 - 550, h // 2 - 150))
        self.right_rect = self.arrow_right.get_rect(center=(w // 2 + 550, h // 2 - 150))

        # select button
        self.select_button = pygame.Rect(w // 2 - 200, h - 150, 400, 80)

        # bg
        self.bg_surface = pygame.Surface((w, h))
        self.bg_surface.fill((220, 220, 220))

        # fade
        self.fade_alpha = 255
        self.is_fading = False
        self.fade_direction = -1

        self.load_current_car()

    def load_current_car(self):
        car_data = CAR_ASSETS[self.current_car_id]
        car_folder = car_data["folder"]
        car_front = car_data["front"]

        car_path = os.path.join(self.assets_path, f"Car images/{car_folder}/{car_front}")
        if not os.path.exists(car_path):
            raise FileNotFoundError(f"Missing car image: {car_path}")

        self.car_image = pygame.image.load(car_path).convert_alpha()

        w, h = self.game.screen.get_size()
        max_width = int(w * 0.35)
        max_height = int(h * 0.28)
        self.car_image = pygame.transform.smoothscale(self.car_image, (max_width, max_height))
        self.car_rect = self.car_image.get_rect(center=(w // 2, h // 2 - 150))

        self.car_name = car_folder.replace("_", " ").upper()
        self.stats = car_data["stats"]

        self.fade_alpha = 255
        self.is_fading = True
        self.fade_direction = -1

    def next_car(self):
        self.current_car_id += 1
        if self.current_car_id > len(CAR_ASSETS):
            self.current_car_id = 1
        self.load_current_car()

    def prev_car(self):
        self.current_car_id -= 1
        if self.current_car_id < 1:
            self.current_car_id = len(CAR_ASSETS)
        self.load_current_car()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                from scenes.menu import MenuScene
                self.game.current_scene = MenuScene(self.game)
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if self.left_rect.collidepoint(x, y):
                    self.prev_car()
                elif self.right_rect.collidepoint(x, y):
                    self.next_car()
                elif self.select_button.collidepoint(x, y):
                    from scenes.level_select import LevelSelectionScene
                    self.game.current_scene = LevelSelectionScene(self.game, self.current_car_id)
                    return

    def update(self):
        if self.is_fading:
            self.fade_alpha += self.fade_direction * 20
            if self.fade_alpha <= 0:
                self.fade_direction = 1
            elif self.fade_alpha >= 255:
                self.is_fading = False

    def draw_stats(self):
        w, h = self.game.screen.get_size()
        start_y = h // 2 + 250
        bar_x = w // 2 - 150
        bar_width = 500
        bar_height = 25
        spacing = 60

        for i, (label, value) in enumerate(self.stats.items()):
            y = start_y + i * spacing
            txt = self.small_font.render(label.upper(), True, (0, 0, 0))
            self.game.screen.blit(txt, (bar_x - 210, y - 5))

            pygame.draw.rect(self.game.screen, (0, 0, 0),
                             (bar_x, y, bar_width, bar_height), 2)
            fill_width = int(bar_width * (value / 100))
            pygame.draw.rect(self.game.screen, (60, 150, 255),
                             (bar_x, y, fill_width, bar_height))

    def draw(self):
        self.game.screen.blit(self.bg_surface, (0, 0))

        car_surface = self.car_image.copy()
        if self.is_fading:
            car_surface.set_alpha(self.fade_alpha)
        self.game.screen.blit(car_surface, self.car_rect)

        self.game.screen.blit(self.arrow_left, self.left_rect)
        self.game.screen.blit(self.arrow_right, self.right_rect)

        name_surface = self.font.render(self.car_name, True, (10, 10, 10))
        name_rect = name_surface.get_rect(center=(self.car_rect.centerx,
                                                  self.car_rect.bottom + 40))
        if self.is_fading:
            name_surface.set_alpha(self.fade_alpha)
        self.game.screen.blit(name_surface, name_rect)

        self.draw_stats()

        pygame.draw.rect(self.game.screen, (180, 180, 180), self.select_button)
        pygame.draw.rect(self.game.screen, (0, 0, 0), self.select_button, 2)
        txt = self.small_font.render("SELECT CAR", True, (0, 0, 0))
        txt_rect = txt.get_rect(center=self.select_button.center)
        self.game.screen.blit(txt, txt_rect)
