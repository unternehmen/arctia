from common import *
from stage import Stage
from path import PathFinder
import os

def _ensure_path_is_legal(stage, start, path):
    x, y = start

    while len(path) > 0:
        assert not tile_is_solid(stage.get_tile_at(x, y))
        x += path[0][0]
        y += path[0][1]
        path = path[1:]

def test_path_is_walkable_0():
    # This was a path that broke during play---a penguin walked
    # straight into the river instead of walking over the bridge.
    # Let's make sure it doesn't break any more.
    stage = Stage(os.path.join('maps', 'test-river.tmx'))
    finder = PathFinder(stage)
    start = 27, 31
    finder.start(start[0], start[1], lambda pos: pos == (6, 1))
    result = finder.run(-1)

    assert result is not None
    _ensure_path_is_legal(stage, start, result)

def test_path_is_walkable_1():
    stage = Stage(os.path.join('maps', 'test-river.tmx'))
    finder = PathFinder(stage)
    start = 26, 31
    finder.start(start[0], start[1], lambda pos: pos == (6, 1))
    result = finder.run(-1)

    assert result is not None
    _ensure_path_is_legal(stage, start, result)

def test_path_is_walkable_2():
    stage = Stage(os.path.join('maps', 'test-river.tmx'))
    finder = PathFinder(stage)
    start = 30, 23
    finder.start(start[0], start[1], lambda pos: pos == (6, 1))
    result = finder.run(-1)

    assert result is not None
    _ensure_path_is_legal(stage, start, result)

def test_path_busy():
    stage = Stage(os.path.join('maps', 'tuxville.tmx'))
    finder = PathFinder(stage)
    assert not finder.busy
    finder.start(50, 50, lambda pos: pos == (50, 51))
    assert finder.busy
    result = finder.run(-1)
    assert result is not None
    assert len(result) == 1
    assert not finder.busy

def test_path_correct_results_0():
    stage = Stage(os.path.join('maps', 'tuxville.tmx'))
    finder = PathFinder(stage)
    finder.start(50, 50, lambda pos: pos == (50, 51))
    result = finder.run(-1)
    assert result is not None
    assert len(result) == 1

def test_path_correct_results_1():
    stage = Stage(os.path.join('maps', 'tuxville.tmx'))
    finder = PathFinder(stage)
    finder.start(50, 50, lambda pos: pos == (50, 62))
    result = finder.run(1)

    assert result is None

    result = finder.run(-1)

    assert result is not None
    assert len(result) == 12

def test_path_notify():
    stage = Stage(os.path.join('maps', 'tuxville.tmx'))
    finder = PathFinder(stage)
    movement = (-1, -1)
    finder.start(50, 50, lambda pos: pos == (50, 62))
    finder.run(1)
    finder.notify(*movement)
    result = finder.run(-1)

    assert result is not None
    assert len(result) == 13
    assert result[0] == (-movement[0], -movement[1])
