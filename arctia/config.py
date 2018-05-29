"""
The config module provides tweakable constants for adjusting the game.
"""

# Configurable constants
#
# You can tune the following to alter the game experience.


# The screen width (in scaled pixels).
SCREEN_LOGICAL_WIDTH = 256


# The screen height (in scaled pixels).
SCREEN_LOGICAL_HEIGHT = 240


# How many times to scale the screen.
#
# Since the sprites are small, you may want to scale up the game
# screen with this constant.  By default, the screen is scaled by 2,
# which means pixels are drawn at double their size.
SCREEN_ZOOM = 2


# The width (in pixels) of the menu on the left side of the screen.
MENU_WIDTH = 16


# How fast the stage scrolls when the player drags it.
#
# By default, the stage scrolls at double speed.
SCROLL_FACTOR = 2


# How much time (in turns) until a full penguin becomes hungry.
HUNGER_THRESHOLD = 40


# How much time (in turns) until a full penguin begins starving.
STARVING_THRESHOLD = 80


# Non-configurable constants
#
# These constants do not need to be configured because they follow
# directly from the variables above.

# The logical (in scaled pixels) screen dimensions.
SCREEN_LOGICAL_DIMS = SCREEN_LOGICAL_WIDTH, SCREEN_LOGICAL_HEIGHT

# The real (in actual pixels) screen dimensions.
SCREEN_REAL_DIMS = tuple([x * SCREEN_ZOOM for x in SCREEN_LOGICAL_DIMS])
