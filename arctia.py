#!/usr/bin/env python
import pygame
import atexit
import sys
import os
import pytmx
import math
import random
from functools import partial

from config import *
from common import *
from stage import Stage
from stockpile import Stockpile
from job import Job, HaulJob, MineJob
from task import TaskGo, TaskMine, TaskTake, TaskDrop, TaskTrade, TaskGoToAnyMatchingSpot, TaskEat, TaskWait

from astar import astar
from partition import partition

class PartitionSystem(object):
    """
    A PartitionSystem updates the partition matrix of units.

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

    def tile_changed(self, prev_id, cur_id, coords):
        """
        Notify the PartitionSystem that a tile has changed.

        Arguments:
            prev_id: the previous ID of the changed tile
            cur_id: the current ID of the changed tile
            coords: the (x, y) coordinates of the changed tile
        """
        x, y = coords

        # Determine which mobs need partition refreshs.
        mobs_to_refresh = []

        for mob in self._mobs:
            need_refresh = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ox = mob.x + dx
                    oy = mob.y + dy

                    if mob.partition[oy][ox]:
                        need_refresh = True
                        break
                if need_refresh:
                    break
            if need_refresh:
                mobs_to_refresh.append(mob)

        # Update partitions on mobs which need it.
        self._refresh_partial(mobs_to_refresh)

    def _refresh_partial(self, mobs):
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

    def refresh(self):
        """
        Update the partition matrices of all mobs.
        """
        self._refresh_partial(self._mobs)


class BugDispatchSystem(object):
    """
    A BugDispatchSystem chooses jobs for bugs to do.
    """
    def __init__(self, stage):
        self._bugs = []
        self._stage = stage

    def add(self, bug):
        self._bugs.append(bug)

    def update(self):
        """
        Only run this once every turn (not every frame).
        """
        def forget_task(bug):
            bug.task = None

        i = 0
        for bug in self._bugs:
            if bug.task:
                bug.task.enact()
            elif bug.hunger >= bug.hunger_threshold:
                # Find a piece of food the bug can reach.
                def is_valid_food(entity, a, b):
                    kind = entity.kind
                    x, y = entity.location
                    return bug.partition[y][x] and kind == 'fish'

                result = self._stage.find_entity(is_valid_food)
                  
                if result:
                    entity, loc = result

                    def eat_food(bug, entity):
                        bug.task = TaskEat(self._stage, 
                                           bug, entity,
                                           interrupted_proc=\
                                             partial(forget_task, bug),
                                           finished_proc=\
                                             partial(forget_task, bug))

                    # Make the bug go eat the food.
                    # bug - TaskGo doesn't recover if the object is
                    #       stolen by another unit (?)
                    bug.task = TaskGo(self._stage, bug, entity.location, 
                                      blocked_proc=partial(forget_task, bug),
                                      finished_proc=partial(eat_food, bug, entity))
            else:
                # Choose whether to brood or to wander.
                choices = ['wandering', 'brooding']
                available = map(lambda a: a in bug.components, choices)
                selected = random.choice(choices)

                if selected == 'wandering':
                    # Step wildly to find a goal for our wandering.
                    goal = bug.x, bug.y

                    for step in range(40):
                        offset = random.choice([(-1, -1), (-1, 0),
                                                (-1, 1), (0, -1),
                                                (0, 1), (1, -1),
                                                (1, 0), (1, 1)])
                        shifted = goal[0] + offset[0], \
                                  goal[1] + offset[1]
                        if 0 <= shifted[0] < self._stage.width \
                           and 0 <= shifted[1] < self._stage.height \
                           and not tile_is_solid(
                                     self._stage.get_tile_at(
                                       *shifted)):
                            goal = shifted

                    # Go to our goal position.
                    bug.task = TaskGo(self._stage, bug, goal,
                                      delay=bug.wandering_delay,
                                      blocked_proc=partial(forget_task,
                                                           bug),
                                      finished_proc=partial(forget_task,
                                                            bug))
                elif selected == 'brooding':
                    bug.task = TaskWait(duration=bug.brooding_duration,
                                        finished_proc=\
                                          partial(forget_task, bug))
            bug.hunger += 1
            i += 1

class BugDrawSystem(object):
    def __init__(self):
        self._bugs = []

    def update(self, screen, tileset, camera_x, camera_y):
        for bug in self._bugs:
            screen.blit(tileset,
                        (bug.x * 16 - camera_x + MENU_WIDTH,
                         bug.y * 16 - camera_y),
                        (7 * 16, 0, 16, 16))

    def add(self, bug):
        self._bugs.append(bug)


class Bug(object):
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.hunger = 0
        self.hunger_threshold = 50
        self.wandering_delay = 1
        self.brooding_duration = 6
        self.task = None
        self.partition = None
        self.components = ['eating', 'wandering', 'brooding']


class Penguin(object):
    """
    A Penguin is a unit that follows the player's orders.
    """
    def __init__(self, ident, stage, x, y, jobs, stockpiles):
        """
        Create a new Penguin.

        Arguments:
            ident: an identification number
            stage: the Stage the penguin exists in
            x: the x coordinate of the penguin
            y: the y coordinate of the penguin
            jobs: the global list of Jobs
            stockpiles: the global list of Stockpiles

        Returns: a new Penguin
        """
        assert x >= 0 and x < stage.width
        assert y >= 0 and y < stage.height

        ## Main data
        # The penguin's identification number (used for debugging)
        self.ident = ident

        # The penguin's location
        self.x = x
        self.y = y

        # The partition of the stage that this penguin can reach
        self.partition = None

        ## Gameplay stats
        # The penguin's hunger (0 = full, >40 = hungry, >80 = starving)
        self._hunger = 0

        ## Job data
        # Entity held by the penguin for a drop-job
        self._held_entity = None

        # The penguin's current job
        self._current_job = None

        # The penguin's current task
        self._current_task = None

        # The path to the penguin's current job
        self._path_to_current_job = None

        ## External data
        self._stage = stage
        self._stockpiles = stockpiles
        self._jobs = jobs

    def draw(self, screen, tileset, camera_x, camera_y):
        """
        Draw the Penguin onto a screen or surface.

        Arguments:
            screen: the Pygame screen or surface
            tileset: the tileset to use
            camera_x: the x coordinate of the camera
            camera_y: the y coordinate of the camera
        """
        screen.blit(tileset,
                    (self.x * 16 - camera_x + MENU_WIDTH,
                     self.y * 16 - camera_y),
                    (0, 0, 16, 16))

    def _look_for_job(self):
        """
        Find a job to do.
        """
        assert self._current_job is None, \
               'Penguin %s looked for a job but it already has one!' % \
                 self.ident

        if self._hunger >= HUNGER_THRESHOLD:
            # Look for food!
            pass

        # Find a mining job first.
        for job in filter(lambda j: isinstance(j, MineJob), self._jobs):
            x, y = job.locations[0]

            if self.partition[y][x]:
                if job.reserved or job.done:
                    continue

                def start_mining():
                    task = TaskMine(self._stage, self, (x, y),
                                    finished_proc = \
                                      self._finish_job_entirely)
                    self._current_task = task

                task = TaskGo(self._stage, self, (x, y),
                              blocked_proc=self._forget_job,
                              finished_proc=start_mining)
                self._current_task = task

                job.reserve()
                self._current_job = job
                return

        # Otherwise, find a hauling job.
        for stock in self._stockpiles:
            if not stock.full and self.partition[stock.y][stock.x]:
                def _entity_is_stockpiled(entity, x, y):
                    for stock in self._stockpiles:
                        if entity.kind in stock.accepted_kinds \
                           and x >= stock.x \
                           and x < stock.x + stock.w \
                           and y >= stock.y \
                           and y < stock.y + stock.h:
                            return True
                    return False

                result = \
                  self._stage.find_entity(
                    lambda e, x, y: \
                      self.partition[y][x] \
                      and e.kind in stock.accepted_kinds \
                      and not e.reserved \
                      and not _entity_is_stockpiled(e, x, y))

                if result:
                    entity, loc = result
                    x, y = loc

                    def cancel_haul():
                        self._current_job.stockpile.relinquish_slot(
                            self._current_job.slot_location)
                        self._forget_job()

                    def drop_and_forget():
                        task = TaskDrop(self._stage, self,
                                        finished_proc=\
                                            cancel_haul)
                        self._current_task = task

                    def nowhere_to_dump_error():
                        assert False, 'penguin could not find anywhere to dump an object'

                    def dump_somewhere():
                        def spot_is_empty(spot):
                            no_entities = \
                              self._stage.entity_at(spot) is None
                            not_solid = \
                              not tile_is_solid( \
                                    self._stage.get_tile_at( \
                                      spot[0], spot[1]))
                            not_in_stock = spot[0] < stock.x \
                                           or spot[0] >= stock.x + stock.w \
                                           or spot[1] < stock.y \
                                           or spot[1] >= stock.y + stock.h
                            return no_entities and not_solid and not_in_stock
                        task = TaskGoToAnyMatchingSpot(
                                 self._stage, self, spot_is_empty,
                                 impossible_proc=nowhere_to_dump_error,
                                 finished_proc=drop_and_finish)
                        self._current_task = task
                    
                    def try_storing_it():
                        occupier = self._stage.entity_at(
                                     (self.x, self.y))
                        if occupier:
                            task = TaskTrade(self._stage, self,
                                             occupier,
                                             finished_proc=\
                                                 dump_somewhere)
                        else:
                            task = TaskDrop(self._stage, self,
                                            finished_proc=\
                                              self._finish_job_entirely)
                        self._current_task = task

                    def go_to_stock_slot():
                        # Unreserve the object we picked up.
                        self._held_entity.relinquish()

                        # Check if we can reach the stockpile.
                        sx = self._current_job.stockpile.x
                        sy = self._current_job.stockpile.y
                        if not self.partition[sy][sx]:
                            drop_and_finish()
                        else:
                            task = TaskGo(self._stage, self,
                                          self._current_job.slot_location,
                                          blocked_proc=drop_and_forget,
                                          finished_proc=try_storing_it)
                            self._current_task = task
                    
                    def pick_up_and_go():
                        task = TaskTake(self._stage,
                                        self, entity,
                                        not_found_proc=\
                                          self._forget_job,
                                        finished_proc=\
                                          go_to_stock_slot)
                        self._current_task = task

                    task = TaskGo(self._stage, self, (x, y),
                                  blocked_proc=self._forget_job,
                                  finished_proc=pick_up_and_go)
                    self._current_task = task

                    entity.reserve()

                    job = HaulJob(entity)
                    job.slot_location = stock.reserve_slot()
                    job.stockpile = stock

                    self._current_job = job
                    return

    def _forget_job(self):
        self._current_task = None
        self._current_job.relinquish()
        self._current_job = None
        self._path_to_current_job = None
        self._look_for_job()

    def _finish_job_entirely(self):
        """
        Mark the current job as complete and get rid of its state.
        """
        self._current_task = None
        self._current_job.finish()
        self._current_job = None
        self._path_to_current_job = None
        self._look_for_job()

    def update(self):
        """
        Update the state of the Penguin.

        This should only be called once every turn.
        """
        # Find a job if we don't have one.
        if self._current_job is None:
            self._look_for_job()

        # Get hungrier.
        self._hunger += 1

        # If we have a task, do it.
        if self._current_task:
            self._current_task.enact()


if __name__ == '__main__':
    pygame.init()
    atexit.register(pygame.quit)
    screen = pygame.display.set_mode(SCREEN_REAL_DIMS)
    virtual_screen = pygame.Surface(SCREEN_LOGICAL_DIMS)
    scaled_screen = pygame.Surface(SCREEN_REAL_DIMS)

    pygame.mixer.music.load(os.path.join('music', 'nescape.ogg'))
    tileset = pygame.image.load(os.path.join('gfx', 'tileset.png'))
    stage = Stage(os.path.join('maps', 'tuxville.tmx'))

    player_start_x, player_start_y = stage.get_player_start_pos()
    camera_x = player_start_x + 8 \
               - math.floor(SCREEN_LOGICAL_WIDTH / 2.0)
    camera_y = player_start_y + 8 \
               - math.floor(SCREEN_LOGICAL_HEIGHT / 2.0)
    jobs = []
    for entity in stage.entities:
        kind, x, y = entity
        if kind == 'fish':
            jobs.append(HaulJob(entity))

    # for now, stockpiles will be just for fish...
    stockpiles = [Stockpile(stage, (50, 50, 4, 4),
                            jobs, ['fish'])]
    penguin_offsets = [(0, 0), (1, -1), (-1, 1), (-1, -1), (1, 1)]
    mobs = []
    penguins = []
    timeslice = 0
    ident = 0

    for x, y in penguin_offsets:
        penguins.append(Penguin(ident, stage,
                                math.floor(player_start_x / 16) + x,
                                math.floor(player_start_y / 16) + y,
                                jobs,
                                stockpiles))
        ident += 1

    mobs += penguins

    bugs = [Bug(51, 50),
            Bug(52, 50),
            Bug(53, 50),
            Bug(54, 50)]

    mobs += bugs

    bug_dispatch_system = BugDispatchSystem(stage)
    bug_draw_system = BugDrawSystem()

    for bug in bugs:
        bug_dispatch_system.add(bug)
        bug_draw_system.add(bug)

    partition_system = PartitionSystem(stage, mobs)

    drag_origin = None
    block_origin = None

    tools = ['cursor', 'mine', 'haul', 'stockpile']
    selected_tool = 'cursor'


    subturn = 0
    pygame.mixer.music.play(loops=-1)
    clock = pygame.time.Clock()
    while True:
        # Handle user input.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx = math.floor(event.pos[0] / SCREEN_ZOOM)
                my = math.floor(event.pos[1] / SCREEN_ZOOM)
                if event.button == 1:
                    if mx < MENU_WIDTH:
                        # Select a tool in the menu bar.
                        if my < len(tools) * 16:
                            selected_tool = tools[math.floor(my / 16)]
                    else:
                        # Use the selected tool.
                        if selected_tool == 'cursor':
                            tx = math.floor((camera_x + mx
                                             - MENU_WIDTH)
                                            / 16)
                            ty = math.floor((camera_y + my) / 16)
                            #stage.set_tile_at(tx, ty, 2)
                            ent = stage.entity_at((tx, ty))
                            if ent:
                                print('Entity:', ent.kind)
                                print('  location:', ent.location)
                                print('  reserved:', ent.reserved)
                            for penguin in penguins:
                                if (penguin.x, penguin.y) == (tx, ty):
                                    print('Penguin:')
                                    if penguin._current_job:
                                        print('  job:', penguin._current_job.__class__.__name__)
                                    else:
                                        print('  job: none')
                        elif selected_tool == 'mine' \
                             or selected_tool == 'stockpile':
                            tx = math.floor((camera_x + mx
                                             - MENU_WIDTH)
                                            / 16)
                            ty = math.floor((camera_y + my) / 16)
                            block_origin = tx, ty
                elif event.button == 3:
                    # Begin dragging the screen.
                    drag_origin = math.floor(event.pos[0] \
                                             / SCREEN_ZOOM), \
                                  math.floor(event.pos[1] \
                                             / SCREEN_ZOOM)
            elif event.type == pygame.MOUSEBUTTONUP:
                mx = math.floor(event.pos[0] / SCREEN_ZOOM)
                my = math.floor(event.pos[1] / SCREEN_ZOOM)
                if event.button == 1:
                    if block_origin:
                        ox, oy = block_origin
                        block_origin = None
                        tx = math.floor((camera_x + mx
                                         - MENU_WIDTH)
                                        / 16)
                        ty = math.floor((camera_y + my) / 16)

                        left = min((tx, ox))
                        right = max((tx, ox))
                        top = min((ty, oy))
                        bottom = max((ty, oy))

                        if selected_tool == 'mine':
                            for y in range(top, bottom + 1):
                                for x in range(left, right + 1):
                                    tid = stage.get_tile_at(x, y)

                                    if tid is None:
                                        pass
                                    elif tid == 2:
                                        job_exists = False
                                        for job in jobs:
                                            loc = job.locations[0]
                                            if loc == (x, y):
                                                job_exists = True
                                                break
                                        if not job_exists:
                                            jobs.append(MineJob((x, y)))
                        elif selected_tool == 'stockpile':
                            # Check if this conflicts with existing stockpiles.
                            conflicts = False
                            for stock in stockpiles:
                                sx, sy = stock.x, stock.y
                                sw, sh = stock.w, stock.h
                                if not (sx > right \
                                        or sy > bottom \
                                        or sx + sw <= left \
                                        or sy + sh <= top):
                                    conflicts = True
                                    break

                            all_walkable = True
                            for y in range(top, bottom + 1):
                                for x in range(left, right + 1):
                                    tid = stage.get_tile_at(x, y)

                                    if tid is None:
                                        pass
                                    elif tile_is_solid(tid):
                                        all_walkable = False
                                if not all_walkable:
                                    break

                            if not conflicts and all_walkable:
                                # Make the new stockpile.
                                stock = Stockpile(stage,
                                                  (left, top,
                                                   right - left + 1,
                                                   bottom - top + 1),
                                                  jobs, ['fish'])
                                stockpiles.append(stock)

                elif event.button == 3:
                    # Stop dragging the screen.
                    drag_origin = None

        # Get the mouse position for dragging and drawing cursors.
        mouse_x, mouse_y = pygame.mouse.get_pos()
        mouse_x = math.floor(mouse_x / SCREEN_ZOOM)
        mouse_y = math.floor(mouse_y / SCREEN_ZOOM)

        # Handle dragging the map.
        if drag_origin is not None:
            camera_x += (drag_origin[0] - mouse_x) \
                        * SCROLL_FACTOR
            camera_y += (drag_origin[1] - mouse_y) \
                        * SCROLL_FACTOR
            drag_origin = mouse_x, mouse_y

        # Delete finished jobs.
        for job in jobs:
            if job.done:
                jobs.remove(job)

        # Update the game state every turn.
        if subturn == 0:
            for penguin in penguins:
                penguin.update()

            bug_dispatch_system.update()

        # Clear the screen.
        virtual_screen.fill((0, 0, 0))

        # Draw the world.
        stage.draw(virtual_screen, tileset, camera_x, camera_y)

        for penguin in penguins:
            penguin.draw(virtual_screen, tileset, camera_x, camera_y)

        # Draw stockpiles.
        for pile in stockpiles:
            pile.draw(virtual_screen, tileset, camera_x, camera_y)

        # Draw bugs.
        bug_draw_system.update(virtual_screen, tileset, camera_x, camera_y)

        # Hilight MineJob designated areas.
        for job in filter(lambda x: isinstance(x, MineJob), jobs):
            pos = job.locations[0]
            virtual_screen.blit(tileset,
                                (pos[0] * 16 - camera_x \
                                 + MENU_WIDTH,
                                 pos[1] * 16 - camera_y),
                                (160, 0, 16, 16))

        # Draw the selection box under the cursor if there is one.
        if not block_origin and mouse_x > MENU_WIDTH:
            wx = math.floor((camera_x + mouse_x - MENU_WIDTH) / 16)
            wy = math.floor((camera_y + mouse_y) / 16)
            virtual_screen.blit(tileset,
                                (wx * 16 - camera_x + MENU_WIDTH,
                                 wy * 16 - camera_y),
                                (128, 0, 16, 16))

        # Draw the designation rectangle if we are drawing a region.
        if block_origin:
            ox, oy = block_origin
            tx = math.floor((camera_x + mouse_x - MENU_WIDTH) / 16)
            ty = math.floor((camera_y + mouse_y) / 16)

            left = min((tx, ox))
            right = max((tx, ox))
            top = min((ty, oy))
            bottom = max((ty, oy))

            virtual_screen.blit(tileset,
                                (left * 16 - camera_x + MENU_WIDTH,
                                 top * 16 - camera_y),
                                (128, 0, 8, 8))
            virtual_screen.blit(tileset,
                                (left * 16 - camera_x + MENU_WIDTH,
                                 bottom * 16 - camera_y + 8),
                                (128, 8, 8, 8))
            virtual_screen.blit(tileset,
                                (right * 16 - camera_x + MENU_WIDTH + 8,
                                 top * 16 - camera_y),
                                (136, 0, 8, 8))
            virtual_screen.blit(tileset,
                                (right * 16 - camera_x + MENU_WIDTH + 8,
                                 bottom * 16 - camera_y + 8),
                                (136, 8, 8, 8))

        # Draw the menu bar.
        pygame.draw.rect(virtual_screen,
                         (0, 0, 0),
                         (0, 0, MENU_WIDTH, SCREEN_LOGICAL_HEIGHT))

        for i in range(len(tools)):
            if selected_tool == tools[i]:
                offset_y = 32
            else:
                offset_y = 16
            virtual_screen.blit(tileset, (0, i * 16),
                                (128 + i * 16, offset_y, 16, 16))

        # Scale and draw onto the real screen.
        pygame.transform.scale(virtual_screen,
                               SCREEN_REAL_DIMS,
                               scaled_screen)
        screen.blit(scaled_screen, (0, 0))
        pygame.display.flip();

        # Wait for the next frame.
        subturn = (subturn + 1) % 10
        clock.tick(40)
