from arctia.common import tile_is_solid, unit_can_reach
from arctia.search import astar

class GoBeside(object):
    """
    The target location must be reachable by the unit.

    Arguments:
        stage:         the Stage containing the unit
        unit:          the unit (e.g., Penguin) whose task this
        target:        the target position as a pair of x-y coordinates
        delay:         the number of turns to delay between steps
        blocked_proc:  the procedure to run if the path is broken
        finished_proc: the procedure to run if the task is finished
    """
    def __init__(self, stage, unit, target, delay=0,
                 blocked_proc=None, finished_proc=None):
        self._unit = unit
        self._delay = delay
        self._timer = 0
        self._target = target
        self._blocked_proc = blocked_proc
        self._finished_proc = finished_proc
        self._stage = stage
        self._finished = False

        assert unit_can_reach(unit, target), \
               'destination tile is unreachable'

        # Find the path to the destination.
        self._path = astar(stage, (unit.x, unit.y), target)

    def enact(self):
        assert not self._finished, \
               'task enacted after it was finished'

        # If the unit is already on the tile it needs to go beside,
        # then step off the tile.
        if (self._unit.x, self._unit.y) == self._target:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if (dx, dy) == (0, 0):
                        continue
                    if not tile_is_solid(
                             self._stage.get_tile_at(
                               self._unit.x + dx,
                               self._unit.y + dy)):
                        self._unit.x += dx
                        self._unit.y += dy
                        self._finished = True
                        self._finished_proc()
                        return
            # It is impossible to step off the tile, so just
            # prolong the task.
            return

        # bug - if we are after an object and the object becomes
        #       unreachable, that should count as a block!
        # If the target is not reachable, call blocked_proc.
        if not unit_can_reach(self._unit, self._target):
            self._finished = True
            self._blocked_proc()
            return

        unit = self._unit
        x, y = unit.x, unit.y
        path = self._path

        if len(path) == 1:
            self._finished = True
            self._finished_proc()
            return

        if self._timer == 0:
            dx, dy = (self._path[0][0] - x, self._path[0][1] - y)
            assert -1 <= dx <= 1
            assert -1 <= dy <= 1

            if not tile_is_solid(self._stage.get_tile_at(x + dx, y + dy)):
                # Step toward the target.
                unit.x += dx
                unit.y += dy
                self._path = path[1:]
            else:
                # The path was blocked, so calculate a new path.
                self._path = astar(self._stage,
                                   (unit.x, unit.y),
                                   self._target)
        if self._delay > 0:
            self._timer = (self._timer + 1) % (self._delay + 1)
