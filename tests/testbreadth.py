import os
from stage import Stage
from search import find_path_to_matching

def test_breadth_search_correct_results():
    def _point_is_water(point):
        return stage.get_tile_at(*point) == 3
    
    stage = Stage(os.path.join('maps', 'test-valley.tmx'))
    path = find_path_to_matching(stage, (9, 3), _point_is_water)
    assert path is not None
    assert len(path) == 6
    assert path[0] == (9, 3)
    assert path[-1] == (14, 8)

def test_breadth_blocked_in():
    def _point_is_water(point):
        return stage.get_tile_at(*point) == 3

    stage = Stage(os.path.join('maps', 'test-valley.tmx'))
    path = find_path_to_matching(stage, (3, 12), _point_is_water)
    assert path is None

def test_breadth_on_object():
    def _point_is_bug(point):
        return stage.entity_at(point).kind == 'bug'

    stage = Stage(os.path.join('maps', 'test-valley.tmx'))
    path = find_path_to_matching(stage, (5, 12), _point_is_bug)
    assert path is not None
    assert len(path) == 1
