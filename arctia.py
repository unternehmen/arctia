#!/usr/bin/env python
import pygame
import atexit
import sys
import os
import pytmx
import math


# Game constants
SCREEN_LOGICAL_WIDTH = 256
SCREEN_LOGICAL_HEIGHT = 240
SCREEN_LOGICAL_DIMS = SCREEN_LOGICAL_WIDTH, SCREEN_LOGICAL_HEIGHT
SCREEN_ZOOM = 2
SCREEN_REAL_DIMS = tuple([x * SCREEN_ZOOM for x in SCREEN_LOGICAL_DIMS])
MENU_WIDTH = 16
SCROLL_FACTOR = 2


class Stage(object):
    def __init__(self):
        tiled_map = \
            pytmx.TiledMap(os.path.join('maps', 'tuxville.tmx'))
        self.width = tiled_map.width
        self.height = tiled_map.height
        self.data = [[x for x in range(self.width)]
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
        for y in range(self.height):
            for x in range(self.width):
                tid = self.data[y][x]
                tx = tid % 16
                ty = math.floor(tid / 16)
                screen.blit(tileset,
                            (x * 16 - camera_x + MENU_WIDTH,
                             y * 16 - camera_y + MENU_WIDTH),
                            (tx * 16, ty * 16, 16, 16))

    def get_player_start_pos(self):
        return self.player_start_x, self.player_start_y

    def get_tile_at(self, x, y):
        return self.data[y][x]


class Penguin(object):
    def __init__(self, stage, x, y):
        assert x >= 0 and x < stage.width
        assert y >= 0 and y < stage.height

        self.x = x
        self.y = y
        self.stage = stage
        self.timer = 10

    def draw(self, screen, tileset, camera_x, camera_y):
        screen.blit(tileset,
                    (self.x * 16 - camera_x + MENU_WIDTH,
                     self.y * 16 - camera_y + MENU_WIDTH),
                    (0, 0, 16, 16))

    def _take_turn(self):
        target = self.stage.get_tile_at(self.x - 1, self.y - 1)

        if target != 2:
            self.x -= 1
            self.y -= 1

    def update(self):
        self.timer = (self.timer - 1) % 10

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
    penguin = Penguin(stage,
                      math.floor(player_start_x / 16),
                      math.floor(player_start_y / 16))

    drag_origin = None

    # 'cursor' | 'mine' | 'haul'
    tools = ['cursor', 'mine', 'haul']
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
                        if my < len(tools) * 16:
                            selected_tool = tools[math.floor(my / 16)]
                elif event.button == 3:
                    # Begin dragging the screen.
                    drag_origin = event.pos[0], event.pos[1]
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    pass
                elif event.button == 3:
                    # Stop dragging the screen.
                    drag_origin = None

        # Handle dragging the map.
        if drag_origin is not None:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            camera_x += ((drag_origin[0] - mouse_x) / SCREEN_ZOOM) \
                        * SCROLL_FACTOR
            camera_y += ((drag_origin[1] - mouse_y) / SCREEN_ZOOM) \
                        * SCROLL_FACTOR
            drag_origin = mouse_x, mouse_y

        # Update the game state.
        penguin.update()

        # Clear the screen.
        virtual_screen.fill((0, 0, 0))

        # Draw the world.
        stage.draw(virtual_screen, tileset, camera_x, camera_y)
        penguin.draw(virtual_screen, tileset, camera_x, camera_y)

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
                                (i * 16, offset_y, 16, 16))

        # Scale and draw onto the real screen.
        pygame.transform.scale(virtual_screen,
                               SCREEN_REAL_DIMS,
                               scaled_screen)
        screen.blit(scaled_screen, (0, 0))
        pygame.display.flip();

        # Wait for the next frame.
        clock.tick(40)
