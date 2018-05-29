"""
The partition module provides a way of finding tiles a unit can reach.
"""
from .common import tile_is_solid

def partition(stage, location):
    """
    Return the region of a stage that is accessible from a location.

    The location is always reachable from itself.

    Arguments:
        stage: a Stage whose size is (m, n)
        location: a pair of coordinates (x, y) within the stage bounds

    Return:
        an m-by-n array of bools in which True means a location
        is reachable and False means the location is unreachable
    """
    loc_x, loc_y = location

    assert 0 <= loc_x < stage.width
    assert 0 <= loc_y < stage.height

    reachable = [[False for x in range(stage.width)]
                 for y in range(stage.height)]
    reachable[loc_y][loc_x] = True

    directions = [
        (0, -1), (0, 1), (-1, 0), (1, 0),
        (-1, -1), (1, -1), (-1, 1), (1, 1)
    ]

    fringe = [(loc_x, loc_y)]

    while True:
        if not fringe:
            break

        new_fringe = []

        for x, y in fringe:
            if not tile_is_solid(stage.get_tile_at(x, y)) \
               or (x, y) == location:
                for dx, dy in directions:
                    neighbor_x = dx + x
                    neighbor_y = dy + y

                    if 0 <= neighbor_x < stage.width \
                       and 0 <= neighbor_y < stage.height \
                       and not reachable[neighbor_y][neighbor_x]:
                        new_fringe.append((neighbor_x, neighbor_y))
                        reachable[neighbor_y][neighbor_x] = True

        fringe = new_fringe

    return reachable
