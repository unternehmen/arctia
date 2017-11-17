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
        self.reserved = False

    def reserve(self):
        """
        Reserve the Job.

        This lets mobs know that this Job is already taken.
        """
        self.reserved = True

    def relinquish(self):
        """
        Relinquish the Job.

        This lets mobs know that this Job is free for the taking.
        """
        self.reserved = False

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
        self.locations = [location]


class HaulJob(Job):
    """
    A HaulJob represents the task of picking up and moving something.
    """
    def __init__(self, entity):
        """
        Create a new HaulJob.

        Arguments:
            entity: the entity that needs to be hauled

        Returns: a new HaulJob.
        """
        Job.__init__(self)
        self.entity = entity
        self.slot_location = None
        self.stockpile = None

    def finish(self):
        self.stockpile.relinquish_slot(self.slot_location)
        super().finish()

    @property
    def locations(self):
        return [self.entity.location]
