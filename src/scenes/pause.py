import pygame
from settings1 import *

class PauseScene:
    def __init__(self, game, previous_scene):
        self.game = game
        self.previous_scene = previous_scene
        self.font = pygame.font.Font(None, 120)
        self.resume_rect = pygame.Rect(760, 500, 400, 100)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game.current_scene = self.previous_scene
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.resume_rect.collidepoint(event.pos):
                    self.game.current_scene = self.previous_scene

    def update(self):
        pass

    def draw(self):
        self.previous_scene.draw()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(120)
        overlay.fill((0, 0, 0))
        self.game.screen.blit(overlay, (0, 0))
        text = self.font.render("PAUSED", True, (255, 255, 255))
        self.game.screen.blit(text, (SCREEN_WIDTH // 2 - 180, 300))
        pygame.draw.rect(self.game.screen, (255, 255, 255), self.resume_rect, border_radius=10)
        txt = pygame.font.Font(None, 60).render("Resume", True, (0, 0, 0))
        self.game.screen.blit(txt, (self.resume_rect.x + 100, self.resume_rect.y + 25))
