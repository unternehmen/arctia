from common import tile_is_solid
from astar import astar

# A Task is a unitary action that a unit should take.
# Once a task is complete, it can run code to decide what
# next action should be taken.  This code is given as
# a callback.
class TaskGo(object):
    """
    The target location must be reachable by the unit.

    Arguments:
        stage:         the Stage containing the unit
        unit:          the unit (e.g., Penguin) whose task this
        target:        the target position as a pair of x-y coordinates
        blocked_proc:  the procedure to run if the path is broken
        finished_proc: the procedure to run if the task is finished
    """
    def __init__(self, stage, unit, target,
                 blocked_proc, finished_proc):
        self._unit = unit
        self._target = target
        self._target_is_solid = \
          tile_is_solid(stage.get_tile_at(target[0], target[1]))
        self._blocked_proc = blocked_proc
        self._finished_proc = finished_proc
        self._stage = stage

        # If the unit is already at its goal, just finish the task.
        if (unit.x, unit.y) == target:
            self._finished_proc()
            return

        assert self._target_is_reachable(), \
               'destination tile is unreachable'

        # Find the path to the destination.
        self._path = astar(stage, (unit.x, unit.y), target)

    def _target_is_reachable(self):
        tx, ty = self._target
        return self._unit.partition[ty][tx]

    def enact(self):
        # bug - if we are after an object and the object becomes
        #       unreachable, that should count as a block!
        # If the target is not reachable, call blocked_proc.
        if not self._target_is_reachable():
            print('Running blocked_proc...')
            self._blocked_proc()
            return

        unit = self._unit
        x, y = unit.x, unit.y
        path = self._path

        if len(path) == 0:
            # We have reached the goal, so finish the task.
            self._finished_proc()
            return
        elif self._target_is_solid and len(path) == 1:
            # The target is solid and we've reached it,
            # so finish the task.
            self._finished_proc()
            return

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

class TaskMine(object):
    """
    Arguments:
        stage:         the Stage containing the unit
        unit:          the unit (e.g., Penguin) whose task this
        target:        the target position as a pair of x-y coordinates
        finished_proc: the procedure to run if the task is finished
    """
    def __init__(self, stage, unit, target, finished_proc):
        self._stage = stage
        self._unit = unit
        self._target = target
        self._work_left = 10
        self._assert_unit_is_within_range()
        self._finished_proc = finished_proc

    def _assert_unit_is_within_range(self):
        x, y = self._unit.x, self._unit.y
        tx, ty = self._target

        assert -1 <= x - tx <= 1, 'not in range of mine job'
        assert -1 <= y - ty <= 1, 'not in range of mine job'

    def enact(self):
        self._assert_unit_is_within_range()
        tx, ty = self._target

        self._work_left -= 1
        if self._work_left == 0:
            self._stage.set_tile_at(tx, ty, 1)
            self._finished_proc()
            return

class TaskTake(object):
    def __init__(self, stage, unit, entity, finished_proc):
        self._stage = stage
        self._unit = unit
        self._entity = entity
        self._finished_proc = finished_proc
        assert (unit.x, unit.y) == entity.location

    def enact(self):
        assert not self._unit._held_entity, \
               'unit tried to take when its hands were full'
        self._unit._held_entity = self._entity
        self._entity.relinquish()
        self._entity.location = None
        self._stage.delete_entity(self._entity)
        self._finished_proc()
        return

class TaskDrop(object):
    def __init__(self, stage, unit, finished_proc):
        self._stage = stage
        self._unit = unit
        self._finished_proc = finished_proc

    def enact(self):
        unit = self._unit
        entity = unit._held_entity
        unit._held_entity = None

        self._stage.add_entity(entity, (unit.x, unit.y))
        entity.location = (unit.x, unit.y)
        self._finished_proc()
        return
