"""
The stage module provides a class representing the game world.
"""
import math
import random
import pytmx
from entity import Entity
from config import SCREEN_LOGICAL_WIDTH, SCREEN_LOGICAL_HEIGHT
from common import make_2d_constant_array

class Stage(object):
    """
    A Stage represents the game world, including tiles, objects, etc.

    Arguments:
        path: a path to a .tmx file containing the stage data
              (see examples in "maps/")
    """
    def __init__(self, path):
        tiled_map = \
            pytmx.TiledMap(path)
        assert tiled_map is not None

        self.width = tiled_map.width
        self.height = tiled_map.height
        self.data = make_2d_constant_array(self.width, self.height, 0)
        self._entity_matrix = \
          make_2d_constant_array(self.width, self.height, None)

        # The list of on-stage entities and their coordinates.
        # Contains tuples of the following format: (entity, x, y)
        self._entity_list = []

        player_start_obj = \
            tiled_map.get_object_by_name('Player Start')
        player_start_x = player_start_obj.x
        player_start_y = player_start_obj.y
        self.player_start_loc = player_start_x, player_start_y

        self._tile_change_listeners = []

        for layer_ref in tiled_map.visible_tile_layers:
            layer = tiled_map.layers[layer_ref]
            for x, y, img in layer.tiles():
                target_x = math.floor(img[1][0] / 16)
                target_y = math.floor(img[1][1] / 16)
                tid = target_y * 16 + target_x

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
        """
        Register an object to be signalled whenever a tile changes.

        The listening object must have a method called tile_changed
        accepting the previous tile ID, the new tile ID, and the
        position as a pair of (x, y) coordinates.  For example:

            def tile_changed(self, prev_tid, cur_tid, position)

        Whenever a tile changes on this Stage, the tile_changed
        method will be called on every listener.

        Argument:
            listener: the object to signal when a tile changes
        """
        self._tile_change_listeners.append(listener)

    def _draw_tile_at(self, screen, tileset, camera, loc):
        x, y = loc
        tid = self.data[y][x]
        target_x = tid % 16
        target_y = math.floor(tid / 16)
        screen.blit(tileset,
                    camera.transform_game_to_screen(
                        (x, y), scalar=16),
                    (target_x * 16, target_y * 16, 16, 16))

    def _draw_entity_at(self, screen, tileset, camera, loc):
        x, y = loc
        if self._entity_matrix[y][x]:
            kind = self._entity_matrix[y][x].kind

            if kind == 'rock':
                target_x = 6
            elif kind == 'bug':
                target_x = 7
            elif kind == 'fish':
                target_x = 4

            screen.blit(tileset,
                        camera.transform_game_to_screen(
                            (x, y), scalar=16),
                        (target_x * 16, 0, 16, 16))

    def draw(self, screen, tileset, camera):
        """
        Draw the visible map area onto a screen.

        Arguments:
            screen: the screen to draw on
            tileset: the tileset to use for tiles and objects
            camera: the Camera to draw with
        """
        clip_left = math.floor(camera.x / 16)
        clip_top = math.floor(camera.y / 16)
        clip_width = math.floor(SCREEN_LOGICAL_WIDTH / 16)
        clip_height = math.floor(SCREEN_LOGICAL_HEIGHT / 16 + 1)

        for y in range(clip_top, clip_top + clip_height):
            for x in range(clip_left, clip_left + clip_width):
                if x < 0 or x >= self.width \
                   or y < 0 or y >= self.height:
                    continue

                args = screen, tileset, camera, (x, y)
                self._draw_tile_at(*args)
                self._draw_entity_at(*args)

    def get_player_start_pos(self):
        """
        Return the default starting location of the player.

        Returns: the default starting location of the player
        """
        return self.player_start_loc

    def get_tile_at(self, x, y):
        """
        Return the ID of the tile at (x, y), or None if off-map.

        Arguments:
            x: the x coordinate of the tile
            y: the y coordinate of the tile

        Returns: the tile ID of the tile at (x, y),
                 or None if the coordinates are off-map
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return None

        return self.data[y][x]

    def set_tile_at(self, x, y, tid):
        """
        Set the tile at (x, y) to the tile ID tid.

        The coordinates must actually be within the Stage.

        Arguments:
            x: the x coordinate of the tile to change
            y: the y coordinate of the tile to change
            tid: the tile ID the tile should be changed to
        """
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
            location: the location at which to place the entity
        """
        x, y = location

        assert 0 <= x < self.width
        assert 0 <= y < self.height
        assert not self._entity_matrix[y][x], \
               'location is not empty: x=%d, y=%d' % (x, y)

        entity.location = location
        self._entity_matrix[y][x] = entity
        self._entity_list.append((entity, x, y))

    def create_entity(self, kind, location):
        """
        Create an entity of the given kind at a location in this Stage.

        Arguments:
            kind: the kind of entity (bug | stone | fish)
            location: a tuple (x, y) specifying a location
        """
        entity = Entity(kind=kind, location=location)
        self.add_entity(entity, location)

    def delete_entity(self, entity):
        """
        Delete an entity from this Stage.

        Arguments:
            entity: the entity to delete
        """
        for y in range(self.height):
            for x in range(self.width):
                if self._entity_matrix[y][x] == entity:
                    self._entity_matrix[y][x] = None
                    self._entity_list.remove((entity, x, y))
                    entity.location = None

    def find_entity(self, condition):
        """
        Find an entity on the stage satisfying a condition.

        Arguments:
            condition: a lambda taking an entity, the entity's
                x coordinate, and the entity's y coordinate,
                and returning True if the entity is accepted
                or False if the entity is not accepted
        Returns:
            a tuple (entity, (x, y)) if an entity was accepted,
            or None if no entity was accepted
        """
        random.shuffle(self._entity_list)
        for ent, x, y in self._entity_list:
            if condition(ent, x, y):
                return ent, (x, y)

        return None

    def entity_at(self, location):
        """
        Return the entity at a location if there is one, otherwise None.

        Arguments:
            location: the pair of coordinates (x, y)

        Returns: the entity at the location, or None if there is none
        """
        x, y = location
        return self._entity_matrix[y][x]
