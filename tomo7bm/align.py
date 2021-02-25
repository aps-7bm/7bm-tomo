#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

import numpy as np
from skimage.feature import match_template, register_translation
import matplotlib.pyplot as plt
import skimage.filters

from tomo7bm import log
from tomo7bm import flir
from tomo7bm import aps7bm


def find_resolution(params):
    log.info('find resolution')
    global_PVs = aps7bm.init_general_PVs(params)
    
    try: 
        if not flir.check_camera_IOC(global_PVs, params):
            return False

        flir.init(global_PVs, params)
        dark_field, white_field = flir.take_dark_and_white(global_PVs, params, True)

        start_position = global_PVs["Motor_SampleX"].get()    
        log.info('  *** First image at X: %f mm' % (start_position))
        log.info('  *** acquire first image')
        sphere_0 = flir.take_image(global_PVs, params)
       
        second_image_x_position = start_position  + params.off_axis_position
        log.info('  *** Second image at X: %f mm' % (second_image_x_position))
        global_PVs["Motor_SampleX"].put(second_image_x_position, wait=True, timeout=600.0)
        time.sleep(0.5)
        log.info('  *** acquire second image')
        sphere_1 = flir.take_image(global_PVs, params)

        log.info('  *** moving X stage back to %f mm position' % (start_position))
        aps7bm.close_shutters(global_PVs, params)
        global_PVs["Motor_SampleX"].put(start_position, wait=True)
        
        sphere_0 = normalize(sphere_0, white_field, dark_field)
        sphere_1 = normalize(sphere_1, white_field, dark_field)
        log.info('  *** images normalized and unsharp masked')
        plt.imshow(sphere_0 - sphere_1)#, vmin=-4, vmax=4)
        plt.colorbar()
        plt.title('Difference image 1 - 2')
        
        #Find pixel shift between images
        log.info('  *** Calculating shift.  This will take a minute.')
        shifts, error, phasediff = register_translation(sphere_0, sphere_1, 10)
        log.info('  *** Calculated shift is ({0:6.4f}, {1:6.4f})'.format(shifts[0], shifts[1]))
        total_shift = np.hypot(shifts[0], shifts[1])
        log.info('  *** total shift {:6.4f} pixels'.format(total_shift))
        calc_image_pixel_size = params.off_axis_position * 1000 / total_shift 
        log.info('  *** image pixel size {:6.4f} microns'.format(calc_image_pixel_size))
        global_PVs['Actual_Pixel_Size'].put(calc_image_pixel_size)
        #Plot the shifted image
        sphere_1 = np.roll(sphere_1, (int(shifts[0]), int(shifts[1])), axis=(0,1))
        plt.figure(2)
        plt.imshow((sphere_0 - sphere_1)[abs(int(shifts[0])):,abs(int(shifts[1])):])
        plt.colorbar()
        plt.title('Difference image after shift')
        plt.show() 
    except  KeyError:
        log.error('  *** Some PV assignment failed!')
        pass


def find_tilt_rotation_axis(params):
    global_PVs = aps7bm.init_general_PVs(params)
    params.file_name = None # so we don't run the flir._setup_hdf_writer 

    try: 
        if not flir.check_camera_IOC(global_PVs, params):
            return False

        flir.init(global_PVs, params)
        sphere_0, sphere_180 = take_sphere_0_180(global_PVs, params)
        sphere_180_flip = sphere_180[...,::-1]
        
        #Find pixel shift between images
        log.info('  *** Calculating shift.  This will take a minute.')
        shifts, error, phasediff = register_translation(sphere_0, sphere_180_flip, 10)
        log.info('  *** Calculated shift is ({0:6.4f}, {1:6.4f})'.format(shifts[0], shifts[1]))
        overall_res = float(global_PVs['Actual_Pixel_Size'].get())
        log.info(' *** Rotation axis off by {0:6.4} mm'.format(shifts[1] * overall_res / 2e3))
        log.info(' *** Move SampleX by {0:6.4} mm'.format(shifts[1] * overall_res / 2e3))
        log.info(' *** Shift in Y = {0:6.4} microns'.format(shifts[0] * overall_res))
        tilt_angle = np.degrees(shifts[0] * overall_res / 25.4 / 1e3)
        log.info(' *** Equivalent to {0:6.4} deg'.format(tilt_angle))
        #Plot the shifted image
        sphere_1 = np.roll(sphere_180_flip, (int(shifts[0]), int(shifts[1])), axis=(0,1))
        plt.figure(2)
        plt.imshow((sphere_0 - sphere_1)[abs(int(shifts[0])):,abs(int(shifts[1])):], vmin=-0.1, vmax=0.1)
        plt.colorbar()
        plt.title('Difference image after shift')
        plt.show() 
        return 0, 0
    except  KeyError:
        log.error('  *** Some PV assignment failed!')


def take_sphere_0_180(global_PVs, params):
    '''Take images at 0 and 180 degrees, returning images as two arrays.
    '''
    try:
        dark_field, white_field = flir.take_dark_and_white(global_PVs, params, True)
        log.info('  *** Take first image of 0/180 degree set.')
        image_0 = flir.take_image(global_PVs, params)
        log.info('  *** *** DONE')
        log.info('  *** Move stage 180 degrees.')
        global_PVs['Motor_SampleRot'].move(180, relative=True, wait=True)
        log.info('  *** Take second image of 0/180 degree set.')
        image_180 = flir.take_image(global_PVs, params)
        log.info('  *** *** DONE')
        log.info('  *** Move stage back.')
        global_PVs['Motor_SampleRot'].move(-180, relative=True, wait=False)
    finally:
        aps7bm.close_shutters(global_PVs, params)
    image_0 = normalize(image_0, white_field, dark_field)
    image_180 = normalize(image_180, white_field, dark_field)
    return image_0, image_180


def template_match_images(image1, image2):
    '''Determine shift required to make image2 match image1.
    '''
    #Make images floats, ignoring first row (bad from camera)
    image1 = image1.astype(np.float64)
    image2 = image2.astype(np.float64)
    #Make template sizes and shapes
    row_shift = image1.shape[0]//2
    col_shift = image1.shape[1]//2
    padded_image1 = np.pad(image1, ((row_shift, row_shift), (col_shift, col_shift)))
    correlation_matrix = match_template(padded_image1, image2)
    print('Maximum correlation = {0:6.4f}'.format(np.max(correlation_matrix)))
    print(correlation_matrix.shape)
    log.info('Maximum correlation = {0:6.4f}'.format(np.max(correlation_matrix)))
    shift_tuple = np.unravel_index(np.argmax(correlation_matrix),correlation_matrix.shape)
    row_shift = shift_tuple[0] - row_shift
    col_shift = shift_tuple[1] - col_shift
    log.info('Shift of (row, column) = ({0:d}, {1:d})'.format(row_shift, col_shift))
    #Now display an image showing how well the images match
    return row_shift, col_shift


def center_rotation_axis(global_PVs, params):

    nCol = global_PVs['Cam1_SizeX_RBV'].get()
    
    log.info(' ')
    log.info('  *** centering rotation axis')

    current_axis_position = global_PVs["Motor_SampleX"].drive
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
    trans = (im[1:,:] - dark[1:,:]) / (bright[1:,:] - dark[1:,:])
    trans[trans < dark_cutoff] = dark_cutoff
    trans[trans > bright_clip] = 1
    #Do an unsharp mask
    return skimage.filters.unsharp_mask(trans, 50, 1.0) - trans
    return 1-trans
    return -np.log(trans)


