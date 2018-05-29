from .common import make_2d_constant_array

class Stockpile(object):
    def __init__(self, stage, rect, accepted_kinds):
        self.x, self.y, self.width, self.height = rect
        self.accepted_kinds = accepted_kinds
        self._stage = stage

    def draw(self, screen, tileset, camera):
        for y in range(self.y, self.y + self.height):
            for x in range(self.x, self.x + self.width):
                screen.blit(tileset,
                            camera.transform_game_to_screen(
                                (x, y), scalar=16),
                            (176, 0, 16, 16))
