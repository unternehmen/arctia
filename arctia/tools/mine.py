from ..config import MENU_WIDTH
from ..transform import translate


tooltip = 'Mine'
inactive_icon_clip = (144, 16, 16, 16)
active_icon_clip = (144, 32, 16, 16)


_block_origin = None

def start_on_tile(pos, stage, player_team):
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

    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            if x < 0 or x >= stage.width or \
               y < 0 or y >= stage.height:
                continue

            tid = stage.get_tile_at(x, y)

            if tid is None:
                pass
            elif tid == 2:
                designations = \
                  player_team.designations

                already_exists = False
                for designation in designations:
                    loc = designation['location']
                    if loc == (x, y):
                        already_exists = True
                        break

                if not already_exists:
                    designations.append({
                        'kind': 'mine',
                        'location': (x, y),
                        'done': False
                    })

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
