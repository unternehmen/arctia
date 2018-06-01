class Eat(object):
    def __init__(self, stage, unit, entity,
                 interrupted_proc, finished_proc):
        self._work_left = 10
        self._stage = stage
        self._unit = unit
        self._entity = entity
        self._interrupted_proc = interrupted_proc
        self._finished_proc = finished_proc
        self._finished = False

    def enact(self):
        assert not self._finished, \
               'task enacted after it was finished'

        # If the object is no longer on the stage, interrupt.
        if self._entity.location is None:
            self._interrupted_proc()
            self._finished = True
            return

        # If the object is no longer near the unit, interrupt.
        if -1 <= self._unit.x - self._entity.location[0] <= 1 \
           and -1 <= self._unit.y - self._entity.location[1] <= 1:
            pass
        else:
            self._interrupted_proc()
            self._finished = True
            return

        # Otherwise, continue eating.
        self._work_left -= 1
        if self._work_left == 0:
            self._unit.hunger = max(0, self._unit.hunger - self._unit.hunger_diet[self._entity.kind])
            self._stage.delete_entity(self._entity)
            self._finished_proc()
            self._finished = True
            return

