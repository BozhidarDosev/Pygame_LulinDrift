import pygame
import sys
import os
from settings1 import *
from scenes.level_select import LevelSelectionScene

class MenuScene:
    def __init__(self, game):
        self.game = game
        self.rebuild_layout()

    def rebuild_layout(self):
        base_path = os.path.dirname(os.path.dirname(__file__))  # scenes -> src
        self.assets_path = os.path.join(base_path, "../assets")

        # font
        font_path = os.path.join(self.assets_path, "Basic/Dalmation-FREE.otf")
        if os.path.exists(font_path):
            self.title_font = pygame.font.Font(font_path, 100)
            self.button_font = pygame.font.Font(font_path, 100)
        else:
            self.font = pygame.font.SysFont("Arial", 70, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 45, bold=True)

        w, h = self.game.screen.get_size()


        # background
        base_path = os.path.dirname(os.path.dirname(__file__))  # scenes -> src
        img_path = os.path.join(base_path, f"../assets/Basic/menu_bg.png")

        if os.path.exists(img_path):
            self.bg = pygame.image.load(img_path).convert()
            w, h = self.game.screen.get_size()
            self.bg = pygame.transform.scale(self.bg, (w, h))
        else:
            self.bg = pygame.Surface(self.game.screen.get_size())
            self.bg.fill((80, 80, 80))

        # Buttons
        button_width = int(w * 0.3)
        button_height = int(h * 0.07)
        gap = int(h * 0.01)

        start_x = (w - button_width) // 2
        start_y = int(h * 0.75)

        self.buttons = [
            ("NEW GAME", pygame.Rect(start_x, start_y + 0 * (button_height + gap), button_width, button_height)),
            ("LOAD GAME", pygame.Rect(start_x, start_y + 1 * (button_height + gap), button_width, button_height)),
            ("QUIT", pygame.Rect(start_x, start_y + 2 * (button_height + gap), button_width, button_height)),
        ]

        # Title position
        self.title_pos = (w // 2, int(h * 0.18))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                for label, rect in self.buttons:
                    if rect.collidepoint(x, y):
                        if label == "NEW GAME":
                            self.game.current_scene = LevelSelectionScene(self.game, 1)  # pass selected car_id as 1 for now
                        elif label == "LOAD GAME":
                            self.open_load_game()
                        elif label == "QUIT":
                            pygame.quit()
                            sys.exit()

    def open_load_game(self):
        self.game.current_scene = LevelSelectionScene(self.game, 1)  # temporary, change later to load game logic

    def draw(self):
        self.game.screen.blit(self.bg, (0, 0))

        # Title
        title_surface = self.title_font.render("LULIN DRIFT", True, (0, 0, 0))
        title_rect = title_surface.get_rect(center=self.title_pos)
        self.game.screen.blit(title_surface, title_rect)

        # Draw buttons
        for label, rect in self.buttons:
            # Only the border and text (no fill)
            #pygame.draw.rect(self.game.screen, (0, 0, 0), rect, 3)  # Button border
            txt = self.button_font.render(label, True, (211, 211, 211))  # Button text color
            txt_rect = txt.get_rect(center=rect.center)
            self.game.screen.blit(txt, txt_rect)
