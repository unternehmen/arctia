from common import tile_is_solid

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
    #print('Partitioning...')
    lx, ly = location

    assert 0 <= lx < stage.width
    assert 0 <= ly < stage.height

    reachable = [[False for x in range(stage.width)]
                 for y in range(stage.height)]
    reachable[ly][lx] = True

    directions = [
        (0, -1), (0, 1), (-1, 0), (1, 0),
        (-1, -1), (1, -1), (-1, 1), (1, 1)
    ]

    fringe = [(lx, ly)]

    while True:
        if len(fringe) == 0:
            break

        new_fringe = []

        for x, y in fringe:
            if not tile_is_solid(stage.get_tile_at(x, y)) \
               or (x, y) == location:
                for dx, dy in directions:
                    nx = dx + x
                    ny = dy + y

                    if 0 <= nx < stage.width \
                       and 0 <= ny < stage.height \
                       and not reachable[ny][nx]:
                        new_fringe.append((nx, ny))
                        reachable[ny][nx] = True

        fringe = new_fringe

    return reachable
