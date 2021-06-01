# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import numpy as np
import pickle
from tools import visualization as vis
from datetime import datetime
from reconstruction import common
from analysis.compare_gt import align_gt
import sys

import cv2
from reconstruction import epipolar as ep
import argparse
import os

# parse the input
a = argparse.ArgumentParser()
a.add_argument("--config_file", type=str, help="path to the proper config file", required=True)
a.add_argument("--debug", action="store_true", help="debug mode: run with ground truth)")

args = a.parse_args()

print('Reconstruct with only static part of the scene.\n')

if args.debug:
    print("RUN ON DEBUG MODE WITH GROUND TRUTH STATIC POINTS")

# Initialize a scene from the json template
flight = common.create_scene(args.config_file)

# Initialize the static part
flight.init_static()

'''---------------Incremental reconstruction----------------'''
start = datetime.now()
np.set_printoptions(precision=4)

cam_temp = 2
while True:
    print('\n----------------- Bundle Adjustment with {} cameras -----------------'.format(cam_temp))
    print('\nMean error of the static part in each camera before BA:   ', np.asarray([np.mean(flight.error_cam_static(x, debug=args.debug)) for x in flight.sequence[:cam_temp]]))

    print('\nDoing the first BA')
    # Bundle adjustment
    res = flight.BA(cam_temp, debug=args.debug)

    print('\nMean error of the static part in each camera after the first BA:    ', np.asarray([np.mean(flight.error_cam_static(x, debug=args.debug)) for x in flight.sequence[:cam_temp]]))

    # remove outliers
    print('\nRemove outliers after first BA')
    flight.remove_outliers_static(flight.sequence[:cam_temp],thres=flight.settings['thres_outlier'])

    print('\nDoing the second BA')
    # Bundle adjustment after outlier removal
    res = flight.BA(cam_temp, debug=args.debug)

    print('\nMean error of the static part in each camera after the second BA:    ', np.asarray([np.mean(flight.error_cam_static(x, debug=args.debug)) for x in flight.sequence[:cam_temp]]))

    num_end = flight.numCam if flight.find_order else len(flight.sequence)
    if cam_temp == num_end:
        print('\nTotal time: {}\n\n\n'.format(datetime.now()-start))
        break

    # Add the next camera and get its pose
    flight.get_camera_pose(flight.sequence[cam_temp], flight.sequence[:cam_temp], debug=args.debug)

    # Triangulate new points and update the static scene
    flight.triangulate_static(flight.sequence[cam_temp], flight.sequence[:cam_temp], thres=flight.settings['thres_triangulation'])

    print('\nTotal time: {}\n\n\n'.format(datetime.now()-start))
    cam_temp += 1

# Visualize the 3D static points
vis.show_3D_all(flight.static[flight.inlier_mask > 0], color=False, line=False)
# vis.show_trajectory_3D(flight.traj[1:],line=False)

# Align with the ground truth data if available
if flight.gt is not None:
    flight.out = align_gt(flight, flight.gt['frequency'], flight.gt['filepath'], visualize=False)
with open(flight.settings['path_output'],'wb') as f:
    pickle.dump(flight, f)

print('Finished!')