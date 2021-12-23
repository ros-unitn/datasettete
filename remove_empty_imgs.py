import cv2
import os
from shutil import copyfile


def contains_red(img):
    # Convert the image to HSV colour space
    #img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # print(img)
    # Define a range for red color
    #lower_red = np.array([0,0,254])
    #upper_red = np.array([0,0,255])
    #mask = cv2.inRange(img, lower_red, upper_red)

    for row in img:
        for pixel in row:
            if pixel[2] == 255:
                return True

    # Determine if the color exists on the image
    return False


files = [f for f in os.listdir("images_bbox") if os.path.isfile(
    os.path.join("images_bbox", f))]
for f in files:
    # print(f)
    img = cv2.imread("images_bbox/"+f)
    if(contains_red(img)):
        copyfile("images_bbox/"+f, "images_bbox_new/"+f)
        copyfile("images/"+f, "images_new/"+f)
        copyfile("labels/"+f.replace(".jpeg", ".txt"),
                 "labels_new/"+f.replace(".jpeg", ".txt"))
        print("1 copied")
        # sleep(0.5)
