import numpy as np
import cv2
import math


class Group:
    def __init__(self,e,i):
        self.edges=e[:]
        self.im = i
        self.oriented_bounding_box = None
        self.axis_aligned_bounded_box = np.zeros((2, 2), np.int32)
        self.axis_aligned_bounded_box[0][0]=self.im.shape[0]
        self.axis_aligned_bounded_box[0][1]=self.im.shape[1]
    
        #first, find the axis_aligned_bounded_box for the group of edges
        for e in self.edges:
            #x min & max
            if e[0][0]<self.axis_aligned_bounded_box[0][0]:
                self.axis_aligned_bounded_box[0][0]=e[0][0]
            elif e[0][0]>self.axis_aligned_bounded_box[1][0]:
                self.axis_aligned_bounded_box[1][0]=e[0][0]
            #y min & max
            if e[0][1]<self.axis_aligned_bounded_box[0][1]:
                self.axis_aligned_bounded_box[0][1]=e[0][1]
            elif e[0][1]>self.axis_aligned_bounded_box[1][1]:
                self.axis_aligned_bounded_box[1][1]=e[0][1]

        self.oriented_bounding_box = cv2.minAreaRect(self.edges)

    def display(self):
        box = cv2.boxPoints(self.oriented_bounding_box) # cv2.boxPoints(rect) for OpenCV 3.x
        box = np.int0(box)
        bounding_box = np.zeros((4,2), np.int32)
        bounding_box[0] = self.axis_aligned_bounded_box[0]
        bounding_box[1] = (self.axis_aligned_bounded_box[0][0], self.axis_aligned_bounded_box[1][1])
        bounding_box[2] = self.axis_aligned_bounded_box[1]
        bounding_box[3] = (self.axis_aligned_bounded_box[1][0], self.axis_aligned_bounded_box[0][1])
        cv2.drawContours(self.im, self.edges, -1, (0,255,255), 1)
        cv2.polylines(self.im, [bounding_box], True, (255,0,0), 1)
        cv2.drawContours(self.im, [box], 0, (0,0,255), 1)
        
        print("BOX: ", box)
        min_x = math.inf
        min_y = math.inf
        max_x = -1
        max_y = -1
        for points in box:
            x = points[0]
            y = points[1]
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
        print("Min x: ", min_x, " Max x: " , max_x)
        print("Min y: ", min_y, " Max y: " , max_y)

        crop_img = self.im[min_y:max_y, min_x:max_x].copy()

        cv2.imshow("Crop" , crop_img)

        cv2.imshow("Group", self.im)

    def envelope(self, b):
        #FIXME: use oriented_bounding_box
        return b.axis_aligned_bounded_box[0][0]>=self.axis_aligned_bounded_box[0][0] and b.axis_aligned_bounded_box[0][1]>=self.axis_aligned_bounded_box[0][1] and b.axis_aligned_bounded_box[1][0]<=self.axis_aligned_bounded_box[1][0] and b.axis_aligned_bounded_box[1][1]<=self.axis_aligned_bounded_box[1][1]

    def overlap(self, b):
        #overlapping groups should be merged
        return False
        
