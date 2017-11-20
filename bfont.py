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
        cw = 0
        ch = image.get_height()
        
        while idx < len(chars):
            if image.get_at((x + cw, 0)) == sep_color:
                self.cells[idx] = (x, 0, cw, ch)
                idx += 1
                x += cw + 1
                cw = 0
            else:
                cw += 1

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

        for c in text:
            if c == '\n':
                x = position[0]
                y += self.cells[0][3]
            else:
                clip = self.cells[self.chars.index(c)]
                surface.blit(self.image, (x, y), clip)
                x += clip[2]

