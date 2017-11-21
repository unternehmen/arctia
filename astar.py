"""
The astar module provides a function (astar) which does A* path finding.
"""
import math
import heapq
from common import tile_is_solid
from path import make_2d_constant_array, reconstruct_path

def _calc_distance(a, b):
    a_x, a_y = a
    b_x, b_y = b

    return math.sqrt((b_x - a_x) ** 2 + (b_y - a_y) ** 2)

def _index(mat, tup):
    return mat[tup[1]][tup[0]]

def astar(stage, start, end):
    """
    Quickly find a path from one point to another on a stage.

    This code is adapted from the pseudocode at:

        <https://en.wikipedia.org/wiki/A*_search_algorithm>

    Arguments:
        stage: a stage
        start: a pair of starting coordinates, e.g., (0, 0)
        end: a pair of ending coordinates, e.g., (2, 2)

    Returns: a list of coordinates for each step in the path including
             both endpoints, e.g., [(0, 0), (1, 1), (2, 2)]
    """
    openset = [(_calc_distance(start, end), start)]
    closedset = set()
    previous = make_2d_constant_array(stage.width, stage.height, None)

    scost = make_2d_constant_array(stage.width, stage.height, math.inf)
    scost[start[1]][start[0]] = 0

    offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0),
               (1, 0), (-1, 1), (0, 1), (1, 1)]

    while openset:
        current = heapq.heappop(openset)[1]

        if current == end:
            return list(reversed(reconstruct_path(previous, current)))

        closedset.add(current)

        if tile_is_solid(stage.get_tile_at(*current)):
            continue

        for offset in offsets:
            neighbor = tuple([offset[x] + current[x] for x in range(2)])

            if neighbor[0] < 0 or neighbor[0] >= stage.width \
               or neighbor[1] < 0 or neighbor[1] >= stage.height:
                continue

            if neighbor in closedset:
                continue

            if neighbor not in map(lambda p: p[1], openset):
                heapq.heappush(openset, (_index(scost, current) \
                                         + _calc_distance(neighbor,
                                                          end),
                                         neighbor))

            tmp = _index(scost, current) + 1
            if tmp >= _index(scost, neighbor):
                continue # not a better path

            previous[neighbor[1]][neighbor[0]] = current
            scost[neighbor[1]][neighbor[0]] = tmp

    return None
