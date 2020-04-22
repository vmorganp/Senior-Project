# The main python file, run from the commandline
import argparse
import cv2
import numpy as np
import imutils
import skimage
import meta

work_pool = []
finish_pool = []

def get_edges(image):
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
    cv2.drawContours(image, contours, -1, (0,255,0),2)
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
    a_p = imutils.convenience.rotate_bound(a.im, 90 + a.obb[2])
    b_p = imutils.convenience.rotate_bound(b.im, 90 + b.obb[2])

    a_p = a_p[int(a.obb[0][0]):int(a.obb[1][0]), int(a.obb[0][0]):int(a.obb[1][0])].copy()
    b_p = b_p[int(b.obb[0][0]):int(b.obb[1][0]), int(b.obb[0][0]):int(b.obb[1][0])].copy()

    if a_p.shape[0] < 3 or a_p.shape[1] < 3 or b_p.shape[0] < 3 or b_p.shape[1]:
        return None

    cv2.imshow(a.id + "'", a_p)
    cv2.imshow(b.id + "'", b_p)
    cv2.waitKey(0)

    a_len = int(a_p.shape[0])
    b_len = int(b_p.shape[0])
    min_len = min(a_len, b_len)

    sml_img = None
    big_img = None
    sml_grp = None
    big_grp = None

    try:
        if a_len <= b_len:
            sml_img, sml_grp = (a_p, a)
            big_img, big_grp = (b_p, b)
        else:
            sml_img, sml_grp = (b_p, b)
            big_img, big_grp = (a_p, a)

        for i in range(min_len + 1):
            # small image on left, large on right
            (score, diff) = skimage.metrics.structural_similarity(sml_img[0:sml_img.shape[0], sml_img.shape[1] - 3:sml_img.shape[1]],
                                                                  big_img[i:min_len + i, 0:3],
                                                                  win_size=3, full=True, multichannel=True)
            if score > 0.8:  # arbitrary
                print("FOUND EDGE MATCH SMALL/LARGE")
                a_pos = np.array([i, 0])
                return a.merge(b, 0.0, a_pos)

            # small image on right, large on left


    except ValueError as ve:
        print(ve)
        print(str(a_len)+" " + str(a_p.shape[0]) + "," + str(a_p.shape[1]))
        print(str(b_len)+" " + str(b_p.shape[0]) + "," + str(b_p.shape[1]))
    print("no match")
    return None

# Pre-cuts an image and adds it to the processing pool
def add_image(img):
    image = cv2.imread(img)

    contours = get_edges(image)

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

## MAIN ##
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True, help="Path to the image to be scanned")
    ap.add_argument("-o", "--output", required=False, help="Filename of output PDF")

    args = vars(ap.parse_args())
    add_image(args["image"])

    process_pool()

    for g in finish_pool:
        g.display()
        cv2.waitKey(0)