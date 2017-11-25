class Entity(object):
    """
    An Entity is a immobile item in the game, e.g., a stone.
    """
    def __init__(self, kind, location):
        assert kind in ('bug', 'rock', 'fish'), \
               'unknown entity kind: %s' % (kind,)

        self.location = location
        self.kind = kind
