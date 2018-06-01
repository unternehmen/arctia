class Build(object):
    """
    Arguments:
        stage:         the Stage containing the unit
        unit:          the unit (e.g., Penguin) whose task this
        target:        the target position as a pair of (x, y) coordinates
        finished_proc: the procedure to run if the task is finished
    """
    def __init__(self, stage, unit, target, finished_proc):
        self.stage = stage
        self.unit = unit
        self.target = target
        self.work_left = 10
        self.finished_proc = finished_proc

    def _assert_unit_is_within_range(self):
        x, y = self.unit.x, self.unit.y
        tx, ty = self.target

        assert -1 <= x - tx <= 1, 'not in range of mine job'
        assert -1 <= y - ty <= 1, 'not in range of mine job'

    def enact(self):
        self._assert_unit_is_within_range()
        tx, ty = self.target

        if self.work_left > 0:
            self.work_left -= 1

        # Prolong the task if a mob is in the way.
        for mob in self.stage.mobs:
            if (mob.x, mob.y) == self.target:
                print('Mob in the way, prolonging job.')
                return

        # Prolong the task if an entity is in the way.
        if self.stage.entity_at(self.target):
            print('Mob in the way, prolonging job.')
            return

        # Otherwise, finish the task if it needs no more work.
        if self.work_left == 0:
            self.stage.set_tile_at(tx, ty, 5)
            self.finished_proc()
