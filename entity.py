class Entity(object):
    """
    An Entity is a immobile item in the game, e.g., a stone.
    """
    def __init__(self, kind):
        assert kind in ('bug', 'rock', 'fish'), \
               'unknown entity kind: %s' % (kind,)

        self.kind = kind
        self.reserved = False

    def reserve(self):
        self.reserved = True

    def relinquish(self):
        self.reserved = False
