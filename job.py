class Job(object):
    """
    A Job represents a task that a Penguin can reserve for themselves.
    """
    def __init__(self):
        """
        Create a new, untaken Job.

        Arguments:
            location: a tuple of the Job's location (x, y)

        Returns:
            a new Job
        """
        self.done = False

    def finish(self):
        """
        Finish the Job.

        This lets any job lists know to get rid of this job.
        """
        self.done = True


class MineJob(Job):
    """
    A MineJob represents the task of digging into a mountain.
    """
    def __init__(self, location):
        """
        Create a new MineJob.

        Arguments:
            location: the location (x, y) of the wall to be mined

        Returns: a new MineJob
        """
        Job.__init__(self)
        self.location = location
