from functools import partial
from ..config import MENU_WIDTH
from ..transform import translate
from ..common import tile_is_solid, unit_can_reach


tooltip = 'Build Wall'
inactive_icon_clip = (144, 16, 16, 16)
active_icon_clip = (144, 32, 16, 16)


def start_on_tile(pos, stage, player_team):
    if not tile_is_solid(stage.get_tile_at(*pos)):
        scaffold_jobs = []
        for x in range(5):
            scaffold_jobs.append({
                'kind': 'scaffold',
                'hidden': True,
                'location': pos,
                'resource':
                  lambda unit:
                    stage.find_entity(
                      partial(
                        lambda unit, entity, _unused_x, _unused_y:
                          unit_can_reach(unit, entity.location) \
                          and not unit.team.is_reserved('entity',
                                                        entity) \
                          and entity.kind == 'rock',
                        unit)),
                'done': False
            })
        build_job = {
            'kind': 'build',
            'location': pos,
            'scaffold_jobs': scaffold_jobs,
            'collected_goods': [],
            'done': False
        }
        for scaffold_job in scaffold_jobs:
            scaffold_job['dependent'] = build_job
        player_team.designations.extend(scaffold_jobs)
        player_team.designations.append(build_job)

def stop_on_tile(pos, stage, player_team):
    pass

def draw(screen, camera, tileset, mouse_pos):
    # Draw the selection box under the cursor.
    if mouse_pos[0] > MENU_WIDTH:
        selection = camera.transform_screen_to_tile(mouse_pos)
        screen.blit(tileset,
                    camera.transform_tile_to_screen(selection),
                    (128, 0, 16, 16))
