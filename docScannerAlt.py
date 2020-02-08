from skimage.filters import threshold_local
import numpy as np
import argparse
import cv2
import imutils

ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required = True, help ="Path to the image to be scanned")

args = vars(ap.parse_args())
print(args["image"])
image = cv2.imread(args["image"])
ratio = image.shape[0] / 500.0
orig = image.copy()
image = imutils.resize(image, height = 500)


gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray = cv2.GaussianBlur(gray,(5,5),0)
edged = cv2.Canny(gray, 75, 200)

print("STEP 1: EDGE DETECTION")
cv2.imshow("Orig", image)
cv2.imshow("Edged", edged)
cv2.waitKey(5000)
cv2.destroyAllWindows()
contours= cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
contour2 = imutils.grab_contours(contours)
contour3 = sorted(contour2, key = cv2.contourArea, reverse = True)[:5]

screenContour = []
for c in contour3:
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.02*peri, True)

    if len(approx) == 4:
        screenContour.append(approx)

print("Number of contours found =" + str(len(contours)))
print("Step 2: find Contours of paper")
cv2.drawContours(image, screenContour, -1, (0,255,0),2)
cv2.imshow("Outline", image)
cv2.waitKey(5000)
cv2.destroyAllWindows()
