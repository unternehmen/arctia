"""
The team module provides a class (Team) for coordinating units.
"""
class Team(object):
    """
    A Team allows units to obey designations and make reservations.
    """
    def __init__(self):
        self.designations = []
        self.reservations = {
            'entity': [],
            'location': [],
            'mine': [],
            'designations': []
        }
        self.stockpiles = []

    def _assert_is_legal_kind(self, kind):
        assert kind in self.reservations, \
               'illegal reservation kind: %s' % (kind,)

    def reserve(self, kind, obj):
        """
        Make a reservation of a given kind on an object.

        Arguments:
            kind: the kind of reservation
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
            kind: the kind of reservation
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
            kind: the kind of reservation
            obj: the object

        Returns: whether the entity is reserved
        """
        self._assert_is_legal_kind(kind)
        return obj in self.reservations[kind]

    def get_unreserved_designations(self, kind):
        """
        Return a list of all unreserved designations of a certain kind.

        Args:
            kind (string): The kind of designation.

        Returns:
            A list of all unreserved designations of the given kind.
        """
        return list(filter(lambda d:
                             d['kind'] == kind
                             and not self.is_reserved('designation', d),
                           self.designations))

