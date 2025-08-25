from gpiozero import AngularServo
from time import sleep
import smbus
import os

ADDR = 0x2d
LOW_VOL = 3150 #mV

low = 0
bus = smbus.SMBus(1)

azimuthServo = AngularServo(18, min_angle=-135, max_angle=135, min_pulse_width=0.0005, max_pulse_width=0.0025)
Az = 0
azimuthServo.angle = float(Az)

elevationServo = AngularServo(19, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
El = 0
elevationServo.angle = float(El)

while (True):
    Az = input("azimuth: ")
    if (Az != "") and (-135 <= float(Az) <= 135):
        Az = float(Az)
        azimuthServo.angle = float(Az)

    El = input("elevation: ")
    if (El != "") and (-90 <= float(El) <= 90):
        El = float(El)
        elevationServo.angle = float(El)
    '''for i in range(10):
        data = bus.read_i2c_block_data(ADDR, 0x20, 0x0C)
        current = (data[2] | data[3] << 8)
        if(current > 0x7FFF):
            current -= 0xFFFF
        print("Battery Current %d mA"%current)
        sleep(0.1)'''
    print("")

