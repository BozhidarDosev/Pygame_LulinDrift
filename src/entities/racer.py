import pygame

class Racer:
    def __init__(self, image, x, y, speed):
        self.image = image
        self.pos = [x, y]
        self.speed = speed

    def update(self):
        self.pos[1] -= self.speed  # move forward (up)

    def draw(self, screen):
        screen.blit(self.image, self.pos)
