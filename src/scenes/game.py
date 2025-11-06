import sys
import pygame
import os
from settings1 import *

class GameScene:
    def __init__(self, game, level, car_id):
        self.game = game
        self.level = level
        self.car_id = car_id

        # --- Correct asset paths ---
        base_path = os.path.dirname(os.path.dirname(__file__))  # from scenes/ to src/
        assets_path = os.path.join(base_path, "../assets")

        # Background
        level_bg_path = os.path.join(assets_path, f"Levels/level{level}_bg.png")
        self.bg = pygame.image.load(level_bg_path).convert()
        self.bg = pygame.transform.scale(self.bg, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # Car (use mapping from settings)
        car_data = CAR_ASSETS.get(car_id)
        if not car_data:
            raise ValueError(f"Invalid car_id: {car_id}")

        car_folder = car_data["folder"]
        car_image_name = car_data["front"]

        car_path = os.path.join(assets_path, f"Car images/{car_folder}/{car_image_name}")
        if not os.path.exists(car_path):
            raise FileNotFoundError(f"Car image not found at {car_path}")

        self.car_image = pygame.image.load(car_path).convert_alpha()

        # Player position
        self.player_pos = [
            SCREEN_WIDTH // 2 - self.car_image.get_width() // 2,
            SCREEN_HEIGHT - 200
        ]
        self.speed = 12

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            from scenes.menu import MenuScene
            self.game.current_scene = MenuScene(self.game)

        if keys[pygame.K_LEFT]:
            self.player_pos[0] -= self.speed
        if keys[pygame.K_RIGHT]:
            self.player_pos[0] += self.speed

    def update(self):
        # Keep the car inside the screen
        self.player_pos[0] = max(0, min(self.player_pos[0],
                                        SCREEN_WIDTH - self.car_image.get_width()))

    def draw(self):
        self.game.screen.blit(self.bg, (0, 0))
        self.game.screen.blit(self.car_image, self.player_pos)
