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
        self.locations = []

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
        self.locations.append(location)


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
        self.locations.append((entity[1], entity[2]))
        self.slot_location = None

class DropJob(Job):
    """
    A DropJob represents the task of dropping something somewhere.
    """
    def __init__(self, haul_job, entity):
        """
        Create a new DropJob.

        Arguments:
            haul_job: the HaulJob that led to this DropJob
            entity: the entity that needs to be dropped off

        Returns: a new DropJob.
        """
        Job.__init__(self)
        self.haul_job = haul_job
        self.entity = entity
