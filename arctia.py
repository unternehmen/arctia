#!/usr/bin/env python
import pygame
import atexit
import sys
import os


# Game constants
SCREEN_LOGICAL_WIDTH = 256
SCREEN_LOGICAL_HEIGHT = 240
SCREEN_LOGICAL_DIMS = SCREEN_LOGICAL_WIDTH, SCREEN_LOGICAL_HEIGHT
SCREEN_ZOOM = 2
SCREEN_REAL_DIMS = tuple([x * SCREEN_ZOOM for x in SCREEN_LOGICAL_DIMS])


if __name__ == '__main__':
    pygame.init()
    atexit.register(pygame.quit)
    screen = pygame.display.set_mode(SCREEN_REAL_DIMS)
    virtual_screen = pygame.Surface(SCREEN_LOGICAL_DIMS)
    scaled_screen = pygame.Surface(SCREEN_REAL_DIMS)

    pygame.mixer.music.load(os.path.join('music', 'nescape.ogg'))
    pygame.mixer.music.play(loops=-1)

    clock = pygame.time.Clock()
    while True:
        # Handle user input.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        # Draw everything.
        virtual_screen.fill((255, 255, 255))

        # Scale and draw onto the real screen.
        pygame.transform.scale(virtual_screen,
                               SCREEN_REAL_DIMS,
                               scaled_screen)
        screen.blit(scaled_screen, (0, 0))
        pygame.display.flip();

        # Wait for the next frame.
        clock.tick(25)
