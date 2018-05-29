import os
import pygame
from arctia.bfont import BitmapFont
from arctia.resources import load_image

def test_bfont_load():
    pygame.init()
    font_img = load_image('gfx/fawnt.png')
    chars = 'ABC'

    expected = [(1, 0, 7, 12),
                (9, 0, 7, 12),
                (17, 0, 7, 12)]

    bfont = BitmapFont(chars, font_img)

    assert bfont is not None
    for i, cell in enumerate(bfont.cells[:2]):
        assert cell == expected[i]
    assert len(bfont.cells) == len(chars)

def test_bfont_measure():
    pygame.init()
    font_img = load_image('gfx/fawnt.png')
    chars = 'ABC'
    bfont = BitmapFont(chars, font_img)
    result = bfont.measure('BACAB\nAB')
    assert(bfont.measure('BACAB\nAB') == (35, 24))
