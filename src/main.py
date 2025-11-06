import pygame
import sys
import os
from settings1 import *
from scenes.menu import MenuScene

pygame.init()

class Game:
    def __init__(self):
        pygame.display.set_caption(GAME_TITLE)

        # Borderless fullscreen (uses native monitor resolution)
        self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)

        # Optional: lock cursor inside window (disable if unwanted)
        pygame.event.set_grab(True)

        # Store display info
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h

        print(f"Resolution: {self.screen_width}x{self.screen_height}")

        self.clock = pygame.time.Clock()
        self.current_scene = MenuScene(self)
        self.current_profile = None
        self.fullscreen = True  # starts borderless fullscreen

    def toggle_fullscreen(self):
        """Toggle between windowed (2K) and borderless fullscreen."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
        else:
            os.environ["SDL_VIDEO_CENTERED"] = "1"
            self.screen = pygame.display.set_mode((2560, 1440))

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.current_scene.handle_events()
            self.current_scene.draw()
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()
