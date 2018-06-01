class Wait(object):
    """
    A TaskWait represents waiting without moving for some span of time.
    
    Arguments:
        duration:      the amount of turns to wait
        finished_proc: the procedure to run after this task is done
    """
    def __init__(self, duration, finished_proc):
        assert duration >= 0, 'duration must be >= 0, not ' + duration

        self._duration = duration
        self._timer = 0
        self._finished_proc = finished_proc
        self._finished = False
        pass

    def enact(self):
        """
        Enact the task, i.e., make the unit carry it out.
        """
        assert not self._finished, \
               'task enacted after it was finished'

        self._timer += 1

        if self._timer == self._duration:
            self._finished = True
            self._finished_proc()
            return
