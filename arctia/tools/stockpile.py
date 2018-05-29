from ..config import MENU_WIDTH
from ..common import tile_is_solid
from ..transform import translate
from ..stockpile import Stockpile


tooltip = 'Create Stockpile'
inactive_icon_clip = (176, 16, 16, 16)
active_icon_clip = (176, 32, 16, 16)


_block_origin = None

def start_on_tile(pos, player_team):
    global _block_origin
    _block_origin = pos

def stop_on_tile(pos, stage, player_team):
    global _block_origin

    if not _block_origin:
        return

    ox, oy = _block_origin
    tx, ty = pos
    _block_origin = None

    left = min((tx, ox))
    right = max((tx, ox))
    top = min((ty, oy))
    bottom = max((ty, oy))

    # Check if this conflicts with existing stockpiles.
    conflicts = False
    for stock in player_team.stockpiles:
        sx, sy = stock.x, stock.y
        sw, sh = stock.width, stock.height
        if not (sx > right \
                or sy > bottom \
                or sx + sw <= left \
                or sy + sh <= top):
            conflicts = True
            break

    all_walkable = True
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            if x < 0 or x >= stage.width or \
               y < 0 or y >= stage.height:
                all_walkable = False
                break

            tid = stage.get_tile_at(x, y)

            if tid is None:
                pass
            elif tile_is_solid(tid):
                all_walkable = False
        if not all_walkable:
            break

    if not conflicts and all_walkable:
        # Make the new stockpile.
        stock = Stockpile(stage,
                          (left, top,
                           right - left + 1,
                           bottom - top + 1),
                           ['fish'])
        player_team.stockpiles.append(stock)

def draw(screen, camera, tileset, mouse_pos):
    global _block_origin

    # Draw the selection box under the cursor.
    if not _block_origin and mouse_pos[0] > MENU_WIDTH:
        selection = camera.transform_screen_to_tile(mouse_pos)
        screen.blit(tileset,
                    camera.transform_tile_to_screen(selection),
                    (128, 0, 16, 16))

    # Draw the designation rectangle if we are drawing a region.
    if _block_origin:
        ox, oy = _block_origin
        tx, ty = camera.transform_screen_to_tile(mouse_pos)

        left = min((tx, ox))
        right = max((tx, ox))
        top = min((ty, oy))
        bottom = max((ty, oy))

        top_left_coords     = camera.transform_tile_to_screen(
                                (left, top)),
        top_right_coords    = translate(
                                camera.transform_tile_to_screen(
                                  (right, top)),
                                (8, 0))
        bottom_left_coords  = translate(
                                camera.transform_tile_to_screen(
                                  (left, bottom)),
                                (0, 8))
        bottom_right_coords = translate(
                                camera.transform_tile_to_screen(
                                  (right, bottom)),
                                (8, 8))

        screen.blit(tileset, top_left_coords, (128, 0, 8, 8))
        screen.blit(tileset, bottom_left_coords, (128, 8, 8, 8))
        screen.blit(tileset, top_right_coords, (136, 0, 8, 8))
        screen.blit(tileset, bottom_right_coords, (136, 8, 8, 8))
