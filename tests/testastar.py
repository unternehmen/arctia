import os
from arctia.stage import Stage
from arctia.search import astar
from arctia.common import tile_is_solid

def _ensure_path_is_legal(stage, path):
    for step in path:
        assert not tile_is_solid(stage.get_tile_at(*step))

def test_path_is_walkable_0():
    # This was a path that broke during play---a penguin walked
    # straight into the river instead of walking over the bridge.
    # Let's make sure it doesn't break any more.
    stage = Stage('maps/test-river.tmx')
    path = astar(stage, (27, 31), (6, 1))
    assert path is not None
    _ensure_path_is_legal(stage, path)

def test_path_is_walkable_0_reverse():
    stage = Stage('maps/test-river.tmx')
    path = astar(stage, (6, 1), (27, 31))
    assert path is not None
    _ensure_path_is_legal(stage, path)

def test_path_is_walkable_1():
    stage = Stage('maps/test-river.tmx')
    path = astar(stage, (26, 31), (6, 1))
    assert path is not None
    _ensure_path_is_legal(stage, path)

def test_path_is_walkable_2():
    stage = Stage('maps/test-river.tmx')
    path = astar(stage, (30, 23), (6, 1))
    assert path is not None
    _ensure_path_is_legal(stage, path)

def test_path_correct_results_0():
    stage = Stage('maps/tuxville.tmx')
    path = astar(stage, (50, 50), (50, 51))
    assert path is not None

def test_path_returns_endpoints():
    stage = Stage('maps/tuxville.tmx')
    path = astar(stage, (50, 50), (50, 51))
    assert path[0] == (50, 50)
    assert path[-1] == (50, 51)
