import pytmx
import os
import math
from config import *

class Stage(object):
    def __init__(self):
        tiled_map = \
            pytmx.TiledMap(os.path.join('maps', 'tuxville.tmx'))
        self.width = tiled_map.width
        self.height = tiled_map.height
        self.data = [[0 for x in range(self.width)]
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
        clip_left = math.floor(camera_x / 16)
        clip_top = math.floor(camera_y / 16)
        clip_width = math.floor(SCREEN_LOGICAL_WIDTH / 16)
        clip_height = math.floor(SCREEN_LOGICAL_HEIGHT / 16 + 1)
        for y in range(clip_top, clip_top + clip_height):
            for x in range(clip_left, clip_left + clip_width):
                if x < 0 or x >= self.width \
                   or y < 0 or y >= self.height:
                    continue
                tid = self.data[y][x]
                tx = tid % 16
                ty = math.floor(tid / 16)
                screen.blit(tileset,
                            (x * 16 - camera_x + MENU_WIDTH,
                             y * 16 - camera_y),
                            (tx * 16, ty * 16, 16, 16))

    def get_player_start_pos(self):
        return self.player_start_x, self.player_start_y

    def get_tile_at(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return None

        return self.data[y][x]

    def set_tile_at(self, x, y, tid):
        assert x >= 0
        assert x < self.width
        assert y >= 0
        assert y < self.height

        self.data[y][x] = tid