#!/usr/bin/env python
import pygame
import atexit
import sys
import os
import pytmx
import math

from config import *
from common import *
from job import Job
from stage import Stage
from stopwatch import Stopwatch
from jobsearch import JobSearch


class Penguin(object):
    def __init__(self, stage, x, y, job_search, stopwatch):
        assert x >= 0 and x < stage.width
        assert y >= 0 and y < stage.height

        self.x = x
        self.y = y
        self.stage = stage
        self.timer = 10
        self.job_search = job_search
        self.work_left = 0
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
        if self.work_left > 0:
            self.work_left -= 1
            if self.work_left == 0:
                # Turn the job's location's tile into floor.
                # Note: this just assumes that it is a mining job
                jx, jy = self._current_job.location
                self.stage.set_tile_at(jx, jy, 1)

                # Get rid of the job.
                self._current_job.finish()
                self._current_job = None
                self._path_to_current_job = None

                # Jumpstart our next search to keep other penguins
                # from doing jobs that this penguin should do.
                self.job_search.start(self.x, self.y)
                self._look_for_job(ignore_timeslice=True)
        elif self._current_job and len(self._path_to_current_job) > 0:
            xoff, yoff = self._path_to_current_job[0]

            if not tile_is_solid(
                     self.stage.get_tile_at(
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
        else:
            if not self.job_search.busy:
                self.job_search.start(self.x, self.y)

    def update(self):
        """
        Update the state of the Penguin.

        This should be called every frame before drawing.
        """
        self._look_for_job(ignore_timeslice=False)

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
    stage = Stage()

    player_start_x, player_start_y = stage.get_player_start_pos()
    camera_x = player_start_x + 8 \
               - math.floor(SCREEN_LOGICAL_WIDTH / 2.0)
    camera_y = player_start_y + 8 \
               - math.floor(SCREEN_LOGICAL_HEIGHT / 2.0)
    mine_jobs = []
    stopwatch = Stopwatch()

    penguin_offsets = [(0, 0), (1, -1), (-1, 1), (-1, -1), (1, 1)]
    penguins = []
    timeslice = 0
    for x, y in penguin_offsets:
        penguins.append(Penguin(stage,
                                math.floor(player_start_x / 16) + x,
                                math.floor(player_start_y / 16) + y,
                                JobSearch(stage, mine_jobs,
                                          timeslice, stopwatch),
                                stopwatch))
        timeslice = (timeslice + 1) % NUM_OF_TIMESLICES

    drag_origin = None

    tools = ['cursor', 'mine', 'haul', 'stockpile']
    selected_tool = 'cursor'

    stockpile = (penguins[0].x, penguins[0].y - 8, 4, 4)
    def draw_stockpile(stockpile, screen, tileset, camera_x, camera_y):
        for y in range(stockpile[1], stockpile[1] + stockpile[3]):
            for x in range(stockpile[0], stockpile[0] + stockpile[2]):
                virtual_screen.blit(tileset,
                                    (x * 16 - camera_x \
                                     + MENU_WIDTH,
                                     y * 16 - camera_y),
                                    (176, 0, 16, 16))

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
                                for job in mine_jobs:

                                    if job.location[0] == tx \
                                       and job.location[1] == ty:
                                        print('Job already exists')
                                        job_exists = True
                                        break

                                if not job_exists:
                                    mine_jobs.append(Job((tx, ty)))
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
        for job in mine_jobs:
            if job.done:
                mine_jobs.remove(job)

        # Clear the screen.
        virtual_screen.fill((0, 0, 0))

        # Draw the world.
        stage.draw(virtual_screen, tileset, camera_x, camera_y)

        for penguin in penguins:
            penguin.draw(virtual_screen, tileset, camera_x, camera_y)

        # Draw stockpiles.
        draw_stockpile(stockpile, virtual_screen, tileset, camera_x, camera_y)

        # Hilight job-designated areas.
        for job in mine_jobs:
            pos = job.location
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
