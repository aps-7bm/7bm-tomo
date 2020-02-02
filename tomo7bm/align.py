#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import time
from epics import PV
import h5py
import shutil
import os
import argparse

import traceback
import numpy as np
from datetime import datetime
import pathlib
import signal

from tomo7bm import log
from tomo7bm import flir
from tomo7bm import aps7bm
from tomo7bm import config
from tomo7bm import util

#import matplotlib.pylab as pl
import matplotlib.widgets as wdg


from skimage import filters
from skimage.measure import regionprops
from skimage.feature import register_translation

global variableDict


def find_resolution(params):

    log.info('find resolution')
    global_PVs = aps7bm.init_general_PVs(params)
    aps7bm.user_info_update(global_PVs, params)

    params.file_name = None # so we don't run the flir._setup_hdf_writer 
    try: 
        detector_sn = global_PVs['Cam1_SerialNumber'].get()
        if ((detector_sn == None) or (detector_sn == 'Unknown')):
            log.info('   *** The Point Grey Camera with EPICS IOC prefix %s is down' % params.camera_ioc_prefix)
            log.info('   *** Failed!')
        else:
            log.info('   *** The Point Grey Camera with EPICS IOC prefix %s and serial number %s is on' \
                        % (params.camera_ioc_prefix, detector_sn))

            flir.init(global_PVs, params)
            flir.set(global_PVs, params) 

            dark_field, white_field = flir.take_dark_and_white(global_PVs, params)

            log.info('  *** First image at X: %f mm' % (params.sample_in_position))
            log.info('  *** acquire first image')
            sphere_0 = normalize(flir.take_image(global_PVs, params), white_field, dark_field)

            second_image_x_position = params.sample_in_position + params.off_axis_position
            log.info('  *** Second image at X: %f mm' % (second_image_x_position))
            global_PVs["Motor_SampleX"].put(second_image_x_position, wait=True, timeout=600.0)
            log.info('  *** acquire second image')
            sphere_1 = normalize(flir.take_image(global_PVs, params), white_field, dark_field)

            log.info('  *** moving X stage back to %f mm position' % (params.sample_in_position))
            aps7bm.move_sample_in(global_PVs, params)

            shift = register_translation(sphere_0, sphere_1, 10)

            log.info('  *** shift %f' % shift[0][1])

            params.resolution =  abs(params.off_axis_position) / np.abs(shift[0][1]) * 1000.0
            
            config.update_sphere(params)

            return params.resolution

    except  KeyError:
        log.error('  *** Some PV assignment failed!')
        pass


def find_roll_and_rotation_axis_location(params):

    global_PVs = aps7bm.init_general_PVs(params)

    params.file_name = None # so we don't run the flir._setup_hdf_writer 

    try: 
        detector_sn = global_PVs['Cam1_SerialNumber'].get()
        if ((detector_sn == None) or (detector_sn == 'Unknown')):
            log.info('*** The Point Grey Camera with EPICS IOC prefix %s is down' % params.camera_ioc_prefix)
            log.info('  *** Failed!')
        else:
            log.info('*** The Point Grey Camera with EPICS IOC prefix %s and serial number %s is on' \
                        % (params.camera_ioc_prefix, detector_sn))

            flir.init(global_PVs, params)
            flir.set(global_PVs, params) 

            sphere_0, sphere_180 = take_sphere_0_180(global_PVs, params)

            cmass_0 = center_of_mass(sphere_0)
            cmass_180 = center_of_mass(sphere_180)

            params.rotation_axis_position = (cmass_180[1] + cmass_0[1]) / 2.0
            log.info('  *** shift (center of mass): [%f, %f]' % ((cmass_180[0] - cmass_0[0]) ,(cmass_180[1] - cmass_0[1])))

            params.roll = np.rad2deg(np.arctan((cmass_180[0] - cmass_0[0]) / (cmass_180[1] - cmass_0[1])))
            log.info("  *** roll:%f" % (params.roll))
            config.update_sphere(params)

        return params.rotation_axis_position, params.roll
    except  KeyError:
        log.error('  *** Some PV assignment failed!')
        pass


def take_sphere_0_180(global_PVs, params):
    '''Take images at 0 and 180 degrees, returning images as two arrays.
    '''
    dark_field, white_field = flir.take_dark_and_white(global_PVs, params)

    log.info('  *** moving rotary stage to %f deg position' % float(params.sample_rotation_start))
    global_PVs["Motor_SampleRot"].put(float(params.sample_rotation_start), wait=True, timeout=600.0)
    
    log.info('  *** acquire sphere at %f deg position' % float(params.sample_rotation_start))
    sphere_0 = normalize(flir.take_image(global_PVs, params), white_field, dark_field)
 
    log.info('  *** moving rotary stage to %f deg position' % float(params.sample_rotation_end))
    global_PVs["Motor_SampleRot"].put(float(params.sample_rotation_end), wait=True, timeout=600.0)
    
    log.info('  *** acquire sphere at %f deg position' % float(params.sample_rotation_end))
    sphere_180 = normalize(flir.take_image(global_PVs, params), white_field, dark_field)

    log.info('  *** moving rotary stage back to %f deg position' % float(params.sample_rotation_start))
    global_PVs["Motor_SampleRot"].put(float(params.sample_rotation_start), wait=True, timeout=600.0)
    
    return sphere_0, sphere_180


def template_match_images(image1, image2):
    '''Determine shift required to make image2 match image1.
    '''
    #Make template sizes and shapes
    padded_image1 = np.zeros((image1.shape[0]*2, image1.shape[1]*2))
    row_shift = image1.shape[0]//2
    col_shift = image1.shape[1]//2
    padded_image1[row_shift:image1.shape[0]+row_shift,col_shift:col_shift+image1.shape[1]] = image1 
    correlation_matrix = match_template(padded_image1, image2)
    shift_tuple = np.unravel_index(np.argmax(correlation_matrix),correlation_matrix.shape)
    row_shift = shift_tuple[0] - row_shift
    col_shift = shift_tuple[1] - col_shift


def center_of_mass(image):
    
    threshold_value = filters.threshold_otsu(image)
    log.info("  *** threshold_value: %f" % (threshold_value))
    labeled_foreground = (image < threshold_value).astype(int)
    properties = regionprops(labeled_foreground, image)
    return properties[0].weighted_centroid
    # return properties[0].centroid


def center_rotation_axis(global_PVs, params):

    nCol = global_PVs['Cam1_SizeX_RBV'].get()
    
    log.info(' ')
    log.info('  *** centering rotation axis')

    current_axis_position = global_PVs["Motor_SampleX"].get()
    log.info('  *** current axis position: %f' % current_axis_position)
    time.sleep(.5)
    correction = (((nCol / 2.0) - variableDict['AxisLocation']) * variableDict['DetectorResolution'] / 1000.0) + current_axis_position
    log.info('  *** correction: %f' % correction)

    log.info('  *** moving to: %f (mm)' % correction)
    global_PVs["Motor_SampleX"].put(correction, wait=True, timeout=600.0)

    log.info('  *** re-setting position from %f (mm) to 0 (mm)' % correction)
    global_PVs["Motor_SampleX_SET"].put(1, wait=True, timeout=5.0)
    time.sleep(.5)
    global_PVs["Motor_SampleX"].put(0, wait=True, timeout=5.0)
    time.sleep(.5)
    global_PVs["Motor_SampleX_SET"].put(0, wait=True, timeout=5.0)


def normalize(im, bright, dark, dark_cutoff=1e-6,bright_clip=1):
    trans = (im - dark) / (bright - dark)
    trans[trans < dark_cutoff] = dark_cutoff
    trans[trans > bright_clip] = 1
    return -np.log(trans)
