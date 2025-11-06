from scenes.game import GameScene

class LevelManager:
    def __init__(self, game):
        self.game = game
        self.current_level = 1

    def next_level(self):
        self.current_level += 1
        if self.current_level > 3:
            self.current_level = 1
        self.game.current_scene = GameScene(self.game, self.current_level, self.current_level)
