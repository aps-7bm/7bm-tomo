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


def init_general_PVs(params):
    '''Initialize epics PV objects.
    '''
    global_PVs = {}
    log.info('Creating PV objects.')

    # shutter pv's
    global_PVs['ShutterA_Open'] = PV('7bma1:rShtrA:Open')
    global_PVs['ShutterA_Close'] = PV('7bma1:rShtrA:Close')
    global_PVs['ShutterA_Move_Status'] = PV('PB:07BM:STA_A_FES_CLSD_PL.VAL')

    # Experimment Info
    global_PVs['Sample_Name'] = PV('7bmb1:ExpInfo:SampleName')
    global_PVs['Sample_Description'] = PV('7bmb1:ExpInfo:SampleDescription.VAL')
    global_PVs['User_Badge'] = PV('7bmb1:ExpInfo:UserBadge.VAL')
    global_PVs['User_Email'] = PV('7bmb1:ExpInfo:UserEmail.VAL')
    global_PVs['User_Institution'] = PV('7bmb1:ExpInfo:UserInstitution.VAL')
    global_PVs['Proposal_Number'] = PV('7bmb1:ExpInfo:ProposalNumber.VAL')
    global_PVs['Proposal_Title'] = PV('7bmb1:ExpInfo:ProposalTitle.VAL')
    global_PVs['User_Info_Update'] = PV('7bmb1:ExpInfo:UserInfoUpdate.VAL')
    global_PVs['Lens_Magnification'] = PV('7bmb1:ExpInfo:LensMagFloat.VAL')
    global_PVs['Scintillator_Type'] = PV('7bmb1:ExpInfo:ScintillatorType.VAL')
    global_PVs['Scintillator_Thickness'] = PV('7bmb1:ExpInfo:ScintillatorThickness.VAL')
    global_PVs['Camera_IOC_Prefix'] = PV('7bmb1:ExpInfo:CameraIOCPrefix.VAL')
    global_PVs['PixelSizeMicrons'] = PV('7bmb1:ExpInfo:PixelSizeum.VAL')
    global_PVs['Filters'] = PV('7bmb1:ExpInfo:Filters.VAL')
    global_PVs['File_Name'] = PV('7bmb1:ExpInfo:FileName.VAL')
    global_PVs['Station'] = PV('7bmb1:ExpInfo:Station.VAL')
    global_PVs['Remote_Data_Trasfer'] = PV('7bmb1:ExpInfo:RemoteDataTrasfer.VAL')
    global_PVs['Remote_Analysis_Dir'] = PV('7bmb1:ExpInfo:RemoteAnalysisDir.VAL')
    global_PVs['User_Last_Name'] = PV('7bmb1:ExpInfo:UserLastName.VAL')
    global_PVs['Experiment_Year_Month'] = PV('7bmb1:ExpInfo:ExperimentYearMonth.VAL')
    global_PVs['Use_Furnace'] = PV('7bmb1:ExpInfo:UseFurnace.VAL')
    global_PVs['White_Field_Motion'] = PV('7bmb1:ExpInfo:WhiteFieldMotion.VAL')
    global_PVs['Num_White_Images'] = PV('7bmb1:ExpInfo:NumWhiteImages.VAL')
    global_PVs['Bright_Exp_Time'] = PV('7bmb1:ExpInfo:BrightExposureTime.VAL')
    global_PVs['Sample_Detector_Distance'] = PV('7bmb1:ExpInfo:SampleDetectorDistance.VAL')
    global_PVs['Sample_Out_Position_Y'] = PV('7bmb1:ExpInfo:SampleOutPositionY.VAL')
    global_PVs['Sample_Out_Position_X'] = PV('7bmb1:ExpInfo:SampleOutPositionX.VAL')
    global_PVs['Num_Projections'] = PV('7bmb1:ExpInfo:NumProjections.VAL')
    global_PVs['Sample_Rotation_Start'] = PV('7bmb1:ExpInfo:SampleRotationStart.VAL')
    global_PVs['Sample_Rotation_End'] = PV('7bmb1:ExpInfo:SampleRotationEnd.VAL')
    global_PVs['Sample_Rotation_Speed'] = PV('7bmb1:ExpInfo:SampleRotationSpeed.VAL')
    global_PVs['Sample_Retrace_Speed'] = PV('7bmb1:ExpInfo:RetraceSpeed.VAL')
    global_PVs['Furnace_In_Position'] = PV('7bmb1:ExpInfo:FurnaceInPosition.VAL')
    global_PVs['Furnace_Out_Position'] = PV('7bmb1:ExpInfo:FurnaceOutPosition.VAL')
    global_PVs['Scan_Type'] = PV('7bmb1:ExpInfo:ScanType.VAL')
    global_PVs['Sleep_Time'] = PV('7bmb1:ExpInfo:SleepTime.VAL')
    global_PVs['Scan_Replicates'] = PV('7bmb1:ExpInfo:ScanReplicates.VAL')
    global_PVs['Vertical_Scan_Start'] = PV('7bmb1:ExpInfo:VerticalScanStart.VAL')
    global_PVs['Vertical_Scan_End'] = PV('7bmb1:ExpInfo:VerticalScanEnd.VAL')
    global_PVs['Vertical_Scan_Step_Size'] = PV('7bmb1:ExpInfo:VerticalScanStepSize.VAL')
    global_PVs['Horizontal_Scan_Start'] = PV('7bmb1:ExpInfo:HorizontalScanStart.VAL')
    global_PVs['Horizontal_Scan_End'] = PV('7bmb1:ExpInfo:HorizontalScanEnd.VAL')
    global_PVs['Horizontal_Scan_Step_Size'] = PV('7bmb1:ExpInfo:HorizontalScanStepSize.VAL')

    params.station = global_PVs['Station'].get(as_string=True)
    log.info('Running in station {:s}.'.format(params.station))
    if params.station == '7-BM-B':
        log.info('*** Running in station 7-BM-B:')
        # Set sample stack motor:
        global_PVs['Motor_SampleX'] = Motor('7bmb1:aero:m2')
        global_PVs['Motor_SampleY'] = Motor('7bmb1:aero:m1')
        global_PVs['Motor_SampleRot'] = Motor('7bmb1:aero:m3') # Aerotech ABR-250
        global_PVs['Motor_Focus'] = Motor('7bmb1:m38')
    else:
        log.error('*** %s is not a valid station' % params.station)

    # detector pv's
    params.valid_camera_prefixes = ['7bm_pg1:', '7bm_pg2:', '7bm_pg3:', '7bm_pg4:']
    params.camera_ioc_prefix = global_PVs['Camera_IOC_Prefix'].get(as_string=True)
    if params.camera_ioc_prefix[-1] != ':':
        params.camera_ioc_prefix = params.camera_ioc_prefix + ':'
    log.info('Using camera IOC with prefix {:s}'.format(params.camera_ioc_prefix))
    if params.camera_ioc_prefix in params.valid_camera_prefixes:
        update_pixel_size(global_PVs, params)
        # init Point Grey PV's
        # general PV's
        global_PVs['Cam1_SerialNumber'] = PV(params.camera_ioc_prefix + 'cam1:SerialNumber')
        global_PVs['Cam1_AsynPort'] = PV(params.camera_ioc_prefix + 'cam1:PortName_RBV')
        global_PVs['Cam1_ImageMode'] = PV(params.camera_ioc_prefix + 'cam1:ImageMode')
        global_PVs['Cam1_ArrayCallbacks'] = PV(params.camera_ioc_prefix + 'cam1:ArrayCallbacks')
        global_PVs['Cam1_AcquirePeriod'] = PV(params.camera_ioc_prefix + 'cam1:AcquirePeriod')
        global_PVs['Cam1_TriggerMode'] = PV(params.camera_ioc_prefix + 'cam1:TriggerMode')
        global_PVs['Cam1_SoftwareTrigger'] = PV(params.camera_ioc_prefix + 'cam1:SoftwareTrigger')  ### ask Mark is this is exposed in the medm screen
        global_PVs['Cam1_AcquireTime'] = PV(params.camera_ioc_prefix + 'cam1:AcquireTime')
        global_PVs['Cam1_FrameType'] = PV(params.camera_ioc_prefix + 'cam1:FrameType')
        global_PVs['Cam1_NumImages'] = PV(params.camera_ioc_prefix + 'cam1:NumImages')
        global_PVs['Cam1_NumImagesCounter'] = PV(params.camera_ioc_prefix + 'cam1:NumImagesCounter_RBV')
        global_PVs['Cam1_Acquire'] = PV(params.camera_ioc_prefix + 'cam1:Acquire')
        global_PVs['Cam1_AttributeFile'] = PV(params.camera_ioc_prefix + 'cam1:NDAttributesFile')
        global_PVs['Cam1_FrameTypeZRST'] = PV(params.camera_ioc_prefix + 'cam1:FrameType.ZRST')
        global_PVs['Cam1_FrameTypeONST'] = PV(params.camera_ioc_prefix + 'cam1:FrameType.ONST')
        global_PVs['Cam1_FrameTypeTWST'] = PV(params.camera_ioc_prefix + 'cam1:FrameType.TWST')
        global_PVs['Cam1_Display'] = PV(params.camera_ioc_prefix + 'image1:EnableCallbacks')

        global_PVs['Cam1_SizeX'] = PV(params.camera_ioc_prefix + 'cam1:SizeX')
        global_PVs['Cam1_SizeY'] = PV(params.camera_ioc_prefix + 'cam1:SizeY')
        global_PVs['Cam1_SizeX_RBV'] = PV(params.camera_ioc_prefix + 'cam1:SizeX_RBV')
        global_PVs['Cam1_SizeY_RBV'] = PV(params.camera_ioc_prefix + 'cam1:SizeY_RBV')
        global_PVs['Cam1_MaxSizeX_RBV'] = PV(params.camera_ioc_prefix + 'cam1:MaxSizeX_RBV')
        global_PVs['Cam1_MaxSizeY_RBV'] = PV(params.camera_ioc_prefix + 'cam1:MaxSizeY_RBV')
        global_PVs['Cam1PixelFormat_RBV'] = PV(params.camera_ioc_prefix + 'cam1:PixelFormat_RBV')
        global_PVs['Cam1_Image_Dtype'] = PV(params.camera_ioc_prefix + 'image1:DataType_RBV')
        global_PVs['Cam1_Image'] = PV(params.camera_ioc_prefix + 'image1:ArrayData')

        # hdf5 writer PV's
        global_PVs['HDF1_AutoSave'] = PV(params.camera_ioc_prefix + 'HDF1:AutoSave')
        global_PVs['HDF1_DeleteDriverFile'] = PV(params.camera_ioc_prefix + 'HDF1:DeleteDriverFile')
        global_PVs['HDF1_EnableCallbacks'] = PV(params.camera_ioc_prefix + 'HDF1:EnableCallbacks')
        global_PVs['HDF1_BlockingCallbacks'] = PV(params.camera_ioc_prefix + 'HDF1:BlockingCallbacks')
        global_PVs['HDF1_FileWriteMode'] = PV(params.camera_ioc_prefix + 'HDF1:FileWriteMode')
        global_PVs['HDF1_NumCapture'] = PV(params.camera_ioc_prefix + 'HDF1:NumCapture')
        global_PVs['HDF1_Capture'] = PV(params.camera_ioc_prefix + 'HDF1:Capture')
        global_PVs['HDF1_Capture_RBV'] = PV(params.camera_ioc_prefix + 'HDF1:Capture_RBV')
        global_PVs['HDF1_FilePath'] = PV(params.camera_ioc_prefix + 'HDF1:FilePath')
        global_PVs['HDF1_FileName'] = PV(params.camera_ioc_prefix + 'HDF1:FileName')
        global_PVs['HDF1_FullFileName_RBV'] = PV(params.camera_ioc_prefix + 'HDF1:FullFileName_RBV')
        global_PVs['HDF1_FileTemplate'] = PV(params.camera_ioc_prefix + 'HDF1:FileTemplate')
        global_PVs['HDF1_ArrayPort'] = PV(params.camera_ioc_prefix + 'HDF1:NDArrayPort')
        global_PVs['HDF1_FileNumber'] = PV(params.camera_ioc_prefix + 'HDF1:FileNumber')
        global_PVs['HDF1_XMLFileName'] = PV(params.camera_ioc_prefix + 'HDF1:XMLFileName')
        global_PVs['HDF1_ExtraDimSizeN'] = PV(params.camera_ioc_prefix + 'HDF1:ExtraDimSizeN')

        global_PVs['HDF1_QueueSize'] = PV(params.camera_ioc_prefix + 'HDF1:QueueSize')
        global_PVs['HDF1_QueueFree'] = PV(params.camera_ioc_prefix + 'HDF1:QueueFree')
                                                                      
        # proc1 PV's
        global_PVs['Image1_Callbacks'] = PV(params.camera_ioc_prefix + 'image1:EnableCallbacks')
        global_PVs['Proc1_Callbacks'] = PV(params.camera_ioc_prefix + 'Proc1:EnableCallbacks')
        global_PVs['Proc1_ArrayPort'] = PV(params.camera_ioc_prefix + 'Proc1:NDArrayPort')
        global_PVs['Proc1_Filter_Enable'] = PV(params.camera_ioc_prefix + 'Proc1:EnableFilter')
        global_PVs['Proc1_Filter_Type'] = PV(params.camera_ioc_prefix + 'Proc1:FilterType')
        global_PVs['Proc1_Num_Filter'] = PV(params.camera_ioc_prefix + 'Proc1:NumFilter')
        global_PVs['Proc1_Reset_Filter'] = PV(params.camera_ioc_prefix + 'Proc1:ResetFilter')
        global_PVs['Proc1_AutoReset_Filter'] = PV(params.camera_ioc_prefix + 'Proc1:AutoResetFilter')
        global_PVs['Proc1_Filter_Callbacks'] = PV(params.camera_ioc_prefix + 'Proc1:FilterCallbacks')       

        global_PVs['Proc1_Enable_Background'] = PV(params.camera_ioc_prefix + 'Proc1:EnableBackground')
        global_PVs['Proc1_Enable_FlatField'] = PV(params.camera_ioc_prefix + 'Proc1:EnableFlatField')
        global_PVs['Proc1_Enable_Offset_Scale'] = PV(params.camera_ioc_prefix + 'Proc1:EnableOffsetScale')
        global_PVs['Proc1_Enable_Low_Clip'] = PV(params.camera_ioc_prefix + 'Proc1:EnableLowClip')
        global_PVs['Proc1_Enable_High_Clip'] = PV(params.camera_ioc_prefix + 'Proc1:EnableHighClip')

    elif (params.camera_ioc_prefix == '2bmbSP1:'):
        global_PVs['Cam1_AcquireTimeAuto'] = PV(params.camera_ioc_prefix + 'cam1:AcquireTimeAuto')
        global_PVs['Cam1_FrameRateOnOff'] = PV(params.camera_ioc_prefix + 'cam1:FrameRateEnable')

        global_PVs['Cam1_TriggerSource'] = PV(params.camera_ioc_prefix + 'cam1:TriggerSource')
        global_PVs['Cam1_TriggerOverlap'] = PV(params.camera_ioc_prefix + 'cam1:TriggerOverlap')
        global_PVs['Cam1_ExposureMode'] = PV(params.camera_ioc_prefix + 'cam1:ExposureMode')
        global_PVs['Cam1_TriggerSelector'] = PV(params.camera_ioc_prefix + 'cam1:TriggerSelector')
        global_PVs['Cam1_TriggerActivation'] = PV(params.camera_ioc_prefix + 'cam1:TriggerActivation')
    
    else:
        log.error('Detector %s is not defined' % params.camera_ioc_prefix)
        return            
    global TESTING
    TESTING = params.testing
    user_info_update(global_PVs, params)
    if params.update_from_PVs:
        update_params_from_PVs(global_PVs, params)      
    return global_PVs


def user_info_update(global_PVs, params):
    params.proposal_title = global_PVs['Proposal_Title'].get(as_string=True)
    params.user_email = global_PVs['User_Email'].get(as_string=True)
    params.user_badge = global_PVs['User_Badge'].get(as_string=True)
    params.user_last_name = global_PVs['User_Last_Name'].get(as_string=True)
    params.proposal_number = global_PVs['Proposal_Number'].get(as_string=True)
    params.user_institution = global_PVs['User_Institution'].get(as_string=True)
    params.experiment_year_month = global_PVs['Experiment_Year_Month'].get(as_string=True)
    params.user_info_update = global_PVs['User_Info_Update'].get(as_string=True)


def open_shutters(global_PVs, params):
    log.info(' ')
    log.info('  *** open_shutters')
    if TESTING:
        log.warning('  *** testing mode - shutters are deactivated during the scans !!!!')
    else:
        global_PVs['ShutterA_Open'].put(1, wait=True)
        wait_pv(global_PVs['ShutterA_Move_Status'], ShutterA_Open_Value)
        log.info('  *** open_shutter A: Done!')
 

def close_shutters(global_PVs, params):
    log.info(' ')
    log.info('  *** close_shutters')
    if TESTING:
        log.warning('  *** testing mode - shutters are deactivated during the scans !!!!')
    else:
        global_PVs['ShutterA_Close'].put(1, wait=True)
        wait_pv(global_PVs['ShutterA_Move_Status'], ShutterA_Close_Value)
        log.info('  *** close_shutter A: Done!')


def update_pixel_size(global_PVs, params):
    '''Uses the camera model number to set the correct pixel size.
    '''
    if params.camera_ioc_prefix in ['7bm_pg1:', '7bm_pg2:', '7bm_pg3:']:
        global_PVs['PixelSizeMicrons'].put(5.86, wait=True)
        log.info('Camera pixel size for this camera = 5.86 microns.')
    elif params.camera_ioc_prefix == '7bm_pg4:':
        global_PVs['PixelSizeMicrons'].put(3.45, wait=True)
        log.info('Camera pixel size for this camera = 3.45 microns.')


def update_params_from_PVs(global_PVs, params):
    '''Update values of params to values from global_PVs.
    '''
    log.info('  *** Updating parameters from PVs')
    params.num_white_images = global_PVs['Num_White_Images'].get()
    params.num_dark_images = global_PVs['Num_White_Images'].get()
    params.sleep_steps = global_PVs['Scan_Replicates'].get()
    params.lens_magnification = global_PVs['Lens_Magnification'].get()
    params.resolution = global_PVs['PixelSizeMicrons'].get()
    params.scintillator_type = global_PVs['Scintillator_Type'].get(as_string=True)
    params.scintillator_thickness = global_PVs['Scintillator_Thickness'].get()
    params.exposure_time = global_PVs['Cam1_AcquireTime'].get()
    params.bright_exposure_time = global_PVs['Bright_Exp_Time'].get()
    params.sample_rotation_start = global_PVs['Sample_Rotation_Start'].get()
    params.sample_rotation_end = global_PVs['Sample_Rotation_End'].get()
    params.num_projections = global_PVs['Num_Projections'].get()
    params.retrace_speed = global_PVs['Sample_Retrace_Speed'].get()
    params.vertical_scan_start = global_PVs['Vertical_Scan_Start'].get()
    params.vertical_scan_end = global_PVs['Vertical_Scan_End'].get()
    params.vertical_scan_step_size = global_PVs['Vertical_Scan_Step_Size'].get()
    params.horizontal_scan_start = global_PVs['Horizontal_Scan_Start'].get()
    params.horizontal_scan_end = global_PVs['Horizontal_Scan_End'].get()
    params.horizontal_scan_step_size = global_PVs['Horizontal_Scan_Step_Size'].get()
    params.sample_out_x = global_PVs['Sample_Out_Position_X'].get()
    params.sample_out_y = global_PVs['Sample_Out_Position_Y'].get()
