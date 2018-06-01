class Take(object):
    def __init__(self, stage, unit, entity,
                 not_found_proc, finished_proc):
        self._stage = stage
        self._unit = unit
        self._entity = entity
        self._finished_proc = finished_proc
        self._not_found_proc = not_found_proc

    def enact(self):
        if not self._entity.location \
           or self._entity.location != (self._unit.x, self._unit.y):
            self._not_found_proc()
            return

        self._entity.location = None
        self._stage.delete_entity(self._entity)
        self._finished_proc()
        return
