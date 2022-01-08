import random
import sys
import cv2
import os
from pathlib import Path

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

images = Path("images")
bboxes = Path("bboxes")
labels = Path("labels")
depth = Path("depth")

train = Path("train")
val = Path("val")
test = Path("test")

stages = [
    train,
    val,
    test
]

for dir in [images, bboxes, labels, depth]:
    for stage in stages:
        dir.joinpath(stage).mkdir(exist_ok=True, parents=True)

img_width = 1024
table_width = 0.64
table_height = 0.75
iterations = 5000

def render_picture(file_path_str):
    bpy.context.scene.render.filepath = file_path_str
    bpy.context.scene.render.resolution_x = img_width
    bpy.context.scene.render.resolution_y = img_width
    bpy.context.scene.render.image_settings.file_format = "JPEG"
    bpy.ops.render.render(write_still=1)

def make_depth_map(img_path):
    #switch on nodes
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    links = tree.links

    # create input render layer node
    rl = tree.nodes.new('CompositorNodeRLayers')    
    n = tree.nodes.new('CompositorNodeNormalize')    

    # create output node
    c = tree.nodes.new('CompositorNodeComposite')   
    c.use_alpha = True

    # Links
    l1 = links.new(rl.outputs['Depth'], n.inputs['Value']) # link Z to output
    l2 = links.new(n.outputs['Value'], c.inputs['Image'])

    # render
    render_picture(str(depth.joinpath(img_path)))

    # delete links and nodes
    links.remove(l1)
    links.remove(l2)
    tree.nodes.remove(rl)
    tree.nodes.remove(n)
    tree.nodes.remove(c)

def make_pictures(i):
    for name in names:
        if random.choice([True, False]):
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
                    bpy.ops.transform.translate(
                        value=(0, 0, diff), orient_type="GLOBAL"
                    )

            # first select object
            bpy.data.objects[name].select_set(state=True)
            # then
            bpy.ops.rigidbody.object_add(type="ACTIVE")
            bpy.ops.rigidbody.enabled = True
            bpy.context.scene.gravity = (0, 0, -9.81)
            bpy.context.scene.use_gravity = True
            bpy.data.objects[name].select_set(state=False)

    stage = stages[(i * len(stages)) // iterations]
    img_path = stage.joinpath(f"img{i}.jpeg")
    txt_path = stage.joinpath(f"img{i}.txt")

    render_picture(str(images.joinpath(img_path)))
    make_depth_map(img_path)

    count_obj = 0
    img = cv2.imread(str(images.joinpath(img_path)))

    with open(labels.joinpath(txt_path), "w") as f:
        for name in names:
            if name in bpy.data.objects and bpy.data.objects[name].location.z > 0.73:
                count_obj = count_obj + 1
                obj = bpy.data.objects[name]

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
                    f.write(
                        f"{names.index(name)} {yolo_x} {yolo_y} {yolo_w} {yolo_h}\n"
                    )

                    cv2.rectangle(
                        img,
                        (int(center_x - w / 2), int(center_y + h / 2)),
                        (int(center_x + w / 2), int(center_y - h / 2)),
                        (0, 0, 255),
                        2,
                    )
                    cv2.putText(
                        img,
                        name,
                        (int(center_x - w / 2), int(center_y - h / 2 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (0, 0, 255),
                        2,
                    )

    if count_obj > 0:
        cv2.imwrite(str(bboxes.joinpath(img_path)), img)
        return True
    else:
        os.remove(images.joinpath(img_path))
        os.remove(depth.joinpath(img_path))
        os.remove(labels.joinpath(txt_path))
        return False


def stop_playback(scene):
    if scene.frame_current == 30:
        bpy.ops.screen.animation_cancel(restore_frame=False)
        ok = True

def object_lowest_point(obj):
    matrix_w = obj.matrix_world
    vectors = [matrix_w @ vertex.co for vertex in obj.data.vertices]
    return min(vectors, key=lambda item: item.z)

def process(i):
    while not make_pictures(i):
        pass

    for name in names:
        if name in bpy.data.objects:
            bpy.data.objects[name].select_set(True)
            bpy.ops.object.delete()

start_from = 1
for i in tqdm(range(start_from, iterations)):
    process(i)
