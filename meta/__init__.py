
import numpy as np
from numpy import linalg
import cv2


class Edge:
    def __init__(self, g, pt_a, pt_b):
        self.group = g
        self.pos = pt_a
        vector = pt_b - pt_a
        self.len = linalg.norm(vector)
        self.vec = np.array([vector[0][0]/self.len, vector[0][1]/self.len])
        self.perp = np.array([self.vec[1], self.vec[0]])


class Group:
    def __init__(self, e, i):
        self.contour = e[:]
        self.im = i
        self.obb = None
        self.aabb = np.zeros((2, 2), np.int32)
        self.aabb[0][0] = self.im.shape[0]
        self.aabb[0][1] = self.im.shape[1]
        self.im = i

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

        self.obb = cv2.minAreaRect(self.contour)

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
        cv2.imshow("Final Grouping", self.im)

    def envelope(self, b):
        # FIXME: use OBB
        return b.aabb[0][0] >= self.aabb[0][0] and b.aabb[0][1] >= self.aabb[0][1] and b.aabb[1][0] <= self.aabb[1][
            0] and b.aabb[1][1] <= self.aabb[1][1]

    def overlap(self, b):
        # overlapping groups should be merged
        return False

    def merge(self, b, angle, offset):
        pass

    def compare(self, b):
        return False

    def edge(self, idx):
        next_idx = (idx + 1) % len(self.contour)
        e = Edge(self, self.contour[idx], self.contour[next_idx])
        return e

    def area(self):
        cv2.contourArea(self.contour);


__all__ = ["Group", "Edge"]
