from skimage.filters import threshold_local
import numpy as np
import argparse
import cv2
import imutils

class Group:
	def __init__(self,e,i):
		self.edges=e[:]
		self.im = i
		self.obb = None
		self.aabb = np.zeros((2, 2), np.int32)
		self.aabb[0][0]=self.im.shape[0]
		self.aabb[0][1]=self.im.shape[1]

		#first, find the aabb for the group of edges
		for e in self.edges:
			#x min & max
			if e[0][0]<self.aabb[0][0]:
				self.aabb[0][0]=e[0][0]
			elif e[0][0]>self.aabb[1][0]:
				self.aabb[1][0]=e[0][0]
			#y min & max
			if e[0][1]<self.aabb[0][1]:
				self.aabb[0][1]=e[0][1]
			elif e[0][1]>self.aabb[1][1]:
				self.aabb[1][1]=e[0][1]

		self.obb = cv2.minAreaRect(self.edges)

	def display(self):
		box = cv2.boxPoints(self.obb) # cv2.boxPoints(rect) for OpenCV 3.x
		box = np.int0(box)
		bb = np.zeros((4,2), np.int32)
		bb[0] = self.aabb[0]
		bb[1] = (self.aabb[0][0], self.aabb[1][1])
		bb[2] = self.aabb[1]
		bb[3] = (self.aabb[1][0], self.aabb[0][1])
		cv2.drawContours(self.im, self.edges, -1, (0,255,255), 1)
		cv2.polylines(self.im, [bb], True, (255,0,0), 1)
		cv2.drawContours(self.im, [box], 0, (0,0,255), 1)
		cv2.imshow("Group", self.im)

	def envelope(self, b):
		#FIXME: use OBB
		return b.aabb[0][0]>=self.aabb[0][0] and b.aabb[0][1]>=self.aabb[0][1] and b.aabb[1][0]<=self.aabb[1][0] and b.aabb[1][1]<=self.aabb[1][1]

	def overlap(self, b):
		#overlapping groups should be merged
		return False
		

#the group pools are used by the worker threads (lists in CPython are 
#inherently thread-safe because of the GIL)
#groups in the same pool will never be compared to eachother, 
# (always compare an A to a B) this way we never need to worry about comparing
#two groups to each other more than once
#initially, put all groups in B, and move one to A before starting the workers
group_pool_A = []
group_pool_B = []

ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required = True, help ="Path to the image to be scanned")

args = vars(ap.parse_args())
print(args["image"])
image = cv2.imread(args["image"])
ratio = image.shape[0] / 500.0
image = imutils.resize(image, height = 500)
orig = image.copy()

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray,(5,5),0)
edged = cv2.Canny(blurred, 75, 200)


def create_groups(edges, grayImage):
	for e in edges:
		g = Group(e, grayImage)
		group_pool_A.append(g)


print("STEP 1: EDGE DETECTION")
cv2.imshow("Orig", image)
cv2.imshow("Edged", edged)
cv2.waitKey(5000)
cv2.destroyAllWindows()
contours, hierarchy = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

cont = contours;
#print(type(contours[0]))
#for c in contours:
#	peri = cv2.arcLength(c, True)
#	approx = cv2.approxPolyDP(c, 0.02 * peri, True)
#
#	if len(approx) == 4:
#		cont = [approx]
#		break


print("Number of contours found =" + str(len(contours)))
print("Step 2: find Contours of paper")
cv2.drawContours(image, cont, -1, (0,255,0),2)
cv2.imshow("Outline", image)

print("Step 3: Grouping")
create_groups(contours, orig)
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

#TODO: simplify each group further by making the edges "square", using the OBB 
#to remove points that aren't near the straight edge
print("Possible groups ="+str(len(group_pool_B)))

group_pool_A = [group_pool_B.pop(0)]

#at this point we have our two groups, we can unleash the worker threads on 
#them and find the matching edges
for i,g in enumerate(group_pool_B):
	g.display()
group_pool_A[0].display()


cv2.waitKey(0)
cv2.destroyAllWindows()
