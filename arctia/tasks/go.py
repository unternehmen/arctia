from arctia.common import tile_is_solid
from arctia.search import astar

class Go(object):
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
        self._target_is_solid = \
          tile_is_solid(stage.get_tile_at(target[0], target[1]))
        self._blocked_proc = blocked_proc
        self._finished_proc = finished_proc
        self._stage = stage
        self._finished = False

        assert self._target_is_reachable(), \
               'destination tile is unreachable'

        # Find the path to the destination.
        self._path = astar(stage, (unit.x, unit.y), target)

    def _target_is_reachable(self):
        tx, ty = self._target
        return self._unit.partition[ty][tx]

    def enact(self):
        assert not self._finished, \
               'task enacted after it was finished'

        # If we have reached the goal, just finish the task.
        if (self._unit.x, self._unit.y) == self._target:
            # We have reached the goal, so finish the task.
            self._finished = True
            self._finished_proc()
            return

        # bug - if we are after an object and the object becomes
        #       unreachable, that should count as a block!
        # If the target is not reachable, call blocked_proc.
        if not self._target_is_reachable():
            self._finished = True
            self._blocked_proc()
            return

        unit = self._unit
        x, y = unit.x, unit.y
        path = self._path

        if self._target_is_solid and len(path) == 1:
            # The target is solid and we've reached it,
            # so finish the task.
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

