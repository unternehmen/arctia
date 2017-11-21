class Stockpile(object):
    def __init__(self, stage, rect, accepted_kinds):
        self.x, self.y, self.width, self.height = rect
        self.accepted_kinds = accepted_kinds
        self._stage = stage
        self._reservations = \
            [[False for x in range(self.x, self.x + self.width)]
             for y in range(self.y, self.y + self.height)]

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

    def _entity_at(self, relative_location):
        """
        Return the entity which is at a location relative to the pile.

        Arguments:
            location: the location as an (x, y) tuple

        Returns:
            the entity if there is one, otherwise None
        """
        x, y = relative_location
        return self._stage.entity_at((self.x + x, self.y + y))

    def _slot_is_reserved(self, relative_location):
        """
        Return whether a slot at some location is reserved.
        """
        x, y = relative_location
        return self._reservations[y][x]

    @property
    def full(self):
        for y in range(self.height):
            for x in range(self.width):
                if self._slot_is_reserved((x, y)):
                    continue

                entity = self._entity_at((x, y))

                if not entity or entity.kind not in self.accepted_kinds:
                    return False
        return True

    def draw(self, screen, tileset, camera):
        for y in range(self.y, self.y + self.height):
            for x in range(self.x, self.x + self.width):
                screen.blit(tileset,
                            camera.transform_game_to_screen(
                                (x, y), scalar=16),
                            (176, 0, 16, 16))

    def reserve_slot(self):
        for y in range(self.height):
            for x in range(self.width):
                if self._slot_is_reserved((x, y)):
                    continue

                entity = self._entity_at((x, y))

                if not entity or entity.kind not in self.accepted_kinds:
                    self._reservations[y][x] = True
                    return self.x + x, self.y + y

        assert False, "tried to reserve a slot " + \
                      "but none are available!"

    def relinquish_slot(self, location):
        x, y = location[0] - self.x, \
               location[1] - self.y
        assert self._slot_is_reserved((x, y))
        self._reservations[y][x] = False
