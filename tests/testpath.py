from stage import Stage
from path import PathFinder

stage = Stage()

finder = PathFinder(stage)

assert not finder.busy

finder.start(50, 50, lambda pos: pos == (50, 51))

assert finder.busy

result = finder.run(-1)

assert result is not None
assert len(result) == 1
assert not finder.busy

finder.start(50, 50, lambda pos: pos == (50, 62))

assert finder.busy

result = finder.run(1)

assert result is None
assert finder.busy

result = finder.run(-1)

assert result is not None
assert len(result) == 12
assert not finder.busy

# Test PathFinder.notify
movement = (-1, -1)
finder.start(50, 50, lambda pos: pos == (50, 62))
finder.run(1)
finder.notify(*movement)
result = finder.run(-1)
assert result is not None
assert len(result) == 13
assert result[0] == (-movement[0], -movement[1])

print('All tests succeeded.')
