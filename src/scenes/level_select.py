import pygame
import os
import sys
from settings1 import *

class LevelSelectionScene:
    def __init__(self, game, selected_car_id):
        self.game = game
        self.selected_car_id = selected_car_id
        self.font = pygame.font.Font(None, 80)
        self.small_font = pygame.font.Font(None, 50)

        # Load background placeholder
        self.bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.bg_surface.fill((235, 235, 235))  # light gray background

        # Assets path
        base_path = os.path.dirname(os.path.dirname(__file__))  # from scenes/ to src/
        self.assets_path = os.path.join(base_path, "../assets/Levels")

        # Create level previews (3 slots)
        self.levels = []
        spacing = 200
        rect_width = 400
        rect_height = 250
        start_x = (SCREEN_WIDTH - (3 * rect_width + 2 * spacing)) // 2
        y = SCREEN_HEIGHT // 2 - rect_height // 2

        for i in range(3):
            x = start_x + i * (rect_width + spacing)
            rect = pygame.Rect(x, y, rect_width, rect_height)
            img_path = os.path.join(self.assets_path, f"level{i+1}_bg.jpg")
            image = None
            if os.path.exists(img_path):
                image = pygame.image.load(img_path).convert()
                image = pygame.transform.scale(image, (rect_width, rect_height))
            self.levels.append({
                "id": i + 1,
                "rect": rect,
                "image": image
            })

        # Back button
        self.back_button = pygame.Rect(50, 50, 200, 70)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos

                # Back button
                if self.back_button.collidepoint(x, y):
                    from scenes.car_select import CarSelectionScene
                    self.game.current_scene = CarSelectionScene(self.game)
                    return

                # Level click
                for level in self.levels:
                    if level["rect"].collidepoint(x, y):
                        print(f"Selected Level {level['id']}")  # debug
                        from scenes.level_scene import LevelScene
                        self.game.current_scene = LevelScene(self.game, level["id"], self.selected_car_id)
                        return

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                from scenes.car_select import CarSelectionScene
                self.game.current_scene = CarSelectionScene(self.game)

    def draw(self):
        self.game.screen.blit(self.bg_surface, (0, 0))

        # Title
        title_surface = self.font.render("SELECT A LEVEL", True, (0, 0, 0))
        self.game.screen.blit(title_surface, (SCREEN_WIDTH // 2 - title_surface.get_width() // 2, 120))

        # Draw levels
        for level in self.levels:
            rect = level["rect"]
            pygame.draw.rect(self.game.screen, (0, 0, 0), rect, 3)
            if level["image"]:
                self.game.screen.blit(level["image"], rect)
            else:
                pygame.draw.rect(self.game.screen, (190, 190, 190), rect)
                txt = self.small_font.render(f"LEVEL {level['id']}", True, (0, 0, 0))
                self.game.screen.blit(txt, txt.get_rect(center=rect.center))

        # Back button
        pygame.draw.rect(self.game.screen, (200, 200, 200), self.back_button)
        pygame.draw.rect(self.game.screen, (0, 0, 0), self.back_button, 2)
        txt = self.small_font.render("BACK", True, (0, 0, 0))
        txt_rect = txt.get_rect(center=self.back_button.center)
        self.game.screen.blit(txt, txt_rect)
