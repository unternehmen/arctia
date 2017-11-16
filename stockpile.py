from config import *

class Stockpile(object):
    def _detect_acceptable_item_at(self, x, y):
        tid = self._stage.get_tile_at(x, y)

        kind = ''
        if tid == 4:
            kind = 'fish'
        elif tid == 6:
            kind = 'rock'
        elif tid == 7:
            kind = 'bug'

        return kind in self.accepted_kinds

    def __init__(self, stage, rect, jobs, accepted_kinds):
        self.x, self.y, self.w, self.h = rect
        self.accepted_kinds = accepted_kinds
        self._stage = stage
        self._reservations = [[False
                               for x in range(self.x, self.x + self.w)]
                              for y in range(self.y, self.y + self.h)]

    @property
    def full(self):
        for y in range(self.h):
            for x in range(self.w):
                if self._reservations[y][x]:
                    continue

                entity = self._stage.entity_at((self.x + x, self.y + y))

                if not entity or entity.kind not in self.accepted_kinds:
                    return False
        return True

    def draw(self, screen, tileset, camera_x, camera_y):
        for y in range(self.y, self.y + self.h):
            for x in range(self.x, self.x + self.w):
                screen.blit(tileset,
                            (x * 16 - camera_x \
                             + MENU_WIDTH,
                             y * 16 - camera_y),
                            (176, 0, 16, 16))

    def reserve_slot(self):
        for y in range(self.h):
            for x in range(self.w):
                if self._reservations[y][x]:
                    continue

                entity = self._stage.entity_at((self.x + x, self.y + y))

                if not entity or entity.kind not in self.accepted_kinds:
                    self._reservations[y][x] = True
                    return self.x + x, self.y + y

        assert False, "tried to reserve a slot " + \
                      "but none are available!"

    def relinquish_slot(self, location):
        x, y = location
        assert self._reservations[y - self.y][x - self.x]
        self._reservations[y - self.y][x - self.x] = False
