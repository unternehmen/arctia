"""
The systems module provides classes which update the game's state.
"""
from functools import partial
import random

from .common import tile_is_solid
from .partition import partition
from .transform import translate
from .task import TaskEat, TaskGo, TaskWait, TaskMine, TaskTake, \
                  TaskTrade, TaskGoToAnyMatchingSpot, TaskDrop


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

    def _seek_idling_job(self, unit):
        def _forget_task(unit):
            unit.task = None

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

    def _seek_eating_job(self, unit):
        def _forget_task(unit, entity):
            unit.task = None
            if unit.team:
                unit.team.relinquish('entity', entity)

        if not unit.task and unit.hunger >= unit.hunger_threshold:
            # Find a piece of food the unit can reach.
            def _is_valid_food(unit, entity, _unused_x, _unused_y):
                kind = entity.kind
                x, y = entity.location
                reserved = False
                if unit.team:
                    reserved = unit.team.is_reserved('entity', entity)
                return unit.partition[y][x] \
                       and kind in unit.hunger_diet \
                       and not reserved

            result = \
              self._stage.find_entity(partial(_is_valid_food, unit))

            if result:
                entity, _ = result

                def _eat_food(unit, entity):
                    unit.task = TaskEat(self._stage,
                                        unit, entity,
                                        interrupted_proc=\
                                          partial(_forget_task,
                                                  unit, entity),
                                        finished_proc=\
                                          partial(_forget_task,
                                                  unit, entity))

                if unit.team:
                    unit.team.reserve('entity', entity)
                unit.task = TaskGo(self._stage, unit,
                                   entity.location,
                                   delay=unit.movement_delay,
                                   blocked_proc=\
                                     partial(_forget_task,
                                             unit, entity),
                                   finished_proc=\
                                     partial(_eat_food,
                                             unit, entity))

    def _seek_mining_job(self, unit):
        assert unit.team, 'unit considered mining but has no team'

        # Find a mining job first.
        for designation in filter(lambda d: d['kind'] == 'mine',
                                  unit.team.designations):
            loc = designation['location']

            # If we can't reach the mining job, skip it.
            if not unit.partition[loc[1]][loc[0]]:
                continue

            # If the mining job is reserved or already done, skip it.
            if unit.team.is_reserved('mine', designation) \
               or designation['done']:
                continue

            # Take the job.
            def _complete_mining(designation):
                designation['done'] = True
                unit.task = None

            def _forget_job(designation):
                unit.team.relinquish('mine', designation)
                unit.task = None

            def _start_mining(designation):
                loc = designation['location']
                task = TaskMine(self._stage, unit, loc,
                                finished_proc = \
                                  partial(_complete_mining,
                                          designation))
                unit.task = task

            task = TaskGo(self._stage, unit, loc,
                          blocked_proc=\
                            partial(_forget_job, designation),
                          finished_proc=\
                            partial(_start_mining, designation))
            unit.task = task
            unit.team.reserve('mine', designation)
            return

    def _seek_hauling_job(self, unit):
        assert unit.team, 'unit considered hauling but has no team'

        for stock in unit.team.stockpiles:
            # If we cannot reach the stockpile, skip it.
            if not unit.partition[stock.y][stock.x]:
                continue

            # Determine whether the stockpile is full or not.
            pile_is_full = True
            chosen_slot = None
            accepted_kinds = stock.accepted_kinds

            for y in range(stock.y, stock.y + stock.height):
                for x in range(stock.x, stock.x + stock.width):
                    loc = x, y
                    ent = self._stage.entity_at(loc)

                    if ent and ent.kind in accepted_kinds:
                        continue

                    if unit.team.is_reserved('location', loc):
                        continue

                    chosen_slot = loc
                    pile_is_full = False
                    break
                if not pile_is_full:
                    break

            # If the stockpile is full, skip it.
            if pile_is_full:
                continue

            # Find an entity that needs to be stored in the stockpile.
            def _entity_is_stockpiled(entity, x, y):
                for stock in unit.team.stockpiles:
                    if entity.kind in stock.accepted_kinds \
                       and x >= stock.x \
                       and x < stock.x + stock.width \
                       and y >= stock.y \
                       and y < stock.y + stock.height:
                        return True
                return False

            result = \
              self._stage.find_entity(
                lambda e, x, y: \
                  unit.partition[y][x] \
                  and e.kind in accepted_kinds \
                  and not unit.team.is_reserved('entity', e) \
                  and not _entity_is_stockpiled(e, x, y))

            # If there is no such entity, skip this stockpile.
            if not result:
                break

            # Otherwise, take the hauling job.
            entity, loc = result
            x, y = loc

            def _start_haul_job(stock, entity, chosen_slot):
                unit.team.reserve('location', chosen_slot)
                unit.team.reserve('entity', entity)
                unit.task = \
                    TaskGo(self._stage, unit,
                           target=entity.location,
                           delay=0,
                           blocked_proc=\
                             partial(_abort_entity_inaccessible,
                                     stock, entity, chosen_slot),
                           finished_proc=
                             partial(_pick_up_entity,
                                     stock, entity, chosen_slot))


            def _pick_up_entity(stock, entity, chosen_slot):
                unit.task = \
                    TaskTake(self._stage, unit, entity,
                             not_found_proc=\
                               partial(_abort_entity_inaccessible,
                                       stock, entity, chosen_slot),
                             finished_proc=\
                               partial(_haul_entity_to_slot,
                                       stock, entity, chosen_slot))

            def _abort_entity_inaccessible(_unused_stock,
                                          entity, chosen_slot):
                unit.team.relinquish('location', chosen_slot)
                unit.team.relinquish('entity', entity)
                unit.task = None

            def _haul_entity_to_slot(stock, entity, chosen_slot):
                unit.team.relinquish('entity', entity)
                unit.task = \
                    TaskGo(self._stage, unit,
                           target=chosen_slot,
                           delay=0,
                           blocked_proc=\
                             partial(_abort_dump_wherever,
                                     stock, entity, chosen_slot),
                           finished_proc=\
                             partial(_put_entity_into_slot,
                                     stock, entity, chosen_slot))

            def _abort_dump_wherever(stock, entity, chosen_slot):
                def _location_is_empty(loc):
                    return not self._stage.entity_at(loc)
                if unit.team.is_reserved('location', chosen_slot):
                    unit.team.relinquish('location', chosen_slot)
                unit.task = \
                  TaskGoToAnyMatchingSpot(
                    self._stage, unit,
                    condition_func=_location_is_empty,
                    impossible_proc=\
                      partial(_die_no_dump_location,
                              stock, entity, chosen_slot),
                    finished_proc=\
                      partial(_try_to_dump,
                              stock, entity, chosen_slot))

            def _try_to_dump(stock, entity, chosen_slot):
                unit.task = \
                  TaskDrop(
                    self._stage, entity, unit,
                    blocked_proc=\
                      partial(_abort_dump_wherever,
                              stock, entity, chosen_slot),
                    finished_proc=_abort_no_cleanup_needed)

            def _die_no_dump_location(_unused_stock,
                                     _unused_entity,
                                     _unused_chosen_slot):
                assert False, 'error: no accessible dump location'

            def _put_entity_into_slot(stock, entity, chosen_slot):
                occupier = self._stage.entity_at(chosen_slot)

                if occupier:
                    unit.task = \
                      TaskTrade(
                        self._stage, entity, unit, occupier,
                        finished_proc=\
                          partial(_abort_dump_wherever,
                                  stock, occupier, chosen_slot))
                else:
                    unit.task = \
                      TaskDrop(
                        self._stage, entity, unit,
                        blocked_proc=\
                          partial(_put_entity_into_slot,
                                  stock, entity, chosen_slot),
                        finished_proc=\
                          partial(_abort_and_relinquish_slot,
                                  stock, entity, chosen_slot))

            def _abort_no_cleanup_needed():
                unit.task = None

            def _abort_and_relinquish_slot(stock, entity, chosen_slot):
                unit.team.relinquish('location', chosen_slot)
                unit.task = None

            _start_haul_job(stock, entity, chosen_slot)
            return

    def update(self):
        """
        Give jobs to all units that need them.

        Only run this once every turn (not every frame).
        """
        def _forget_task(unit):
            unit.task = None

        for unit in self._units:
            if not unit.task:
                if 'eating' in unit.components:
                    self._seek_eating_job(unit)

                if not unit.task and 'mining' in unit.components:
                    self._seek_mining_job(unit)

                if not unit.task and 'hauling' in unit.components:
                    self._seek_hauling_job(unit)

                if not unit.task:
                    self._seek_idling_job(unit)

            if unit.task:
                unit.task.enact()

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
