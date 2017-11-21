"""
The breadth module provides a function for breadth-first searching.
"""
from itertools import product
from common import tile_is_solid
from path import make_2d_constant_array, reconstruct_path

def find_path_to_matching(stage, start, cond):
    """
    Breadth-first search for a location matching a condition.

    Arguments:
        stage: the stage to search on
        start: the starting point of the search
        cond: a lambda taking coordinates and returning True/False
    """
    fringe = [start]
    visited = make_2d_constant_array(stage.width, stage.height, False)
    visited[start[1]][start[0]] = True
    previous = make_2d_constant_array(stage.width, stage.height, None)

    while fringe:
        node = fringe[0]
        fringe = fringe[1:]

        if cond(node):
            return list(reversed(reconstruct_path(previous, node)))

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
