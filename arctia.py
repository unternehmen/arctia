#!/usr/bin/env python
import pygame
import atexit
import sys
import os
import pytmx
import math

from job import Job

# Game constants
SCREEN_LOGICAL_WIDTH = 256
SCREEN_LOGICAL_HEIGHT = 240
SCREEN_LOGICAL_DIMS = SCREEN_LOGICAL_WIDTH, SCREEN_LOGICAL_HEIGHT
SCREEN_ZOOM = 2
SCREEN_REAL_DIMS = tuple([x * SCREEN_ZOOM for x in SCREEN_LOGICAL_DIMS])
MENU_WIDTH = 16
SCROLL_FACTOR = 2

def tile_is_solid(tid):
    return tid in (2, 3, 5)

class Stage(object):
    def __init__(self):
        tiled_map = \
            pytmx.TiledMap(os.path.join('maps', 'tuxville.tmx'))
        self.width = tiled_map.width
        self.height = tiled_map.height
        self.data = [[0 for x in range(self.width)]
                     for y in range(self.height)]
        player_start_obj = \
            tiled_map.get_object_by_name('Player Start')
        self.player_start_x = player_start_obj.x
        self.player_start_y = player_start_obj.y

        for layer_ref in tiled_map.visible_tile_layers:
            layer = tiled_map.layers[layer_ref]
            for x, y, img in layer.tiles():
                tx = math.floor(img[1][0] / 16)
                ty = math.floor(img[1][1] / 16)
                self.data[y][x] = ty * 16 + tx

    def draw(self, screen, tileset, camera_x, camera_y):
        clip_left = math.floor(camera_x / 16)
        clip_top = math.floor(camera_y / 16)
        clip_width = math.floor(SCREEN_LOGICAL_WIDTH / 16)
        clip_height = math.floor(SCREEN_LOGICAL_HEIGHT / 16 + 1)
        for y in range(clip_top, clip_top + clip_height):
            for x in range(clip_left, clip_left + clip_width):
                if x < 0 or x >= self.width \
                   or y < 0 or y >= self.height:
                    continue
                tid = self.data[y][x]
                tx = tid % 16
                ty = math.floor(tid / 16)
                screen.blit(tileset,
                            (x * 16 - camera_x + MENU_WIDTH,
                             y * 16 - camera_y),
                            (tx * 16, ty * 16, 16, 16))

    def get_player_start_pos(self):
        return self.player_start_x, self.player_start_y

    def get_tile_at(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return None
        return self.data[y][x]

    def set_tile_at(self, x, y, tid):
        assert x >= 0
        assert x < self.width
        assert y >= 0
        assert y < self.height

        self.data[y][x] = tid

class JobSearch(object):
    """
    A JobSearch searches the map for untaken jobs that Penguins can do.

    This class exists because the seeking algorithm uses two big arrays
    which should not be reallocated every time the seek runs.
    """
    LEFT      = 0
    UPLEFT    = 1
    UPRIGHT   = 2
    RIGHT     = 3
    UP        = 4
    DOWN      = 5
    DOWNLEFT  = 6
    DOWNRIGHT = 7

    def __init__(self, stage, mine_jobs):
        """Create a new JobSearch."""
        self.busy = False
        self._stage = stage
        self._mine_jobs = mine_jobs

        self._paths = [[None for x in range(self._stage.width)]
                       for y in range(self._stage.height)]
        self._visited = [[False for x in range(self._stage.width)]
                         for y in range(self._stage.height)]
        self._staleness = [[False for x in range(self._stage.width)]
                           for y in range(self._stage.height)]
        self._offsets = [(-1, -1), (-1, 0), (-1, 1),
                         ( 0, -1),          ( 0, 1),
                         ( 1, -1), ( 1, 0), ( 1, 1)]
        self._directions = [JobSearch.UPLEFT,
                            JobSearch.LEFT,
                            JobSearch.DOWNLEFT,
                            JobSearch.UP,
                            JobSearch.DOWN,
                            JobSearch.UPRIGHT,
                            JobSearch.RIGHT,
                            JobSearch.DOWNRIGHT]

    def start(self, from_x, from_y):
        """
        Begin searching for jobs starting from the given position.

        Arguments:
            from_x: the initial x coordinate
            from_y: the initial y coordinate

        Returns:
            the found job as (x, y) or None if no job was found
        """
        self._shortest_path = []
        self._start_x = from_x
        self._start_y = from_y

        # Clear the state arrays.
        for y in range(len(self._visited)):
            for x in range(len(self._visited[0])):
                self._visited[y][x] = False
                self._staleness[y][x] = False
                self._paths[y][x] = None

        # Mark the starting point as visited.
        self._visited[from_y][from_x] = True

        # State that the job searcher is busy.
        self.busy = True

    def notify(self, xoff, yoff):
        """
        Notify the job search that the originating mob has moved.

        Job searches are always started from some mob's location.
        Because job searches are run incrementally over many frames,
        the object which started the job search might move in mid-search.

        In order for the job search to give a correct shortest path
        to the found job, it needs to know where the originating mob
        is at all times.  To that end, this procedure should be run
        whenever the mob responsible for the job search moves.

        For example, if a penguin moves (1, 1) from its previous
        position, it should also run notify(1, 1) on its job_search.

        Arguments:
            xoff: the offset from the original starting x coordinate
            yoff: the offset from the original starting y coordinate
        """
        if not self.busy:
            return

        self._shortest_path.insert(0, (xoff, yoff))

    def _traceback(self, job):
        """
        Return the already-calculated shortest path to the found Job.

        Arguments:
            job:
                The Job we found.

        Returns:
            A list of 2-tuples representing steps along the path to
            the Job.  For example, [(1, 1), (1, 0), ...]
        """
        path_suffix = []
        cx, cy = job.location
        direction = self._paths[cy][cx]

        while direction is not None:
            for i, sel_direction in enumerate(self._directions):
                if sel_direction == direction:
                    xoff, yoff = self._offsets[i]

            path_suffix.insert(0, (xoff, yoff))
            cx -= xoff
            cy -= yoff
            direction = self._paths[cy][cx]

        return self._shortest_path + path_suffix

    def run(self, limit=10):
        """
        Continue a previously started job search.

        Arguments:
            limit: the number of breadth descensions to try

        Returns:
            the found job as (x, y) or None if no job was found
        """
        exhausted_tiles = False

        while not exhausted_tiles and limit > 0:
            exhausted_tiles = True

            for y in range(self._stage.height):
                for x in range(self._stage.width):
                    if self._visited[y][x] \
                       and not self._staleness[y][x] \
                       and not tile_is_solid(
                                 self._stage.get_tile_at(x, y)):
                        # This is a non-solid tile, so
                        # check all paths leading out from it.
                        i = 0
                        for xoff, yoff in self._offsets:
                            ox = x + xoff
                            oy = y + yoff
                            if ox < 0 or ox >= self._stage.width \
                               or oy < 0 or oy >= self._stage.height:
                                pass
                            elif not self._visited[oy][ox]:
                                self._visited[oy][ox] = True
                                self._paths[oy][ox] = \
                                    self._directions[i]
                                exhausted_tiles = False
                                # Check if there is a job there.
                                for job in self._mine_jobs:
                                    if not job.reserved \
                                       and not job.done \
                                       and job.location[0] == ox \
                                       and job.location[1] == oy:
                                        self.busy = False
                                        job.reserve()
                                        return (job,
                                                self._traceback(job))
                            i += 1
                        self._staleness[y][x] = True
            limit -= 1

        if exhausted_tiles:
            self.busy = False

        # No job was found.
        return None

class Penguin(object):
    def __init__(self, stage, x, y, job_search):
        assert x >= 0 and x < stage.width
        assert y >= 0 and y < stage.height

        self.x = x
        self.y = y
        self.stage = stage
        self.timer = 10
        self.job_search = job_search
        self.work_left = 0

        self._current_job = None
        self._path_to_current_job = None

    def draw(self, screen, tileset, camera_x, camera_y):
        screen.blit(tileset,
                    (self.x * 16 - camera_x + MENU_WIDTH,
                     self.y * 16 - camera_y),
                    (0, 0, 16, 16))

    def _look_for_job(self):
        """
        Continue an in-progress job search.
        """
        if self.job_search.busy:
            job = self.job_search.run(limit=2)

            if job:
                # We found a job!
                self._current_job, \
                  self._path_to_current_job = job

    def _take_turn(self):
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

                self.job_search.start(self.x, self.y)
                self._look_for_job()
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
        self.timer = (self.timer - 1) % 10
        self._look_for_job()

        if self.timer == 0:
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

    penguins = [Penguin(stage,
                        math.floor(player_start_x / 16),
                        math.floor(player_start_y / 16),
                        JobSearch(stage, mine_jobs)),
                Penguin(stage,
                        math.floor(player_start_x / 16) + 1,
                        math.floor(player_start_y / 16) - 1,
                        JobSearch(stage, mine_jobs))]

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
        clock.tick(40)
