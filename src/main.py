import pygame
from settings1 import *
from scenes.menu import MenuScene

pygame.init()

class Game:
    def __init__(self):
        pygame.display.set_caption(GAME_TITLE)


        # Borderless fullscreen at native resolution
        BASE_W, BASE_H = 1920,1080
        flags = pygame.SCALED | pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((BASE_W, BASE_H), flags)

        self.clock = pygame.time.Clock()
        self.current_scene = MenuScene(self)
        self.current_profile = None

    def toggle_fullscreen(self):
        """Toggle between windowed 2560x1440 and borderless fullscreen."""
        pass

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.current_scene.handle_events()

            # if current_scene has update(), call it
            if hasattr(self.current_scene, "update"):
                self.current_scene.update()

            self.current_scene.draw()
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()
