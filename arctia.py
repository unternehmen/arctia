#!/usr/bin/env python
import pygame
import atexit
import sys
import os
import pytmx
import math

from config import *
from common import *
from stage import Stage
from stockpile import Stockpile
from job import Job, HaulJob, MineJob
from task import TaskGo, TaskMine, TaskTake, TaskDrop, TaskTrade, TaskGoToAnyMatchingSpot
from stopwatch import Stopwatch

from astar import astar
from partition import partition

class PartitionSystem(object):
    def __init__(self, stage, mobs):
        self._mobs = mobs
        self._stage = stage

        stage.register_tile_change_listener(self)

        self.refresh()

    def tile_changed(self, prev_id, cur_id, coords):
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
        self._refresh_partial(self._mobs)


class Penguin(object):
    """
    A Penguin is a unit that follows the player's orders.
    """
    def __init__(self, ident, stage, x, y, jobs, stopwatch, stockpiles):
        """
        Create a new Penguin.

        Arguments:
            ident: an identification number
            stage: the Stage the penguin exists in
            x: the x coordinate of the penguin
            y: the y coordinate of the penguin
            jobs: the global list of Jobs
            stopwatch: the global Stopwatch
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

        # Stopwatch cookie for scheduling the penguin's turns
        self._cookie = stopwatch.start()

        ## Gameplay stats
        # The penguin's hunger (0 = full, >40 = hungry, >80 = starving)
        self._hunger = 0

        ## Job data
        # Amount of work left (in turns) for the current job
        self._work_left = 0

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
        self._stopwatch = stopwatch
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
                            return no_entities and not_solid
                        task = TaskGoToAnyMatchingSpot(
                                 self._stage, self, spot_is_empty,
                                 impossible_proc=nowhere_to_dump_error,
                                 finished_proc=drop_and_finish)
                        self._current_task = task

                    def drop_and_finish():
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
                        # Check if we can reach the stockpile.
                        sx = self._current_job.stockpile.x
                        sy = self._current_job.stockpile.y
                        if not self.partition[sy][sx]:
                            drop_and_finish()
                        else:
                            task = TaskGo(self._stage, self,
                                          self._current_job.slot_location,
                                          blocked_proc=drop_and_forget,
                                          finished_proc=drop_and_finish)
                            self._current_task = task
                    
                    def pick_up_and_go():
                        task = TaskTake(self._stage,
                                        self, entity,
                                        finished_proc=\
                                          go_to_stock_slot)
                        self._current_task = task

                    task = TaskGo(self._stage, self, (x, y),
                                  blocked_proc=self._forget_job,
                                  finished_proc=pick_up_and_go)
                    self._current_task = task

                    entity.reserve()

                    job = HaulJob(entity, (x, y))
                    job.slot_location = stock.reserve_slot()
                    job.stockpile = stock

                    self._current_job = job

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

    def _take_turn(self):
        """
        Make the Penguin take a turn.
        """
        # Get hungrier.
        self._hunger += 1

        if self._current_task:
            self._current_task.enact()

    def update(self):
        """
        Update the state of the Penguin.

        This should be called every frame before drawing.
        """
        if self._current_job is None:
            self._look_for_job()

        if self._stopwatch.measure(self._cookie) == 10:
            self._cookie = self._stopwatch.start()
            self._take_turn()


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
    stopwatch = Stopwatch()

    # for now, stockpiles will be just for fish...
    stockpiles = [Stockpile(stage, (50, 50, 4, 4),
                            jobs, ['fish'])]
    penguin_offsets = [(0, 0), (1, -1), (-1, 1), (-1, -1), (1, 1)]
    penguins = []
    timeslice = 0
    ident = 0
    for x, y in penguin_offsets:
        penguins.append(Penguin(ident, stage,
                                math.floor(player_start_x / 16) + x,
                                math.floor(player_start_y / 16) + y,
                                jobs,
                                stopwatch, stockpiles))
        ident += 1

    partition_system = PartitionSystem(stage, penguins)

    drag_origin = None
    block_origin = None

    tools = ['cursor', 'mine', 'haul', 'stockpile']
    selected_tool = 'cursor'


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
                            stage.set_tile_at(tx, ty, 2)
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

        # Update the game state.
        for penguin in penguins:
            penguin.update()

        # Clear the screen.
        virtual_screen.fill((0, 0, 0))

        # Draw the world.
        stage.draw(virtual_screen, tileset, camera_x, camera_y)

        for penguin in penguins:
            penguin.draw(virtual_screen, tileset, camera_x, camera_y)

        # Draw stockpiles.
        for pile in stockpiles:
            pile.draw(virtual_screen, tileset, camera_x, camera_y)

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
        stopwatch.tick()
        clock.tick(40)
