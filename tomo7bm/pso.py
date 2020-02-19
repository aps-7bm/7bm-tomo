'''Useful functions for PyEPICS scripting.

Alan Kastengren, XSD, APS

Started: February 13, 2015
'''
import epics
import numpy as np
import time
import math

from tomo7bm import log

#Parameters for positioning
req_start = None 
req_end = None
actual_end = None
delta_encoder_counts = None
delta_egu = None
num_proj = None 
num_images_per_proj = None
PSO_positions = None
proj_positions = None
overall_sense = None
motor_start = None
speed = None
user_direction = None


class AerotechDriver():
    def __init__(self, motor='7bmb1:aero:m1', asynRec='7bmb1:PSOFly1:cmdWriteRead', axis='Z', PSOInput=3,encoder_multiply=1e5):
        self.motor = epics.Motor(motor)
        self.asynRec = epics.PV(asynRec + '.BOUT')
        self.axis = axis
        self.PSOInput = PSOInput
        self.encoder_multiply = encoder_multiply

    def program_PSO(self):
        '''Performs programming of PSO output on the Aerotech driver.
        '''
        #Place the motor at the position where the first PSO pulse should be triggered
        self.motor.move(PSO_positions[0], wait=True)

        #Make sure the PSO control is off
        self.asynRec.put('PSOCONTROL %s RESET' % self.axis, wait=True, timeout=300.0)
        time.sleep(0.05)
      
        ## initPSO: commands to the Ensemble to control PSO output.
        # Everything but arming and setting the positions for which pulses will occur.
        #Set the output to occur from the I/O terminal on the controller
        self.asynRec.put('PSOOUTPUT %s CONTROL 1' % self.axis, wait=True, timeout=300.0)
        time.sleep(0.05)
        #Set a pulse 10 us long, 20 us total duration, so 10 us on, 10 us off
        self.asynRec.put('PSOPULSE %s TIME 20,10' % self.axis, wait=True, timeout=300.0)
        time.sleep(0.05)
        #Set the pulses to only occur in a specific window
        self.asynRec.put('PSOOUTPUT %s PULSE WINDOW MASK' % self.axis, wait=True, timeout=300.0)
        time.sleep(0.05)
        #Set which encoder we will use.  3 = the MXH (encoder multiplier) input, which is what we generally want
        self.asynRec.put('PSOTRACK %s INPUT %d' % (self.axis, self.PSOInput), wait=True, timeout=300.0)
        time.sleep(0.05)
        #Set the distance between pulses.  Do this in encoder counts.
        self.asynRec.put('PSODISTANCE %s FIXED %d' % (self.axis, delta_encoder_counts), wait=True, timeout=300.0)
        time.sleep(0.05)
        #Which encoder is being used to calculate whether we are in the window.  1 for single axis
        self.asynRec.put('PSOWINDOW %s 1 INPUT %d' % (self.axis, self.PSOInput), wait=True, timeout=300.0)
        time.sleep(0.05)

        #Calculate window function parameters.  Must be in encoder counts, and is 
        #referenced from the stage location where we arm the PSO.  We are at that point now.
        #We want pulses to start at start - delta/2, end at end + delta/2.  
        range_start = -round(delta_encoder_counts / 2) * overall_sense
        range_length = PSO_positions.shape[0] * delta_encoder_counts
        #The start of the PSO window must be < end.  Handle this.
        if overall_sense > 0:
            window_start = range_start
            window_end = window_start + range_length
        else:
            window_end = range_start
            window_start = window_end - range_length
        #Remember, the window settings must be in encoder counts
        self.asynRec.put('PSOWINDOW %s 1 RANGE %d,%d' % (self.axis, window_start-5, window_end+5), wait=True, timeout=300.0)
        #print('PSOWINDOW %s 1 RANGE %d,%d' % (self.axis, window_start, window_end))
        #Arm the PSO
        time.sleep(0.05)
        self.asynRec.put('PSOCONTROL %s ARM' % self.axis, wait=True, timeout=300.0)
        #Move to the actual start position and set the motor speed
        self.motor.move(motor_start, wait=True)
        self.motor.put('VELO', speed, wait=True)

    def cleanup_PSO(self):
        '''Cleanup activities after a PSO scan. 
        Turns off PSO and sets the speed back to default.
        '''
        log.info('Cleaning up PSO programming and setting to retrace speed.')
        self.asynRec.put('PSOWINDOW %s OFF' % self.axis, wait=True)
        self.asynRec.put('PSOCONTROL %s OFF' % self.axis, wait=True)
        self.motor.put('VELO', self.default_speed, wait=True)
 

driver = AerotechDriver(motor='7bmb1:aero:m3', asynRec='7bmb1:PSOFly3:cmdWriteRead', axis='A', PSOInput=3, encoder_multiply=float(2**15)/0.36)


def _compute_senses():
    '''Computes the senses of motion: encoder direction, motor direction,
    user direction, overall sense.
    '''
    # Encoder direction compared to dial coordinates.  Hard code this; could ask controller
    encoderDir = -1
    #Get motor direction (dial vs. user)
    motor_dir = -1 if driver.motor.direction else 1
    #Figure out whether motion is in positive or negative direction in user coordinates
    global user_direction
    user_direction = 1 if req_end > req_start else -1
    #Figure out overall sense: +1 if motion in + encoder direction, -1 otherwise
    global overall_sense
    overall_sense = user_direction * motor_dir * encoderDir

    
def compute_positions():
    '''Computes several parameters describing the fly scan motion.
    These calculations are for tomography scans, where for N images we need N pulses.
    Moreover, we base these on the number of images, not the delta between.
    '''
    global actual_end, delta_egu, delta_encoder_counts, motor_start, motor_end, PSO_positions
    global proj_positions
    _compute_senses()
    #Get the distance needed for acceleration = 1/2 a t^2 = 1/2 * v * t
    motor_accl_time = driver.motor.acceleration    #Acceleration time in s
    accel_dist = motor_accl_time * speed / 2.0  

    #Compute the actual delta to keep things at an integral number of encoder counts
    raw_delta_encoder_counts = (abs(req_end - req_start) 
                                    / ((num_proj - 1) * num_images_per_proj) * driver.encoder_multiply)
    delta_encoder_counts = round(raw_delta_encoder_counts)
    if abs(raw_delta_encoder_counts - delta_encoder_counts) > 1e-4:
        log.warning('  *** *** *** Requested scan would have used a non-integer number of encoder pulses.')
        log.warning('  *** *** *** Calculated # of encoder pulses per step = {0:9.4f}'.format(raw_delta_encoder_counts))
        log.warning('  *** *** *** Instead, using {0:d}'.format(delta_encoder_counts))
    delta_egu = delta_encoder_counts / driver.encoder_multiply
                
    #Make taxi distance an integral number of measurement deltas >= accel distance
    #Add 1/2 of a delta to ensure that we are really up to speed.
    taxi_dist = (math.ceil(accel_dist / delta_egu) + 0.5) * delta_egu
    motor_start = req_start - taxi_dist * user_direction
    motor_end = req_end + taxi_dist * user_direction
    
    #Where will the last point actually be?
    actual_end = req_start + (num_proj * num_images_per_proj- 1) * delta_egu * user_direction
    end_proj = req_start + (num_proj - 1) * delta_egu * user_direction * num_images_per_proj
    PSO_positions = np.linspace(req_start, actual_end, num_proj * num_images_per_proj)
    proj_positions = np.linspace(req_start, end_proj, num_proj) 
    log_info()

    
def set_default_speed(speed):
    log.info('Setting retrace speed on motor to {0:f} deg/s'.format(float(speed)))
    driver.default_speed = speed


def program_PSO():
    '''Cause the Aerotech driver to program its PSO.
    '''
    log.info('  *** *** Programming motor')
    driver.program_PSO()


def cleanup_PSO():
    driver.cleanup_PSO()

def log_info():
    log.warning('  *** *** Positions for fly scan.')
    log.info('  *** *** *** Motor start = {0:f}'.format(req_start))
    log.info('  *** *** *** Motor end = {0:f}'.format(actual_end))
    log.info('  *** *** *** # Points = {0:4d}'.format(num_proj))
    log.info('  *** *** *** Degrees per image = {0:f}'.format(delta_egu))
    log.info('  *** *** *** Degrees per projection = {0:f}'.format(delta_egu / num_images_per_proj))
    log.info('  *** *** *** Encoder counts per image = {0:d}'.format(delta_encoder_counts))


def pso_init(params):
    '''Initialize calculations.
    '''
    global req_start, req_end, num_proj, num_images_per_proj, speed
    req_start = params.sample_rotation_start
    req_end = params.sample_rotation_end
    num_proj = params.num_projections
    if params.recursive_filter:
        num_images_per_proj = params.recursive_filter_n_images
    else:
        num_images_per_proj = 1
    speed = params.slew_speed
    driver.default_speed = params.retrace_speed
    compute_positions()


def fly(global_PVs, params):
    angular_range =  params.sample_rotation_end -  params.sample_rotation_start
    flyscan_time_estimate = angular_range / params.slew_speed
    log.warning('  *** Fly Scan Time Estimate: %4.2f minutes' % (flyscan_time_estimate/60.))
    #Trigger fly motion to start.  Don't wait for it, since it takes time.
    start_time = time.time()
    driver.motor.move(motor_end, wait=False)
    time.sleep(1)
    old_image_counter = 0
    expected_framerate = driver.motor.slew_speed / delta_egu
    #Monitor the motion to make sure we aren't stuck.
    i = 0
    while time.time() - start_time < 1.5 * flyscan_time_estimate:
        i += 1
        if i % 10 == 0:
            log.info('  *** *** Sample rotation at angle {:f}'.format(driver.motor.readback))
        time.sleep(1)
        if not driver.motor.moving:
            log.info('  *** *** Sample rotation stopped moving.')
            if abs(driver.motor.drive - motor_end) > 1e-2:
                log.error('  *** *** Sample rotation ended but not at right position!')
                raise ValueError
            else:
                log.info('  *** *** Stopped at correct position.')
                break
        #Make sure we're actually getting frames.
        current_image_counter = global_PVs['Cam1_NumImagesCounter'].get()
        if current_image_counter - old_image_counter < 0.2 * expected_framerate:
            log.error('  *** *** Not collecting frames!')
            raise ValueError 
        else:
            old_image_counter = current_image_counter
    else:
        log.warning('  *** *** Fly motion timed out!')
        raise ValueError
