"""
The bfont module provides a class for loading and using bitmap fonts.
"""

class BitmapFont(object):
    """
    A BitmapFont is a font derived from a bitmap image.

    The top-left pixel of the bitmap image names the "separator color".
    This separator color is used to separate cells of the font file.

    Arguments:
        chars: a string of characters in the font, i.e., "abcdefg"
        image: an image
    """
    def __init__(self, chars, image):
        self.cells = [None for c in chars]
        self.chars = chars
        self.image = image

        # Determine the cells.
        sep_color = image.get_at((0, 0))
        idx = 0
        x = 1
        cwidth = 0
        cheight = image.get_height()

        while idx < len(chars):
            if image.get_at((x + cwidth, 0)) == sep_color:
                self.cells[idx] = (x, 0, cwidth, cheight)
                idx += 1
                x += cwidth + 1
                cwidth = 0
            else:
                cwidth += 1

    def write(self, surface, text, position):
        """
        Render text to a surface at a position using this font.

        Arguments:
            surface: the surface to draw onto
            text: the text to write
            position: the coordinates (x, y) at which to write
        """
        x = position[0]
        y = position[1]

        for char in text:
            if char == '\n':
                x = position[0]
                y += self.cells[0][3]
            else:
                clip = self.cells[self.chars.index(char)]
                surface.blit(self.image, (x, y), clip)
                x += clip[2]

    def measure(self, text):
        """
        Return the space that a given text would take up.

        Arguments:
            text: a text

        Returns: a tuple describing a width and height, e.g., (16, 16)
        """
        x = 0
        y = 0
        width = 0
        height = 0

        for char in text:
            if char == '\n':
                x = 0
                y += self.cells[0][3]
            else:
                clip = self.cells[self.chars.index(char)]
                if width < x + clip[2]:
                    width = x + clip[2]
                elif height < y + clip[3]:
                    height = y + clip[3]
                x += clip[2]

        return width, height
