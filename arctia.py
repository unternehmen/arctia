#!/usr/bin/env python
import pygame
import atexit
import sys
import os
import pytmx
import math

from config import *
from common import *
from job import Job, HaulJob, MineJob, DropJob
from stage import Stage
from stopwatch import Stopwatch
from jobsearch import JobSearch
from path import PathFinder


class Penguin(object):
    def __init__(self, stage, x, y, job_search, stopwatch):
        assert x >= 0 and x < stage.width
        assert y >= 0 and y < stage.height

        self.x = x
        self.y = y
        self._stage = stage
        self.timer = 10
        self.job_search = job_search
        self.work_left = 0
        self._held_entity = None
        self._stopwatch = stopwatch
        self._cookie = stopwatch.start()

        self._current_job = None
        self._path_to_current_job = None

    def draw(self, screen, tileset, camera_x, camera_y):
        screen.blit(tileset,
                    (self.x * 16 - camera_x + MENU_WIDTH,
                     self.y * 16 - camera_y),
                    (0, 0, 16, 16))

    def _look_for_job(self, ignore_timeslice=False):
        """
        Continue an in-progress job search.

        Arguments:
            ignore_timeslice: whether to search even if it is
                not the timeslice assigned to this penguin's JobSearch
        """
        if self.job_search.busy:
            job = self.job_search.run(limit=2,
                                      ignore_timeslice=ignore_timeslice)

            if job:
                # We found a job!
                self._current_job, \
                  self._path_to_current_job = job
                self._current_job.reserve()

    def _take_turn(self):
        """
        Make the Penguin take a turn.
        """
        if self._current_job is None:
            if not self.job_search.busy:
                self.job_search.start(self.x, self.y)
        elif isinstance(self._current_job, MineJob):
            if self.work_left > 0:
                self.work_left -= 1
                if self.work_left == 0:
                    # Turn the job's location's tile into floor.
                    # Note: this just assumes that it is a mining job
                    jx, jy = self._current_job.locations[0]
                    self._stage.set_tile_at(jx, jy, 1)

                    # Get rid of the job.
                    self._current_job.finish()
                    self._current_job = None
                    self._path_to_current_job = None

                    # Jumpstart our next search to keep other penguins
                    # from doing jobs that this penguin should do.
                    self.job_search.start(self.x, self.y)
                    self._look_for_job(ignore_timeslice=True)
            elif len(self._path_to_current_job) > 0:
                xoff, yoff = self._path_to_current_job[0]

                if not tile_is_solid(
                         self._stage.get_tile_at(
                           self.x + xoff,
                           self.y + yoff)):
                    self.x += xoff
                    self.y += yoff
                    self._path_to_current_job = \
                      self._path_to_current_job[1:]
                elif len(self._path_to_current_job) == 1:
                    # Start working on the assigned job.
                    self.work_left = 10
                else:
                    # bug - does not adapt if the path changes!  fix me!
                    assert False, "the path was blocked for a penguin's job!"
        elif isinstance(self._current_job, DropJob):
            if len(self._path_to_current_job) > 0:
                xoff, yoff = self._path_to_current_job[0]

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
                    assert False, "the path was blocked " \
                                  + "for a penguin's drop-job! (fixme)"
            else:
                # Drop the item and do something else.
                self._stage.add_entity(self._held_entity,
                                       self.x, self.y)
                self._current_job.haul_job.finish()
                self._current_job = None
                self._path_to_current_job = None
        elif isinstance(self._current_job, HaulJob):
            if len(self._path_to_current_job) > 0:
                xoff, yoff = self._path_to_current_job[0]

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
                    assert False, "the path was blocked " \
                                  + "for a penguin's haul-job! (fixme)"
            elif len(self._path_to_current_job) == 0:
                # Pick up the entity.
                self._held_entity = self._current_job.entity
                self._stage.delete_entity(self._held_entity)

                # Get a path to the stockpile.
                target = self._current_job.slot_location
                pf = PathFinder(self._stage)
                pf.start(self.x, self.y, lambda pos: pos == target)
                result = pf.run(-1)

                if result:
                    self._current_job = DropJob(self._current_job,
                                                self._held_entity)
                    self._path_to_current_job = result
                else:
                    assert False, "a penguin cannot reach stockpile " \
                                  + "it planned to use! (fixme)"


    def update(self):
        """
        Update the state of the Penguin.

        This should be called every frame before drawing.
        """
        self._look_for_job(ignore_timeslice=False)

        if self._stopwatch.measure(self._cookie) == 10:
            self._cookie = self._stopwatch.start()
            self._take_turn()


class Stockpile(object):
    def _detect_acceptable_item_at(self, x, y):
        tid = self._stage.get_tile_at(x, y)

        kind = ''
        if tid == 4:
            kind = 'fish'
        elif tid == 6:
            kind = 'rock'
        elif tid == 7:
            kind = 'bug'

        return kind in self.accepted_kinds

    def __init__(self, stage, rect, jobs, accepted_kinds):
        self.x, self.y, self.w, self.h = rect
        self.accepted_kinds = accepted_kinds
        self._stage = stage
        self._slots = [[self._detect_acceptable_item_at(x, y)
                        for x in range(self.x, self.x + self.w)]
                       for y in range(self.y, self.y + self.h)]

    @property
    def full(self):
        for y in range(self.h):
            for x in range(self.w):
                if not self._slots[y][x]:
                    return False
        return True

    def draw(self, screen, tileset, camera_x, camera_y):
        for y in range(self.y, self.y + self.h):
            for x in range(self.x, self.x + self.w):
                virtual_screen.blit(tileset,
                                    (x * 16 - camera_x \
                                     + MENU_WIDTH,
                                     y * 16 - camera_y),
                                    (176, 0, 16, 16))

    def reserve_slot(self):
        for y in range(self.h):
            for x in range(self.w):
                if not self._slots[y][x]:
                    self._slots[y][x] = True
                    return (x + self.x, y + self.y)
        assert False, "tried to reserve a slot " + \
                      "but none are available!"


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
    for x, y in penguin_offsets:
        penguins.append(Penguin(stage,
                                math.floor(player_start_x / 16) + x,
                                math.floor(player_start_y / 16) + y,
                                JobSearch(stage, jobs,
                                          timeslice, stopwatch,
                                          stockpiles),
                                stopwatch))
        timeslice = (timeslice + 1) % NUM_OF_TIMESLICES

    drag_origin = None

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
                        if selected_tool == 'mine':
                            tx = math.floor((camera_x + mx
                                             - MENU_WIDTH)
                                            / 16)
                            ty = math.floor((camera_y + my) / 16)
                            tid = stage.get_tile_at(tx, ty)

                            if tid is None:
                                pass
                            elif tid == 2:
                                job_exists = False
                                for job in jobs:

                                    if job.locations[0][0] == tx \
                                       and job.locations[0][1] == ty:
                                        job_exists = True
                                        break

                                if not job_exists:
                                    jobs.append(MineJob((tx, ty)))
                elif event.button == 3:
                    # Begin dragging the screen.
                    drag_origin = math.floor(event.pos[0] \
                                             / SCREEN_ZOOM), \
                                  math.floor(event.pos[1] \
                                             / SCREEN_ZOOM)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    pass
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

        # Update the game state.
        for penguin in penguins:
            penguin.update()

        # Delete finished mining jobs.
        for job in jobs:
            if job.done:
                jobs.remove(job)

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
        if mouse_x > MENU_WIDTH:
            wx = math.floor((camera_x + mouse_x - MENU_WIDTH) / 16)
            wy = math.floor((camera_y + mouse_y) / 16)
            virtual_screen.blit(tileset,
                                (wx * 16 - camera_x + MENU_WIDTH,
                                 wy * 16 - camera_y),
                                (128, 0, 16, 16))

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
