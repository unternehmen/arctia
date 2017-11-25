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

        self._refresh()

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


    def _refresh(self):
        """
        Update the partition matrices of all known mobs.
        """
        _refresh_partitions_of_mobs(self._stage, self._mobs)

    def update(self):
        """
        Do nothing.

        This method exists so that this class matches the interface of
        other systems.
        """
        pass


class UnitDispatchSystem(object):
    """
    A UnitDispatchSystem chooses jobs for units to do.

    Arguments:
        stage: the stage
    """
    def __init__(self, stage):
        self._units = []
        self._stage = stage

    def add(self, unit):
        """
        Add a unit whose jobs should be managed by this system.

        Arguments:
            unit: the unit
        """
        self._units.append(unit)

    def update(self):
        """
        Give jobs to all units that need them.

        Only run this once every turn (not every frame).
        """
        def _forget_task(unit):
            unit.task = None

        for unit in self._units:
            if unit.task:
                unit.task.enact()

            if 'eating' in unit.components:
                if not unit.task and unit.hunger >= unit.hunger_threshold:
                    # Find a piece of food the unit can reach.
                    def _is_valid_food(unit, entity, _unused_x, _unused_y):
                        kind = entity.kind
                        x, y = entity.location
                        return unit.partition[y][x] and kind in unit.hunger_diet

                    result = \
                      self._stage.find_entity(partial(_is_valid_food, unit))

                    if result:
                        entity, _ = result

                        def _eat_food(unit, entity):
                            unit.task = TaskEat(self._stage,
                                                unit, entity,
                                                interrupted_proc=\
                                                  partial(_forget_task, unit),
                                                finished_proc=\
                                                  partial(_forget_task, unit))

                        # Make the unit go eat the food.
                        # unit - TaskGo doesn't recover if the object is
                        #       stolen by another unit (?)
                        unit.task = TaskGo(self._stage, unit,
                                           entity.location,
                                           delay=unit.movement_delay,
                                           blocked_proc=\
                                             partial(_forget_task,
                                                     unit),
                                           finished_proc=\
                                             partial(_eat_food,
                                                     unit, entity))

            if not unit.task:
                # Choose whether to brood or to wander.
                choices = ['wandering', 'brooding']
                choices = \
                    list(
                        filter(
                            lambda obj: obj in unit.components,
                            choices))
                selected = random.choice(choices)

                if selected == 'wandering':
                    # Step wildly to find a goal for our wandering.
                    goal = unit.x, unit.y

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
                    unit.task = TaskGo(self._stage, unit, goal,
                                       delay=\
                                         unit.movement_delay \
                                         + unit.wandering_delay,
                                       blocked_proc=\
                                         partial(_forget_task, unit),
                                       finished_proc=\
                                         partial(_forget_task, unit))
                elif selected == 'brooding':
                    unit.task = TaskWait(duration=unit.brooding_duration,
                                         finished_proc=\
                                           partial(_forget_task, unit))

            unit.hunger += 1


class UnitDrawSystem(object):
    """
    A UnitDrawSystem draws units onto the screen.
    """
    def __init__(self):
        self._units = []

    def add(self, unit):
        """
        Add a unit to be drawn by this system.

        Arguments:
            unit: the unit
        """
        self._units.append(unit)

    def update(self, screen, tileset, camera):
        """
        Draws all units onto the screen.

        Arguments:
            screen: the screen to draw onto
            tileset: the tileset to use for drawing
            camera: the camera to project from
        """
        for unit in self._units:
            screen.blit(tileset,
                        camera.transform_game_to_screen(
                            (unit.x, unit.y), scalar=16),
                        unit.clip)
