#!/usr/bin/env python
import atexit
import sys
import os
import math
from functools import partial

import pygame

from transform import translate
from bfont import BitmapFont
from config import *
from common import *
from camera import Camera
from stage import Stage
from stockpile import Stockpile
from task import TaskGo, TaskMine, TaskTake, TaskDrop, TaskTrade, TaskGoToAnyMatchingSpot
from systems import UnitDispatchSystem, UnitDrawSystem, \
                    PartitionUpdateSystem
from team import Team

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
    def __init__(self, team, ident, stage, x, y, stockpiles):
        """
        Create a new Penguin.

        Arguments:
            team: the team this Penguin is on
            ident: an identification number
            stage: the Stage the penguin exists in
            x: the x coordinate of the penguin
            y: the y coordinate of the penguin
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

        # The penguin's team
        self.team = team

        # The partition of the stage that this penguin can reach
        self.partition = None

        ## Gameplay stats
        # The penguin's hunger (0 = full, >40 = hungry, >80 = starving)
        self._hunger = 0

        # The penguin's current task
        self.task = None

        ## External data
        self._stage = stage
        self._stockpiles = stockpiles

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
        assert not self.task, \
               'Penguin %s looked for a job but it already has a task!' % \
                 self.ident

        if self._hunger >= HUNGER_THRESHOLD:
            # Look for food!
            pass

        # Find a mining job first.
        for designation in filter(lambda d: d['kind'] == 'mine',
                                  self.team.designations):
            loc = designation['location']

            # If we can't reach the mining job, skip it.
            if not self.partition[loc[1]][loc[0]]:
                continue

            # If the mining job is reserved or already done, skip it.
            if self.team.is_reserved('mine', designation) \
               or designation['done']:
                continue

            # Take the job.
            def _complete_mining(designation):
                designation['done'] = True
                self.task = None
                self._look_for_job()

            def _forget_job(designation):
                self.team.relinquish('mine', designation)
                self.task = None
                self._look_for_job()

            def _start_mining(designation):
                task = TaskMine(self._stage, self, loc,
                                finished_proc = \
                                  partial(_complete_mining,
                                          designation))
                self.task = task

            task = TaskGo(self._stage, self, loc,
                          blocked_proc=\
                            partial(_forget_job, designation),
                          finished_proc=\
                            partial(_start_mining, designation))
            self.task = task
            self.team.reserve('mine', designation)

            # We have a job now, so stop searching.
            return

        # Otherwise, find a hauling job.
        for stock in self._stockpiles:
            # If we cannot reach the stockpile, skip it.
            if not self.partition[stock.y][stock.x]:
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

                    if self.team.is_reserved('location', loc):
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
                  and e.kind in accepted_kinds \
                  and not self.team.is_reserved('entity', e) \
                  and not _entity_is_stockpiled(e, x, y))

            # If there is no such entity, skip this stockpile.
            if not result:
                break

            # Otherwise, take the hauling job.
            entity, loc = result
            x, y = loc

            def _start_haul_job(stock, entity, chosen_slot):
                self.team.reserve('location', chosen_slot)
                self.team.reserve('entity', entity)
                self.task = \
                    TaskGo(self._stage, self,
                           target=entity.location,
                           delay=0,
                           blocked_proc=\
                             partial(_abort_entity_inaccessible,
                                     stock, entity, chosen_slot),
                           finished_proc=
                             partial(_pick_up_entity,
                                     stock, entity, chosen_slot))


            def _pick_up_entity(stock, entity, chosen_slot):
                self.task = \
                    TaskTake(self._stage, self, entity,
                             not_found_proc=\
                               partial(_abort_entity_inaccessible,
                                       stock, entity, chosen_slot),
                             finished_proc=\
                               partial(_haul_entity_to_slot,
                                       stock, entity, chosen_slot))

            def _abort_entity_inaccessible(_unused_stock,
                                          entity, chosen_slot):
                self.team.relinquish('location', chosen_slot)
                self.team.relinquish('entity', entity)
                self.task = None

            def _haul_entity_to_slot(stock, entity, chosen_slot):
                self.team.relinquish('entity', entity)
                self.task = \
                    TaskGo(self._stage, self,
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
                if self.team.is_reserved('location', chosen_slot):
                    self.team.relinquish('location', chosen_slot)
                self.task = \
                  TaskGoToAnyMatchingSpot(
                    self._stage, self,
                    condition_func=_location_is_empty,
                    impossible_proc=\
                      partial(_die_no_dump_location,
                              stock, entity, chosen_slot),
                    finished_proc=\
                      partial(_try_to_dump,
                              stock, entity, chosen_slot))

            def _try_to_dump(stock, entity, chosen_slot):
                self.task = \
                  TaskDrop(
                    self._stage, entity, self,
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
                    self.task = \
                      TaskTrade(
                        self._stage, entity, self, occupier,
                        finished_proc=\
                          partial(_abort_dump_wherever,
                                  stock, occupier, chosen_slot))
                else:
                    self.task = \
                      TaskDrop(
                        self._stage, entity, self,
                        blocked_proc=\
                          partial(_put_entity_into_slot,
                                  stock, entity, chosen_slot),
                        finished_proc=\
                          partial(_abort_and_relinquish_slot,
                                  stock, entity, chosen_slot))

            def _abort_no_cleanup_needed():
                self.task = None

            def _abort_and_relinquish_slot(stock, entity, chosen_slot):
                self.team.relinquish('location', chosen_slot)
                self.task = None

            _start_haul_job(stock, entity, chosen_slot)

            # We have a job now, so stop searching.
            return

    def update(self):
        """
        Update the state of the Penguin.

        This should only be called once every turn.
        """
        # Find a job if we don't have one.
        if self.task is None:
            self._look_for_job()

        # Get hungrier.
        self._hunger += 1

        # If we have a task, do it.
        if self.task:
            self.task.enact()


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

    # for now, stockpiles will be just for fish...
    stockpiles = []
    penguin_offsets = [(0, 0), (1, -1), (-1, 1), (-1, -1), (1, 1)]
    mobs = []
    penguins = []
    timeslice = 0
    ident = 0

    player_team = Team()

    for x, y in penguin_offsets:
        penguins.append(Penguin(player_team, ident, stage,
                                math.floor(player_start_x / 16) + x,
                                math.floor(player_start_y / 16) + y,
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
                            print('  Location:')
                            if player_team.is_reserved('location', target):
                                print('    reserved: yes')
                            else:
                                print('    reserved: no')
                            ent = stage.entity_at(target)
                            if ent:
                                print('  Entity:', ent.kind)
                                print('    location:', ent.location)
                                #print('    reserved:', ent.reserved)
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
                                        designations = \
                                          player_team.designations

                                        already_exists = False
                                        for designation in designations:
                                            loc = designation['location']
                                            if loc == (x, y):
                                                already_exists = True
                                                break

                                        if not already_exists:
                                            designations.append({
                                                'kind': 'mine',
                                                'location': (x, y),
                                                'done': False
                                            })
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

        # Delete finished designations.
        for designation in player_team.designations:
            if designation['done']:
                player_team.designations.remove(designation)

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

        # Hilight designations.
        for designation in player_team.designations:
            loc = designation['location']
            virtual_screen.blit(tileset,
                                camera.transform_game_to_screen(
                                  loc, scalar=16),
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
