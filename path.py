"""
The path module provides functions used by many path-finding algorithms.
"""

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
