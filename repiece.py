# The main python file, run from the commandline
import argparse
import os
import boto3


import cv2
import numpy as np
import skimage.measure
import meta

work_pool = []
finish_pool = []


def get_edgess(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray,(5,5),0)
    edged = cv2.Canny(blurred, 75, 200)

    # print("STEP 1: EDGE DETECTION")
    # cv2.imshow("Orig", image)
    # cv2.imshow("Edged", edged)
    # cv2.waitKey(5000)
    # cv2.destroyAllWindows()
    contours, hierarchy = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    #get convex hulls of each of the contours
    eroded = np.zeros((image.shape[0], image.shape[1]), np.uint8)
    kernel = np.ones((5,5), np.uint8)

    for c in contours:
        #hull = cv2.convexHull(c, False)
        hull = c
        cv2.fillPoly(eroded, pts=[hull], color=(255,))

    # img_erosion = cv2.erode(img, kernel, iterations=1)
    eroded = cv2.dilate(eroded, kernel, iterations=1)
    eroded = cv2.erode(eroded, kernel, iterations=1)
    #cv2.imshow("filled", eroded)

    contours, hierarchy = cv2.findContours(eroded.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    print("Number of contours found =" + str(len(contours)))
    print("Step 2: find Contours of paper")
    # cv2.drawContours(image, contours, -1, (0,255,0),2)
    #cv2.imshow("Outline", image)

    return contours


def create_groups(edges, grayImage):
    group = []
    for i,e in enumerate(edges):
        g = meta.Group(grayImage, e)
        g.id = str(i)
        group.append(g)
    return group


def fill_work_pool(groups):
    groups.reverse()
    # simplify, remove groups that are entirely within other groups
    trash = []
    for i, g in enumerate(groups):
        for h in groups[i + 1:]:
            if h not in trash and (g.envelope(h) or h.area() < 10000):
                trash.append(h)

    for g in groups:
        if g not in trash:
            work_pool.append(g)

def compare_and_merge(a, b):

    #test slice width
    test_width=5

    a_p = a.get_obb_subimage()
    b_p = b.get_obb_subimage()

    if a_p.shape[0] < 3 or a_p.shape[1] < 3 or b_p.shape[0] < 3 or b_p.shape[1] < 3:
        return None

    #cv2.imshow(a.id + "'", a_p)
    #cv2.imshow(b.id + "'", b_p)
    #cv2.waitKey(0)

    a_len = int(a_p.shape[0])
    b_len = int(b_p.shape[0])
    min_len = min(a_len, b_len)
    idiff = 0

    sml_img = None
    big_img = None
    sml_grp = None
    big_grp = None

    try:
        if a_len <= b_len:
            sml_img, sml_grp = (a_p, a)
            big_img, big_grp = (b_p, b)
            idiff = b_len - a_len
        else:
            sml_img, sml_grp = (b_p, b)
            big_img, big_grp = (a_p, a)
            idiff = a_len - b_len

        for i in range(idiff + 1):
            # small image on left, large on right
            (score, diff) = skimage.metrics.structural_similarity(
                sml_img[0:sml_img.shape[0], sml_img.shape[1] - test_width:sml_img.shape[1]],
                big_img[i:min_len + i, 0:test_width],
                win_size=3, full=True, multichannel=True)

            if score > 0.2:  # arbitrary
                print("FOUND EDGE MATCH SMALL/LARGE ("+sml_grp.id+"+"+big_grp.id+")")
                a_pos = np.array([i, 0])
                return sml_grp.merge(big_grp, 0.0, [a_pos])

            # small image on right, large on left
            (score, diff) = skimage.metrics.structural_similarity(
                sml_img[0:sml_img.shape[0], 0:test_width],
                big_img[i:min_len + i, big_img.shape[1] - test_width:big_img.shape[1]],
                win_size=3, full=True, multichannel=True)

            if score > 0.2:  # arbitrary
                print("FOUND EDGE MATCH LARGE/SMALL ("+big_grp.id+"+"+sml_grp.id+")")
                a_pos = np.array([i, 0])
                return big_grp.merge(sml_grp, 0.0, [a_pos])

    except ValueError as ve:
        print(ve)
        print(str(a_len)+" " + str(sml_img.shape[0]) + "," + str(sml_img.shape[1]))
        print(str(b_len)+" " + str(big_img.shape[0]) + "," + str(big_img.shape[1]))
    print(a.id+"+"+b.id+" = no match")
    return None

# Pre-cuts an image and adds it to the processing pool
def add_image(img):
    image = cv2.imread(img)

    contours = meta.get_edges(image)

    g = create_groups(contours, image)

    fill_work_pool(g)

def process_pool():

    while work_pool:
        in_hand = work_pool.pop(0)
        work_pool_copy = work_pool[:]

        while work_pool_copy:
            b = work_pool_copy.pop(0)
            # a = compare_and_merge_segments(in_hand, b)
            a = compare_and_merge(in_hand, b)
            if a is not None:
                in_hand = a
                work_pool.remove(b)

        finish_pool.append(in_hand)


def main():
    if os.environ.get('file'):
        file = os.environ['file']
        s3 = boto3.client('s3')
        s3.download_file('repiece-master', file, '/home/image.jpg')
        add_image('/home/image.jpg')
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument("-i", "--image", required=True, help="Path to the image to be scanned")
        ap.add_argument("-o", "--output", required=False, help="Filename of output PDF")
        args = vars(ap.parse_args())
        add_image(args["image"])
    

    process_pool()

    cv2.imwrite("output.png", finish_pool[0].im)

    if os.environ.get('file'):
        output_location = os.envion['file'].replace('uploads','outputs')
        s3_client = boto3.client('s3')
        response = s3_client.upload_file('output.png', 'repiece-master', output_location)

## MAIN ##
if __name__ == "__main__":
    main()