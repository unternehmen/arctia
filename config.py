"""
Configurable constants

You can tune these constants to alter the game experience.
"""

"""
The screen width (in scaled pixels).
"""
SCREEN_LOGICAL_WIDTH = 256


"""
The screen height (in scaled pixels).
"""
SCREEN_LOGICAL_HEIGHT = 240


"""
How many times to scale the screen.

Since the sprites are small, you may want to scale up the game
screen with this constant.  By default, the screen is scaled by 2,
which means pixels are drawn at double their size.
"""
SCREEN_ZOOM = 2


"""
The width (in pixels) of the menu on the left side of the screen.
"""
MENU_WIDTH = 16


"""
How fast the stage scrolls when the player drags it.

By default, the stage scrolls at double speed.
"""
SCROLL_FACTOR = 2


"""
The number of job search timeslices there are.

This controls how many job searches are processed per frame,
since each job search only runs during a certain timeslice (e.g., 1).

If there are less timeslices, the game will run slower but mobs will
be able to find jobs quicker (in game-time).

On the other hand, If there are more slices, the game will run
faster but mobs will take more time to find jobs.
"""
NUM_OF_TIMESLICES = 4

"""
Non-configurable constants

These constants do not need to be configured because they follow
directly from the variables above.
"""

"""
The logical (in scaled pixels) screen dimensions.
"""
SCREEN_LOGICAL_DIMS = SCREEN_LOGICAL_WIDTH, SCREEN_LOGICAL_HEIGHT

"""
The real (in actual pixels) screen dimensions.
"""
SCREEN_REAL_DIMS = tuple([x * SCREEN_ZOOM for x in SCREEN_LOGICAL_DIMS])

