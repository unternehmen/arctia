"""
The team module provides a class (Team) for coordinating units.
"""
class Team(object):
    """
    A Team allows units to coordinate, i.e., reserve things.
    """
    def __init__(self):
        self.designations = []
        self.reservations = {
            'entity': [],
            'location': [],
            'mine': []
        }
        print('Dont forget to put stockpiles into the Team object')
        self.stockpiles = []

    def _assert_is_legal_kind(self, kind):
        assert kind in self.reservations, \
               'illegal reservation kind: %s' % (kind,)

    def reserve(self, kind, obj):
        """
        Make a reservation of a given kind on an object.

        Arguments:
            kind: the kind of object
            obj: the object
        """
        self._assert_is_legal_kind(kind)
        assert not self.is_reserved(kind, obj), \
               'tried to reserve already-reserved %s' % (kind,)
        self.reservations[kind].append(obj)

    def relinquish(self, kind, obj):
        """
        Delete a reservation of a given kind on an object.

        Arguments:
            kind: the kind of object
            obj: the object
        """
        self._assert_is_legal_kind(kind)
        assert self.is_reserved(kind, obj), \
               'tried to relinquish already-unreserved %s' % (kind,)
        self.reservations[kind].remove(obj)

    def is_reserved(self, kind, obj):
        """
        Return whether a reservation of the given kind is on an object.

        Arguments:
            kind: the kind of object
            obj: the object

        Returns: whether the entity is reserved
        """
        self._assert_is_legal_kind(kind)
        return obj in self.reservations[kind]
