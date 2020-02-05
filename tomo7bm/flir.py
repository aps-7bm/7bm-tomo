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

from tomo7bm import aps7bm
from tomo7bm import log
from tomo7bm import pso
from tomo7bm import scan

FrameTypeData = 0
FrameTypeDark = 1
FrameTypeWhite = 2

DetectorIdle = 0
DetectorAcquire = 1

Recursive_Filter_Type = 'RecursiveAve'

def init(global_PVs, params):
    '''Performs initialization of camera.
    Takes a frame to make sure we have frame data.
    '''
    if params.camera_ioc_prefix in params.valid_camera_prefixes:
        log.info('  *** init Point Grey camera')
        global_PVs['HDF1_Capture'].put(0, wait=True)
        global_PVs['HDF1_EnableCallbacks'].put('Disable', wait=True)
        global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)    # 
        global_PVs['Cam1_TriggerMode'].put('Overlapped', wait=True)  # sequence Internal / Overlapped / internal because of CCD bug!!
        global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)    #
        global_PVs['Proc1_Filter_Callbacks'].put( 'Every array' )
        global_PVs['Cam1_ImageMode'].put('Single', wait=True)
        global_PVs['Cam1_Display'].put(1)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Proc1_Callbacks'].put('Disable')
        global_PVs['Proc1_Filter_Enable'].put('Disable')
        global_PVs['HDF1_ArrayPort'].put(global_PVs['Cam1_AsynPort'].get())
        log.info('  *** init Point Grey camera: Done!')


def set(global_PVs, params):
    '''Sets up detector and arms it for PSO pulses.
    '''
    fname = params.file_name
    # Set detectors
    if params.camera_ioc_prefix in params.valid_camera_prefixes:
        log.info(' ')
        log.info('  *** setup Point Grey')

        # Make sure that we aren't acquiring now
        global_PVs['Cam1_Acquire'].put(DetectorIdle)
        aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle)
        #Set up the XML files to determine HDF file layout
        attrib_file = Path.joinpath(Path(__file__).parent,'mctDetectorAttributes1.xml')
        global_PVs['Cam1_AttributeFile'].put(str(attrib_file), wait=True) 
        layout_file = Path.joinpath(Path(__file__).parent,'mct3.xml')
        global_PVs['HDF1_XMLFileName'].put(str(layout_file),wait=True) 

        global_PVs['Cam1_ArrayCallbacks'].put('Enable', wait=True)
        global_PVs['Cam1_AcquirePeriod'].put(float(params.exposure_time), wait=True)
        global_PVs['Cam1_AcquireTime'].put(float(params.exposure_time), wait=True)

        log.info('  *** setup Point Grey: Done!')
    else:
        log.error('Detector %s is not defined' % params.camera_ioc_prefix)
        return
    if params.file_name is None:
        log.warning('  *** hdf_writer will not be configured')
    else:
        _setup_hdf_writer(global_PVs, params, fname)


def _setup_hdf_writer(global_PVs, params, fname=None):

    if params.camera_ioc_prefix in params.valid_camera_prefixes:
        # setup Point Grey hdf writer PV's
        log.info('  ')
        log.info('  *** setup hdf_writer')
        _setup_frame_type(global_PVs, params)
        if params.recursive_filter == True:
            log.info('    *** Recursive Filter Enabled')
            global_PVs['Proc1_Enable_Background'].put('Disable', wait=True)
            global_PVs['Proc1_Enable_FlatField'].put('Disable', wait=True)
            global_PVs['Proc1_Enable_Offset_Scale'].put('Disable', wait=True)
            global_PVs['Proc1_Enable_Low_Clip'].put('Disable', wait=True)
            global_PVs['Proc1_Enable_High_Clip'].put('Disable', wait=True)

            global_PVs['Proc1_Callbacks'].put('Enable', wait=True)
            global_PVs['Proc1_Filter_Enable'].put('Enable', wait=True)
            global_PVs['HDF1_ArrayPort'].put('PROC1', wait=True)
            global_PVs['Proc1_Filter_Type'].put(Recursive_Filter_Type, wait=True)
            global_PVs['Proc1_Num_Filter'].put(int(params.recursive_filter_n_images), wait=True)
            global_PVs['Proc1_Reset_Filter'].put(1, wait=True)
            global_PVs['Proc1_AutoReset_Filter'].put('Yes', wait=True)
            global_PVs['Proc1_Filter_Callbacks'].put('Array N only', wait=True)
            log.info('    *** Recursive Filter Enabled: Done!')
        else:
            global_PVs['Proc1_Filter_Enable'].put('Disable')
            global_PVs['HDF1_ArrayPort'].put(global_PVs['Cam1_AsynPort'].get(), wait=True)
        global_PVs['HDF1_AutoSave'].put('Yes')
        global_PVs['HDF1_DeleteDriverFile'].put('No')
        global_PVs['HDF1_EnableCallbacks'].put('Enable', wait=True)
        global_PVs['HDF1_BlockingCallbacks'].put('No')

        totalProj = (int(params.num_projections) 
                        + int(params.num_dark_images) + int(params.num_white_images))

        global_PVs['HDF1_NumCapture'].put(totalProj, wait=True)
        global_PVs['HDF1_ExtraDimSizeN'].put(totalProj, wait=True)
        global_PVs['HDF1_FileWriteMode'].put(str(params.file_write_mode), wait=True)
        if fname is not None:
            global_PVs['HDF1_FileName'].put(str(fname), wait=True)
        global_PVs['HDF1_Capture'].put(1)
        aps7bm.wait_pv(global_PVs['HDF1_Capture'], 1)
        log.info('  *** setup hdf_writer: Done!')
    else:
        log.error('Detector %s is not defined' % params.camera_ioc_prefix)
        return


def _setup_frame_type(global_PVs, params):
    global_PVs['Cam1_FrameTypeZRST'].put('/exchange/data')
    global_PVs['Cam1_FrameTypeONST'].put('/exchange/data_dark')
    global_PVs['Cam1_FrameTypeTWST'].put('/exchange/data_white')


def acquire(global_PVs, params):
    # Make sure that we aren't acquiring now
    global_PVs['Cam1_Acquire'].put(DetectorIdle)
    aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle)

    global_PVs['Cam1_FrameType'].put(FrameTypeData, wait=True)
    global_PVs['Cam1_ImageMode'].put('Multiple', wait=True)

    num_images = int(params.num_projections)  * params.recursive_filter_n_images   
    global_PVs['Cam1_NumImages'].put(num_images, wait=True)

    # Set trigger mode
    global_PVs['Cam1_TriggerMode'].put('Overlapped', wait=True)

    # start acquiring
    global_PVs['Cam1_Acquire'].put(DetectorAcquire)
    aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire)

    log.info(' ')
    log.info('  *** Fly Scan: Start!')
    pso.fly(global_PVs, params)

    # if the fly scan wait times out we should call done on the detector
    if aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, 5) == False:
        log.warning('  *** *** Camera did not finish acquisition')
        global_PVs['Cam1_Acquire'].put(DetectorIdle)
    log.info('  *** Fly Scan: Done!')
    # Set trigger mode to internal for post dark and white
    global_PVs['Cam1_TriggerMode'].put('Internal')
    return pso.proj_positions
            

def acquire_flat(global_PVs, params):
    log.info('      *** White Fields')
    # Make sure that we aren't acquiring now
    global_PVs['Cam1_Acquire'].put(DetectorIdle)
    aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle)
    global_PVs['Cam1_ImageMode'].put('Multiple', wait=True)
    global_PVs['Cam1_FrameType'].put(FrameTypeWhite, wait=True)             
    global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)
    num_images = int(params.num_white_images)  * params.recursive_filter_n_images
    global_PVs['Cam1_NumImages'].put(num_images, wait=True)
    wait_time = int(params.num_white_images) * params.exposure_time + 5
    global_PVs['Cam1_Acquire'].put(DetectorAcquire)
    time.sleep(1)
    if aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time):
        log.info('      *** White Fields: Done!')
    else:
        log.error('     *** *** Timeout.')
        raise Exception    


def acquire_dark(global_PVs, params):
    log.info('      *** Dark Fields')
    # Make sure that we aren't acquiring now
    global_PVs['Cam1_Acquire'].put(DetectorIdle)
    aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle)
    global_PVs['Cam1_ImageMode'].put('Multiple', wait=True)
    global_PVs['Cam1_FrameType'].put(FrameTypeDark, wait=True)             
    global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)
    num_images = int(params.num_white_images)  * params.recursive_filter_n_images
    global_PVs['Cam1_NumImages'].put(num_images, wait=True)
    wait_time = int(params.num_dark_images) * params.exposure_time + 5
    global_PVs['Cam1_Acquire'].put(DetectorAcquire)
    time.sleep(1.0)
    if aps7bm.wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time):
        log.info('      *** Dark Fields: Done!')
    else:
        log.error('     *** *** Timeout.')
        raise Exception    


def checkclose_hdf(global_PVs, params):
    ''' Check if the HDF5 file has closed.  Will wait for data to flush to disk.
    '''
    buffer_queue = global_PVs['HDF1_QueueSize'].get() - global_PVs['HDF1_QueueFree'].get()
    frate = 55.0
    wait_on_hdd = buffer_queue / frate + 10
    log.info('  *** Buffer Queue (frames): %d ' % buffer_queue)
    log.info('  *** Wait HDD (s): %f' % wait_on_hdd)
    if aps7bm.wait_pv(global_PVs["HDF1_Capture_RBV"], 0, wait_on_hdd) == False: # needs to wait for HDF plugin queue to dump to disk
        global_PVs["HDF1_Capture"].put(0)
        log.info('  *** File was not closed => forced to close')
        log.info('      *** before %d' % global_PVs["HDF1_Capture_RBV"].get())
        aps7bm.wait_pv(global_PVs["HDF1_Capture_RBV"], 0, 5) 
        log.info('      *** after %d' % global_PVs["HDF1_Capture_RBV"].get())
        if (global_PVs["HDF1_Capture_RBV"].get() == 1):
            log.error('  *** ERROR HDF FILE DID NOT CLOSE; add_theta will fail')


def add_theta(global_PVs, params):
    log.info(' ')
    log.info('  *** add_theta')
    
    fullname = global_PVs['HDF1_FullFileName_RBV'].get(as_string=True)
    theta_arr = pso.proj_positions
    if theta_arr is None:
        return
    try:
        with h5py.File(fullname, mode='a') as hdf_f:
            hdf_f.create_dataset('/exchange/theta', data=theta_arr) 
        log.info('  *** add_theta: Done!')
    except Exception as ee:
        traceback.print_exc(file=sys.stdout)
        log.info('  *** add_theta: Failed accessing: %s' % fullname)
        raise ee


def take_image(global_PVs, params):

    log.info('  *** taking a single image')
   
    nRow = global_PVs['Cam1_SizeY_RBV'].get()
    nCol = global_PVs['Cam1_SizeX_RBV'].get()

    image_size = nRow * nCol

    global_PVs['Cam1_ImageMode'].put('Single', wait=True)
    global_PVs['Cam1_NumImages'].put(1, wait=True)

    global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)
    wait_time_sec = int(params.exposure_time) + 5

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

    return img


def take_flat(global_PVs, params):

    log.info('  *** acquire white')
    return take_image(global_PVs, params)


def take_dark(global_PVs, params):
    
    log.info('  *** acquire dark')
    return take_image(global_PVs, params)


def take_dark_and_white(global_PVs, params, leave_shutter_open=False):
    aps7bm.close_shutters(global_PVs, params)
    dark_field = take_dark(global_PVs, params)
    aps7bm.open_shutters(global_PVs, params)
    scan.move_sample_out(global_PVs, params)
    white_field = take_flat(global_PVs, params)
    scan.move_sample_in(global_PVs, params)
    if not leave_shutter_open:
        aps7bm.close_shutters(global_PVs, params)
    return dark_field, white_field


def calc_max_framerate(global_PVs, params):
    '''Calculates the maximum possible framerate based on the throughput
    of the camera data connection.
    '''
    nRow = global_PVs['Cam1_SizeY_RBV'].get()
    nCol = global_PVs['Cam1_SizeX_RBV'].get()
    data_per_frame = nRow * nCol * 2
    USB3_throughput = 360e6
    return USB3_throughput / data_per_frame
