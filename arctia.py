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
from job import Job, HaulJob, MineJob, DropJob
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

        ## Job data
        # Amount of work left (in turns) for the current job
        self._work_left = 0

        # Entity held by the penguin for a drop-job
        self._held_entity = None

        # The penguin's current job
        self._current_job = None

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
        # Find a mining job first.
        for job in filter(lambda j: isinstance(j, MineJob), self._jobs):
            x, y = job.locations[0]

            if self.partition[y][x]:
                if job.reserved or job.done:
                    continue

                path = astar(self._stage,
                             (self.x, self.y),
                             job.locations[0])
                assert path

                job.reserve()
                self._current_job = job
                self._path_to_current_job = path[1:]
                self._work_left = 10
                break

        if self._current_job:
            return

        # Otherwise, find a hauling job.
        for job in filter(lambda j: isinstance(j, HaulJob), self._jobs):
            x, y = job.locations[0]

            if self.partition[y][x]:
                if job.reserved or job.done:
                    continue

                # Ensure that there is a stockpile we can haul to.
                found_stockpile = None
                for stock in self._stockpiles:
                    if self.partition[stock.y][stock.x]:
                        if job.entity[0] in stock.accepted_kinds:
                            found_stockpile = stock
                            break

                if found_stockpile and not found_stockpile.full:
                    slot = found_stockpile.reserve_slot()

                    job.slot_location = slot

                    path = astar(self._stage,
                                 (self.x, self.y),
                                 job.locations[0])
                    assert path

                    job.reserve()
                    self._current_job = job
                    self._path_to_current_job = path[1:]
                    break

    def _take_turn(self):
        """
        Make the Penguin take a turn.
        """
        if not self._current_job:
            # We have no job, so do nothing on our turn.
            pass
        elif (len(self._path_to_current_job) > 0 \
            and not isinstance(self._current_job, MineJob)) \
           or (len(self._path_to_current_job) > 1 \
               and isinstance(self._current_job, MineJob)):
            # Step toward the job.
            xoff, yoff = \
              (self._path_to_current_job[0][0] - self.x,
               self._path_to_current_job[0][1] - self.y)
            assert -1 <= xoff <= 1
            assert -1 <= yoff <= 1

            if not tile_is_solid(
                     self._stage.get_tile_at(
                       self.x + xoff,
                       self.y + yoff)):
                self.x += xoff
                self.y += yoff
                self._path_to_current_job = \
                  self._path_to_current_job[1:]
            else:
                # bug - does not adapt if the path changes!  fix me!
                assert False, "the path was blocked for a penguin's job!"
        elif isinstance(self._current_job, MineJob):
            if self._work_left == 0:
                # Complete the mine job
                jx, jy = self._current_job.locations[0]
                self._stage.set_tile_at(jx, jy, 1)
                self._current_job.finish()
                self._current_job = None
                self._path_to_current_job = None
                self._look_for_job()
            else:
                # Work on the mine job
                self._work_left -= 1
        elif isinstance(self._current_job, HaulJob):
            # Complete the haul job
            self._held_entity = self._current_job.entity
            self._stage.delete_entity(self._held_entity)

            # Get a path to the stockpile.
            target = self._current_job.slot_location
            path = astar(self._stage, (self.x, self.y), target)

            if path:
                self._current_job = DropJob(self._current_job,
                                            self._held_entity)
                self._path_to_current_job = path
            else:
                assert False, "a penguin cannot reach stockpile " \
                              + "it planned to use! (fixme)"
        elif isinstance(self._current_job, DropJob):
            # Complete the drop job
            self._stage.add_entity(self._held_entity, self.x, self.y)
            self._held_entity = None
            self._current_job.haul_job.finish()
            self._current_job = None
            self._path_to_current_job = None
            self._look_for_job()

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
        timeslice = (timeslice + 1) % NUM_OF_TIMESLICES
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

                            access = 0
                            for penguin in penguins:
                                if penguin.partition[ty][tx]:
                                    access += 1
                            print('Accessibility: %d; ' % (access,))

                            for job in jobs:
                                if job.locations[0] != (tx, ty):
                                    continue

                                print('(J: ', end='')
                                if job.reserved:
                                    print('reserved', end='')
                                elif job.done:
                                    print('done', end='')
                                else:
                                    print('free', end='')
                                print(')', end='')

                            print()
                        elif selected_tool == 'mine':
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

                        for y in range(top, bottom + 1):
                            for x in range(left, right + 1):
                                # for each tile in the block, do the following:
                                tid = stage.get_tile_at(x, y)

                                if tid is None:
                                    pass
                                elif tid == 2:
                                    job_exists = False
                                    for job in jobs:
        
                                        if job.locations[0][0] == x \
                                           and job.locations[0][1] == y:
                                            job_exists = True
                                            break

                                    if not job_exists:
                                        jobs.append(MineJob((x, y)))
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
