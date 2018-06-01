import random

class Mine(object):
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
            # Turn the mountain into a dirt tile.
            self._stage.set_tile_at(tx, ty, 18)

            # 50% chance of rock appearing
            if random.randint(0, 1) == 0:
                self._stage.create_entity('rock', (tx, ty))

            # Finish the mining task
            self._finished_proc()
            return
