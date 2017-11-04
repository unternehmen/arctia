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


class Stage:
    def __init__(self):
        self.tiled_map = \
            pytmx.TiledMap(os.path.join('maps', 'tuxville.tmx'))

    def draw(self, screen, tileset, camera_x, camera_y):
        for layer_ref in self.tiled_map.visible_tile_layers:
            layer = self.tiled_map.layers[layer_ref]
            for x, y, img in layer.tiles():
                virtual_screen.blit(tileset,
                                    (x * 16 - camera_x + MENU_WIDTH,
                                     y * 16 - camera_y + MENU_WIDTH),
                                    img[1])

    def get_player_start_pos(self):
        player_start_obj = \
            self.tiled_map.get_object_by_name('Player Start')
        return player_start_obj.x, player_start_obj.y


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

    pygame.mixer.music.play(loops=-1)
    clock = pygame.time.Clock()
    while True:
        # Handle user input.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        # Draw everything.
        virtual_screen.fill((255, 255, 255))
        stage.draw(virtual_screen, tileset, camera_x, camera_y)

        # Scale and draw onto the real screen.
        pygame.transform.scale(virtual_screen,
                               SCREEN_REAL_DIMS,
                               scaled_screen)
        screen.blit(scaled_screen, (0, 0))
        pygame.display.flip();

        # Wait for the next frame.
        clock.tick(25)
