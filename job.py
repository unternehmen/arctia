class Job(object):
    def __init__(self, location):
        """
        Create a new, untaken Job.

        Arguments:
            location: a tuple of the Job's location (x, y)

        Returns:
            a new Job
        """
        self.done = False
        self.reserved = False
        self.location = location

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
