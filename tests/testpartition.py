import os
from arctia.stage import Stage
from arctia.partition import partition

def test_partition_size():
    stage = Stage('maps/test-valley.tmx')
    result = partition(stage, (3, 11))

    assert len(result) == stage.height
    for row in result:
        assert len(row) == stage.width

def _assert_has_trues(matrix):
    has_trues = False
    for row in matrix:
        for item in row:
            if item == True:
                has_trues = True
                break
        if has_trues:
            break

    assert has_trues

def test_partition_has_trues_1():
    stage = Stage('maps/test-valley.tmx')
    result = partition(stage, (3, 11))
    _assert_has_trues(result)

def test_partition_has_trues_2():
    stage = Stage('maps/test-valley.tmx')
    result = partition(stage, (10, 6))
    _assert_has_trues(result)

def test_partition_equality():
    stage = Stage('maps/test-valley.tmx')
    result1 = partition(stage, (4, 7))
    result2 = partition(stage, (10, 6))

    for y in range(len(result1)):
       for x in range(len(result1[0])):
           assert result1[y][x] == result2[y][x]

def test_partition_inequality():
    stage = Stage('maps/test-valley.tmx')
    result1 = partition(stage, (3, 11))
    result2 = partition(stage, (10, 6))

    all_equal = True
    for y in range(len(result1)):
        for x in range(len(result1[0])):
            if result1[y][x] != result2[y][x]:
                all_equal = False
                break
        if not all_equal:
            break

    assert not all_equal

def test_big_map_has_trues():
    stage = Stage('maps/tuxville.tmx')
    result = partition(stage, (26, 59))
    _assert_has_trues(result)
