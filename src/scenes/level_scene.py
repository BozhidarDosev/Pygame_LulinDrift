import pygame
import os
import sys
from settings1 import *

class LevelScene:
    def __init__(self, game, level_id, selected_car_id):
        self.game = game
        self.level_id = level_id
        self.selected_car_id = selected_car_id

        base_path = os.path.dirname(os.path.dirname(__file__))  # scenes -> src
        img_path = os.path.join(base_path, f"../assets/Levels/level{level_id}_bg.jpg")

        if os.path.exists(img_path):
            self.bg = pygame.image.load(img_path).convert()
            w, h = self.game.screen.get_size()
            self.bg = pygame.transform.scale(self.bg, (w, h))
        else:
            self.bg = pygame.Surface(self.game.screen.get_size())
            self.bg.fill((80, 80, 80))

        self.font = pygame.font.Font(None, 80)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                from scenes.level_select import LevelSelectionScene
                self.game.current_scene = LevelSelectionScene(
                    self.game, self.selected_car_id
                )

    def draw(self):
        self.game.screen.blit(self.bg, (0, 0))
        txt = self.font.render(f"LEVEL {self.level_id}", True, (255, 255, 255))
        rect = txt.get_rect(center=(self.game.screen.get_width() // 2, 80))
        self.game.screen.blit(txt, rect)
