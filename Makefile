color:
	blender world.blend --python blender.py > /dev/null

depth:
	blender world.blend --python depth.py > /dev/null

.PHONY: color depth