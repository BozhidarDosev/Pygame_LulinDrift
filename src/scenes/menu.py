import pygame
import sys
import os
from settings1 import *
from utils.profile_manager import create_profile, load_profile
from scenes.car_select import CarSelectionScene

class MenuScene:
    def __init__(self, game):
        self.game = game
        self.rebuild_layout()
        self.input_active = False
        self.input_text = ""
        self.message = ""
        self.input_mode = None

    def rebuild_layout(self):
        base_path = os.path.dirname(os.path.dirname(__file__))
        self.assets_path = os.path.join(base_path, "../assets")

        # fonts
        font_path = os.path.join(self.assets_path, "Basic/Dalmation-FREE.otf")
        if os.path.exists(font_path):
            self.title_font = pygame.font.Font(font_path, 120)
            self.button_font = pygame.font.Font(font_path, 85)
        else:
            self.title_font = pygame.font.SysFont("Arial", 120, bold=True)
            self.button_font = pygame.font.SysFont("Arial", 85, bold=True)

        w, h = self.game.screen.get_size()

        # background
        img_path = os.path.join(self.assets_path, "Basic/menu_bg.png")
        if os.path.exists(img_path):
            self.bg = pygame.image.load(img_path).convert()
            self.bg = pygame.transform.scale(self.bg, (w, h))
        else:
            self.bg = pygame.Surface((w, h))
            self.bg.fill((80, 80, 80))

        # button positions (2x2 grid)
        col1_x = int(w * 0.28)
        col2_x = int(w * 0.72)
        top_y  = int(h * 0.72)
        bot_y  = int(h * 0.82)

        self.buttons = {
            "NEW GAME": pygame.Rect(col1_x, top_y, 0, 0),
            "SETTINGS": pygame.Rect(col2_x, top_y, 0, 0),
            "LOAD GAME": pygame.Rect(col1_x, bot_y, 0, 0),
            "QUIT": pygame.Rect(col2_x, bot_y, 0, 0),
        }

        self.title_pos = (w // 2, int(h * 0.18))

    # ----------- EVENT HANDLING -------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.input_active:
                self.handle_input_events(event)
            else:
                self.handle_menu_clicks(event)

    def handle_menu_clicks(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos

            for label, rect in self.buttons.items():
                # text-only buttons use point distance, so check text rect
                txt = self.button_font.render(label, True, (255, 255, 255))
                txt_rect = txt.get_rect(center=rect.center)

                if txt_rect.collidepoint(x, y):

                    if label == "NEW GAME":
                        self.open_input("new")
                    elif label == "LOAD GAME":
                        self.open_input("load")
                    elif label == "SETTINGS":
                        print("SETTINGS clicked — add settings scene later")
                    elif label == "QUIT":
                        pygame.quit()
                        sys.exit()

    # ----------- INPUT LOGIC -----------------
    def handle_input_events(self, event):
        # if event.key == pygame.K_ESCAPE:
        #     self.input_active = False
        #     self.message = "sdfsfsdf"

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

    def open_input(self, mode):
        self.input_active = True
        self.input_text = ""
        self.message = ""
        self.input_mode = mode

    def confirm_input(self):
        username = self.input_text.strip()
        if not username:
            self.message = "Please enter a valid name."
            return

        if self.input_mode == "new":
            data = create_profile(username)
            if data is None:
                self.message = f"Profile '{username}' already exists!"
                return
            self.game.current_profile = data
            self.input_active = False
            self.game.current_scene = CarSelectionScene(self.game)
            return

        elif self.input_mode == "load":
            data = load_profile(username)
            if data is None:
                self.message = f"No save found for '{username}'."
                return
            self.game.current_profile = data
            self.input_active = False
            self.game.current_scene = CarSelectionScene(self.game)
            return

    # ----------- INPUT OVERLAY ---------------
    def draw_input_box(self):
        w, h = self.game.screen.get_size()

        # Dim background
        overlay = pygame.Surface((w, h))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        self.game.screen.blit(overlay, (0, 0))

        # Popup box
        box_w, box_h = int(w * 0.4), int(h * 0.18)
        box = pygame.Rect((w - box_w) // 2, (h - box_h) // 2, box_w, box_h)
        pygame.draw.rect(self.game.screen, (255, 255, 255), box)
        pygame.draw.rect(self.game.screen, (0, 0, 0), box, 3)

        font = pygame.font.Font(None, 50)

        title = font.render("ENTER RACER NAME", True, (0, 0, 0))
        self.game.screen.blit(title, (w // 2 - title.get_width() // 2, box.top + 20))

        text = font.render(self.input_text + "_", True, (0, 0, 0))
        self.game.screen.blit(text, (w // 2 - text.get_width() // 2, box.centery - 15))

        if self.message:
            msg = font.render(self.message, True, (200, 0, 0))
            self.game.screen.blit(msg, (w // 2 - msg.get_width() // 2, box.bottom - 40))

    # ------------------ DRAW ------------------
    def draw(self):
        self.game.screen.blit(self.bg, (0, 0))

        # Title
        title = self.title_font.render("LULIN DRIFT", True, (255, 255, 255))
        self.game.screen.blit(title, title.get_rect(center=self.title_pos))

        # 2×2 grid buttons
        for label, rect in self.buttons.items():
            txt = self.button_font.render(label, True, (220, 220, 220))
            txt_rect = txt.get_rect(center=rect.center)
            self.game.screen.blit(txt, txt_rect)

        # input popup
        if self.input_active:
            self.draw_input_box()
