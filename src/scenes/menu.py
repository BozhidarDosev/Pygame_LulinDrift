import pygame
import sys
import os
from settings1 import *
from utils.profile_manager import create_profile, load_profile
from scenes.car_select import CarSelectionScene

class MenuScene:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(None, 100)
        self.small_font = pygame.font.Font(None, 60)
        self.bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.bg.fill((240, 240, 240))

        # Menu buttons
        self.buttons = [
            ("NEW GAME", pygame.Rect(SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 80, 400, 80)),
            ("LOAD GAME", pygame.Rect(SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 + 20, 400, 80)),
            ("QUIT", pygame.Rect(SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 + 120, 400, 80))
        ]

        # Input dialog state
        self.input_active = False
        self.input_text = ""
        self.input_mode = None  # "new" or "load"
        self.message = ""

    def open_input(self, mode):
        """Opens text input box for new/load game."""
        self.input_active = True
        self.input_mode = mode
        self.input_text = ""
        self.message = ""

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif self.input_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.confirm_input()
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    else:
                        if len(self.input_text) < 16:
                            self.input_text += event.unicode
                continue

            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                for label, rect in self.buttons:
                    if rect.collidepoint(x, y):
                        if label == "NEW GAME":
                            self.open_input("new")
                        elif label == "LOAD GAME":
                            self.open_input("load")
                        elif label == "QUIT":
                            pygame.quit()
                            sys.exit()

    def confirm_input(self):
        """Triggered when Enter is pressed in input mode."""
        username = self.input_text.strip()
        if not username:
            self.message = "Please enter a valid name."
            return

        if self.input_mode == "new":
            data = create_profile(username)
            if data is None:
                self.message = f"Profile '{username}' already exists!"
            else:
                self.game.current_profile = data
                from scenes.car_select import CarSelectionScene
                self.game.current_scene = CarSelectionScene(self.game)
                return

        elif self.input_mode == "load":
            data = load_profile(username)
            if data is None:
                self.message = f"No save found for '{username}'."
            else:
                self.game.current_profile = data
                from scenes.car_select import CarSelectionScene
                self.game.current_scene = CarSelectionScene(self.game)
                return

        # If message set, reset input mode
        self.input_mode = None
        self.input_active = True

    def draw_input_box(self):
        """Draws text input overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(150)
        self.game.screen.blit(overlay, (0, 0))

        box = pygame.Rect(SCREEN_WIDTH//2 - 250, SCREEN_HEIGHT//2 - 60, 500, 120)
        pygame.draw.rect(self.game.screen, (255, 255, 255), box)
        pygame.draw.rect(self.game.screen, (0, 0, 0), box, 3)

        title = "ENTER RACER NAME"
        title_surface = self.small_font.render(title, True, (0, 0, 0))
        self.game.screen.blit(title_surface, (SCREEN_WIDTH//2 - title_surface.get_width()//2, SCREEN_HEIGHT//2 - 120))

        input_surface = self.small_font.render(self.input_text + "_", True, (0, 0, 0))
        self.game.screen.blit(input_surface, (SCREEN_WIDTH//2 - input_surface.get_width()//2, SCREEN_HEIGHT//2 - 15))

        if self.message:
            msg_surface = self.small_font.render(self.message, True, (180, 0, 0))
            self.game.screen.blit(msg_surface, (SCREEN_WIDTH//2 - msg_surface.get_width()//2, SCREEN_HEIGHT//2 + 80))

    def draw(self):
        self.game.screen.blit(self.bg, (0, 0))

        title_surface = self.font.render(GAME_TITLE, True, (0, 0, 0))
        self.game.screen.blit(title_surface, (SCREEN_WIDTH//2 - title_surface.get_width()//2, 120))

        for label, rect in self.buttons:
            pygame.draw.rect(self.game.screen, (200, 200, 200), rect)
            pygame.draw.rect(self.game.screen, (0, 0, 0), rect, 3)
            txt = self.small_font.render(label, True, (0, 0, 0))
            self.game.screen.blit(txt, txt.get_rect(center=rect.center))

        if self.input_active:
            self.draw_input_box()
