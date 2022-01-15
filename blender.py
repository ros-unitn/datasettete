import random
import math
import os
from pathlib import Path

import cv2
from tqdm.std import tqdm

import bpy
from bpy_extras.object_utils import world_to_camera_view

names = [
    "X1-Y1-Z2",
    "X1-Y2-Z1",
    "X1-Y2-Z2",
    "X1-Y2-Z2-CHAMFER",
    "X1-Y2-Z2-TWINFILLET",
    "X1-Y3-Z2",
    "X1-Y3-Z2-FILLET",
    "X1-Y4-Z1",
    "X1-Y4-Z2",
    "X2-Y2-Z2",
    "X2-Y2-Z2-FILLET",
]
ok = False

colors = Path("colors")
bboxes = Path("bboxes")
labels = Path("labels")

train = Path("train")
val = Path("val")
test = Path("test")

# 80% train, 10% val, 10% test
stages = [*([train] * 8), val, test]

for dir in [colors, bboxes, labels]:
    for stage in stages:
        dir.joinpath(stage).mkdir(exist_ok=True, parents=True)

img_width = 1024
table_width = 0.64
table_height = 0.75

block_min = 1
block_max = 7

start_from = 0
iterations = 5000

animation_frames = 60

protected_objects = ["Sun", "Camera", "Table"]


def render(file_path_str):
    bpy.context.scene.render.filepath = file_path_str
    bpy.context.scene.render.resolution_x = img_width
    bpy.context.scene.render.resolution_y = img_width
    bpy.context.scene.render.image_settings.file_format = "JPEG"
    bpy.ops.render.render(write_still=1)


def make_scene():
    sun = bpy.data.lights["Sun"]
    # sun.color = (1.0, 0.0, 0.0)
    sun.energy = random.uniform(3, 7)
    sun.specular_factor = random.uniform(0.1, 0.9)  # 0.5 const
    sun.angle = math.pi * random.uniform(1, 10) / 180.0  # In radians, it was 10 const

    # rotating texture
    mat = bpy.data.materials["Material.003"]
    txt_mapping = mat.node_tree.nodes["Mapping"]
    txt_mapping.inputs["Rotation"].default_value[2] = random.randrange(0, 361)

    # adding random noise
    ntree_noise = mat.node_tree.nodes["Noise Texture"]
    if random.choice([False, True]):  # some pics with noise, some without
        ntree_noise.inputs["Scale"].default_value = random.uniform(0, 4)
        ntree_noise.inputs["Detail"].default_value = random.uniform(0, 4)
        ntree_noise.inputs["Roughness"].default_value = random.uniform(0, 4)
        ntree_noise.inputs["Distortion"].default_value = random.uniform(0, 1)
    else:
        ntree_noise.inputs["Scale"].default_value = 0
        ntree_noise.inputs["Detail"].default_value = 0
        ntree_noise.inputs["Roughness"].default_value = 0
        ntree_noise.inputs["Distortion"].default_value = 0

    size = random.randint(block_min, block_max)
    random_blocks = [random.choice(names) for _ in range(size)]

    for name in random_blocks:
        bpy.ops.object.select_all(action="DESELECT")
        x = random.uniform(-table_width / 2, table_width / 2)  # table x(-0.375,0.375)
        y = random.uniform(-table_width / 2, table_width / 2)  # table y(-0.375,0.375)
        z = table_height
        bpy.ops.import_mesh.stl(filepath="stl/" + name + ".stl")
        bpy.ops.transform.translate(value=(x, y, z), orient_type="GLOBAL")

        ob = bpy.data.objects[name]
        material = bpy.data.materials.new(
            name="randcolor" + str(random.randint(0, 6000))
        )
        material.diffuse_color = [
            random.uniform(0, 1),
            random.uniform(0, 1),
            random.uniform(0, 1),
            1,
        ]
        ob.active_material = material

        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == "VIEW_3D":
                    override = {"window": window, "screen": screen, "area": area}
                    bpy.ops.screen.screen_full_area(override)
                    break

        m = ob.modifiers.new("Solidify", type="SOLIDIFY")
        m.thickness = 0.00001

        if random.choice([True, False]):
            original_type = bpy.context.area.type
            bpy.context.area.type = "VIEW_3D"
            bpy.ops.transform.rotate(value=random.uniform(0, 6.28), orient_axis="X")
            bpy.ops.transform.rotate(value=random.uniform(0, 6.28), orient_axis="Y")
            bpy.ops.transform.rotate(value=random.uniform(0, 6.28), orient_axis="Z")
            bpy.context.area.type = original_type

            diff = z - object_lowest_point(bpy.data.objects[name]).z
            if diff > 0:
                bpy.ops.transform.translate(value=(0, 0, diff), orient_type="GLOBAL")

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.area.type = "VIEW_3D"
    bodies = [
        item.name
        for item in bpy.data.objects
        if item.type == "MESH" and item.name not in protected_objects
    ]
    for name in bodies:
        bpy.data.objects[name].select_set(True)
    bpy.ops.rigidbody.objects_add(type="ACTIVE")
    bpy.ops.rigidbody.enabled = True
    bpy.ops.rigidbody.mass = 0.0025  # in kg (perhaps)
    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS")
    bpy.ops.object.select_all(action="DESELECT")


def make_picture(i):
    bodies = [
        item
        for item in bpy.data.objects
        if item.type == "MESH"
        and item.name not in protected_objects
        and item.location.z > 0.73
    ]

    if len(bodies) == 0:
        return False

    stage = stages[(i * len(stages)) // iterations]
    img_path = stage.joinpath(f"img{i}.jpeg")
    txt_path = stage.joinpath(f"img{i}.txt")

    render(str(colors.joinpath(img_path)))

    # img = cv2.imread(str(colors.joinpath(img_path)))

    with open(labels.joinpath(txt_path), "w") as f:
        for obj in bodies:
            label = obj.name.split(".", 1)[0]  # ABCD.001 -> ABCD
            scene = bpy.context.scene

            render_scale = scene.render.resolution_percentage / 100
            res_x = scene.render.resolution_x * render_scale
            res_y = scene.render.resolution_y * render_scale

            cam = bpy.data.objects["Camera"]

            verts = [vert.co for vert in obj.data.vertices]
            for i in range(len(verts)):
                verts[i] = obj.matrix_world @ verts[i]

            coords_2d = [world_to_camera_view(scene, cam, coord) for coord in verts]

            x_max = max(coords_2d[0])
            y_max = max(coords_2d[1])
            x_min = min(coords_2d[0])
            y_min = min(coords_2d[1])

            verts_2d = []
            for x, y, _ in coords_2d:
                verts_2d.append(tuple((round(res_x * x), round(res_y - res_y * y))))

            y_max = max(verts_2d, key=lambda i: i[1])[1]
            x_max = max(verts_2d, key=lambda i: i[0])[0]
            y_min = min(verts_2d, key=lambda i: i[1])[1]
            x_min = min(verts_2d, key=lambda i: i[0])[0]

            y_max = min(y_max, 1024)
            x_max = min(x_max, 1024)
            y_min = max(y_min, 0)
            x_min = max(x_min, 0)

            center_x = (x_max + x_min) / 2
            center_y = (y_max + y_min) / 2
            w = x_max - x_min
            h = y_max - y_min

            # go to percentage, 0-1 range values
            yolo_x = center_x / 1024
            yolo_y = center_y / 1024
            yolo_w = w / 1024
            yolo_h = h / 1024

            if (
                yolo_x + yolo_w / 2 <= 1
                and yolo_x - yolo_w / 2 >= 0
                and yolo_y + yolo_h / 2 <= 1
                and yolo_y - yolo_h / 2 >= 0
            ):
                f.write(f"{label} {yolo_x} {yolo_y} {yolo_w} {yolo_h}\n")

                # cv2.rectangle(
                #     img,
                #     (int(center_x - w / 2), int(center_y + h / 2)),
                #     (int(center_x + w / 2), int(center_y - h / 2)),
                #     (0, 0, 255),
                #     2,
                # )
                # cv2.putText(
                #     img,
                #     label,
                #     (int(center_x - w / 2), int(center_y - h / 2 - 10)),
                #     cv2.FONT_HERSHEY_SIMPLEX,
                #     0.9,
                #     (0, 0, 255),
                #     2,
                # )

    # cv2.putText(
    #     img,
    #     str(len(bodies)),
    #     (10, 30),
    #     cv2.FONT_HERSHEY_SIMPLEX,
    #     0.9,
    #     (0, 0, 255),
    #     2,
    # )
    # cv2.imwrite(str(bboxes.joinpath(img_path)), img)
    return True


def object_lowest_point(obj):
    matrix_w = obj.matrix_world
    vectors = [matrix_w @ vertex.co for vertex in obj.data.vertices]
    return min(vectors, key=lambda item: item.z)


def process(i):
    good = False
    while not good:
        make_scene()
        for n in range(animation_frames):
            bpy.context.scene.frame_set(n)
        good = make_picture(i)
        to_delete = [
            item.name
            for item in bpy.data.objects
            if item.type == "MESH" and item.name not in protected_objects
        ]
        for name in to_delete:
            bpy.data.objects[name].select_set(True)
            bpy.ops.object.delete()
        bpy.ops.screen.animation_cancel(restore_frame=True)


bpy.context.scene.gravity = (0, 0, -9.81)
bpy.context.scene.use_gravity = True

for i in tqdm(range(start_from, iterations)):
    process(i)
