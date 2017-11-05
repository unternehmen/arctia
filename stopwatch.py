class Stopwatch(object):
    """
    A Stopwatch measures the passage of time (in frames).

    It provides these services:

    * getting the current moment
    * seeing how many frames have passed since a given moment
    """
    def __init__(self):
        """
        Create a new Stopwatch.
        """
        self.frame = 0

    def tick(self):
        """
        Notify the Stopwatch that a frame has passed.
        """
        self.frame += 1

    def start(self):
        """
        Start the Stopwatch.

        Returns: a cookie to be later used with time_since()
        """
        return self.frame

    def measure(self, cookie):
        """
        Measure the time since the Stopwatch was started.

        Arguments:
            cookie: a cookie as returned by start()

        Returns: the amount of frames since the cookie was created
        """
        return self.frame - cookie
