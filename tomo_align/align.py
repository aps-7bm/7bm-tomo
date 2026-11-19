#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

import numpy as np
#from skimage.feature import match_template, register_translation
from skimage.registration import phase_cross_correlation
import matplotlib.pyplot as plt
import skimage.filters
import epics
from tomo_align import log
from tomo_align import flir
from tomo_align import aps7bm


def find_resolution(params):
    log.info('find resolution')
    global_PVs = aps7bm.init_general_PVs(params)
    
    try: 
        if not flir.check_camera_IOC(global_PVs, params):
            return False

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
        aps7bm.close_shutters(global_PVs, params, False)
        global_PVs["Motor_SampleX"].put(start_position)
        
        sphere_0 = normalize(sphere_0, white_field, dark_field)
        sphere_1 = normalize(sphere_1, white_field, dark_field)
        log.info('  *** images normalized and unsharp masked')
        plt.imshow(sphere_0 - sphere_1)#, vmin=-4, vmax=4)
        plt.colorbar()
        plt.title('Difference image 1 - 2')
        
        #Find pixel shift between images
        log.info('  *** Calculating shift.  This will take a minute.')
        #shifts, error, phasediff = register_translation(sphere_0, sphere_1, 10)
        shifts, error, phasediff = phase_cross_correlation(sphere_0, sphere_1, normalization=None)
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

        sphere_0, sphere_180 = take_sphere_0_180(global_PVs, params)
        sphere_180_flip = sphere_180[...,::-1]
        
        #Find pixel shift between images
        log.info('  *** Calculating shift.  This will take a minute.')
        #shifts, error, phasediff = register_translation(sphere_0, sphere_180_flip, 10)
        shifts, error, phasediff = phase_cross_correlation(sphere_0, sphere_180_flip, normalization=None)
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
    finally:
        aps7bm.close_shutters(global_PVs, params, False)


def find_roll_correlation(params, side_fraction = 0.1):
    global_PVs = aps7bm.init_general_PVs(params)
    params.file_name = None # so we don't run the flir._setup_hdf_writer 

    try: 
        if not flir.check_camera_IOC(global_PVs, params):
            return False

        sphere_0, sphere_180 = take_sphere_0_180(global_PVs, params)
        sphere_180_flip = sphere_180[...,::-1]
        #Take strips on the left and right sides of the images
        side_columns = int(sphere_0.shape[1]*side_fraction)
        side_spacing = sphere_0.shape[1] - side_columns
        sphere_0_left = sphere_0[:,:side_columns]
        sphere_180_left = sphere_180_flip[:,:side_columns]
        sphere_0_right = sphere_0[:,-side_columns:]
        sphere_180_right = sphere_180_flip[:,-side_columns:]
        #Find pixel shift between images on each side
        log.info('  *** Calculating shift for left images.  This will take a minute.')
        left_shifts, left_error, left_phasediff = phase_cross_correlation(sphere_0_left, 
                                                    sphere_180_left, normalization=None)
        log.info(f'  *** Calculated shift for left images is ({left_shifts[0]:6.4f}, {left_shifts[1]:6.4f})')
        right_shifts, right_error, right_phasediff = phase_cross_correlation(sphere_0_right, 
                                                    sphere_180_right, normalization=None)
        log.info(f'  *** Calculated shift for right images is ({right_shifts[0]:6.4f}, {right_shifts[1]:6.4f})')
        implied_angle = np.arctan((left_shifts[1] - right_shifts[1]) / side_spacing)
        log.info(f'  *** Implied camera roll = {implied_angle * 1e3:7.2f} mrad')
        log.info(f'  *** Implied camera roll = {np.degrees(implied_angle):7.5f} deg')
    except  KeyError:
        log.error('  *** Some PV assignment failed!')
    finally:
        aps7bm.close_shutters(global_PVs, params, False)


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
        time.sleep(0.5)
        image_180 = flir.take_image(global_PVs, params)
        log.info('  *** *** DONE')
        log.info('  *** Move stage back.')
        global_PVs['Motor_SampleRot'].move(-180, relative=True, wait=False)
    finally:
        aps7bm.close_shutters(global_PVs, params, False)
    image_0 = normalize(image_0, white_field, dark_field)
    image_180 = normalize(image_180, white_field, dark_field)
    return image_0, image_180


def normalize(im, bright, dark, dark_cutoff=1e-6,bright_clip=1):
    trans = (im[1:,:] - dark[1:,:]) / (bright[1:,:] - dark[1:,:])
    np.nan_to_num(trans, False, bright_clip, bright_clip, dark_cutoff)
    trans[trans < dark_cutoff] = dark_cutoff
    trans[trans > bright_clip] = bright_clip
    #Do an unsharp mask
    return skimage.filters.unsharp_mask(trans, 50, 1.0) - trans


def find_focus(params):
    log.info('find focus')
    global_PVs = aps7bm.init_general_PVs(params)
    
    try: 
        if not flir.check_camera_IOC(global_PVs, params):
            return False

        dark_field, white_field = flir.take_dark_and_white(global_PVs, params, True)
        focus_motor = epics.Motor(params.focus_motor_pv)
        orig_focus = focus_motor.get_position()
        num_images = int(np.round(2 * params.focus_range / params.focus_step)) + 1
        focal_stack_positions = np.linspace(-params.focus_range, params.focus_range, num_images)
        focal_stack_positions += orig_focus
        focal_metric = np.zeros(focal_stack_positions.shape[0])
        #focal_stack_data = np.zeros((num_images, dark_field.shape[0], dark_field.shape[1]))
        if not (focus_motor.within_limits(focal_stack_positions[0]) 
                and focus_motor.within_limits(focal_stack_positions[-1])):
            raise ValueError
        for i in range(num_images): 
            focus_motor.move(focal_stack_positions[i])
            log.info(f'  *** focal stack image {i}/{num_images}')
            temp_image = flir.take_image(global_PVs, params)
            norm_im = (temp_image - dark_field) / (white_field / dark_field)
            focal_metric[i] = np.std(norm_im, dtype=np.float64) / np.mean(norm_im, dtype=np.float64) 
             
        plt.plot(focal_stack_positions, focal_metric, '.-')
        plt.xlabel('Focus motor, mm')
        plt.ylabel('Focal metric')
        plt.show()
        best_focus = focal_stack_positions[np.argmax(focal_metric)]
        log.info(f'  *** Best focus at {best_focus:7.3f} mm')
        focus_motor.move(best_focus)
    except  KeyError:
        log.error('  *** Some PV assignment failed!')
        pass
    finally:
        aps7bm.close_shutters(global_PVs, params, False)

