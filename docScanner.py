
import numpy as np
import argparse
import cv2
import imutils
from meta import Group

import meta

original_image = None # make the original image global
work_queue = []

class Work:
    def __init__(self, a, b):
        self.a=a
        self.b=b

# the group pools are used by the worker threads (lists in CPython are
# inherently thread-safe because of the GIL)
# groups in the same pool will never be compared to eachother,
# (always compare an A to a B) this way we never need to worry about comparing
# two groups to each other more than once
# initially, put all groups in B, and move one to A before starting the workers
def main():
    print("running")
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required = True, help ="Path to the image to be scanned")
    user_args = vars(ap.parse_args())
    image = get_image(user_args["image"])
    edges = get_edges(image)
    group_pieces(edges)


def get_image(image_location):
    print(image_location)
    image = cv2.imread(image_location)
    image = imutils.resize(image, height = 500)
    global original_image
    original_image = image.copy()
    return image


def create_groups(edges, grayImage):
    group = []
    for e in edges:
        g = meta.Group(grayImage, e)
        group.append(g)
    return group

#O(n*m) yay!
def compare_and_merge(a, b):
    large_edge = None
    small_edge = None
    for i in range(len(a.contour)):
        e_a = a.edge(i)
        for j in range(len(b.contour)):
            e_b = b.edge(j)
            if e_a.len >= e_b.len:
                large_edge = e_a
                small_edge = e_b
            else:
                large_edge = e_b
                small_edge = e_a


def match_edges(long_edge, short_edge):
    long_start = 0.0
    for d in range(1000):
        d_norm = d / 1000.0
        large_kern = long_edge.get_kernel_at(d)
        small_kern = short_edge.get_kernel_at(1.0 - d)



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
    cv2.imshow("filled", eroded)

    contours, hierarchy = cv2.findContours(eroded.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    print("Number of contours found =" + str(len(contours)))
    print("Step 2: find Contours of paper")
    cv2.drawContours(image, contours, -1, (0,255,0),2)
    cv2.imshow("Outline", image)

    return contours

def group_pieces(edges):
    print("Step 3: Grouping")
    group_pool_A = create_groups(edges, original_image)

    group_pool_B = []
    #reverse group, larger blocks are usually at the end
    group_pool_A.reverse()
    #simplify, remove groups that are entirely within other groups
    trash = []
    for i,g in enumerate(group_pool_A):
        for h in group_pool_A[i+1:]:
            if h not in trash and g.envelope(h):
                trash.append(h)

    for g in group_pool_A:
        if g not in trash:
            group_pool_B.append(g)

    group_pool_A = []
    #TODO: simplify each group further by making the edges "square", using the OBB 
    #to remove points that aren't near the straight edge
    print("Possible groups ="+str(len(group_pool_B)))

    #at this point we have our two groups, we can unleash the worker threads on 
    #them and find the matching edges

    # this is the entire compare and merge loop
    while group_pool_B:
        in_hand = group_pool_B.pop(0)
        for b in group_pool_B:
            if compare_and_merge(in_hand, b):
                group_pool_B.insert(0, in_hand)

        group_pool_A.append(in_hand)

    group_pool_A[3].display()

    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
