from ..config import MENU_WIDTH
from ..transform import translate


tooltip = 'Delete Stockpile'
inactive_icon_clip = (192, 16, 16, 16)
active_icon_clip = (192, 32, 16, 16)


_block_origin = None

def start_on_tile(pos, player_team):
    # Delete the chosen stockpile
    for stock in player_team.stockpiles:
        if stock.x <= pos[0] < stock.x + stock.width \
           and stock.y <= pos[1] < stock.y + stock.height:
            player_team.stockpiles.remove(stock)
            break

def stop_on_tile(pos, stage, player_team):
    pass

def draw(screen, camera, tileset, mouse_pos):
    global _block_origin

    # Draw the selection box under the cursor.
    if mouse_pos[0] > MENU_WIDTH:
        selection = camera.transform_screen_to_tile(mouse_pos)
        screen.blit(tileset,
                    camera.transform_tile_to_screen(selection),
                    (128, 0, 16, 16))
