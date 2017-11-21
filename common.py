"""
The common module provides functions used by most other modules.
"""

def tile_is_solid(tid):
    """
    Return whether a tile is solid or not based on its ID.

    Arguments:
        tid: the tile ID
    Returns: whether the tile is solid
    """
    return tid in (2, 3, 5)

def make_2d_constant_array(width, height, value):
    """
    Create a width-by-height array with each cell as a given value.

    For example, the call make_2d_constant_array(5, 5, 0) would return:

        [[0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0]]

    Arguments:
        width: the width of the array
        height: the height of the array
        value: the value to fill the array with

    Returns: the new array
    """
    return [[value for x in range(width)] for y in range(height)]
