class Drop(object):
    """
    Task logic:
        1. If there is already an item below the unit,
           then the task is "blocked", meaning it calls
           blocked_proc and then aborts.
        2. Otherwise, the unit drops the item, and
           finished_proc is called.
    """
    def __init__(self, stage, entity, unit, blocked_proc, finished_proc):
        self._stage = stage
        self._entity = entity
        self._unit = unit
        self._blocked_proc = blocked_proc
        self._finished_proc = finished_proc

    def enact(self):
        unit = self._unit

        if self._stage.entity_at((unit.x, unit.y)):
            if self._blocked_proc:
                self._blocked_proc()
            return

        self._stage.add_entity(self._entity, (unit.x, unit.y))
        self._entity.location = (unit.x, unit.y)
        self._finished_proc()
        return

