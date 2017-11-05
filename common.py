def tile_is_solid(tid):
    """
    Return whether a tile is solid or not based on its ID.

    Arguments:
        tid: the tile ID
    Returns: whether the tile is solid
    """
    return tid in (2, 3, 5)
