"""
The camera module provides a Camera class for transforming coordinates.

Such transformations are necessary in order to blit game objects
correctly and determine what tile the player has selected.
"""
import math
from config import MENU_WIDTH

class Camera(object):
    """
    A Camera facilitates transforming coordinates from screen
    coordinates to game world coordinates and vise versa.

    Arguments:
        x: the x coordinate of the camera's view
        y: the y coordinate of the camera's view
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def transform_screen_to_game(self, point, divisor=1):
        """
        Transform screen coordinates into game world coordinates.

        This is useful for, e.g., determining which tile the player
        has clicked.

        When determining a tile coordinate based on a screen coordinate,
        the divisor should be the width or height of a square tile.

        The resulting coordinates are always rounded down.

        Arguments:
            point: a pair of screen coordinates
            divisor: a number to divide each resulting coordinate by

        Returns: a pair of game coordinates
        """
        point_x, point_y = point
        return (math.floor((self.x + point_x - MENU_WIDTH) / divisor),
                math.floor((self.y + point_y) / divisor))

    def transform_game_to_screen(self, point, scalar):
        """
        Transform game world coordinates into screen coordinates.

        This is useful for, e.g., blitting a tile onto the proper
        position on the screen.

        When converting from a tile coordinate to a screen coordinate,
        the scalar should be the width or height of a square tile.

        Arguments:
            point: a pair of screen coordinates
            scalar: a number to multiply each original coordinate by

        Returns: a pair of screen coordinates
        """
        return (point[0] * scalar - self.x + MENU_WIDTH,
                point[1] * scalar - self.y)
