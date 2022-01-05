import random
import shutil
import cv2
import os

import bpy

from bpy_extras.object_utils import world_to_camera_view

names = ['X1-Y1-Z2', 'X1-Y2-Z1', 'X1-Y2-Z2', 'X1-Y2-Z2-CHAMFER', 'X1-Y2-Z2-TWINFILLET',
         'X1-Y3-Z2', 'X1-Y3-Z2-FILLET', 'X1-Y4-Z1', 'X1-Y4-Z2', 'X2-Y2-Z2', 'X2-Y2-Z2-FILLET']
ok = False


def take_pic(i):
    bpy.context.scene.render.filepath = 'images/img'+str(i)+'.jpeg'
    bpy.context.scene.render.resolution_x = 720  # perhaps set resolution in code
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.render.image_settings.file_format = 'JPEG'
    bpy.ops.render.render(write_still=1)
    shutil.copyfile(bpy.context.scene.render.filepath,
                    bpy.context.scene.render.filepath.replace("images", "bboxes"))

    count_obj = 0
    # read image
    img = cv2.imread(bpy.context.scene.render.filepath.replace(
        "images", "bboxes"))
    with open("labels/img"+str(i)+".txt", "w") as f:
        for name in names:
            # se esiste ed è nel campo visivo
            if name in bpy.data.objects and bpy.data.objects[name].location.z > 0.73:
                count_obj = count_obj + 1
                obj = bpy.data.objects[name]
                #bbox = bpy.data.objects[name].bound_box
                min_x = 1000.0
                min_y = 1000.0
                max_x = 0.0
                max_y = 0.0
                scene = bpy.context.scene

                # HERE I NEED TO GO FROM WORLD COORDINATES TO CAMERA PIXEL COORDINATES
                # needed to rescale 2d coordinates
                render_scale = scene.render.resolution_percentage / 100
                res_x = scene.render.resolution_x * render_scale
                res_y = scene.render.resolution_y * render_scale

                cam = bpy.data.objects['Camera']

                verts = [vert.co for vert in obj.data.vertices]
                for i in range(len(verts)):
                    verts[i] = obj.matrix_world @ verts[i]

                coords_2d = [world_to_camera_view(
                    scene, cam, coord) for coord in verts]

                def rnd(i): return round(i)

                X_max = max(coords_2d[0])
                Y_max = max(coords_2d[1])
                X_min = min(coords_2d[0])
                Y_min = min(coords_2d[1])

                verts_2d = []
                for x, y, distance_to_lens in coords_2d:
                    verts_2d.append(tuple((rnd(res_x*x), rnd(res_y-res_y*y))))

                Y_max = max(verts_2d, key=lambda i: i[1])[1]
                X_max = max(verts_2d, key=lambda i: i[0])[0]
                Y_min = min(verts_2d, key=lambda i: i[1])[1]
                X_min = min(verts_2d, key=lambda i: i[0])[0]

                center_x = (X_max+X_min)/2
                center_y = (Y_max+Y_min)/2
                w = X_max - X_min
                h = Y_max - Y_min
                # go to percentage, 0-1 range values
                yolo_x = center_x/1024
                yolo_y = center_y/1024
                yolo_w = w/1024
                yolo_h = h/1024
                if yolo_x+yolo_w/2 <= 1 and yolo_x-yolo_w/2 >= 0 and yolo_y+yolo_h/2 <= 1 and yolo_y-yolo_h/2 >= 0:
                    f.write(str(names.index(name)) + " " + str(yolo_x) + " " +
                            str(yolo_y) + " " + str(yolo_w) + " " + str(yolo_h) + "\n")
                    print("x,y,w,h:", center_x, center_y, w, h)

                    # get contours
                    cv2.rectangle(img, (int(center_x-w/2), int(center_y+h/2)),
                                  (int(center_x+w/2), int(center_y-h/2)), (0, 0, 255), 2)
                    cv2.putText(img, name, (int(center_x-w/2), int(center_y-h/2-10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    # save resulting image
    if(count_obj > 0):
        cv2.imwrite(bpy.context.scene.render.filepath.replace(
            "images", "bboxes"), img)
        return True
    else:
        os.remove(bpy.context.scene.render.filepath)
        os.remove(bpy.context.scene.render.filepath.replace(
            "images", "bboxes"))
        os.remove("labels/img"+str(i)+".txt")
        return False  # no img saved because no objects are on the view


def stop_playback(scene):
    if scene.frame_current == 30:
        bpy.ops.screen.animation_cancel(restore_frame=False)
        ok = True


def object_lowest_point(obj):
    matrix_w = obj.matrix_world
    vectors = [matrix_w @ vertex.co for vertex in obj.data.vertices]
    return min(vectors, key=lambda item: item[2])[2]


def object_lowest_point(obj):
    matrix_w = obj.matrix_world
    vectors = [matrix_w @ vertex.co for vertex in obj.data.vertices]
    return min(vectors, key=lambda item: item.z)


i = 0
while i < 5000:
    #bpy.scene.gravity = (0,0,9.8)
    ok = False
    for name in names:
        if random.choice([True, False]):

            x = random.uniform(-0.32, 0.32)  # table x(-0.375,0.375)
            y = random.uniform(-0.32, 0.32)  # table y(-0.375,0.375)
            z = 0.74  # table z 0.73
            bpy.ops.import_mesh.stl(filepath="stl/"+name+".stl")
            # bpy.ops.transform.resize(value=(0.001, 0.001, 0.001)) no longer required, now stl dimensions are real
            bpy.ops.transform.translate(value=(x, y, z), orient_type='GLOBAL')

            ob = bpy.data.objects[name]
            material = bpy.data.materials.new(
                name="randcolor"+str(random.randint(0, 6000)))
            material.diffuse_color = [random.uniform(0, 1), random.uniform(
                0, 1), random.uniform(0, 1), 1]  # some rose color
            ob.active_material = material

            for window in bpy.context.window_manager.windows:
                screen = window.screen

                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        override = {'window': window,
                                    'screen': screen, 'area': area}
                        bpy.ops.screen.screen_full_area(override)
                        break

            m = ob.modifiers.new("Solidify", type='SOLIDIFY')
            m.thickness = 0.00001
            #m.use_even_offset = True
            #m.use_quality_normals = True
            #m.use_rim = True
            #ob.modifier_apply(apply_as='DATA', modifier=m.name)

            if random.choice([True, False]):
                # to rotate or to not rotate: that is the question
                original_type = bpy.context.area.type
                bpy.context.area.type = "VIEW_3D"
                bpy.ops.transform.rotate(
                    value=random.uniform(0, 6.28), orient_axis='X')
                bpy.ops.transform.rotate(
                    value=random.uniform(0, 6.28), orient_axis='Y')
                bpy.ops.transform.rotate(
                    value=random.uniform(0, 6.28), orient_axis='Z')
                bpy.context.area.type = original_type

                """new_z = z-bpy.data.objects[name].location.z
                if new_z < 0:
                    new_z = 0"""
                #new_z = z +bpy.data.objects[name].dimensions.z/2
                #diff_y = y-bpy.data.objects[name].location.y
                #diff_x = x-bpy.data.objects[name].location.x
                #bpy.ops.transform.translate(value=(x,y,z-bpy.data.objects[name].dimensions.z), orient_type='GLOBAL')

                #minimum_z_point = bpy.data.objects[name].location.z - (bpy.data.objects[name].dimensions.z/2)*1.5
                # print(object_lowest_point(bpy.data.objects[name]))
                diff = z-object_lowest_point(bpy.data.objects[name]).z
                if diff > 0:
                    bpy.ops.transform.translate(
                        value=(0, 0, diff), orient_type='GLOBAL')

            # first select object
            bpy.data.objects[name].select_set(state=True)
            # then
            bpy.ops.rigidbody.object_add(type='ACTIVE')
            bpy.ops.rigidbody.enabled = True
            bpy.context.scene.gravity = (0, 0, -9.81)
            bpy.context.scene.use_gravity = True
            bpy.data.objects[name].select_set(state=False)

    if take_pic(i) == True:
        i = i+1

    # add one of these functions to frame_change_pre handler:
    # bpy.app.handlers.frame_change_pre.append(stop_playback)
    # start animation
    # bpy.ops.screen.animation_play()
    # while True:
     #   if ok:
      #      take_pic(i)
       #     break

    for name in names:
        if name in bpy.data.objects:
            bpy.data.objects[name].select_set(True)
            bpy.ops.object.delete()
