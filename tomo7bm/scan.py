'''
    Scan Lib for Sector 2-BM
    
'''
import sys
import time
import signal
import numpy as np

from tomo7bm import dm
from tomo7bm import log
from tomo7bm import flir
from tomo7bm import aps7bm
from tomo7bm import config
from tomo7bm import pso

global_PVs = {}


def check_camera_IOC(global_PVs, params):
    detector_sn = global_PVs['Cam1_SerialNumber'].get()
    if ((detector_sn == None) or (detector_sn == 'Unknown')):
        log.info('*** The Point Grey Camera with EPICS IOC prefix %s is down' % params.camera_ioc_prefix)
        log.info('  *** Failed!')
        return False
    log.info('*** The Point Grey Camera with EPICS IOC prefix %s and serial number %s is on' \
                % (params.camera_ioc_prefix, detector_sn))
    return True


def fly_scan(params):
    '''Perform potentially repeated fly scan.
    '''
    tic =  time.time()
    global_PVs = aps7bm.init_general_PVs(params)
    try: 
        if not check_camera_IOC(global_PVs, params):
            return False
        # Set the slew speed, possibly based on blur and acquisition parameters
        set_slew_speed(global_PVs, params)
        # init camera
        flir.init(global_PVs, params)

        log.info(' ')
        log.info("  *** Running %d sleep scans" % params.sleep_steps)
        for i in np.arange(params.sleep_steps):
            tic_01 =  time.time()
            # set sample file name
            params.file_path = global_PVs['HDF1_FilePath'].get(as_string=True)
            params.file_name = str('{:03}'.format(global_PVs['HDF1_FileNumber'].get())) + '_' + global_PVs['Sample_Name'].get(as_string=True)
            log.info(' ')
            log.info('  *** Start scan {:d} of {:d}'.format(int(i+1), int(params.sleep_steps)))
            tomo_fly_scan(global_PVs, params)
            if ((i+1)!= params.sleep_steps):
                log.warning('  *** Wait (s): %s ' % str(params.sleep_time))
                time.sleep(params.sleep_time) 

            log.info(' ')
            log.info('  *** Data file: %s' % global_PVs['HDF1_FullFileName_RBV'].get(as_string=True))
            log.info('  *** Total scan time: %s minutes' % str((time.time() - tic_01)/60.))
            log.info('  *** Scan Done!')

            #dm.scp(global_PVs, params)

        log.info('  *** Total loop scan time: %s minutes' % str((time.time() - tic)/60.))
        global_PVs['Cam1_ImageMode'].put('Continuous')
        log.info('  *** Done!')
    except  KeyError:
        log.error('  *** Some PV assignment failed!')
    except Exception as ee:
        stop_scan(global_PVs, params)
        log.info('  Exception recorded: ' + str(ee))


def fly_scan_vertical(params):

    tic =  time.time()
    # aps7bm.update_variable_dict(params)
    global_PVsx = aps7bm.init_general_PVs(global_PVs, params)
    try: 
        detector_sn = global_PVs['Cam1_SerialNumber'].get()
        if ((detector_sn == None) or (detector_sn == 'Unknown')):
            log.info('*** The Point Grey Camera with EPICS IOC prefix %s is down' % params.camera_ioc_prefix)
            log.info('  *** Failed!')
        else:
            log.info('*** The Point Grey Camera with EPICS IOC prefix %s and serial number %s is on' \
                        % (params.camera_ioc_prefix, detector_sn))
            
            # calling global_PVs['Cam1_AcquireTime'] to replace the default 'ExposureTime' with the one set in the camera
            params.exposure_time = global_PVs['Cam1_AcquireTime'].get()
            # calling calc_blur_pixel() to replace the default 'SlewSpeed' 
            blur_pixel, rot_speed, scan_time = calc_blur_pixel(global_PVs, params)
            params.slew_speed = rot_speed

            start_y = params.vertical_scan_start
            end_y = params.vertical_scan_end
            step_size_y = params.vertical_scan_step_size

            # init camera
            flir.init(global_PVs, params)

            log.info(' ')
            log.info("  *** Running %d scans" % params.sleep_steps)
            log.info(' ')
            log.info('  *** Vertical Positions (mm): %s' % np.arange(start_y, end_y, step_size_y))

            for ii in np.arange(0, params.sleep_steps, 1):
                log.info(' ')
                log.info('  *** Start scan %d' % ii)
                for i in np.arange(start_y, end_y, step_size_y):
                    tic_01 =  time.time()
                    # set sample file name
                    params.file_path = global_PVs['HDF1_FilePath'].get(as_string=True)
                    params.file_name = str('{:03}'.format(global_PVs['HDF1_FileNumber'].get())) + '_' + global_PVs['Sample_Name'].get(as_string=True)

                    log.info(' ')
                    log.info('  *** The sample vertical position is at %s mm' % (i))
                    global_PVs['Motor_SampleY'].put(i, wait=True, timeout=1000.0)
                    tomo_fly_scan(global_PVs, params)

                    log.info(' ')
                    log.info('  *** Data file: %s' % global_PVs['HDF1_FullFileName_RBV'].get(as_string=True))
                    log.info('  *** Total scan time: %s minutes' % str((time.time() - tic_01)/60.))
                    log.info('  *** Scan Done!')
        
                    dm.scp(global_PVs, params)

                log.info('  *** Moving vertical stage to start position')
                global_PVs['Motor_SampleY'].put(start_y, wait=True, timeout=1000.0)

                if ((ii+1)!=params.sleep_steps):
                    log.warning('  *** Wait (s): %s ' % str(params.sleep_time))
                    time.sleep(params.sleep_time) 

            log.info('  *** Total loop scan time: %s minutes' % str((time.time() - tic)/60.))
            log.info('  *** Moving rotary stage to start position')
            global_PVs["Motor_SampleRot"].put(0, wait=True, timeout=600.0)
            log.info('  *** Moving rotary stage to start position: Done!')

            global_PVs['Cam1_ImageMode'].put('Continuous')
 
            log.info('  *** Done!')

    except  KeyError:
        log.error('  *** Some PV assignment failed!')
        pass


def fly_scan_mosaic(params):

    tic =  time.time()
    # aps7bm.update_variable_dict(params)
    global_PVsx = aps7bm.init_general_PVs(global_PVs, params)
    try: 
        detector_sn = global_PVs['Cam1_SerialNumber'].get()
        if ((detector_sn == None) or (detector_sn == 'Unknown')):
            log.info('*** The Point Grey Camera with EPICS IOC prefix %s is down' % params.camera_ioc_prefix)
            log.info('  *** Failed!')
        else:
            log.info('*** The Point Grey Camera with EPICS IOC prefix %s and serial number %s is on' \
                        % (params.camera_ioc_prefix, detector_sn))
            
            # calling global_PVs['Cam1_AcquireTime'] to replace the default 'ExposureTime' with the one set in the camera
            params.exposure_time = global_PVs['Cam1_AcquireTime'].get()
            # calling calc_blur_pixel() to replace the default 'SlewSpeed' 
            blur_pixel, rot_speed, scan_time = calc_blur_pixel(global_PVs, params)
            params.slew_speed = rot_speed

            start_y = params.vertical_scan_start
            end_y = params.vertical_scan_end
            step_size_y = params.vertical_scan_step_size


            start_x = params.horizontal_scan_start
            end_x = params.horizontal_scan_end
            step_size_x = params.horizontal_scan_step_size

            # set scan stop so also ends are included
            stop_x = end_x + step_size_x
            stop_y = end_y + step_size_y

            # init camera
            flir.init(global_PVs, params)

            log.info(' ')
            log.info("  *** Running %d sleep scans" % params.sleep_steps)
            for ii in np.arange(0, params.sleep_steps, 1):
                tic_01 =  time.time()

                log.info(' ')
                log.info("  *** Running %d mosaic scans" % (len(np.arange(start_x, stop_x, step_size_x)) * len(np.arange(start_y, stop_y, step_size_y))))
                log.info(' ')
                log.info('  *** Horizontal Positions (mm): %s' % np.arange(start_x, stop_x, step_size_x))
                log.info('  *** Vertical Positions (mm): %s' % np.arange(start_y, stop_y, step_size_y))

                h = 0
                v = 0
                
                for i in np.arange(start_y, stop_y, step_size_y):
                    log.info(' ')
                    log.error('  *** The sample vertical position is at %s mm' % (i))
                    global_PVs['Motor_SampleY'].put(i, wait=True)
                    for j in np.arange(start_x, stop_x, step_size_x):
                        log.error('  *** The sample horizontal position is at %s mm' % (j))
                        params.sample_in_position = j
                        # set sample file name
                        params.file_path = global_PVs['HDF1_FilePath'].get(as_string=True)
                        params.file_name = str('{:03}'.format(global_PVs['HDF1_FileNumber'].get())) + '_' + global_PVs['Sample_Name'].get(as_string=True) + '_y' + str(v) + '_x' + str(h)
                        tomo_fly_scan(global_PVs, params)
                        h = h + 1
                        dm.scp(global_PVs, params)
                    log.info(' ')
                    log.info('  *** Total scan time: %s minutes' % str((time.time() - tic)/60.))
                    log.info('  *** Data file: %s' % global_PVs['HDF1_FullFileName_RBV'].get(as_string=True))
                    v = v + 1
                    h = 0

                log.info('  *** Moving vertical stage to start position')
                global_PVs['Motor_SampleY'].put(start_y, wait=True, timeout=1000.0)

                log.info('  *** Moving horizontal stage to start position')
                global_PVs['Motor_SampleX'].put(start_x, wait=True, timeout=1000.0)

                log.info('  *** Moving rotary stage to start position')
                global_PVs["Motor_SampleRot"].put(0, wait=True, timeout=600.0)
                log.info('  *** Moving rotary stage to start position: Done!')

                if ((ii+1)!=params.sleep_steps):
                    log.warning('  *** Wait (s): %s ' % str(params.sleep_time))
                    time.sleep(params.sleep_time) 

                global_PVs['Cam1_ImageMode'].put('Continuous')

                log.info('  *** Done!')

    except  KeyError:
        log.error('  *** Some PV assignment failed!')
        pass


def dummy_scan(params):
    tic =  time.time()
    # aps7bm.update_variable_dict(params)
    global_PVs = aps7bm.init_general_PVs(global_PVs, params)
    try: 
        detector_sn = global_PVs['Cam1_SerialNumber'].get()
        if ((detector_sn == None) or (detector_sn == 'Unknown')):
            log.info('*** The Point Grey Camera with EPICS IOC prefix %s is down' % params.camera_ioc_prefix)
            log.info('  *** Failed!')
        else:
            log.info('*** The Point Grey Camera with EPICS IOC prefix %s and serial number %s is on' \
                        % (params.camera_ioc_prefix, detector_sn))
    except  KeyError:
        log.error('  *** Some PV assignment failed!')
        pass


def set_image_factor(global_PVs, params):
    if (params.recursive_filter == False):
        params.recursive_filter_n_images = 1 
    return params.recursive_filter_n_images

   
def tomo_fly_scan(global_PVs, params):
    log.info(' ')
    log.info('  *** start_scan')
    #Set things up so Ctrl+C will cause scan to clean up.
    def cleanup(signal, frame):
        stop_scan(global_PVs, params)
        sys.exit(0)
    signal.signal(signal.SIGINT, cleanup)
    set_image_factor(global_PVs, params)
    pso.pso_init(params)
    pso.program_PSO()
    log.info('  *** *** PSO programming DONE!')
    log.info('  *** File name prefix: %s' % params.file_name)
    flir.set(global_PVs, params) 

    move_sample_out(global_PVs, params)
    aps7bm.open_shutters(global_PVs, params)
    flir.acquire_flat(global_PVs, params)
    aps7bm.close_shutters(global_PVs, params)
    time.sleep(0.5)
    flir.acquire_dark(global_PVs, params)
    move_sample_in(global_PVs, params)
    aps7bm.open_shutters(global_PVs, params)
    theta = flir.acquire(global_PVs, params)
    aps7bm.close_shutters(global_PVs, params)
    time.sleep(0.5)
    flir.checkclose_hdf(global_PVs, params)
    flir.add_theta(global_PVs, params)

    # If requested, move rotation stage back to zero
    pso.cleanup_PSO()
    pso.driver.motor.move(pso.req_start, wait=False)
    # update config file
    config.update_config(params)


def set_slew_speed(global_PVs, params):
    '''Determines the slew speed of the rotation stage.
    Make sure that we aren't moving so fast that the camera can't keep up.
    Based on user input, choices are:
    * Use value from config file.  Show how much blur this is and if camera
        can keep up.
    * Base on acquisition parameters (data throughput and exposure).
        Show how much blur this is.
    * Base on both blur and data throughput.
    '''
    log.info('  *** Calculate slew speed and blur')
    scan_range = abs(params.sample_rotation_start - params.sample_rotation_end)
    set_image_factor(global_PVs, params)
    delta_angle = scan_range / (params.num_projections - 1) / params.recursive_filter_n_images 
    data_max_framerate = flir.calc_max_framerate(global_PVs, params)
    acq_max_framerate = 1.0 / (params.exposure_time + params.ccd_readout)
    #Compute the distance from the rotation axis to the farthest edge of the image
    #Assume SampleX motor is at zero when rotation axis is centered
    overall_res = float(global_PVs['PixelSizeMicrons'].get()) / float(global_PVs['Lens_Magnification'].get())
    rot_axis_offset = abs(global_PVs['Motor_SampleX'].drive * 1e3 / overall_res)
    log.info('  *** *** rotation axis offset {0:f} pixels'.format(rot_axis_offset))
    im_half_width = global_PVs['Cam1_SizeX'].get() / 2.0 + rot_axis_offset
    blur_max_framerate = 1e6

    if params.auto_slew_speed == 'manual':
        log.info('  *** *** Using manual slew speed')
        req_framerate = params.slew_speed / delta_angle
        log.info('  *** *** Requested framerate is {:6.3} Hz'.format(req_framerate))
        if acq_max_framerate < req_framerate:
            log.warning('  *** *** Requested framerate too fast for exposure time given.')
            log.warning('  *** *** You will miss frames!')
        if data_max_framerate < req_framerate:
            log.warning('  *** *** Requested framerate too fast for data transfer.')
            log.warning('  *** *** You will miss frames!')
        return finish_set_slew_speed(global_PVs, params)
    elif params.auto_slew_speed == 'acqusition':
        log.info('  *** *** Calc slew speed from data throughput and exposure limits.')
    elif params.recursive_filter_n_images > 1:
        log.warning('  *** *** Blur calculation makes less sense with averaging in each projection.')
    else:
        log.info('  *** *** Calc slew speed based on blur and acquisition parameters.')
        max_blur_angle = np.degrees(np.arcsin(params.permitted_blur / im_half_width))
        blur_max_framerate = max_blur_angle /  (params.exposure_time) / delta_angle
    framerates = np.array([data_max_framerate, acq_max_framerate, blur_max_framerate])
    params.slew_speed = np.min(framerates) * delta_angle
    log.info('  *** *** Max framerate for data transfer is {:6.3f} Hz'.format(data_max_framerate))
    log.info('  *** *** Max framerate for exposure time is {:6.3f} Hz'.format(acq_max_framerate))
    if blur_max_framerate == np.min(framerates):
        log.info('  *** *** Limited by blur to {:6.3f} Hz'.format(blur_max_framerate))
    elif data_max_framerate == np.min(framerates):
        log.info('  *** *** Limited by data throughput to {:6.3f} Hz'.format(data_max_framerate))
    else:
        log.info('  *** *** Limited by acquisition time to {:6.3f} Hz'.format(acq_max_framerate))
    blur = np.sin(np.radians(params.slew_speed * params.exposure_time)) * im_half_width 
    if params.recursive_filter_n_images > 1:
        blur = np.sin(np.radians(delta_angle)) * im_half_width    
    if blur > params.permitted_blur:
        log.warning('  *** *** Motion blur on image edge = {:6.2f} px'.format(blur))
    else:
        log.info('  *** *** Motion blur on image edge = {:6.2f} px'.format(blur))
    log.info('  *** *** Slew speed set to {:6.3f} deg/s'.format(params.slew_speed))
    global_PVs['Sample_Rotation_Speed'].put(params.slew_speed, wait=True)
    return params.slew_speed


def move_sample_out(global_PVs, params):

    log.info('      *** Sample out')
    if params.sample_move_freeze:
        log.info('        *** *** Sample motion is frozen.')
        return
    params.original_x = global_PVs['Motor_SampleX'].drive
    params.original_y = global_PVs['Motor_SampleY'].drive 

    try:
        #Check the limits
        out_x = params.sample_out_x
        out_y = params.sample_out_y
        log.info('      *** Moving to (x,y) = ({0:6.4f}, {1:6.4f})'.format(out_x, out_y))
        if not (global_PVs['Motor_SampleX'].within_limits(out_x)
               and global_PVs['Motor_SampleY'].within_limits(out_y)):
            log.error('        *** *** Sample out position past motor limits.')
            return
        global_PVs['Motor_SampleX'].move(out_x, wait=True, timeout=10)
        global_PVs['Motor_SampleY'].move(out_y, wait=True, timeout=10)
        #Check if we ever got there
        time.sleep(0.2)
        if (abs(global_PVs['Motor_SampleX'].readback - out_x) > 1e-3 
            or abs(global_PVs['Motor_SampleY'].readback - out_y) > 1e-3):
            log.error('        *** *** Sample out motion failed!')
    except Exception as ee:
        log.error('EXCEPTION DURING SAMPLE OUT MOTION!')
        global_PVs['Motor_SampleX'].move(params.original_x, wait=True, timeout=10)
        global_PVs['Motor_SampleY'].move(params.original_y, wait=True, timeout=10)
        raise ee

def move_sample_in(global_PVs, params):
    log.info('      *** Sample in')
    if params.sample_move_freeze:
        log.info('        *** *** Sample motion is frozen.')
        return
    try:
        #If we haven't saved original positions yet, use the current ones.
        try:
            _ = params.original_x
            _ = params.original_y
        except AttributeError:
            params.original_x = global_PVs['Motor_SampleX'].drive 
            params.original_y = global_PVs['Motor_SampleY'].drive 
        log.info('      *** Moving to (x,y) = ({0:6.4f}, {1:6.4f})'.format(
                    params.original_x, params.original_y))
        #Check the limits
        if not (global_PVs['Motor_SampleX'].within_limits(params.original_x)
               and global_PVs['Motor_SampleY'].within_limits(params.original_y)):
            log.error('        *** *** Sample in position past motor limits.')
            return
        global_PVs['Motor_SampleX'].move(params.original_x, wait=True, timeout=10)
        global_PVs['Motor_SampleY'].move(params.original_y, wait=True, timeout=10)
        #Check if we ever got there
        if (abs(global_PVs['Motor_SampleX'].readback - params.original_x) > 1e-3 
            or abs(global_PVs['Motor_SampleY'].readback - params.original_y) > 1e-3):
            log.error('        *** *** Sample in motion failed!')
    except Exception as ee:
        log.error('EXCEPTION DURING SAMPLE IN MOTION!')
        raise ee


def stop_scan(global_PVs, params):
    log.info(' ')
    log.error('  *** Stopping the scan: PLEASE WAIT')
    aps7bm.close_shutters(global_PVs, params)
    global_PVs['Motor_SampleRot'].stop()
    global_PVs['HDF1_Capture'].put(0)
    aps7bm.wait_pv(global_PVs['HDF1_Capture'], 0)
    pso.cleanup_PSO()
    flir.init(global_PVs, params)
    log.error('  *** Stopping scan: Done!')
