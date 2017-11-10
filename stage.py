import pytmx
import os
import math
from entity import Entity
from config import *

class Stage(object):
    def __init__(self, path):
        tiled_map = \
            pytmx.TiledMap(path)
        assert tiled_map is not None

        self.width = tiled_map.width
        self.height = tiled_map.height
        self.data = [[0 for x in range(self.width)]
                     for y in range(self.height)]
        self.entity_matrix = [[None for x in range(self.width)]
                            for y in range(self.height)]
        # The list of on-stage entities and their coordinates.
        # Contains tuples of the following format: (entity, x, y)
        self.entity_list = []

        player_start_obj = \
            tiled_map.get_object_by_name('Player Start')
        self.player_start_x = player_start_obj.x
        self.player_start_y = player_start_obj.y
        
        self._tile_change_listeners = []

        self.entities = []

        for layer_ref in tiled_map.visible_tile_layers:
            layer = tiled_map.layers[layer_ref]
            for x, y, img in layer.tiles():
                tx = math.floor(img[1][0] / 16)
                ty = math.floor(img[1][1] / 16)
                tid = ty * 16 + tx

                # Some tiles add an entity instead of a tile.
                if tid == 4:
                    self.create_entity('fish', (x, y))
                    tid = 1
                elif tid == 6:
                    self.create_entity('rock', (x, y))
                    tid = 1
                elif tid == 7:
                    self.create_entity('bug', (x, y))
                    tid = 1

                self.data[y][x] = tid

    def register_tile_change_listener(self, listener):
        self._tile_change_listeners.append(listener)

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

        # Draw entities.
        for y in range(clip_top, clip_top + clip_height):
            for x in range(clip_left, clip_left + clip_width):
                if x < 0 or x >= self.width \
                   or y < 0 or y >= self.height:
                    continue
                if self.entity_matrix[y][x]:
                    kind = self.entity_matrix[y][x].kind

                    if kind == 'rock':
                        tx = 6
                    elif kind == 'bug':
                        tx = 7
                    elif kind == 'fish':
                        tx = 4

                    screen.blit(tileset,
                                (x * 16 - camera_x + MENU_WIDTH,
                                 y * 16 - camera_y),
                                (tx * 16, 0, 16, 16))


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

        prev_tid = self.data[y][x]
        cur_tid = tid

        self.data[y][x] = tid

        for listener in self._tile_change_listeners:
            listener.tile_changed(prev_tid, cur_tid, (x, y))

    def add_entity(self, entity, location):
        """
        Add an entity to the Stage.

        Arguments:
            entity: the entity
        """
        x, y = location

        assert 0 <= x < self.width
        assert 0 <= y < self.height
        assert not self.entity_matrix[y][x], \
               'location is not empty: x=%d, y=%d' % (x, y)

        self.entity_matrix[y][x] = entity
        self.entity_list.append((entity, x, y))

    def create_entity(self, kind, location):
        """
        Create an entity of the given kind at a location in this Stage.

        Arguments:
            kind: the kind of entity (bug | stone | fish)
            location: a tuple (x, y) specifying a location
        """
        entity = Entity(kind=kind)
        self.add_entity(entity, location)

    def delete_entity(self, entity):
        """
        Delete an entity from this Stage.

        Arguments:
            entity: the entity to delete
        """
        for y in range(self.height):
            for x in range(self.width):
                if self.entity_matrix[y][x] == entity:
                    self.entity_matrix[y][x] = None
                    self.entity_list.remove((entity, x, y))

    def update(self):
        pass

    def find_entity(self, condition):
        """
        Find an entity on the stage satisfying a condition.

        Arguments:
            condition: a lambda taking an event, the event's
                x coordinate, and the event's y coordinate,
                and returning True if the event is accepted
                or False if the event is not accepted
        Returns:
            a tuple (event, (x, y)) if an event was accepted,
            or None if no event was accepted
        """
        for ent, x, y in self.entity_list:
            if condition(ent, x, y):
                return ent, (x, y)

        return None

    def entity_at(self, location):
        x, y = location
        return self.entity_matrix[y][x]
