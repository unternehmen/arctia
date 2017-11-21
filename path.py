"""
The path module provides functions used by many path-finding algorithms.
"""

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

def reconstruct_path(step_matrix, initial):
    """
    Reconstruct a path starting from an initial point in a step matrix.

    A step matrix is a mxn array in which each value is either None
    or a pair of coordinates leading to the "previous" location.
    By following a trail of previous locations, this function can
    determine the path that was taken.

    Arguments:
        step_matrix: the step matrix
        initial: a pair of coordinates (x, y) the initial point
    """
    current = initial
    total_path = [current]

    next_step = step_matrix[current[1]][current[0]]
    while next_step is not None:
        current = next_step
        next_step = step_matrix[current[1]][current[0]]
        total_path.append(current)

    return total_path
