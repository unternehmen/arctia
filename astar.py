import math
import heapq
import os
from stage import Stage
from common import tile_is_solid

def _calc_distance(a, b):
    ax, ay = a
    bx, by = b

    return math.sqrt((bx - ax) ** 2 + (by - ay) ** 2)

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


def astar(stage, start, end):
    openset = [(_calc_distance(start, end), start)]
    closedset = set()
    previous = _2d_constant_array(stage.width, stage.height, None)

    scost = _2d_constant_array(stage.width, stage.height, math.inf)
    sx, sy = start
    scost[sy][sx] = 0

    offsets = [(-1, -1), (0, -1), (1, -1),
               (-1, 0),           (1, 0),
               (-1, 1),  (0, 1),  (1, 1)]

    found = False

    while len(openset) > 0:
        current = heapq.heappop(openset)[1]

        if current == end:
            return list(reversed(_reconstruct_path(previous, current)))

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
