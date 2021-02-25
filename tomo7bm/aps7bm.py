'''
    Epics PV definition for Sector 7-BM  
    
'''
import time

from epics import PV, Motor
from tomo7bm import log

TESTING = True

ShutterA_Open_Value = 0
ShutterA_Close_Value = 1
Recursive_Filter_Type = 'Average'
EPSILON = 0.1


def wait_pv(pv, wait_val, max_timeout_sec=-1):
    ''' Wait on a PV to reach a value.
    max_timeout_sec is an optional timeout time.
    '''
    time.sleep(.01)
    startTime = time.time()
    while True:
        pv_val = pv.get()
        if type(pv_val) == float:
            if abs(pv_val - wait_val) < EPSILON:
                return True
        if (pv_val != wait_val):
            if max_timeout_sec > -1:
                curTime = time.time()
                diffTime = curTime - startTime
                if diffTime >= max_timeout_sec:
                    log.error('  *** ERROR: DROPPED IMAGES ***')
                    log.error('  *** wait_pv(%s, %d, %5.2f reached max timeout. Return False' % (pv.pvname, wait_val, max_timeout_sec))
                    return False
            time.sleep(.01)
        else:
            return True


def make_pv(prefix, name):
    '''Read a text field that contains a PV name.  Make it into a PV object.
    '''
    print(prefix + name)
    name_pv = PV(prefix + name)
    value = PV(name_pv.get(as_string=True))
    log.info(value)
    return value 

   
def init_general_PVs(params):
    '''Initialize epics PV objects.
    '''
    global_PVs = {}
    log.info('Creating PV objects.')

    # shutter pv's
    global_PVs['ShutterA_Open'] = make_pv(params.tomoscan_prefix, 'OpenShutterPVName')
    global_PVs['ShutterA_Close'] = make_pv(params.tomoscan_prefix, 'CloseShutterPVName') 

    global_PVs['PixelSizeMicrons'] = PV(params.tomoscan_prefix + 'DetectorPixelSize')
    global_PVs['Actual_Pixel_Size'] = PV(params.tomoscan_prefix + 'ImagePixelSize')
    global_PVs['Motor_SampleX'] = make_pv(params.tomoscan_prefix, 'SampleXPVName')
    global_PVs['Move_Sample_Out'] = PV(params.tomoscan_prefix + 'MoveSampleOut')
    global_PVs['Move_Sample_In'] = PV(params.tomoscan_prefix + 'MoveSampleIn')
    sample_rot_name = PV(params.tomoscan_prefix + 'RotationPVName').get(as_string=True)
    global_PVs['Motor_SampleRot'] = Motor(sample_rot_name)

    # detector pv's
    params.camera_ioc_prefix = PV(params.tomoscan_prefix + 'CameraPVPrefix').get(as_string=True)
    log.info('Using camera IOC with prefix {:s}'.format(params.camera_ioc_prefix))
    update_pixel_size(global_PVs, params)
    params.exposure_time = PV(params.tomoscan_prefix + 'ExposureTime').get()
    params.bright_exposure_time = PV(params.tomoscan_prefix + 'FlatExposureTime').get()
    params.diff_bright_exposure = PV(params.tomoscan_prefix + 'DifferentFlatExposure').get(as_string=True)
    # init Point Grey PV's
    # general PV's
    global_PVs['Cam1_SerialNumber'] = PV(params.camera_ioc_prefix + 'cam1:SerialNumber_RBV')
    global_PVs['Cam1_ImageMode'] = PV(params.camera_ioc_prefix + 'cam1:ImageMode')
    global_PVs['Cam1_TriggerMode'] = PV(params.camera_ioc_prefix + 'cam1:TriggerMode')
    global_PVs['Cam1_AcquireTime'] = PV(params.camera_ioc_prefix + 'cam1:AcquireTime')
    global_PVs['Cam1_NumImages'] = PV(params.camera_ioc_prefix + 'cam1:NumImages')
    global_PVs['Cam1_Acquire'] = PV(params.camera_ioc_prefix + 'cam1:Acquire')

    global_PVs['Cam1_SizeX'] = PV(params.camera_ioc_prefix + 'cam1:SizeX')
    global_PVs['Cam1_SizeY'] = PV(params.camera_ioc_prefix + 'cam1:SizeY')
    global_PVs['Cam1_SizeX_RBV'] = PV(params.camera_ioc_prefix + 'cam1:SizeX_RBV')
    global_PVs['Cam1_SizeY_RBV'] = PV(params.camera_ioc_prefix + 'cam1:SizeY_RBV')
    global_PVs['Cam1_Image'] = PV(params.camera_ioc_prefix + 'image1:ArrayData')
    global_PVs['Cam1_Image_Dtype'] = PV(params.camera_ioc_prefix + 'image1:DataType_RBV')


    global TESTING
    TESTING = params.testing
    log.info(TESTING)
    return global_PVs


def open_shutters(global_PVs, params):
    log.info(' ')
    log.info('  *** open_shutters')
    if params.testing == True:
        log.warning('  *** testing mode - shutters are deactivated during the scans !!!!')
    else:
        global_PVs['ShutterA_Open'].put(1, wait=True)
        time.sleep(3)
        log.info('  *** open_shutter A: Done!')
 

def close_shutters(global_PVs, params):
    log.info(' ')
    log.info('  *** close_shutters')
    if params.testing == True:
        log.warning('  *** testing mode - shutters are deactivated during the scans !!!!')
    else:
        global_PVs['ShutterA_Close'].put(1, wait=True)
        time.sleep(3)
        log.info('  *** close_shutter A: Done!')
