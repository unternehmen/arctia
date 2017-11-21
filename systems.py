"""
The systems module provides classes which update the game's state.
"""
from partition import partition
from transform import translate

def _refresh_partitions_of_mobs(stage, mobs):
    # This currently assumes that all mobs have
    # the same movement rules!
    parts = []
    for mob in mobs:
        mob.partition = None

        for part in parts:
            if part[mob.y][mob.x]:
                mob.partition = part
                break

        if not mob.partition:
            part = partition(stage, (mob.x, mob.y))
            mob.partition = part
            parts.append(part)

class PartitionUpdateSystem(object):
    """
    A PartitionUpdateSystem updates the partition matrix of units.

    A partition matrix shows whether a unit can reach a location
    given its movement constraints.  This makes testing reachability
    an O(1) operation so long as the partition matrices of all units
    is up-to-date.

    Arguments:
        stage: the stage
        mobs: the list of units
    """
    def __init__(self, stage, mobs):
        self._mobs = mobs
        self._stage = stage

        stage.register_tile_change_listener(self)

        self.refresh()

    def tile_changed(self, _unused_prev_id, _unused_cur_id, coords):
        """
        Notify the PartitionUpdateSystem that a tile has changed.

        Arguments:
            _unused_prev_id: this argument is not used
            _unused_cur_id: this argument is not used
            coords: the (x, y) coordinates of the changed tile
        """
        x, y = coords

        # Determine which mobs need partition refreshs.
        mobs_to_refresh = []

        for mob in self._mobs:
            need_refresh = False

            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    other_x, other_y = \
                      translate((x, y), (dx, dy))

                    if mob.partition[other_y][other_x]:
                        need_refresh = True
                        break
                if need_refresh:
                    break
            if need_refresh:
                mobs_to_refresh.append(mob)

        # Update partitions on mobs which need it.
        _refresh_partitions_of_mobs(self._stage, mobs_to_refresh)


    def refresh(self):
        """
        Update the partition matrices of all known mobs.
        """
        _refresh_partitions_of_mobs(self._stage, self._mobs)
