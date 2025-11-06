import pygame
import os
import sys
from settings1 import *
from scenes.level_manager import LevelManager

class CarSelectionScene:
    def __init__(self, game):
        self.game = game
        self.current_car_id = 1

        # Paths
        base_path = os.path.dirname(os.path.dirname(__file__))  # from scenes/ to src/
        self.assets_path = os.path.join(base_path, "../assets")

        # Load custom font (fallback if missing)
        font_path = os.path.join(self.assets_path, "Basic/Dalmation-FREE.otf")
        if os.path.exists(font_path):
            self.font = pygame.font.Font(font_path, 70)
            self.small_font = pygame.font.Font(font_path, 45)
        else:
            self.font = pygame.font.SysFont("Arial", 70, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 45, bold=True)

        # Load UI arrows
        self.arrow_left = pygame.image.load(os.path.join(self.assets_path, "Basic/arrow_left.png")).convert_alpha()
        self.arrow_right = pygame.image.load(os.path.join(self.assets_path, "Basic/arrow_right.png")).convert_alpha()

        # Adjusted arrow positions (moved slightly up)
        self.left_rect = self.arrow_left.get_rect(center=(400, SCREEN_HEIGHT // 2 - 100))
        self.right_rect = self.arrow_right.get_rect(center=(SCREEN_WIDTH - 400, SCREEN_HEIGHT // 2 - 100))

        # Select button
        self.select_button = pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT - 150, 400, 80)

        # Placeholder background
        self.bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.bg_surface.fill((220, 220, 220))  # light gray

        # Fade animation variables
        self.fade_alpha = 255
        self.is_fading = False
        self.fade_direction = -1

        self.load_current_car()

    def load_current_car(self):
        """Loads the current car image and info based on current_car_id"""
        car_data = CAR_ASSETS[self.current_car_id]
        car_folder = car_data["folder"]
        car_front = car_data["front"]

        car_path = os.path.join(self.assets_path, f"Car images/{car_folder}/{car_front}")
        if not os.path.exists(car_path):
            raise FileNotFoundError(f"Missing car image: {car_path}")

        self.car_image = pygame.image.load(car_path).convert_alpha()

        # Resize for preview (so it fits nicely)
        max_width, max_height = 800, 400
        self.car_image = pygame.transform.smoothscale(self.car_image, (max_width, max_height))
        # Move car image up slightly
        self.car_rect = self.car_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150))

        # Name + stats
        self.car_name = car_folder.replace("_", " ").upper()
        self.stats = car_data["stats"]

        # Reset fade animation
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
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if self.left_rect.collidepoint(x, y):
                    self.prev_car()
                elif self.right_rect.collidepoint(x, y):
                    self.next_car()
                elif self.select_button.collidepoint(x, y):
                    from scenes.level_select import LevelSelectionScene
                    self.game.current_scene = LevelSelectionScene(self.game, self.current_car_id)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                from scenes.menu import MenuScene
                self.game.current_scene = MenuScene(self.game)

    def update(self):
        # Fade effect
        if self.is_fading:
            self.fade_alpha += self.fade_direction * 20
            if self.fade_alpha <= 0:
                self.fade_direction = 1  # fade in
            elif self.fade_alpha >= 255:
                self.is_fading = False

    def draw_stats(self):
        """Draw 3 bars showing speed/handling/acceleration"""
        start_y = SCREEN_HEIGHT // 2 + 150  # moved slightly up
        bar_x = SCREEN_WIDTH // 2 - 150
        bar_width = 500
        bar_height = 25
        spacing = 60

        for i, (label, value) in enumerate(self.stats.items()):
            y = start_y + i * spacing
            # Label
            txt = self.small_font.render(label.upper(), True, (0, 0, 0))
            self.game.screen.blit(txt, (bar_x - 210, y - 5))
            # Bar outline
            pygame.draw.rect(self.game.screen, (0, 0, 0), (bar_x, y, bar_width, bar_height), 2)
            # Filled part
            fill_width = int(bar_width * (value / 100))
            pygame.draw.rect(self.game.screen, (60, 150, 255), (bar_x, y, fill_width, bar_height))

    def draw(self):
        self.game.screen.blit(self.bg_surface, (0, 0))

        # Car preview (moved slightly up)
        car_surface = self.car_image.copy()
        if self.is_fading:
            car_surface.set_alpha(self.fade_alpha)
        self.game.screen.blit(car_surface, self.car_rect)

        # Arrows (also slightly up)
        self.game.screen.blit(self.arrow_left, self.left_rect)
        self.game.screen.blit(self.arrow_right, self.right_rect)

        # Car name BELOW the car image
        name_surface = self.font.render(self.car_name, True, (10, 10, 10))
        name_rect = name_surface.get_rect(center=(SCREEN_WIDTH // 2, self.car_rect.bottom + 60))
        if self.is_fading:
            name_surface.set_alpha(self.fade_alpha)
        self.game.screen.blit(name_surface, name_rect)

        # Stats bars
        self.draw_stats()

        # Select button
        pygame.draw.rect(self.game.screen, (180, 180, 180), self.select_button)
        pygame.draw.rect(self.game.screen, (0, 0, 0), self.select_button, 2)
        txt = self.small_font.render("SELECT CAR", True, (0, 0, 0))
        txt_rect = txt.get_rect(center=self.select_button.center)
        self.game.screen.blit(txt, txt_rect)
