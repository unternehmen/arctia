"""
The systems module provides classes which update the game's state.
"""
from functools import partial
import random

from common import tile_is_solid
from partition import partition
from transform import translate
from task import TaskEat, TaskGo, TaskWait


def _refresh_partitions_of_mobs(stage, mobs):
    # This currently assumes that all mobs have
    # the same movement rules!
    parts = []
    for mob in mobs:
        mob.partition = None

        for part in parts:
            if part[mob.y][mob.x]:
                mob.partition = part
                break

        if not mob.partition:
            part = partition(stage, (mob.x, mob.y))
            mob.partition = part
            parts.append(part)

class PartitionUpdateSystem(object):
    """
    A PartitionUpdateSystem updates the partition matrix of units.

    A partition matrix shows whether a unit can reach a location
    given its movement constraints.  This makes testing reachability
    an O(1) operation so long as the partition matrices of all units
    is up-to-date.

    Arguments:
        stage: the stage
        mobs: the list of units
    """
    def __init__(self, stage, mobs):
        self._mobs = mobs
        self._stage = stage

        stage.register_tile_change_listener(self)

        self.refresh()

    def tile_changed(self, _unused_prev_id, _unused_cur_id, coords):
        """
        Notify the PartitionUpdateSystem that a tile has changed.

        Arguments:
            _unused_prev_id: this argument is not used
            _unused_cur_id: this argument is not used
            coords: the (x, y) coordinates of the changed tile
        """
        x, y = coords

        # Determine which mobs need partition refreshs.
        mobs_to_refresh = []

        for mob in self._mobs:
            need_refresh = False

            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    other_x, other_y = \
                      translate((x, y), (dx, dy))

                    if mob.partition[other_y][other_x]:
                        need_refresh = True
                        break
                if need_refresh:
                    break
            if need_refresh:
                mobs_to_refresh.append(mob)

        # Update partitions on mobs which need it.
        _refresh_partitions_of_mobs(self._stage, mobs_to_refresh)


    def refresh(self):
        """
        Update the partition matrices of all known mobs.
        """
        _refresh_partitions_of_mobs(self._stage, self._mobs)


class BugDispatchSystem(object):
    """
    A BugDispatchSystem chooses jobs for bugs to do.

    Arguments:
        stage: the stage
    """
    def __init__(self, stage):
        self._bugs = []
        self._stage = stage

    def add(self, bug):
        """
        Add a Bug whose jobs should be managed by this system.

        Arguments:
            bug: the Bug
        """
        self._bugs.append(bug)

    def update(self):
        """
        Give jobs to all Bugs that need them.

        Only run this once every turn (not every frame).
        """
        def _forget_task(bug):
            bug.task = None

        for bug in self._bugs:
            if bug.task:
                bug.task.enact()

            if not bug.task and bug.hunger >= bug.hunger_threshold:
                # Find a piece of food the bug can reach.
                def _is_valid_food(bug, entity, _unused_x, _unused_y):
                    kind = entity.kind
                    x, y = entity.location
                    return bug.partition[y][x] and kind == 'fish'

                result = \
                  self._stage.find_entity(partial(_is_valid_food, bug))

                if result:
                    entity, _ = result

                    def _eat_food(bug, entity):
                        bug.task = TaskEat(self._stage,
                                           bug, entity,
                                           interrupted_proc=\
                                             partial(_forget_task, bug),
                                           finished_proc=\
                                             partial(_forget_task, bug))

                    # Make the bug go eat the food.
                    # bug - TaskGo doesn't recover if the object is
                    #       stolen by another unit (?)
                    bug.task = TaskGo(self._stage, bug, entity.location,
                                      blocked_proc=partial(_forget_task, bug),
                                      finished_proc=partial(_eat_food, bug, entity))

            if not bug.task:
                # Choose whether to brood or to wander.
                choices = ['wandering', 'brooding']
                selected = random.choice(choices)

                if selected == 'wandering':
                    # Step wildly to find a goal for our wandering.
                    goal = bug.x, bug.y

                    for _ in range(40):
                        offset = random.choice([(-1, -1), (-1, 0),
                                                (-1, 1), (0, -1),
                                                (0, 1), (1, -1),
                                                (1, 0), (1, 1)])
                        shifted = translate(goal, offset)
                        tile = self._stage.get_tile_at(*shifted)

                        if 0 <= shifted[0] < self._stage.width \
                           and 0 <= shifted[1] < self._stage.height \
                           and not tile_is_solid(tile):
                            goal = shifted

                    # Go to our goal position.
                    bug.task = TaskGo(self._stage, bug, goal,
                                      delay=bug.wandering_delay,
                                      blocked_proc=\
                                        partial(_forget_task, bug),
                                      finished_proc=\
                                        partial(_forget_task, bug))
                elif selected == 'brooding':
                    bug.task = TaskWait(duration=bug.brooding_duration,
                                        finished_proc=\
                                          partial(_forget_task, bug))

            bug.hunger += 1


class BugDrawSystem(object):
    """
    A BugDrawSystem draws bugs onto the screen.
    """
    def __init__(self):
        self._bugs = []

    def add(self, bug):
        """
        Add a Bug to be drawn by this system.

        Arguments:
            bug: the Bug
        """
        self._bugs.append(bug)

    def update(self, screen, tileset, camera):
        """
        Draws all Bugs onto the screen.

        Arguments:
            screen: the screen to draw onto
            tileset: the tileset to use for drawing
            camera: the camera to project from
        """
        for bug in self._bugs:
            screen.blit(tileset,
                        camera.transform_game_to_screen(
                            (bug.x, bug.y), scalar=16),
                        (7 * 16, 0, 16, 16))
