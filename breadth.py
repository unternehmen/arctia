import math
from common import tile_is_solid
from stage import Stage
from itertools import product

def _2d_constant_array(width, height, value):
    return [[value for x in range(width)] for y in range(height)]

def _index(mat, tup):
    return mat[tup[1]][tup[0]]

def _reconstruct_path(previous, current):
    total_path = [current]

    while _index(previous, current) is not None:
        current = _index(previous, current)
        total_path.append(current)

    return total_path


def find_path_to_matching(stage, start, cond):
    """
    Breadth-first search for a location matching a condition.

    Arguments:
        stage: the stage to search on
        start: the starting point of the search
        cond: a lambda taking coordinates and returning True/False
    """
    fringe = [start]
    visited = _2d_constant_array(stage.width, stage.height, False)
    visited[start[1]][start[0]] = True
    previous = _2d_constant_array(stage.width, stage.height, None)

    while len(fringe) > 0:
        node = fringe[0]
        fringe = fringe[1:]

        if cond(node):
            return list(reversed(_reconstruct_path(previous, node)))

        if tile_is_solid(stage.get_tile_at(node[0], node[1])):
            continue

        for offset in product((1, 0, -1), (1, 0, -1)):
            if offset == (0, 0):
                continue

            neighbor = (node[0] + offset[0], node[1] + offset[1])

            if not visited[neighbor[1]][neighbor[0]]:
                visited[neighbor[1]][neighbor[0]] = True
                previous[neighbor[1]][neighbor[0]] = node
                fringe.append(neighbor)

    return None

