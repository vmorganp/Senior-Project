# The main python file, run from the commandline
import argparse
import cv2
import numpy as np
from reportlab.pdfgen import canvas
import meta

work_pool = []


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


def create_groups(edges, image):
    for e in edges:
        g = meta.Group(e, image)
        work_pool.append(g)


def compare_and_merge(a, b):
    for i in range(a.contour):
        e_a = a.edge(i)


# Pre-cuts an image and adds it to the processing pool
def add_image(img):
    image = cv2.imread(img)

    contours = get_edges(image)

    create_groups(contours, image)


def process_pool():
    pass


## MAIN ##
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True, help="Path to the image to be scanned")
    ap.add_argument("-o", "--output", required=False, help="Filename of output PDF")

    args = vars(ap.parse_args())
    add_image(args["image"])

    process_pool()