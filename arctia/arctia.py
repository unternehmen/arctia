#!/usr/bin/env python
import atexit
import sys
import os
import math
from functools import partial

import pygame

from .transform import translate
from .bfont import BitmapFont
from .config import *
from .common import *
from .camera import Camera
from .stage import Stage
from .stockpile import Stockpile
from .systems import UnitDispatchSystem, UnitDrawSystem, \
                    PartitionUpdateSystem
from .team import Team
from .resources import load_music, load_image

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
        self.team = None
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
            'rock': 300
        }
        self.team = None
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
    def __init__(self, stage, team, x, y):
        """
        Create a new Penguin.

        Arguments:
            team: the team this Penguin is on
            x: the x coordinate of the penguin
            y: the y coordinate of the penguin

        Returns: a new Penguin
        """
        assert x >= 0 and x < stage.width
        assert y >= 0 and y < stage.height

        ## Main data

        # The penguin's location
        self.x = x
        self.y = y

        # The penguin's team
        self.team = team

        # The penguin's sprite clip
        self.clip = (0, 0, 16, 16)

        # The partition of the stage that this penguin can reach
        self.partition = None

        # The penguin's current task
        self.task = None

        ## Gameplay stats
        self.movement_delay = 0
        self.hunger = 0
        self.hunger_threshold = 100
        self.hunger_diet = { 'fish': 200 }
        self.wandering_delay = 1
        self.brooding_duration = 12
        self.components = ['eating', 'wandering', 'brooding',
                           'mining', 'hauling']

def main():
    pygame.init()
    atexit.register(pygame.quit)
    screen = pygame.display.set_mode(SCREEN_REAL_DIMS)
    virtual_screen = pygame.Surface(SCREEN_LOGICAL_DIMS)
    scaled_screen = pygame.Surface(SCREEN_REAL_DIMS)

    load_music('music/nescape.ogg')
    tileset = load_image('gfx/tileset.png')
    stage = Stage('maps/tuxville.tmx')
    bfont = BitmapFont(
              'ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz',
              load_image('gfx/fawnt.png'))

    player_start_x, player_start_y = stage.get_player_start_pos()
    camera = Camera(player_start_x + 8
                      - math.floor(SCREEN_LOGICAL_WIDTH / 2.0),
                    player_start_y + 8
                      - math.floor(SCREEN_LOGICAL_HEIGHT / 2.0))

    # Set up the starting mobs.
    penguin_offsets = [(0, 0), (1, -1), (-1, 1), (-1, -1), (1, 1)]
    mobs = []

    player_team = Team()

    for dx, dy in penguin_offsets:
        mobs.append(Penguin(stage, player_team,
                            math.floor(player_start_x / 16) + dx,
                            math.floor(player_start_y / 16) + dy))

    mobs += [Gnoose(50, 50),
             Bug(51, 50),
             Bug(52, 50),
             Bug(53, 50),
             Bug(54, 50)]

    # Set up game systems
    unit_dispatch_system = UnitDispatchSystem(stage)
    unit_draw_system = UnitDrawSystem()

    for unit in mobs:
        unit_dispatch_system.add(unit)
        unit_draw_system.add(unit)

    partition_system = PartitionUpdateSystem(stage, mobs)

    # UI elements
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
                                if player_team.is_reserved('entity', ent):
                                    print('    reserved: yes')
                                else:
                                    print('    reserved: no')
                        elif selected_tool == 'mine' \
                             or selected_tool == 'stockpile':
                            target = camera.transform_screen_to_game(
                                       (mx, my), divisor=16)
                            block_origin = target
                        elif selected_tool == 'delete-stockpile':
                            # Delete the chosen stockpile
                            target = camera.transform_screen_to_game(
                                       (mx, my), divisor=16)
                            for stock in player_team.stockpiles:
                                if stock.x <= target[0] < stock.x + stock.width \
                                   and stock.y <= target[1] < stock.y + stock.height:
                                    player_team.stockpiles.remove(stock)
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
                            for stock in player_team.stockpiles:
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
                                player_team.stockpiles.append(stock)

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
            unit_dispatch_system.update()

        # Clear the screen.
        virtual_screen.fill((0, 0, 0))

        # Draw the world.
        stage.draw(virtual_screen, tileset, camera)

        # Draw stockpiles.
        for pile in player_team.stockpiles:
            pile.draw(virtual_screen, tileset, camera)

        # Draw all units.
        unit_draw_system.update(virtual_screen, tileset, camera)

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
