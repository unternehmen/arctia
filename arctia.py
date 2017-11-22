#!/usr/bin/env python
import atexit
import sys
import os
import math

import pygame

from transform import translate
from bfont import BitmapFont
from config import *
from common import *
from camera import Camera
from stage import Stage
from stockpile import Stockpile
from job import HaulJob, MineJob
from task import TaskGo, TaskMine, TaskTake, TaskDrop, TaskTrade, TaskGoToAnyMatchingSpot
from systems import UnitDispatchSystem, UnitDrawSystem, \
                    PartitionUpdateSystem

class Bug(object):
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.movement_delay = 0
        self.hunger = 0
        self.hunger_threshold = 50
        self.hunger_diet = {
            'fish': 100
        }
        self.wandering_delay = 1
        self.brooding_duration = 6
        self.task = None
        self.partition = None
        self.components = ['eating', 'wandering', 'brooding']
        self.clip = (112, 0, 16, 16)

class Gnoose(object):
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.movement_delay = 2
        self.hunger = 0
        self.hunger_threshold = 100
        self.hunger_diet = {
            'rock': 200
        }
        self.wandering_delay = 1
        self.brooding_duration = 12
        self.task = None
        self.partition = None
        self.components = ['eating', 'wandering', 'brooding']
        self.clip = (16, 16, 16, 16)

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

    def draw(self, screen, tileset, camera):
        """
        Draw the Penguin onto a screen or surface.

        Arguments:
            screen: the Pygame screen or surface
            tileset: the tileset to use
            camera: the camera to use
        """
        screen.blit(tileset,
                    camera.transform_game_to_screen(
                      (self.x, self.y), scalar=16),
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
                           and x < stock.x + stock.width \
                           and y >= stock.y \
                           and y < stock.y + stock.height:
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

                    def drop_and_finish():
                        task = TaskDrop(self._stage, self,
                                        blocked_proc=\
                                          dump_somewhere,
                                        finished_proc=\
                                          self._finish_job_entirely)
                        self._current_task = task

                    def spot_is_empty(spot):
                        no_entities = \
                          self._stage.entity_at(spot) is None
                        not_solid = \
                          not tile_is_solid( \
                                self._stage.get_tile_at( \
                                  spot[0], spot[1]))
                        not_in_stock = spot[0] < stock.x \
                                       or spot[0] >= stock.x + stock.width \
                                       or spot[1] < stock.y \
                                       or spot[1] >= stock.y + stock.height
                        return no_entities and not_solid and not_in_stock

                    def nowhere_to_dump_error():
                        assert False, 'penguin could not find anywhere to dump an object'

                    def dump_somewhere():
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
                                            blocked_proc=\
                                              None,
                                            finished_proc=\
                                              self._finish_job_entirely)
                        self._current_task = task

                    def go_to_stock_slot():
                        # Unreserve the object we picked up.
                        self._held_entity.relinquish()

                        # Only continue if the stockpile still exsits.
                        if not self._current_job.stockpile \
                               in self._stockpiles:
                            drop_and_finish()
                            return

                        # Check if we can reach the stockpile.
                        sx = self._current_job.stockpile.x
                        sy = self._current_job.stockpile.y
                        if not self.partition[sy][sx]:
                            drop_and_finish()
                            return
                        else:
                            task = TaskGo(self._stage, self,
                                          self._current_job.slot_location,
                                          blocked_proc=drop_and_finish,
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
    bfont = BitmapFont(
              'ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz',
              pygame.image.load(
                os.path.join('gfx', 'fawnt.png')))

    player_start_x, player_start_y = stage.get_player_start_pos()
    camera = Camera(player_start_x + 8
                      - math.floor(SCREEN_LOGICAL_WIDTH / 2.0),
                    player_start_y + 8
                      - math.floor(SCREEN_LOGICAL_HEIGHT / 2.0))
    jobs = []
    for entity in stage.entities:
        kind, x, y = entity
        if kind == 'fish':
            jobs.append(HaulJob(entity))

    # for now, stockpiles will be just for fish...
    stockpiles = []
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

    bugs = [Gnoose(50, 50),
            Bug(51, 50),
            Bug(52, 50),
            Bug(53, 50),
            Bug(54, 50)]

    mobs += bugs

    bug_dispatch_system = UnitDispatchSystem(stage)
    bug_draw_system = UnitDrawSystem()

    for bug in bugs:
        bug_dispatch_system.add(bug)
        bug_draw_system.add(bug)

    partition_system = PartitionUpdateSystem(stage, mobs)

    drag_origin = None
    block_origin = None

    tools = [
        {
            'ident': 'cursor',
            'label': 'Select'
        },
        {
            'ident': 'mine',
            'label': 'Mine'
        },
        {
            'ident': 'haul',
            'label': 'Not Implemented'
        },
        {
            'ident': 'stockpile',
            'label': 'Create Stockpile'
        },
        {
            'ident': 'delete-stockpile',
            'label': 'Delete Stockpile'
        }
    ]
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
                            selected_tool = tools[math.floor(my / 16)]['ident']
                    else:
                        # Use the selected tool.
                        if selected_tool == 'cursor':
                            target = camera.transform_screen_to_game(
                                       (mx, my), divisor=16)
                            print('***')
                            ent = stage.entity_at(target)
                            if ent:
                                print('  Entity:', ent.kind)
                                print('    location:', ent.location)
                                print('    reserved:', ent.reserved)
                            for penguin in penguins:
                                if (penguin.x, penguin.y) == target:
                                    print('  Penguin:')
                                    if penguin._current_job:
                                        print('    job:', penguin._current_job.__class__.__name__)
                                    else:
                                        print('    job: none')
                            for stock in stockpiles:
                                if stock.x <= target[0] < stock.x + stock.width \
                                   and stock.y <= target[1] < stock.y + stock.height:
                                    print('  Stock slot: ', end='')
                                    if stock._reservations[target[1] - stock.y][target[0] - stock.x]:
                                        print('reserved')
                                    else:
                                        print('free')
                                    break
                        elif selected_tool == 'mine' \
                             or selected_tool == 'stockpile':
                            target = camera.transform_screen_to_game(
                                       (mx, my), divisor=16)
                            block_origin = target
                        elif selected_tool == 'delete-stockpile':
                            # Delete the chosen stockpile
                            target = camera.transform_screen_to_game(
                                       (mx, my), divisor=16)
                            for stock in stockpiles:
                                if stock.x <= target[0] < stock.x + stock.width \
                                   and stock.y <= target[1] < stock.y + stock.height:
                                    stockpiles.remove(stock)
                                    break
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
                        target = camera.transform_screen_to_game(
                                   (mx, my), divisor=16)

                        left = min((target[0], ox))
                        right = max((target[0], ox))
                        top = min((target[1], oy))
                        bottom = max((target[1], oy))

                        if selected_tool == 'mine':
                            for y in range(top, bottom + 1):
                                for x in range(left, right + 1):
                                    if x < 0 or x >= stage.width or \
                                       y < 0 or y >= stage.height:
                                        continue

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
                                sw, sh = stock.width, stock.height
                                if not (sx > right \
                                        or sy > bottom \
                                        or sx + sw <= left \
                                        or sy + sh <= top):
                                    conflicts = True
                                    break

                            all_walkable = True
                            for y in range(top, bottom + 1):
                                for x in range(left, right + 1):
                                    if x < 0 or x >= stage.width or \
                                       y < 0 or y >= stage.height:
                                        all_walkable = False
                                        break

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
                                                   ['fish'])
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
            camera.x += (drag_origin[0] - mouse_x) \
                        * SCROLL_FACTOR
            camera.y += (drag_origin[1] - mouse_y) \
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
        stage.draw(virtual_screen, tileset, camera)

        for penguin in penguins:
            penguin.draw(virtual_screen, tileset, camera)

        # Draw stockpiles.
        for pile in stockpiles:
            pile.draw(virtual_screen, tileset, camera)

        # Draw bugs.
        bug_draw_system.update(virtual_screen, tileset, camera)

        # Hilight MineJob designated areas.
        for job in filter(lambda x: isinstance(x, MineJob), jobs):
            pos = job.locations[0]
            virtual_screen.blit(tileset,
                                camera.transform_game_to_screen(
                                  pos, scalar=16),
                                (160, 0, 16, 16))

        # Draw the selection box under the cursor if there is one.
        if not block_origin and mouse_x > MENU_WIDTH:
            selection = camera.transform_screen_to_game(
                          (mouse_x, mouse_y), divisor=16)
            virtual_screen.blit(tileset,
                                camera.transform_game_to_screen(
                                  selection, scalar=16),
                                (128, 0, 16, 16))

        # Draw the designation rectangle if we are drawing a region.
        if block_origin:
            ox, oy = block_origin
            target = camera.transform_screen_to_game((mouse_x, mouse_y), divisor=16)

            left = min((target[0], ox))
            right = max((target[0], ox))
            top = min((target[1], oy))
            bottom = max((target[1], oy))

            top_left_coords     = camera.transform_game_to_screen(
                                    (left, top), scalar=16),
            top_right_coords    = translate(
                                    camera.transform_game_to_screen(
                                      (right, top), scalar=16),
                                    (8, 0))
            bottom_left_coords  = translate(
                                    camera.transform_game_to_screen(
                                      (left, bottom), scalar=16),
                                    (0, 8))
            bottom_right_coords = translate(
                                    camera.transform_game_to_screen(
                                      (right, bottom), scalar=16),
                                    (8, 8))

            virtual_screen.blit(tileset, top_left_coords, (128, 0, 8, 8))
            virtual_screen.blit(tileset, bottom_left_coords, (128, 8, 8, 8))
            virtual_screen.blit(tileset, top_right_coords, (136, 0, 8, 8))
            virtual_screen.blit(tileset, bottom_right_coords, (136, 8, 8, 8))

        # Draw the menu bar.
        pygame.draw.rect(virtual_screen,
                         (0, 0, 0),
                         (0, 0, MENU_WIDTH, SCREEN_LOGICAL_HEIGHT))

        for i in range(len(tools)):
            if selected_tool == tools[i]['ident']:
                offset_y = 32
            else:
                offset_y = 16
            virtual_screen.blit(tileset, (0, i * 16),
                                (128 + i * 16, offset_y, 16, 16))

        # Draw the label of the currently hovered menu item.
        if mouse_x < MENU_WIDTH:
            if mouse_y < len(tools) * 16:
                tool_idx = math.floor(mouse_y / 16.0)
                bfont.write(virtual_screen,
                            tools[tool_idx]['label'],
                            (17, tool_idx * 16 + 2))

        # Scale and draw onto the real screen.
        pygame.transform.scale(virtual_screen,
                               SCREEN_REAL_DIMS,
                               scaled_screen)
        screen.blit(scaled_screen, (0, 0))
        pygame.display.flip();

        # Wait for the next frame.
        subturn = (subturn + 1) % 10
        clock.tick(40)
