
import numpy as np
from numpy import linalg
import cv2
import math
import imutils


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


class Segment:
    def __init__(self, g, pt_a, pt_b):
        self.group = g
        self.edge = None
        self.pos = pt_a
        vector = pt_b - pt_a
        self.len = linalg.norm(vector)
        self.vec = np.array([vector[0][0]/self.len, vector[0][1]/self.len])
        self.perp = np.array([self.vec[1], self.vec[0]])

    def get_kernel_at(self, d):
        # move along the edge vector by d percentage of self.len
        # then move into the enclosed area by self.perp
        img_loc = self.vec*d*self.len+self.pos + self.perp

        min_x = img_loc[0]-1
        max_x = img_loc[0]+1

        min_y = img_loc[1] - 1
        max_y = img_loc[1] + 1

        return self.group.im[min_y:max_y, min_x:max_x].copy()

    # This does the job, but requires us to rotate the entire image for every
    # segment...
    def get_aligned_subimage(self):
        theta = math.acos((self.vec[0]*0.0+self.vec[1]*1.0))
        im = imutils.convenience.rotate_bound(self.group.im, math.degrees(-theta))

        min_x = int(self.pos[0][0])
        max_x = int(self.pos[0][0] + 8)
        if self.vec[1] < 0:
            min_x = int(self.pos[0][0] - 8)
            max_x = int(self.pos[0][0])

        min_y = int(self.pos[0][1])
        max_y = int(self.pos[0][1] + max(self.len, 3))

        img = im[min_y:max_y, min_x:max_x].copy()
        if(img.shape[0]<3):
            min_y = min_y-1
        if (img.shape[1] < 3):
            min_x=min_x-1
        img = im[min_y:max_y, min_x:max_x].copy()
        return img

    # dot product of two segments
    def dot(self, b):
        return self.vec[0]*b.vec[0]+self.vec[1]*b.vec[1]

    # theta is the angle between two segments
    def theta(self, b):
        #return math.acos(self.dot(b)/(self.len*b.len))
        return math.acos(self.dot(b)) #vectors are both normalized, so len isn't needed?


class Edge:
    def __init__(self, g, s):
        self.segments = [s]
        self.group = g
        self.cardinal = None # the longest segment on the edge

        self._find_cardinal()

    def _find_cardinal(self):
        self.cardinal = self.segments[0]
        for s in self.segments[1:]:
            if self.cardinal.len < s.len:
                self.cardinal = s

    def add_segment(self, s):
        s.edge = self
        if s.len > self.cardinal.len:
            self.cardinal = s


class Group:
    def __init__(self, i, e):
        self.contour = e[:]
        self.segments = []
        self.edges = []
        self.im = i
        self.obb = cv2.minAreaRect(self.contour)
        self.aabb = np.zeros((2, 2), np.int32)
        self.aabb[0][0] = self.im.shape[0]
        self.aabb[0][1] = self.im.shape[1]

        # first, find the aabb for the group of edges
        for e in self.contour:
            # x min & max
            if e[0][0] < self.aabb[0][0]:
                self.aabb[0][0] = e[0][0]
            elif e[0][0] > self.aabb[1][0]:
                self.aabb[1][0] = e[0][0]
            # y min & max
            if e[0][1] < self.aabb[0][1]:
                self.aabb[0][1] = e[0][1]
            elif e[0][1] > self.aabb[1][1]:
                self.aabb[1][1] = e[0][1]

        #second, use the contour to make segments
        for idx in range(len(self.contour)):
            next_idx = (idx + 1) % len(self.contour)
            s = Segment(self, self.contour[idx], self.contour[next_idx])
            self.segments.append(s)

        #third, find "edges" of the group
        self.edges.append(Edge(self, self.segments[0]))
        for s in self.segments[1:]:
            for e in self.edges:
                if e.cardinal.dot(s)>0.7:   #arbitrary
                    e.add_segment(s)
                    break
            else:
                e = Edge(self, s)
                self.edges.append(e)

    def display(self):
        box = cv2.boxPoints(self.obb)  # cv2.boxPoints(rect) for OpenCV 3.x
        box = np.int0(box)
        bb = np.zeros((4, 2), np.int32)
        bb[0] = self.aabb[0]
        bb[1] = (self.aabb[0][0], self.aabb[1][1])
        bb[2] = self.aabb[1]
        bb[3] = (self.aabb[1][0], self.aabb[0][1])
        cv2.drawContours(self.im, self.contour, -1, (0, 255, 255), 1)
        cv2.polylines(self.im, [bb], True, (255, 0, 0), 1)
        cv2.drawContours(self.im, [box], 0, (0, 0, 255), 1)

        crop_img = self.im[self.aabb[0][1]:self.aabb[1][1], self.aabb[0][0]:self.aabb[1][0]].copy()

        cv2.imshow("Crop", crop_img)

        cv2.imshow("Group", self.im)

    def envelope(self, b):
        # FIXME: use OBB
        return b.aabb[0][0] >= self.aabb[0][0] and b.aabb[0][1] >= self.aabb[0][1] and b.aabb[1][0] <= self.aabb[1][
            0] and b.aabb[1][1] <= self.aabb[1][1]

    def overlap(self, b):
        # overlapping groups should be merged
        return False

    def merge(self, b, angle, offset):
        a_img = self.im[self.aabb[0][1]:self.aabb[1][1], self.aabb[0][0]:self.aabb[1][0]].copy()
        b_img = b.im[b.aabb[0][1]:b.aabb[1][1], b.aabb[0][0]:b.aabb[1][0]].copy()
        im = imutils.convenience.rotate_bound(b_img, math.degrees(-angle))
        h1, w1 = a_img.shape[:2]
        h2, w2 = im.shape[:2]

        # create empty matrix
        vis = np.zeros((max(h1, h2), w1 + w2, 3), np.uint8)

        print("merge with theta "+str(math.degrees(-angle))+ " and offset "+str(offset))

        # combine 2 images
        vis[:h1, :w1, :3] = a_img
        vis[:h2, w1:w1 + w2, :3] = im
        return Group(vis, get_edges(vis)[0])

    def area(self):
        cv2.contourArea(self.contour)


__all__ = ["Group", "Edge", "Segment"]