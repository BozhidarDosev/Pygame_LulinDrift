import pygame
import os
import sys
from settings1 import *


class LevelSelectionScene:
    def __init__(self, game, selected_car_id):
        self.game = game
        self.selected_car_id = selected_car_id

        self.rebuild_layout()

    # ---------- LAYOUT ----------

    def rebuild_layout(self):
        w, h = self.game.screen.get_size()

        # Fonts
        self.title_font = pygame.font.Font(None, max(40, int(h * 0.08)))
        self.button_font = pygame.font.Font(None, max(24, int(h * 0.045)))

        # Background
        self.bg = pygame.Surface((w, h))
        self.bg.fill((240, 240, 240))

        # Back button (top-left)
        back_w = int(w * 0.12)
        back_h = int(h * 0.07)
        self.back_button = pygame.Rect(int(w * 0.04), int(h * 0.05), back_w, back_h)

        # Title position
        self.title_pos = (w // 2, int(h * 0.12))

        # Level thumbnails row
        # 3 cards centered horizontally
        card_w = int(w * 0.26)
        card_h = int(h * 0.30)
        gap = int(w * 0.04)

        total_width = card_w * 3 + gap * 2
        start_x = (w - total_width) // 2
        y = int(h * 0.40)

        base_path = os.path.dirname(os.path.dirname(__file__))  # scenes -> src
        levels_path = os.path.join(base_path, "../assets/Levels")

        self.level_cards = []
        for i in range(3):
            rect = pygame.Rect(start_x + i * (card_w + gap), y, card_w, card_h)
            img_path = os.path.join(levels_path, f"level{i+1}_bg.png")
            image = None
            if os.path.exists(img_path):
                image = pygame.image.load(img_path).convert()
                image = pygame.transform.smoothscale(image, (card_w, card_h))
            self.level_cards.append({
                "id": i + 1,
                "rect": rect,
                "image": image,
            })

    # ---------- EVENTS ----------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Optional: F11 toggle
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                if hasattr(self.game, "toggle_fullscreen"):
                    self.game.toggle_fullscreen()
                    self.rebuild_layout()
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # ESC behaves like BACK
                from scenes.car_select import CarSelectionScene
                self.game.current_scene = CarSelectionScene(self.game)
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos

                # Back button
                if self.back_button.collidepoint(x, y):
                    from scenes.car_select import CarSelectionScene
                    self.game.current_scene = CarSelectionScene(self.game)
                    return

                # Level cards
                for card in self.level_cards:
                    if card["rect"].collidepoint(x, y):
                        level_id = card["id"]
                        # For now go to placeholder LevelScene; you can replace later
                        from scenes.game import GameScene
                        self.game.current_scene = GameScene(
                            self.game,
                            level_id,
                            self.selected_car_id
                        )

                        return

    # ---------- DRAW ----------

    def draw(self):
        self.game.screen.blit(self.bg, (0, 0))

        # Back button
        pygame.draw.rect(self.game.screen, (230, 230, 230), self.back_button)
        pygame.draw.rect(self.game.screen, (0, 0, 0), self.back_button, 3)
        back_txt = self.button_font.render("BACK", True, (0, 0, 0))
        back_rect = back_txt.get_rect(center=self.back_button.center)
        self.game.screen.blit(back_txt, back_rect)

        # Title
        title_surface = self.title_font.render("SELECT A LEVEL", True, (0, 0, 0))
        title_rect = title_surface.get_rect(center=self.title_pos)
        self.game.screen.blit(title_surface, title_rect)

        # Level cards
        for card in self.level_cards:
            rect = card["rect"]

            # Border
            pygame.draw.rect(self.game.screen, (0, 0, 0), rect, 3)

            # Image or placeholder
            if card["image"]:
                self.game.screen.blit(card["image"], rect)
            else:
                pygame.draw.rect(self.game.screen, (200, 200, 200), rect)
                txt = self.button_font.render(f"LEVEL {card['id']}", True, (0, 0, 0))
                self.game.screen.blit(txt, txt.get_rect(center=rect.center))
