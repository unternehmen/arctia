"""
The systems module provides classes which update the game's state.
"""
from functools import partial
import random

from .common import tile_is_solid
from .partition import partition
from .transform import translate
from .task import TaskEat, TaskGo, TaskWait, TaskMine, TaskTake, \
                  TaskGoToAnyMatchingSpot, TaskDrop

def assign_tasks(unit, designation, deps, tasklist):
    """
    Assign a unit to perform a sequence of tasks.

    Args:
        unit: The unit which shall do the tasks
        designation: The designation of the job or None
        deps: The list of things which should be reserved for the unit
            to perform the task.  This must be a list of tuples of the
            following form: [(kind, obj), ...].  For example,
            [('location', (2, 2))] means the unit should reserve the
            location at coordinates (2, 2).
        tasklist: A list of functions which all return a task.  Each
            function should take two arguments, `abort` and `finish`,
            which are callbacks which may be hooked into the tasks in
            order to carry out the task sequence.
    """
    def abort():
        if unit.team:
            for kind, obj in deps:
                unit.team.relinquish(kind, obj)
        unit.task = None
    def finish():
        abort()
        if designation:
            designation['done'] = True
    next_proc = finish
    for task in reversed(tasklist):
        def proc(task, next_proc):
            unit.task = task(abort, next_proc)
        next_proc = partial(proc, task, next_proc)
    if unit.team:
        for kind, obj in deps:
            unit.team.reserve(kind, obj)
    next_proc()

def _die_cannot_dump():
    assert False, 'error: no accessible dump location'

def assign_dump_job_func(stage, unit, entity, condition_func):
    def func():
        assign_tasks(unit, None,
                     [('entity', entity)],
                     [lambda _unused_abort, finish:
                        TaskGoToAnyMatchingSpot(
                          stage, unit,
                          condition_func=condition_func,
                          impossible_proc=_die_cannot_dump,
                          finished_proc=finish),
                      lambda abort, finish:
                        TaskDrop(stage, entity, unit,
                                 blocked_proc=
                                   do_both(
                                     abort,
                                     assign_dump_job_func(
                                       stage, unit, entity,
                                       condition_func)),
                                 finished_proc=finish)])
    return func

def do_both(proc_a, proc_b):
    def wrapper():
        proc_a()
        proc_b()
    return wrapper

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

    def _try_assigning_idling_job(self, unit):
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
            assign_tasks(unit, None, [],
                         [lambda abort, finish:
                            TaskGo(self._stage, unit, goal,
                                   delay=unit.movement_delay
                                         + unit.wandering_delay,
                                   blocked_proc=abort,
                                   finished_proc=finish)])
        elif selected == 'brooding':
            # Do nothing for the unit's brooding duration.
            assign_tasks(unit, None, [],
                         [lambda _unused_abort, finish:
                            TaskWait(duration=unit.brooding_duration,
                                     finished_proc=finish)])

    def _try_assigning_eating_job(self, unit):
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

                assign_tasks(unit, None,
                             [('entity', entity)],
                             [lambda abort, finish:
                                TaskGo(self._stage, unit, entity.location,
                                       delay=unit.movement_delay,
                                       blocked_proc=abort,
                                       finished_proc=finish),
                              lambda abort, finish:
                                TaskEat(self._stage, unit, entity,
                                        interrupted_proc=abort,
                                        finished_proc=finish)])

    def _try_assigning_mining_job(self, unit):
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
            assign_tasks(unit, designation,
                         [('mine', designation)],
                         [lambda abort, finish:
                            TaskGo(self._stage, unit, loc,
                                   blocked_proc=abort,
                                   finished_proc=finish),
                          lambda abort, finish:
                            TaskMine(self._stage, unit, loc,
                                     finished_proc=finish)])
            break


    def _try_assigning_hauling_job(self, unit):
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

                    if ent:
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
            entity, _ = result

            assign_dump_job = \
              assign_dump_job_func(
                self._stage, unit, entity,
                lambda loc:
                  not self._stage.entity_at(loc)
                  and not unit.team.is_reserved('location', loc))
            assign_tasks(unit, None,
                         [('location', chosen_slot),
                          ('entity', entity)],
                         [lambda abort, finish:
                            TaskGo(self._stage, unit,
                                   target=entity.location,
                                   delay=0,
                                   blocked_proc=abort,
                                   finished_proc=finish),
                          lambda abort, finish:
                            TaskTake(self._stage, unit, entity,
                                     not_found_proc=abort,
                                     finished_proc=finish),
                          lambda abort, finish:
                            TaskGo(self._stage, unit,
                                   target=chosen_slot,
                                   delay=0,
                                   blocked_proc=
                                     do_both(abort, assign_dump_job),
                                   finished_proc=finish),
                          lambda abort, finish:
                            TaskDrop(self._stage, entity, unit,
                                     blocked_proc=
                                       do_both(abort, assign_dump_job),
                                     finished_proc=finish)])
            break

    def _try_assigning_cleaning_job(self, unit):
        # Find a stockpile that has an unfitting item in it.
        found = False
        for stockpile in unit.team.stockpiles:
            if not unit.partition[stockpile.y][stockpile.x]:
                continue
            for y in range(stockpile.y,
                           stockpile.y + stockpile.height):
                for x in range(stockpile.x,
                               stockpile.x + stockpile.width):
                    entity = self._stage.entity_at((x, y))
                    if not entity:
                        continue
                    if entity.kind not in stockpile.accepted_kinds \
                       and not unit.team.is_reserved('entity', entity):
                        found = True
                        break
                if found:
                    break
            if found:
                break

        # Return out of this function if none were found
        if not found:
            return

        # Get that item and put it elsewhere.
        assign_tasks(unit, None,
                     [('entity', entity)],
                     [lambda abort, finish:
                        TaskGo(self._stage, unit,
                               target=entity.location,
                               delay=0,
                               blocked_proc=abort,
                               finished_proc=finish),
                      lambda abort, finish:
                        TaskTake(self._stage, unit, entity,
                                 not_found_proc=abort,
                                 finished_proc=
                                   do_both(
                                     finish,
                                     assign_dump_job_func(
                                       self._stage, unit, entity,
                                       lambda loc:
                                         not self._stage.entity_at(loc)
                                         and not unit.team.is_reserved('location', loc)
                                         and not stockpile.containsloc(loc))))])

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
                    self._try_assigning_eating_job(unit)

                if not unit.task and 'mining' in unit.components:
                    self._try_assigning_mining_job(unit)

                if not unit.task and 'hauling' in unit.components:
                    self._try_assigning_hauling_job(unit)
                    if not unit.task:
                        self._try_assigning_cleaning_job(unit)

                if not unit.task:
                    self._try_assigning_idling_job(unit)

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
