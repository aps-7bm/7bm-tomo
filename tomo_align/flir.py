'''
    detector lib for Sector 2-BM  using Point Grey Grasshooper3 or FLIR Oryx cameras
    
'''
import sys
import json
import time
from pathlib import Path
import h5py
import traceback
import numpy as np

from tomo_align import aps7bm
from tomo_align import log

DetectorIdle = 0
DetectorAcquire = 1

def check_camera_IOC(global_PVs, params):
    detector_sn = global_PVs['Cam1_SerialNumber'].get()
    if ((detector_sn == None) or (detector_sn == 'Unknown')):
        log.info('*** The Point Grey Camera with EPICS IOC prefix %s is down' % params.camera_ioc_prefix)
        log.info('  *** Failed!')
        return False
    log.info('*** The camera with EPICS IOC prefix %s and serial number %s is on' \
                % (params.camera_ioc_prefix, detector_sn))
    return True


def take_image(global_PVs, params):

    log.info('  *** taking a single image')
   
    nRow = global_PVs['Cam1_SizeY_RBV'].get()
    nCol = global_PVs['Cam1_SizeX_RBV'].get()

    image_size = nRow * nCol

    #Figure out the image mode, save it, and stop acquisition
    orig_im_mode = global_PVs['Cam1_ImageMode'].get()
    orig_acquire_mode = global_PVs['Cam1_Acquire'].get()
    global_PVs['Cam1_Acquire'].put(DetectorIdle, wait=True, timeout=5.)

    global_PVs['Cam1_ImageMode'].put('Single', wait=True)
    global_PVs['Cam1_NumImages'].put(1, wait=True)

    global_PVs['Cam1_TriggerMode'].put(0, wait=True)
    wait_time_sec =  3
    time.sleep(0.25)
    global_PVs['Cam1_Acquire'].put(DetectorAcquire, wait=True, timeout=1000.0)
    time.sleep(0.1)
    if aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec) == False: # adjust wait time
        global_PVs['Cam1_Acquire'].put(DetectorIdle)
        log.warning('The camera failed to finish acquisition.  Set to done manually.')
    
    # Get the image loaded in memory
    img_vect = global_PVs['Cam1_Image'].get(count=image_size)
    if global_PVs['Cam1_Image_Dtype'].get(as_string=True) == 'UInt16':
        img_vect = img_vect.astype(np.uint16)
    img = np.reshape(img_vect,[nRow, nCol])
    
    #Set the image mode back to the original value and restart acquisition
    global_PVs['Cam1_ImageMode'].put(orig_im_mode, wait=True)
    time.sleep(0.25)
    global_PVs['Cam1_Acquire'].put(orig_acquire_mode)
    log.info('  *** single image done')
    return img


def take_flat(global_PVs, params):

    log.info('  *** acquire white')
    log.info('  *** *** set exp time')
    if params.diff_bright_exposure == 'Different':
        global_PVs['Cam1_AcquireTime'].put(params.bright_exposure_time, wait=True)
    output = take_image(global_PVs, params)
    global_PVs['Cam1_AcquireTime'].put(params.exposure_time, wait=True)
    return output


def take_dark(global_PVs, params):
    
    log.info('  *** acquire dark')
    return take_image(global_PVs, params)


def take_dark_and_white(global_PVs, params, leave_shutter_open=False):
    global_PVs['Move_Sample_Out'].put('Move', wait=False)
    aps7bm.close_shutters(global_PVs, params)
    dark_field = take_dark(global_PVs, params)
    aps7bm.open_shutters(global_PVs, params)
    aps7bm.wait_pv(global_PVs['Move_Sample_Out'], 0, 10) 
    white_field = take_flat(global_PVs, params)
    global_PVs['Move_Sample_In'].put('Move')
    if not leave_shutter_open:
        aps7bm.close_shutters(global_PVs, params)
    aps7bm.wait_pv(global_PVs['Move_Sample_In'], 0)
    return dark_field, white_field
