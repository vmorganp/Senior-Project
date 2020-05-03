
import numpy as np
from numpy import linalg
import cv2
import math
import random
import imutils


def _rotate_point(p, angle):
    c, s = np.cos(math.radians(angle)), np.sin(math.radians(angle))

    j = np.array(((c, s), (-s, c)))
    return np.dot(j, p)


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
    #print("Step 2: find Contours of paper")
    #cv2.drawContours(image, contours, -1, (0,255,0),2)
    #cv2.imshow("Outline", image)

    return contours


class Segment:
    def __init__(self, g, pt_a, pt_b):
        self.group = g
        self.edge = None
        self.pos = pt_a
        vector = pt_b - pt_a
        self.len = linalg.norm(vector)
        self.vec = np.array([vector[0][0]/self.len, vector[0][1]/self.len])
        self.perp = np.array([self.vec[1], -self.vec[0]])

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
        self.aggregate_vec = np.array([0,0])
        self.len=0

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

        pt_a = self.segments[0].pos
        pt_b = self.segments[-1].pos + self.segments[-1].vec * self.segments[-1].len

        vector = pt_b - pt_a
        self.len = linalg.norm(vector)
        self.aggregate_vec = np.array([vector[0][0] / self.len, vector[0][1] / self.len])

    def get_aligned_subimage(self):

        # make an overall line for the edge
        pt_a = self.segments[0].pos
        pt_b = self.segments[-1].pos+self.segments[-1].vec*self.segments[-1].len

        vector = pt_b - pt_a
        len = linalg.norm(vector)
        vec = np.array([vector[0][0]/len, vector[0][1]/len])

        theta = math.acos((vec[0]*0.0+vec[1]*1.0))
        im = imutils.convenience.rotate_bound(self.group.im, math.degrees(-theta))

        min_x = int(self.segments[0].pos[0][0])
        max_x = int(self.segments[0].pos[0][0] + 8)
        if self.segments[0].vec[1] < 0:
            min_x = int(self.segments[0].pos[0][0] - 8)
            max_x = int(self.segments[0].pos[0][0])

        min_y = int(self.segments[0].pos[0][1])
        max_y = int(self.segments[0].pos[0][1] + max(len, 3))

        img = im[min_y:max_y, min_x:max_x].copy()
        if img.shape[0]<3:
            min_y = min_y-1
        if img.shape[1] < 3:
            min_x = min_x-1
        img = im[min_y:max_y, min_x:max_x].copy()
        return img

    # dot product of two edges' aggregate vector
    def dot(self, b):
        print(""+str(self.aggregate_vec[0])+"*"+str(b.aggregate_vec[0])+"+"+str(self.aggregate_vec[1])+"*"+str(b.aggregate_vec[1]))
        return self.aggregate_vec[0]*b.aggregate_vec[0]+self.aggregate_vec[1]*b.aggregate_vec[1]

    # theta is the angle between two segments
    def theta(self, b):
        #return math.acos(self.dot(b)/(self.len*b.len))
        return math.acos(self.dot(b)) #vectors are both normalized, so len isn't needed?

class Group:
    def __init__(self, i, e, bound_is_extents=False):
        self.contour = e[:]
        self.segments = []
        self.edges = []
        self.im = i
        self.obb = cv2.minAreaRect(self.contour)
        self.aabb = np.zeros((2, 2), np.int32)
        self.aabb[0][0] = self.im.shape[1]
        self.aabb[0][1] = self.im.shape[0]
        self.id = str(random.randint(1,100000))

        # first, find the aabb for the group of edges
        if not bound_is_extents:
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
        else:
            self.aabb[0][0] = 0
            self.aabb[0][1] = 0
            self.aabb[1][0] = self.im.shape[1]
            self.aabb[1][1] = self.im.shape[0]

            #second, use the contour to make segments
        for idx in range(len(self.contour)):
            next_idx = (idx + 1) % len(self.contour)
            s = Segment(self, self.contour[idx], self.contour[next_idx])
            self.segments.append(s)

        self.segments = sorted(self.segments, key=lambda x: x.len, reverse=True)

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

    def get_obb_subimage(self):
        box = cv2.boxPoints(self.obb)
        angle = -(90+self.obb[2])
        i = imutils.convenience.rotate_bound(self.im, angle)

        p1 = _rotate_point(box[0], self.obb[2])
        p2 = _rotate_point(box[2], self.obb[2])

        bmin = np.array((min(p1[0], p2[0]), min(p1[1], p2[1])))
        bmax = np.array((max(p1[0], p2[0]), max(p1[1], p2[1])))

        #return i
        return i[int(bmin[0]):int(bmax[0]), int(bmin[1]):int(bmax[1])].copy()
        #return self.im[self.aabb[0][1]:self.aabb[1][1], self.aabb[0][0]:self.aabb[1][0]].copy()

    def display(self, name=None):
        box = cv2.boxPoints(self.obb)  # cv2.boxPoints(rect) for OpenCV 3.x
        box = np.int0(box)
        bb = np.zeros((4, 2), np.int32)
        bb[0] = self.aabb[0]
        bb[1] = (self.aabb[0][0], self.aabb[1][1])
        bb[2] = self.aabb[1]
        bb[3] = (self.aabb[1][0], self.aabb[0][1])
        im = self.im.copy()
        cv2.drawContours(im, self.contour, -1, (0, 255, 255), 1)
        cv2.polylines(im, [bb], True, (255, 0, 0), 1)
        cv2.drawContours(im, [box], 0, (0, 0, 255), 1)

        #crop_img = im[self.aabb[0][1]:self.aabb[1][1], self.aabb[0][0]:self.aabb[1][0]].copy()
        #cv2.imshow("Crop "+str(self.id), crop_img)

        if name is not None:
            cv2.imshow(name, im)
            print("display "+name)
        else:
            cv2.imshow("Group "+str(self.id), im)
            print("display "+"Group "+str(self.id))

    def envelope(self, b):
        # FIXME: use OBB
        return b.aabb[0][0] >= self.aabb[0][0] and b.aabb[0][1] >= self.aabb[0][1] and b.aabb[1][0] <= self.aabb[1][
            0] and b.aabb[1][1] <= self.aabb[1][1]

    def overlap(self, b):
        # overlapping groups should be merged
        return False

    def merge(self, b, angle, offset):
        oy, ox = offset[0]
        a_img = self.im[self.aabb[0][1]:self.aabb[1][1], self.aabb[0][0]:self.aabb[1][0]].copy()
        b_img = b.im[b.aabb[0][1]:b.aabb[1][1], b.aabb[0][0]:b.aabb[1][0]].copy()
        im = imutils.convenience.rotate_bound(b_img, math.degrees(-angle))
        h1, w1 = a_img.shape[:2]
        h2, w2 = im.shape[:2]

        ox = int(ox)
        oy = int(oy)
        tw = ox+w2+w1
        th = max(oy+h2,h1)

        print("merge with theta " + str(math.degrees(-angle)) + " and offset " + str(ox)+","+str(oy))
        print("a dims "+str(w1)+","+str(h1))
        print("b dims " + str(w2) + "," + str(h2))
        print("total dims "+str(tw)+","+str(th))

        # create empty matrix
        vis = np.zeros((th, tw, 3), np.uint8)

        iy = abs(oy)

        # combine 2 images
        vis[:h1, :w1, :3] = a_img
        print("merged a")
        vis[oy:h2+oy, ox+w1:tw, :3] = im[:h2,:w2]
        print("merged b")
        return Group(vis, get_edges(vis)[0], True)

    def area(self):
        return (self.aabb[1][0] - self.aabb[0][0]) * (self.aabb[1][1] - self.aabb[0][1])


__all__ = ["Group", "Edge", "Segment"]