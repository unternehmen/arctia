"""
The transform module provides functions for transforming points.
"""

def translate(point, offset):
    """
    Translate a point by an offset.

    Arguments:
        point: a point, e.g., (x, y)
        offset: an offset, e.g., (x, y)

    Returns: a translated point
    """
    return (point[0] + offset[0], point[1] + offset[1])
