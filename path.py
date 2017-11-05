from config import *
from common import *

class PathFinder(object):
    """
    A PathFinder incrementally finds a path to some goal in a Stage.

    The goal can be specific (e.g., an exact location) or general
    (e.g., any location that has a job associated with it).

    The search algorithm is a breadth-first search radiating from some
    starting location.  The starting location is usually the location
    of the mob who started the search.
    """
    NOT_VISITED     = 0
    JUST_VISITED    = 1
    ALREADY_VISITED = 2
    
    DIRECTIONS = {
        'up':        (0, -1),
        'down':      (0, 1),
        'left':      (-1, 0),
        'right':     (1, 0),
        'upleft':    (-1, -1),
        'upright':   (1, -1),
        'downleft':  (-1, 1),
        'downright': (1, 1),
    }

    def __init__(self, stage):
        """
        Create a new PathFinder.

        Arguments:
            stage: a Stage

        Returns: a new PathFinder
        """
        self.busy = False
        self._stage = stage
        self._paths     = [[None for x in range(stage.width)]
                           for y in range(stage.height)]
        self._visited   = [[PathFinder.NOT_VISITED
                            for x in range(stage.width)]
                           for y in range(stage.height)]
        self._staleness = [[False for x in range(stage.width)]
                           for y in range(stage.height)]

    def start(self, from_x, from_y, goal_pred):
        """
        Start a search from a given position.

        Arguments:
            from_x: the initial x coordinate
            from_y: the initial y coordinate
            goal_pred: a function taking a pair (x, y)
                       and returning a boolean
        """
        self._path_prefix = []
        self._goal_pred = goal_pred

        # Clear the state arrays.
        for y in range(len(self._visited)):
            for x in range(len(self._visited[0])):
                self._visited[y][x] = PathFinder.NOT_VISITED
                self._staleness[y][x] = False
                self._paths[y][x] = None

        # Mark the starting point as visited.
        self._visited[from_y][from_x] = PathFinder.ALREADY_VISITED

        # State that the job searcher is busy.
        self.busy = True

    def notify(self, xoff, yoff):
        """
        Notify the path finder that the start position has moved.

        Path searches are usually started from some mob's location.
        Because searches run incrementally over many frames, the object
        which started the search the might move in mid-search.

        In order for the search to give a correct path to the goal,
        it needs to know where the originating mob is at all times.
        In light of that, this procedure should be run whenever the mob
        responsible for the path search moves.

        For example, if a penguin moves (1, 1) from its previous
        position, it should also run notify(1, 1) on its path finder.

        This should only be run when there really is a search in
        progress, i.e., when the path finder's "busy" attribute is
        True.

        Arguments:
            xoff: the offset from the original starting x coordinate
            yoff: the offset from the original starting y coordinate
        """
        assert self.busy
        self._path_prefix.insert(0, (-xoff, -yoff))

    def _backtrace(self, x, y):
        """
        Return the already-calculated shortest path to a goal.

        Arguments:
            x: the x coordinate of the goal
            y: the y coordinate of the goal

        Returns:
            a list of 2-tuples representing steps along the path to
            the goal.  For example, [(1, 1), (1, 0), ...]
        """
        shortest_path = []
        dir = self._paths[y][x]

        while dir:
            xoff, yoff = PathFinder.DIRECTIONS[dir]
            shortest_path.insert(0, (xoff, yoff))
            x -= xoff
            y -= yoff
            dir = self._paths[y][x]

        shortest_path = self._path_prefix + shortest_path

        return shortest_path

    def run(self, limit=10):
        """
        Continue a previously started path search.

        If the increment limit is -1, then the search runs until either
        the stage is exhausted or the goal is found.

        Arguments:
            limit: the number of breadth descensions to try

        Returns: the found path as a list of steps, e.g.,
                 [(1, 1), (1, 0), ...], or None if no path was found
        """
        exhausted_tiles = False

        while not exhausted_tiles and limit != 0:
            exhausted_tiles = True

            for y in range(self._stage.height):
                for x in range(self._stage.width):
                    if self._visited[y][x] != \
                         PathFinder.ALREADY_VISITED \
                       or self._staleness[y][x] \
                       or tile_is_solid(self._stage.get_tile_at(x, y)):
                        continue

                    for dir, offset in PathFinder.DIRECTIONS.items():
                        xoff, yoff = offset
                        nx = x + xoff
                        ny = y + yoff

                        if nx >= 0 and nx < self._stage.width \
                           and ny >= 0 and ny < self._stage.height \
                           and self._visited[ny][nx] == \
                                 PathFinder.NOT_VISITED:
                            self._visited[ny][nx] = \
                              PathFinder.JUST_VISITED
                            self._paths[ny][nx] = dir
                            exhausted_tiles = False
                            if self._goal_pred((nx, ny)):
                                self.busy = False
                                return self._backtrace(nx, ny)

                    self._staleness[y][x] = True

            for y in range(self._stage.height):
                for x in range(self._stage.width):
                    if self._visited[y][x] == PathFinder.JUST_VISITED:
                        self._visited[y][x] = PathFinder.ALREADY_VISITED

            if limit > 0:
                limit -= 1

        if exhausted_tiles:
            self.busy = False

        return None
