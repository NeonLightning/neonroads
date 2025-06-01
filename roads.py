import sys
import io
from panda3d.core import loadPrcFileData

#loadPrcFileData('', 'notify-level error')
#loadPrcFileData('', 'default-directnotify-level error')
#loadPrcFileData('', 'window-title ')
#loadPrcFileData('', 'show-frame-rate-meter false')
#loadPrcFileData('', 'audio-library-name null')
#sys.stdout = io.StringIO()
#sys.stderr = io.StringIO()

from ursina import *
from ursina.shader import Shader
from ursina.shaders import unlit_shader

basic_lighting_shader = Shader(name='basic_lighting_shader', language=Shader.GLSL,
vertex = '''
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 texcoord;
in vec3 p3d_Normal;
out vec3 world_normal;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;
    world_normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
}
''',

fragment='''
#version 140
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
in vec2 texcoord;
in vec3 world_normal;
out vec4 fragColor;
void main() {
    vec4 norm = vec4(world_normal*0.5+0.5, 1);
    float grey = 0.21 * norm.r + 0.71 * norm.g + 0.07 * norm.b;
    norm = vec4(grey, grey, grey, 1);
    vec4 color = texture(p3d_Texture0, texcoord) * p3d_ColorScale * norm;
    fragColor = color.rgba;
}


''', geometry='',
)

app = Ursina()

use_gamepad = False
sky = Entity(
    model='sphere',
    texture='sky_default',
    color=color.rgb(0.3,0,0.3),
    scale=600,
    double_sided=True,
    parent=camera,
    position=(0,0,0),
    shader=unlit_shader,
    texture_scale=(6, 6),
    eternal=True
)
sky.light = None
#Sky(texture='sky_default')
window.color = color.black
window.fps_counter.enabled = False
window.entity_counter.enabled = False
window.collider_counter.enabled = False
camera.position = (0, 25, -50)
camera.rotation_x = 20
tile_size_y = 15
tile_size_x = 1.5
visible_rows = 27
generate_threshold = 25
tiles = []
cols = 5
min_tiles = 1
death_chance = 0.1
fixed_rows = 5
light = DirectionalLight(shadows=True)
light.look_at(Vec3(-2, -4, -2))
light.rotation = (45, 45, 0)
light.shadow_resolution = 1024
light.shadow_bias = 0.01
light.shadow_softness = 1
current_row_z = visible_rows
velocity_y = 0
gravity = -9.8
jump_force = 6
on_ground = True
has_landed = False
score = 0
highscore = 0
score_text = None
highscore_file = 'highscore.txt'
game_running = True
min_speed = 20
max_speed = 60
speed = min_speed
speed_step = 20
game_over_text = Text(
    text='',
    position=(0, 0),
    origin=(0, 0),
    scale=2,
    color=color.red,
    background=False,
    enabled=False
)
score_text = Text(
    text=f'Score: {int(score)}',
    position=(-0.85, 0.45),
    scale=2,
    color=color.white,
    background=False
)

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

def load_highscore():
    global highscore
    try:
        with open(highscore_file, 'r') as f:
            highscore = float(f.read().strip())
    except Exception:
        highscore = 0

load_highscore()
highscore_text = Text(
    text=f'Highscore: {int(highscore)}',
    position=(-0.85, 0.4),
    scale=1.5,
    color=color.yellow,
    background=False
)

def spawn_player():
    global player
    player = Entity(
        scale=(0.2, 0.1, 0.4),
        position=(0, 5, 0),
        origin_y=0
    )
    player.collider = BoxCollider(
        entity=player,
        center=Vec3(0, 0, 0),
        size=Vec3(tile_size_x * 0.3, 0.1, 0.8)
    )
    player_model = Entity(
        parent=player,
        model='./player/rocket.obj',
        texture='./player/player.jpg',
        shader=basic_lighting_shader,
        position=(0, 1.0, 0)
    )
    camera.parent = player

def generate_row(index):
    if index < fixed_rows:
        return '=' * cols
    row_chars = [' '] * cols
    for i in range(cols):
        if random.random() < 0.5:
            if random.random() < death_chance:
                row_chars[i] = 'X'
            else:
                row_chars[i] = '='
        else:
            row_chars[i] = ' '
    solid_count = sum(c == '=' for c in row_chars)
    positions_empty = [i for i, c in enumerate(row_chars) if c == ' ']
    while solid_count < min_tiles and positions_empty:
        pos = positions_empty.pop()
        row_chars[pos] = '='
        solid_count += 1
    return ''.join(row_chars)

def make_tile(char, pos):
    if char == '=':
        return Entity(
            model='Cube',
            color=color.gray,
            texture='brick',
            shader=basic_lighting_shader,
            scale=(tile_size_x, 0.5, tile_size_y),
            position=pos,
            collider='box'
        )
    elif char == 'X':
        e = Entity(
            model='Cube',
            color=color.red,
            texture='noise',
            shader=basic_lighting_shader,
            scale=(tile_size_x, 0.5, tile_size_y),
            position=pos,
            collider='box'
        )
        e.death_tile = True
        return e
    return None

def create_level():
    global tiles
    level_data = [generate_row(i) for i in range(visible_rows)]
    for z, row in enumerate(level_data):
        for x, char in enumerate(row):
            pos = Vec3((x - cols // 2) * tile_size_x, 0, z * tile_size_y)
            tile = make_tile(char, pos)
            if tile:
                tiles.append(tile)
    invoke(spawn_player, delay=0.2)

def reset_game():
    global tiles, current_row_z, velocity_y, on_ground, has_landed, player, score, game_running, speed
    for t in tiles:
        destroy(t)
    tiles.clear()
    if 'player' in globals() and player is not None:
        destroy(player)
        player = None
    current_row_z = visible_rows
    velocity_y = 0
    on_ground = True
    has_landed = False
    score = 0
    score_text.text = f'Score: {int(score)}'
    game_running = True
    invoke(create_level, delay=0.01)
    light.shadows = True
    sky.color=color.rgb(0.3,0,0.3)
    speed = min_speed

def game_over():
    global game_running, score, highscore, player
    game_running = False
    if score > highscore:
        highscore = float(score)
        with open(highscore_file, 'w') as f:
            f.write(str(highscore))
        highscore_text.text = f'Highscore: {int(highscore)}'
    for t in tiles:
        destroy(t)
    tiles.clear()
    if player:
        player.disable()
        destroy(player)
        player = None
    game_over_text.text = f'Game Over!\nYour score: {int(score)}\n\nPress Space or a face button on gamepad to continue\nEscape or gamepad start/select to quit.'
    game_over_text.enabled = True
    light.shadows = False
    sky.color = color.rgb(0.3, 0.1, 0.1)
    print(f'Game Over! Your score: {int(score)}')

def update():
    global velocity_y, on_ground, current_row_z, has_landed, score, game_running, speed
    if not game_running:
        if held_keys['space'] or held_keys['gamepad a'] or held_keys['gamepad b'] or held_keys['gamepad x'] or held_keys['gamepad y']:
            game_over_text.enabled = False
            reset_game()
        elif held_keys['escape'] or held_keys['gamepad back'] or held_keys['gamepad start']:
            application.quit()
        return
    if 'player' not in globals() or player is None:
        return
    player.z += speed * time.dt
    score += speed * time.dt
    score_text.text = f'Score: {int(score)}'
    if held_keys['a']:
        player.x -= 5 * time.dt
    if held_keys['d']:
        player.x += 5 * time.dt
    half_width = player.collider.size.x / 2
    half_depth = player.collider.size.z / 2
    ray_origins = [
        player.world_position + Vec3(0, -player.scale_y / 2 + 0.05, 0),
        player.world_position + Vec3(-half_width, -player.scale_y / 2 + 0.05, 0),
        player.world_position + Vec3(half_width, -player.scale_y / 2 + 0.05, 0),
        player.world_position + Vec3(-half_width, -player.scale_y / 2 + 0.05, -half_depth),
        player.world_position + Vec3(half_width, -player.scale_y / 2 + 0.05, -half_depth),
        player.world_position + Vec3(-half_width, -player.scale_y / 2 + 0.05, half_depth),
        player.world_position + Vec3(half_width, -player.scale_y / 2 + 0.05, half_depth),
    ]
    on_any_ground = False
    for ray_origin in ray_origins:
        ray = raycast(ray_origin, Vec3(0, -1, 0), distance=0.6, ignore=[player])
        if ray.hit and hasattr(ray.entity, 'death_tile'):
            print("Hit death tile at edge! Resetting...")
            game_over()
            return
        if ray.hit:
            ground_tile = ray.entity
            tile_top_y = ground_tile.y + (ground_tile.scale_y / 2)
            snap_y = tile_top_y + (player.scale_y / 2)
            distance_to_target = player.y - snap_y
            if velocity_y <= 0 and abs(distance_to_target) <= 0.1:
                player.y = snap_y
                velocity_y = 0
                on_ground = True
                has_landed = True
                on_any_ground = True
                break
    if not on_any_ground:
        velocity_y += gravity * time.dt
        player.y += velocity_y * time.dt
        on_ground = False
    if has_landed and player.y < -5:
        print("Fell! Resetting...")
        game_over()
        return
    move_input = 0
    if held_keys['a'] or held_keys['left arrow']:
        move_input -= 1
    if held_keys['d'] or held_keys['right arrow']:
        move_input += 1
    if use_gamepad:
        move_input += held_keys['gamepad left stick x']
        if held_keys['gamepad dpad left']:
            move_input -= 1
        if held_keys['gamepad dpad right']:
            move_input += 1
    player.x += clamp(move_input, -1, 1) * 5 * time.dt
    speed_input = 0
    if held_keys['w'] or held_keys['up arrow']:
        speed_input += 1
    if held_keys['s'] or held_keys['down arrow']:
        speed_input -= 1
    if use_gamepad:
        speed_input += held_keys['gamepad right trigger']
        speed_input -= held_keys['gamepad left trigger']
        if held_keys['gamepad dpad up']:
            speed_input += 1
        if held_keys['gamepad dpad down']:
            speed_input -= 1
    if speed_input > 0:
        speed = min(max_speed, speed + speed_step * time.dt)
    elif speed_input < 0:
        speed = max(min_speed, speed - speed_step * time.dt)
    if held_keys['space'] and on_ground:
        velocity_y = jump_force
        player.y += 0.01
        on_ground = False
    if use_gamepad and on_ground and (
        held_keys['gamepad a'] or
        held_keys['gamepad b'] or
        held_keys['gamepad x'] or
        held_keys['gamepad y']
    ):
        velocity_y = jump_force
        player.y += 0.01
        on_ground = False
    while player.z + visible_rows * tile_size_y > current_row_z * tile_size_y:
        row = generate_row(current_row_z)
        for x, char in enumerate(row):
            pos = Vec3((x - cols // 2) * tile_size_x, 0, current_row_z * tile_size_y)
            tile = make_tile(char, pos)
            if tile:
                tiles.append(tile)
        current_row_z += 1  
    for t in tiles[:]:
        if t.z < player.z - (tile_size_y * 10):
            destroy(t)
            tiles.remove(t)
invoke(create_level, delay=0.01)

app.run()