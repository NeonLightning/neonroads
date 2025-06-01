from ursina import *

app = Ursina()

tile_size_x = 1
tile_size_y = 1

def make_tunnel_tile(pos):
    floor = Entity(
        model='cube',
        color=color.gray,
        scale=(tile_size_x, 0.5, tile_size_y),
        position=pos,
        collider='box'
    )
    left_wall = Entity(
        model='cube',
        color=color.dark_gray,
        scale=(tile_size_x * 0.2, 2.5, tile_size_y),
        position=pos + Vec3(-(tile_size_x * 0.6), 1.25, 0),
        collider='box',
        parent=floor
    )
    right_wall = Entity(
        model='cube',
        color=color.dark_gray,
        scale=(tile_size_x * 0.2, 2.5, tile_size_y),
        position=pos + Vec3(tile_size_x * 0.6, 1.25, 0),
        collider='box',
        parent=floor
    )
    return floor

tunnel = make_tunnel_tile(Vec3(0,0,0))

EditorCamera()  # allows free mouse control of camera

app.run()
