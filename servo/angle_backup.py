from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

pigpio_factory = PiGPIOFactory()

azimuthServo = AngularServo(18, min_angle=-135, max_angle=135, min_pulse_width=0.0005, max_pulse_width=0.0025, pin_factory=pigpio_factory)
Az = 0
azimuthServo.angle = float(Az)

elevationServo = AngularServo(19, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025, pin_factory=pigpio_factory)
El = 0
elevationServo.angle = float(El)

while (True):
	Az = input("azimuth: ")
	if (Az != "") and (-135 <= float(Az) <= 135):
		Az = float(Az)
		azimuthServo.angle = float(Az)

	El = input("elevation: ")
	if (El != "") and (-80 <= float(El) <= 80):
		El = float(El)
		elevationServo.angle = float(El)
