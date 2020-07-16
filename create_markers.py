#!/usr/bin/python
import imutils
import cv2.aruco as aruco
import cv2
import os
import sys
import argparse
import subprocess
import imp
import importlib

# Hack if a user has 'em' instead of 'empy' installed with pip
# If the module em doesn't have the expand function use the full path
em = None
for path in sys.path:
    filename = os.path.join(path, 'em.py')
    if os.path.exists(filename):
        em = imp.load_source('em', filename)
        if "expand" in dir(em):
            break
# For-else: else is called if loop doesn't break
else:
    print("ERROR: could not find module em, please sudo apt install python-empy")
    exit(2)


"""
Generate a PDF file containaing one or more fiducial marker for printing
"""

# check if specific package exists
def checkCmd(cmd, package):
    rc = os.system("which %s > /dev/null" % cmd)
    if rc != 0:
        print("""This utility requires %s. It can be installed by typing: sudo apt install %s""" % (
            cmd, package))
        sys.exit(1)

# marker in center of paper, with a board wrapper
def genSingleSvg(id, dicno, paper_size, mark_length, border_length):
    return em.expand(
        """
        <svg width="@(paper_width)mm" height="@(paper_height)mm"
        version="1.1"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xmlns="http://www.w3.org/2000/svg">
        <text  x="@(paper_width / 2)mm" y="@(10)mm" text-anchor="middle" style="font-family:ariel; font-size:10;">id:@(id) dict:@(dicno)</text>
        <rect  x="@((paper_width - border_length)/2)mm" y="@(40)mm" width="@(border_length)mm" height="@(border_length)mm" style="fill:rgb(255,255,255);stroke-width:1;stroke:rgb(0,0,0)"/>
        <image x="@((paper_width - border_length)/2 + (border_length - marker_len)/2)mm" y="@(40 + (border_length - marker_len)/2 )mm" width="@(marker_len)mm" height="@(marker_len)mm" xlink:href="/tmp/marker@(id).png" />
        </svg>
        """, {"id": id, "dicno": dicno, "paper_width": paper_size[0], "paper_height": paper_size[1], "marker_len": mark_length, "border_length": border_length}
    )

# two marker on a3 paper, make it horizontal by inverse width and height
def genDoubleSvg(lid, rid, dicno, paper_size, mark_length, border_length, mark_dist):
    return em.expand(
        """
        <svg width="@(paper_height)mm" height="@(paper_width)mm"
        version="1.1"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xmlns="http://www.w3.org/2000/svg">
        <rect  x ="@(x0)mm" y ="@(y0)mm" width="@(border_length*2+dist)mm" height="@(border_length)mm" style="fill:rgb(255,255,255);stroke-width:1;stroke:rgb(0,0,0)"/>
        <line  x1="@(x0+border_length)mm" y1="@(y0)mm" x2="@(x0 + border_length)mm" y2="@(y0+border_length)mm" style="fill:rgb(255,255,255);stroke-width:1;stroke:rgb(0,0,0)" />
        <line  x1="@(x0+border_length+dist)mm" y1="@(y0)mm" x2="@(x0+border_length+dist)mm" y2="@(y0+border_length)mm" style="fill:rgb(255,255,255);stroke-width:1;stroke:rgb(0,0,0)" />
        <image x="@(x0+(border_length - marker_len)/2)mm" y="@(y0+(border_length - marker_len)/2)mm" width="@(marker_len)mm" height="@(marker_len)mm" xlink:href="/tmp/marker@(lid).png"/>
        <image x="@(x0+border_length+dist+(border_length - marker_len)/2)mm" y="@(y0+(border_length - marker_len)/2)mm" width="@(marker_len)mm" height="@(marker_len)mm" xlink:href="/tmp/marker@(rid).png"/>
        <!--
        -->
        </svg>
        """
        , {"lid": lid, "rid": rid, "dicno": dicno, "paper_width": paper_size[0], "paper_height": paper_size[1], "marker_len": mark_length, "border_length": border_length, "dist": mark_dist, "x0":10, "y0":10}
    )

def genMarker(i, dicno, paper_size):
    sys.stdout.flush()
    aruco_dict = aruco.Dictionary_get(dicno)
    img = aruco.drawMarker(aruco_dict, i, 2000)
    # img = imutils.rotate_bound(img, 90)
    cv2.imwrite("/tmp/marker%d.png" % i, img)


def writeMarker(lid, rid, dicno, mark_length, border_length, paper_size, filename):
    # svg = genSingleSvg(lid, dicno, paper_size, mark_length, border_length)
    svg = genDoubleSvg(lid,rid, dicno, paper_size, mark_length, border_length, 50)
    cairo = subprocess.Popen(('cairosvg', '-f', 'pdf', '-o',
                              filename, '/dev/stdin'), stdin=subprocess.PIPE)
    cairo.communicate(input=svg)
    # This way is faster than subprocess, but causes problems when cairosvg is installed from pip
    # because newer versions only support python3, and opencv3 from ros does not
    # cairosvg.svg2pdf(bytestring=svg, write_to='/tmp/marker%d.pdf' % i)
    # os.remove("/tmp/marker%d.png" % i)

if __name__ == "__main__":
    checkCmd("pdfunite", "poppler-utils")  # pdf printer
    checkCmd("cairosvg", "python-cairosvg")  # svg converter

    # parse arguments using ArgumentParser https://docs.python.org/2/library/argparse.html
    parser = argparse.ArgumentParser(description='Generate Aruco Markers.')
    parser.add_argument('startId', type=int,
                        help='start of marker range to generate')
    parser.add_argument('endId', type=int,
                        help='end of marker range to generate')
    parser.add_argument('pdfFile', type=str,
                        help='file to store markers in')
    parser.add_argument('dictionary', type=int, default='8', nargs='?',
                        help='dictionary to generate from')
    parser.add_argument('--paper-size', dest='paper_size', action='store',
                        default='a3', help='paper size to use (letter or a4)')

    args = parser.parse_args()
    outfile = args.pdfFile
    dicno = args.dictionary
    markers = range(args.startId, args.endId + 1)

    if args.paper_size == 'letter':
        paper_size = (215.9, 279.4)
    elif args.paper_size == 'a4':
        paper_size = (210, 297)
    elif args.paper_size == 'a3':
        paper_size = (297.7, 420)

    # gen markers first, try parallel first, if fail, use serial
    try:
        # For a parallel version
        from joblib import Parallel, delayed
        Parallel(n_jobs=-1)(delayed(genMarker)(i, dicno, paper_size)
                            for i in markers)
    except ImportError:
        # Fallback to serial version
        for i in markers:
            genMarker(i, dicno, paper_size)

    writeMarker(13, 14, dicno, 120, 160, paper_size, outfile)