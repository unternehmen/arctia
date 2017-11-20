from bfont import BitmapFont
import os
import pygame

def test_bfont_load():
    pygame.init()
    font_img = pygame.image.load(os.path.join('gfx', 'fawnt.png'))
    chars = 'ABC'

    expected = [(1, 0, 7, 12),
                (9, 0, 7, 12),
                (17, 0, 7, 12)]

    bfont = BitmapFont(chars, font_img)

    assert bfont is not None
    for i, cell in enumerate(bfont.cells[:2]):
        assert cell == expected[i]
    assert len(bfont.cells) == len(chars)
