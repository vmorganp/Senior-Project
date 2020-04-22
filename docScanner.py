import math

import numpy as np
import argparse
import cv2
import imutils
import skimage.measure

import meta

original_image = None # make the original image global
work_queue = []

class Task:
    def __init__(self, a, b):
        self.a=a
        self.b=b
        result = None

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
    edges = meta.get_edges(image)
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
    for i,e in enumerate(edges):
        g = meta.Group(grayImage, e)
        g.id = str(i)
        group.append(g)
    return group


# this has a ridiculous time complexity...
# uses Structural Similarity Index
def compare_and_merge_segments(a, b):

    for a_s in a.segments[:2]:
        a_img = a_s.get_aligned_subimage()
        a_len = max(int(a_s.len), 3)

        if a_img.shape[0] < 3 or a_img.shape[1] < 3:
            continue

        for b_s in b.segments[:2]:

            b_img = b_s.get_aligned_subimage()
            b_len = max(int(b_s.len), 3)

            min_x = min(a_img.shape[1], b_img.shape[1])

            if b_img.shape[0] < 3 or b_img.shape[1] < 3:
                continue

            #print(""+str(a_len)+" ? "+str(b_len))

            try:
                #this is translating a
                if(a_len < b_len):
                    for i in range(int(b_len-a_len)+1):
                        #print("a trans " + str(a_len) + "," + str(a_img.shape[1]))
                        #print("" + str(a_img.shape[0]) + "," + str(a_img.shape[1]))
                        #print("" + str(b_img.shape[0]) + "," + str(b_img.shape[1]))
                        (score, diff) = skimage.metrics.structural_similarity(a_img[0:a_img.shape[0], 0:min_x], b_img[i:a_len+i, 0:min_x],
                                                                              win_size=3, full=True, multichannel=True)
                        if score > 0.8:  # arbitrary
                            print("FOUND MATCH")
                            return a.merge(b, a_s.theta(b_s), b_s.pos)
                else:
                    for i in range(int(a_len-b_len)):
                        #print("b trans "+str(i)+","+str(b_len+i)+":0,"+str(a_img.shape[1]))
                        #print("" + str(a_img.shape[0]) + "," + str(a_img.shape[1]))
                        #print("" + str(b_img.shape[0]) + "," + str(b_img.shape[1]))
                        (score, diff) = skimage.metrics.structural_similarity(b_img[0:b_img.shape[0], 0:min_x], a_img[i:b_len+i, 0:min_x],
                                                                 win_size=3, full=True, multichannel=True)
                        if score > 0.8:  # arbitrary
                            print("FOUND MATCH")
                            return a.merge(b, a_s.theta(b_s), b_s.pos)
            except ValueError as ve:
                print(ve);
                print(str(a_len)+" " + str(a_img.shape[0]) + "," + str(a_img.shape[1]))
                print(str(b_len)+" " + str(b_img.shape[0]) + "," + str(b_img.shape[1]))
    print("no match")
    return None


def compare_and_merge_edges(a, b):

    for a_s in a.edges:
        a_img = a_s.get_aligned_subimage()
        a_len = max(int(a_img.shape[0]), 3)

        if a_img.shape[0] < 3 or a_img.shape[1] < 3:
            continue

        for b_s in b.edges:
            b_img = b_s.get_aligned_subimage()
            b_len = max(int(b_img.shape[0]), 3)

            min_x = min(a_img.shape[1], b_img.shape[1])

            if b_img.shape[0] < 3 or b_img.shape[1] < 3:
                continue
            try:
                #this is translating a
                if(a_len <= b_len):
                    for i in range(int(b_len-a_len)+1):
                        (score, diff) = skimage.metrics.structural_similarity(a_img[0:a_img.shape[0], 0:min_x], b_img[i:a_len+i, 0:min_x],
                                                                              win_size=3, full=True, multichannel=True)
                        if score > 0.8:  # arbitrary
                            print("FOUND EDGE MATCH A")
                            a_pos = np.array([a_s.segments[0].pos[0][0]+i, a_s.segments[0].pos[0][1]])
                            return a.merge(b, math.radians(90+a_s.group.obb[2]), a_pos-b_s.segments[0].pos)
                else:
                    for i in range(int(a_len-b_len)):
                        (score, diff) = skimage.metrics.structural_similarity(b_img[0:b_img.shape[0], 0:min_x], a_img[i:b_len+i, 0:min_x],
                                                                 win_size=3, full=True, multichannel=True)
                        if score > 0.8:  # arbitrary
                            print("FOUND EDGE MATCH B")
                            a_pos = a_s.segments[0].pos
                            return a.merge(b, math.radians(90+b_s.group.obb[2]), a_pos - np.array([b_s.segments[0].pos[0][0]+i, b_s.segments[0].pos[0][1]]))
            except ValueError as ve:
                print(ve)
                print(str(a_len)+" " + str(a_img.shape[0]) + "," + str(a_img.shape[1]))
                print(str(b_len)+" " + str(b_img.shape[0]) + "," + str(b_img.shape[1]))
    print("no match")
    return None

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
            if h not in trash and (g.envelope(h) or h.area()<10000):
                trash.append(h)

    for g in group_pool_A:
        if g not in trash:
            group_pool_B.append(g)

    group_pool_A = []
    print("Possible groups = "+str(len(group_pool_B)))
    for g in group_pool_B:
        g.display()

    #at this point we have our two groups, we can unleash the worker threads on 
    #them and find the matching edges

    # this is the entire compare and merge loop
    in_hand = group_pool_B.pop(0)
    while group_pool_B:
        merged = None

        for b in group_pool_B:
            #a = compare_and_merge_segments(in_hand, b)
            a = compare_and_merge_edges(in_hand, b)
            if a is not None:
                in_hand = a
                merged = b
                break

        in_hand.display()
        cv2.waitKey(0)
        if merged is not None:
            group_pool_B.remove(merged)
        else:
            group_pool_A.append(in_hand)
            in_hand = group_pool_B.pop(0)

    group_pool_A.append(in_hand)

    for g in group_pool_A:
        g.display()
        cv2.waitKey(0)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
