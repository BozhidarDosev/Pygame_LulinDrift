import pygame
import sys
from settings1 import *
from utils.profile_manager import create_profile, load_profile

class MenuScene:
    def __init__(self, game):
        self.game = game

        self.input_active = False
        self.input_text = ""
        self.input_mode = None  # "new" or "load"
        self.message = ""

        self.rebuild_layout()

    def rebuild_layout(self):
        w, h = self.game.screen.get_size()

        # fonts
        title_size = max(40, int(h * 0.08))
        button_font_size = max(24, int(h * 0.04))
        self.title_font = pygame.font.Font(None, title_size)
        self.button_font = pygame.font.Font(None, button_font_size)

        # background
        self.bg = pygame.Surface((w, h))
        self.bg.fill((240, 240, 240))

        # buttons
        button_width = int(w * 0.25)
        button_height = int(h * 0.06)
        spacing = int(h * 0.02)

        start_x = (w - button_width) // 2
        start_y = int(h * 0.45)

        self.buttons = [
            ("NEW GAME", pygame.Rect(start_x, start_y + 0 * (button_height + spacing),
                                     button_width, button_height)),
            ("LOAD GAME", pygame.Rect(start_x, start_y + 1 * (button_height + spacing),
                                      button_width, button_height)),
            ("QUIT", pygame.Rect(start_x, start_y + 2 * (button_height + spacing),
                                 button_width, button_height)),
        ]

        self.title_center = (w // 2, int(h * 0.18))

    # ---------- input overlay ----------

    def open_input(self, mode: str):
        self.input_active = True
        self.input_mode = mode
        self.input_text = ""
        self.message = ""

    def confirm_input(self):
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
                self.input_active = False
                from scenes.car_select import CarSelectionScene
                self.game.current_scene = CarSelectionScene(self.game)
                return

        elif self.input_mode == "load":
            data = load_profile(username)
            if data is None:
                self.message = f"No save found for '{username}'."
            else:
                self.game.current_profile = data
                self.input_active = False
                from scenes.car_select import CarSelectionScene
                self.game.current_scene = CarSelectionScene(self.game)
                return

    def draw_input_box(self):
        w, h = self.game.screen.get_size()
        overlay = pygame.Surface((w, h))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(160)
        self.game.screen.blit(overlay, (0, 0))

        box_w, box_h = int(w * 0.4), int(h * 0.18)
        box = pygame.Rect((w - box_w) // 2, (h - box_h) // 2, box_w, box_h)

        pygame.draw.rect(self.game.screen, (255, 255, 255), box)
        pygame.draw.rect(self.game.screen, (0, 0, 0), box, 3)

        label_font = pygame.font.Font(None, max(28, int(h * 0.035)))

        title = label_font.render("ENTER RACER NAME", True, (0, 0, 0))
        self.game.screen.blit(
            title,
            (w // 2 - title.get_width() // 2, box.top + 15)
        )

        text = label_font.render(self.input_text + "_", True, (0, 0, 0))
        self.game.screen.blit(
            text,
            (w // 2 - text.get_width() // 2, box.centery - 10)
        )

        if self.message:
            msg = label_font.render(self.message, True, (180, 0, 0))
            self.game.screen.blit(
                msg,
                (w // 2 - msg.get_width() // 2, box.bottom - 35)
            )

    # ---------- events ----------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.input_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.confirm_input()
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.input_active = False
                        self.message = ""
                    else:
                        if len(self.input_text) < 16 and event.unicode.isprintable():
                            self.input_text += event.unicode
                continue  # don't click buttons while dialog is open

            if event.type == pygame.MOUSEBUTTONDOWN:
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

    # ---------- draw ----------

    def draw(self):
        self.game.screen.blit(self.bg, (0, 0))

        title_surface = self.title_font.render(GAME_TITLE, True, (0, 0, 0))
        title_rect = title_surface.get_rect(center=self.title_center)
        self.game.screen.blit(title_surface, title_rect)

        for label, rect in self.buttons:
            pygame.draw.rect(self.game.screen, (210, 210, 210), rect)
            pygame.draw.rect(self.game.screen, (0, 0, 0), rect, 3)

            txt = self.button_font.render(label, True, (0, 0, 0))
            txt_rect = txt.get_rect(center=rect.center)
            self.game.screen.blit(txt, txt_rect)

        if self.input_active:
            self.draw_input_box()
